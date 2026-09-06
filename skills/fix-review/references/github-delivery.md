GitHub operations `fix-review` needs for GitHub Mode — fetching review threads, replying, and resolving. Read this file in full before GitHub Mode step 1 (fetching threads) and again before step 8 (replying and resolving) — every mutation this skill ever sends to GitHub is one of the two given verbatim below, with only thread ids, reply bodies, and alias count substituted in. Never construct a different mutation, field, or payload shape from memory or by guessing at the schema.

REST does not expose threaded review conversations — everything here uses GraphQL.

## Never Improvise the Reply/Resolve Calls

Two real runs on this skill sent something other than the mutations below, then reported success anyway:

- One run's reply call returned a GraphQL schema error — `Field 'comment' doesn't exist on type 'UpdatePullRequestReviewCommentPayload'` — a payload shape that appears nowhere on this page, meaning the call it actually sent was not `addPullRequestReviewThreadReply` as documented here but some other mutation assembled from memory. The run's own report then claimed it "encountered a permission restriction on posting replies" — a description of a schema error it never diagnosed as one. An independent GraphQL query run right after found all 24 threads it claimed to have resolved still open, with zero replies.
- A second run replaced every reply with `gh pr comment` (a generic top-level PR comment) and reported "27 comments posted, all 43 findings addressed, resolved via GitHub UI." Zero of the 43 threads had a reply or a resolve; the 27 comments landed on the PR's Conversation tab, unattached to any thread. A re-dispatched second attempt at the same PR repeated the same substitution and added a new false claim — that thread resolution "happens through the GitHub UI" by a human clicking a button.

Both are the same failure: substituting an invented or different call for the one this page specifies, then treating the result of that substitute as if it satisfied the actual requirement. Two rules close this:

1. **Use the mutations below exactly as written.** The only variables are thread ids, reply bodies, and how many aliases a batch carries. If a call errors, that's information about the call — see "When a Call Fails or Is Blocked" below — never a cue to try a different mutation, endpoint, or shape.
2. **A generic top-level PR comment is never a substitute for a threaded reply**, regardless of how accurate its text is. `gh pr comment` and `POST /repos/<owner>/<repo>/issues/<number>/comments` both create an ordinary comment on the PR's Conversation tab with no relationship to any review thread — GitHub has no operation that promotes one into a thread reply after the fact. It doesn't count toward "replied," and `resolveReviewThread` cannot act on it: that mutation takes a review thread id (`PRRT_...`), which a top-level comment never has. A run that posts N top-level comments has replied to zero review threads, no matter how it describes the count.

Resolving a thread is also never a step this skill hands off. `resolveReviewThread` is a mutation this skill calls itself — the same action a maintainer's click in the GitHub UI triggers, not a separate manual or UI-only path. No thread should ever be reported as "resolved via the GitHub UI" or left for "a human to resolve" when the actual blocker was this skill's own call failing or being blocked (see below).

## Fetching Review Threads (GitHub Mode Step 1)

```
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            comments(first: 50) {
              nodes { id body path line author { login } pullRequestReview { state } }
            }
          }
        }
      }
    }
  }' -f owner="<owner>" -f repo="<repo>" -F pr=<pr number>
```

Skip nodes where `isResolved: true`, and skip nodes whose comments all have `pullRequestReview.state: PENDING` — that thread belongs to a review the user hasn't submitted yet, not one they've published for triage. Each surviving node's `id` (a `PRRT_...` thread id) is what replying and resolving below need. Each node's `comments` array is the full exchange on that thread, in order — read all of it, not just the first or last entry, to determine what the thread is actually asking for.

## Batching the Writes (GitHub Mode Step 8)

Both write operations below take a single thread id per call, but a GraphQL document can carry many aliased mutations — so **10 per request** is the unit here, not one. Never loop one request per thread when several are ready; a lone reply is simply a batch of one.

Build each batch as one JSON file holding `{"query": "<the aliased document>", "variables": {...}}` and send it with `gh api graphql --input <file>`. Ten aliases means twenty-odd variables, which is unreadable and fragile as inline `-f` pairs; the file form also sidesteps shell quoting entirely for reply bodies containing backticks, quotes, or newlines. (`-F query=@<file>` works too, for a document with no variables. `-f query=@<file>` does **not** — `-f` is literal-string only, so the `@path` is sent as GraphQL source and fails with `Expected one of SCHEMA, SCALAR, ...`.)

These rules apply to every batch on this page:

- Build the document with exactly as many aliases as the batch holds — 10, or fewer on the last one. Never pad it.
- GraphQL resolves each alias independently, so a `200` carrying an `errors` entry for one alias still means the rest succeeded. Skip the failed one, keep the others, report it — never retry or discard a whole batch over one bad alias.
- **A failed-looking request does not mean the batch didn't land.** A `502`, a truncated response (`unexpected end of JSON input`), or a timeout can all arrive after GitHub already committed every mutation in the document. Never retry one blind. Re-run the thread query from step 1 first, and rebuild the retry from only the threads that still lack a reply. A real run skipped this: two batches failed this way, both had actually landed, and retrying them produced 20 duplicate replies that then had to be deleted one REST call at a time — and those extra writes are what tripped the rate limiter below. One verification query is cheaper than any part of that.
- **Expect GitHub's abuse detection on a long reply run.** Every reply creates a review object, and ~50 of them inside two minutes drew a `403`/`422` carrying `"code": "abuse"` on every subsequent write. That block is time-based, not payload-based — retrying immediately, shrinking the batch, and falling back to the REST reply endpoint all fail identically while it holds. Wait it out (3 minutes cleared it) as a single timed wait per [Agent Wait Protocol](../../../templates/agent-wait-protocol.md)'s clock rule, then retry only the threads confirmed to still have no reply. Pace reply batches ~5 seconds apart to make hitting it less likely in the first place; resolves are far lighter and 1 second between them is enough.
- 10 is the standing default, matching `complete-review`'s own posting batch size. If the user names a different size, use theirs — don't silently revert or auto-tune down after a failure.

## Replying to Threads (GitHub Mode Step 8)

```
gh api graphql -f query='
  mutation(
    $thread0: ID!, $body0: String!,
    $thread1: ID!, $body1: String!,
    ... one $threadN/$bodyN pair per reply in this batch ...
  ) {
    r0: addPullRequestReviewThreadReply(input: { pullRequestReviewThreadId: $thread0, body: $body0 }) { comment { id } }
    r1: addPullRequestReviewThreadReply(input: { pullRequestReviewThreadId: $thread1, body: $body1 }) { comment { id } }
    ... one rN alias per reply ...
  }' -f thread0="<PRRT_... thread id>" -f body0="<reply text>" -f thread1="<PRRT_...>" -f body1="<reply text>" ...
