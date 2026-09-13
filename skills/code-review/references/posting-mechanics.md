# Posting Mechanics

The only procedure this skill uses to write to GitHub — every publish (a `post: true` run, a Publish request, a user's "post 1, 3, 5" after a local report, Batch Mode, and the delta merge after a new commit) goes through exactly these steps. Self-contained: a publishing worker is handed this file's absolute path and reads it whole, never a line range of `SKILL.md`.

---

## Invariants

- **Pending state only.** Never submit, approve, or request changes. The user submits manually on GitHub.
- **Never create GitHub Issues.** Every finding is an inline PR review thread anchored to its line — never a top-level PR comment, never at the top of a file.
- **One pending review per identity per PR** (a GitHub rule). Growing one is always an append via GraphQL, never a delete-and-recreate.
- **Never touch a pending review authored by a different identity** than the one `gh` is authenticated as — that is a human reviewer mid-draft.
- **Never delete a pending review this skill created or is appending to, or any comment on it** — including duplicates this skill itself produced. Report them and let a human remove them. If the whole thing genuinely needs redoing, stop and ask.
- **Never reply to or resolve existing review threads** — triaging prior comments is `fix-review`'s job.
- **Secondary rate limit.** GitHub's abuse-detection limit (HTTP 403, "secondary rate limit" / "temporarily blocked from content creation") is scoped per authenticated account, not per repo or call — it compounds when several PRs post under the same identity around the same moment. A single bulk REST `POST .../reviews` with many comments reliably tripped it (80 in one payload failed on every attempt across 26 minutes; ≤20 always worked), which is why this procedure never issues that call and batches instead. Never fall back to a bulk POST to speed up a slow batch loop.
- **A short comment count means suspect the anchor before pagination.** GitHub silently discards a thread anchored outside the PR's diff hunks (step 3a); pagination (list endpoints default to 30 per page) is the rarer cause, and checking it first sends a run down a dead end — one real run lost 9 of 44 findings this way.
- Never print `gh auth token` output or any credential value — refer to auth state by status only.

## Comment Shape

Each finding becomes one comment: `path`, `line`, `side` (default `RIGHT` when a finding carries none), `body`, plus the `anchor` a dimension agent returned.

**Body format (required, no exceptions)** — open with the finding's structured tag from the zoned report, never bare prose:

```
**[<Zone/Dimension> — <Finding ID>, <Severity>]** <explanation>

**Recommendation:** <concrete, actionable fix>
```

- `<Zone/Dimension>` and `<Finding ID>` are carried verbatim from the zoned report (e.g. `A1`, `Q3`, `S2`, `C1`, `V3`, `G2`) — never renumbered or renamed for GitHub.
- `<Severity>` is Critical / High / Medium / Low, matching the report row.
- **The `Recommendation` line is mandatory on every comment.** A finding phrased as a question still closes with a concrete action; a genuine clarification request phrases it as the action to take once answered ("If X, remove Y; if Z, document why it's needed").
- A comment carried over from an already-pending review that predates this format (e.g. a bare human-authored draft) stays as-is — never retrofit a tag onto content this skill didn't generate.

This applies uniformly — Requirements, Coverage-Gap, and Performance-Audit-style findings included.

**`line` is the line in the file at the PR head commit — never an offset into a diff, patch, or split-diff artifact.** An agent reviewing a `.diff`/`.patch` resolves each finding back to its source line: the hunk header `@@ -a,b +c,d @@` gives the base, or a bounded `grep -n '<anchor text>' <file>` finds it directly. Posting anchors on these values without re-deriving them.

**`anchor` is the exact text of the line the finding points at**, copied verbatim — one line, trimmed, no ellipsis, no paraphrase. The agent already has the file open when it writes the finding, so copying costs nothing there. Without it the publisher cannot trust `line` and re-derives it the expensive way: measured across four real runs, every merge step invented a verification pass re-reading 20–31 source files — **13–35% of that step's token cost and 2.1–4.0 minutes of critical path**, with 21k–102k tokens of context inflation re-billed on every remaining turn. Two agents in that sample had returned diff-relative offsets. A finding whose line genuinely cannot be resolved returns `line: null` with `anchor` still populated.

**Verify with the anchor, never by re-reading files.** To confirm a doubted finding's `line`, `grep -n` its anchor text in its file and compare — one bounded call per doubted finding. If anchor and line disagree, trust the anchor. If `line` is `null`, the anchor resolves it. If neither resolves, the finding is unpostable (step 3a). **Never `Read` whole source files to check line numbers.**

## Procedure

REST's `POST .../reviews` only creates a review with its full comment set in one call — there is no REST way to add to an existing one, which once forced a delete-and-recreate that was never atomic (a repost failing right after a successful delete left a PR with **zero** pending comments). GraphQL supports true incremental appends — confirmed against GitHub's live schema (`AddPullRequestReviewThreadInput.pullRequestReviewId`: *"The Node ID of the review to modify"*).

1. **Resolve the PR's node ID and any existing pending review, in one query:**
   ```
   gh api graphql -f query='
     query($owner: String!, $repo: String!, $pr: Int!, $me: String!) {
       repository(owner: $owner, name: $repo) {
         pullRequest(number: $pr) {
           id
           reviews(first: 1, states: PENDING, author: $me) {
             nodes {
               id
               comments(first: 100) {
                 nodes { path line body }
                 pageInfo { hasNextPage endCursor }
               }
             }
           }
         }
       }
     }' -f owner={owner} -f repo={repo} -F pr={PR} -f me={gh_login}
   ```
   `$me` comes from `gh api user --jq .login`. A non-empty `reviews.nodes` is the authenticated identity's own pending review — reuse its `id` in step 3. If `pageInfo.hasNextPage` is true, page with `after` before trusting the comment count for dedup.

   **The `author: $me` argument is not cosmetic** — it is the only thing enforcing the never-touch-another-identity invariant. If you rewrite this query (inlining literals instead of variables, which step 3b can push you toward), keep the author filter, or select `author { login }` and discard every node whose login isn't the authenticated identity. A real run dropped the filter while inlining literals; nothing went wrong only because no other pending review existed.

2. **Create an empty pending review, only if step 1 found none:**
   ```
   gh api graphql -f query='
     mutation($prId: ID!) {
       addPullRequestReview(input: { pullRequestId: $prId }) { pullRequestReview { id } }
     }' -f prId={pull_request_node_id}
   ```
   `event` omitted → pending state. Zero threads at creation; every comment is added in step 3.

3. **Append findings in batches of 10, one GraphQL request per batch, at least 1 second apart** (GitHub's documented remedy for bulk writes, applied per request). Never one request per finding. 10 is the **standing default, not a tuned constant** — it sits inside the ≤20 the REST data always cleared. If the caller or user names a different batch size, use it; never silently revert to 10 or auto-tune down after a failure.

   Alias one `addPullRequestReviewThread` per finding in a single mutation document — exactly as many aliases as the batch has (fewer on the last batch, never padded):
   ```
   gh api graphql -f query='
     mutation(
       $reviewId: ID!,
       $path0: String!, $line0: Int!, $side0: DiffSide!, $body0: String!,
       $path1: String!, $line1: Int!, $side1: DiffSide!, $body1: String!,
       ... one $pathN/$lineN/$sideN/$bodyN set per finding in this batch ...
     ) {
       c0: addPullRequestReviewThread(input: { pullRequestReviewId: $reviewId, path: $path0, line: $line0, side: $side0, body: $body0 }) { thread { id } }
       c1: addPullRequestReviewThread(input: { pullRequestReviewId: $reviewId, path: $path1, line: $line1, side: $side1, body: $body1 }) { thread { id } }
       ... one cN alias per finding ...
     }' -f reviewId={review_id} -f path0={path} -F line0={line} -f side0={side} -f body0={body} ...
   ```
   Before batching, leave out any finding whose exact `path`+`line`+`body` already exists on the review (step 1's paginated fetch).

   **3a. Validate every anchor against the PR's diff hunks first.** GitHub silently discards a thread anchored outside the PR's diff — `200`, no `errors`, a real thread id, and the comment never exists. Two real runs lost 9 of 44 findings each this way, one a Critical. Get the changed lines (`gh api repos/{owner}/{repo}/pulls/{PR}/files --jq '.[].patch'`, or `git diff <merge-base>...HEAD -- <path>`) and check each finding's `path`+`line` against the `+`/context lines of an actual hunk:
   - Inside a hunk → post as-is.
   - Outside every hunk, but the file has hunks → **re-anchor** to the nearest in-hunk line of that file, opening the body with its true location (e.g. *"This concerns `config.go:18`, outside this PR's diff — anchored here for visibility."*).
   - The file has no hunks (the PR never touched it) → **unpostable**. Don't attempt it; carry it to the report by `path:line` so it reaches a human. A finding never exists only in a run's chat summary.

   **3b. Issuing the call.** Put the whole mutation and every value inline in one plain `Bash` call. Forms confirmed failing on real runs:
   - `-f query=@file` — `gh` does not expand `@path` for the query (`Expected one of SCHEMA, SCALAR, ...`).
   - `-f query="$(cat file)"` — refused by the worktree-isolation guard ("runs gh with a value computed at runtime").
   - wrapping the call in `zsh post_batch.sh` — blocked by the Claude Code permission classifier.
   - `-F lineN:Int=73` — `gh` rejects the annotation; pass bare `-F lineN=73`.
   - `export GH_TOKEN=$(gh auth token …)` on its own line — refused; use the inline prefix `GH_TOKEN=$(gh auth token --user <login>) gh api graphql …`.
   - a `cat > file <<EOF` heredoc — refused on command shape. Use the `Write` tool for any file you need.

   **Never re-issue a posting mutation, for any reason — including to re-read its output.** `addPullRequestReviewThread` is not idempotent; one run re-sent a batch to read its error more clearly and duplicated 9 comments that could not be cleaned up. Capture the response on the first call.

   **Never post placeholder, test, or probe content to a real review** — one run left a literal "Test comment - …" on a PR for ~35 seconds. Validate a mutation's shape against a read-only query instead. Pass bodies verbatim: `%` is a literal `%` in `-F body=` — never `printf`-escape it to `%%`.

4. **Failure shapes per batch — each handled differently:**
   - **The whole request fails** (secondary rate limit 403, or any transport failure): nothing in the batch was created. Retry the identical batch once after 60 seconds, once more after 5 minutes; if it still fails, skip the batch, note which findings didn't post, and continue. Never abort the run over one batch, never delete the review because of it.
   - **200 with a per-alias `errors` entry** (a bad `line`/`path` on one finding): the other aliases succeeded. Skip just the failed one and continue — don't retry or discard the batch.
   - **200 with a real thread id, but the comment never persists**: the silent hunk-drop. Don't retry — it anchors to the same invalid line and vanishes again. Step 3a prevents it; step 6 catches it.
   - **The request never reaches GitHub** — a local permission prompt or classifier denial, recognisable by error text naming the harness and no HTTP status. No rate limit involved: retry the identical batch once immediately; if refused again, continue with the remaining batches and return to it at the end. Say in the report which batch posted out of sequence.

   Report every skipped finding, of any shape.

5. **Never delete** the pending review or any comment on it — see Invariants.

6. **Reconcile what actually landed — mandatory, not a spot check.** After the last batch, re-query the review's comment count and compare it to the number intended:
   ```
   gh api graphql -f query='
     query($owner: String!, $repo: String!, $pr: Int!, $me: String!) {
       repository(owner: $owner, name: $repo) {
         pullRequest(number: $pr) {
           reviews(first: 1, states: PENDING, author: $me) {
             nodes { comments(first: 100) { totalCount } }
           }
         }
       }
     }' -f owner={owner} -f repo={repo} -F pr={PR} -f me={gh_login}
   ```
   Report a mismatch explicitly, never rounded to the intended number. This is the only check that catches a silently-dropped thread or a duplicate — the runs that lost 9 of 44 findings discovered it here, and only because the agent ran it unprompted.

## Confirm

Report: comments added to the pending review, comments carried over from an existing one, re-anchored and unpostable counts, any skipped or out-of-sequence batch, the PR link, and: "Review is pending — submit manually on GitHub."