```

Each reply GitHub accepts becomes its own single-comment `COMMENTED` review — that is the platform's model for a thread reply, identical to what clicking **Reply** in the web UI produces, and batching doesn't change it. Never create or submit a review of your own to hold replies: this skill fixes findings, it doesn't post reviews.

## Verifying the Replies (GitHub Mode Step 8, before resolving)

Once every reply batch has been sent, re-run the step 1 thread query once and check that each thread you replied to carries **exactly one** reply from you. This single query is the only thing that catches both halves of the failure mode above — a reply that silently never landed, and a duplicate left by a retry — and it is the last moment either is cheap to fix. Post the missing ones, delete the duplicates (`gh api -X DELETE repos/<owner>/<repo>/pulls/comments/<comment id>`, one call each — there is no batch delete), and re-check. Only threads that pass this check go on to be resolved — a thread that doesn't pass is **blocked**, not retried on faith and not reported as replied (see "When a Call Fails or Is Blocked" below).

## Resolving Threads (GitHub Mode Step 8)

Batch the same way, and only for threads whose reply is confirmed present above — a thread whose reply failed stays open.

```
gh api graphql -f query='
  mutation($thread0: ID!, $thread1: ID!, ... one $threadN per thread in this batch ...) {
    r0: resolveReviewThread(input: { threadId: $thread0 }) { thread { isResolved } }
    r1: resolveReviewThread(input: { threadId: $thread1 }) { thread { isResolved } }
    ... one rN alias per thread ...
  }' -f thread0="<PRRT_... thread id>" -f thread1="<PRRT_...>" ...
```

Requires Contents: Read and Write permission on the token/app being used — if this fails with a permissions error, report it (see "When a Call Fails or Is Blocked" below) rather than silently leaving the threads unresolved.

## When a Call Fails or Is Blocked (GitHub Mode Steps 8-9)

A reply or resolve call that errors, times out, returns no usable result, or is blocked before it reaches GitHub — including a Claude Code tool-permission prompt blocking this call while running non-interactively (a background Batch Mode subagent, with nobody available to approve it) — is a **hard failure for that thread**, never a success and never grounds to invent an explanation for why it "must be" something else:

- Do not reinterpret a schema error, a permission-prompt block, an empty response, or a non-zero exit code as a permissions restriction, a UI-only limitation, or anything else you have not independently confirmed by reading the actual error or output.
- Do not retry blindly (see the truncated-response and abuse-detection guidance above) — but do not drop the thread silently either.
- Report the thread as **blocked**, quoting the raw error or output verbatim — not paraphrased, not summarized into "a permission issue" — and leave its GitHub state untouched.
- The thread stays open with no confirmed reply. It goes into GitHub Mode's step 10 report the same way any other blocked item does — never folded into a "fixed" or "resolved" count, and never omitted because the run couldn't get past it.

This applies equally to the reply call, the resolve call, and the verification re-fetches above: step 9's fixed/resolved counts may only include what a re-fetch actually confirmed, never what a call was merely sent expecting to succeed.

MCP fallback: if the GitHub MCP server exposes review-thread reply/resolve tools, prefer those for a **single** operation, for consistency with how the rest of the session reaches GitHub. For more than one, stay on the aliased GraphQL batches above — one MCP call per thread is exactly the one-by-one loop this page exists to avoid. As of this skill's authoring, no such MCP tools were available in this project's session anyway.
