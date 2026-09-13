# GitHub Writes

Every write this skill makes to GitHub — posting a pending review, submitting it, replying to and resolving threads — goes through `scripts/github_review.py`. This file covers what you compose (comment bodies, delivery files), the one read you run yourself (the thread fetch), how to invoke the script, and what its output means. Loaded by the review stage for a PR target and by the fix stage for a PR.

---

## Rules

- **Never hand-roll a GitHub write.** No inline `gh api graphql` mutation, no `gh pr review`, no `gh pr comment`, no REST reply endpoint, no top-level PR comment. Each of those has either failed silently on a real run or cannot act on the `PRRT_…` thread ids resolving requires. If the script is missing or exits `2`, the run is **blocked** — report its raw JSON.
- **The script's JSON is the result.** Every count you report — posted, submitted, replied, resolved, re-anchored, unpostable — is quoted from its stdout, never from what you intended to send. Exit `0` confirmed, `1` partial (report exactly which items), `2` fatal (nothing confirmed).
- **Never re-run `post` to read its output again.** Re-running is safe against duplicates (it skips comments already on the review), but the first run's JSON is the record — capture it.
- **Never create GitHub Issues.** Every finding is an inline review thread.
- **Never delete** a pending review, a review comment, or a thread this skill created — including a duplicate review comment `post` reports. Report it and let a human remove it. The one exception is a duplicate **thread reply** `deliver` reports in `duplicates_found`: delete each extra reply (`gh api -X DELETE repos/<owner>/<repo>/pulls/comments/<comment id>`, one call each — there is no batch delete), then re-run `deliver`.
- **Never post placeholder, test, or probe content to a real review** — a pending review is visible to anyone with repo access the moment it exists. Use `--dry-run` to check a run before any write.
- **Never touch another identity's pending review.** The script only reads and extends the authenticated identity's own (`author: $me`).
- **The review stage never replies to or resolves existing threads**; only the fix stage does, through `deliver`.
- **The verdict is always `COMMENT`.** `submit` never approves or requests changes.
- **Secondary rate limits are per account.** Several PR runs under one `gh` identity at once compound them. On an abuse block the script waits 180 s (at most twice) and continues; it never resends a batch without a fresh fetch first. Never work around a slow run with a bulk REST call.
- **Batch size is 10 by default, not a tuned constant.** If the caller or user names a different size, pass `--batch-size N` to `post` and `deliver` — never silently revert to 10 or auto-tune down after a failure.
- Never print `gh auth token` output or any credential.
- Write every input file with the `Write` tool — never a shell heredoc (a worktree-isolated session refuses those).

## Script Location

`~/.claude/skills/code-review/scripts/github_review.py` — a symlink to this skill; the OS follows it. If and only if that path does not exist, the skill is installed project-locally: `.claude/skills/code-review/scripts/github_review.py`. Never `find` for it and never rewrite it as a repo-relative path.

## Comment Shape

Each finding becomes one comment: `path`, `line`, `side` (omit for `RIGHT`), `body`, `anchor`.

**Body** — open with the finding's tag from the zoned report, never bare prose:

```
**[<Zone/Dimension> — <Finding ID>, <Severity>]** <explanation>

**Recommendation:** <concrete, actionable fix>
```

- Zone and Finding ID are carried verbatim from the report (`A1`, `Q3`, `V2`) — never renumbered for GitHub.
- The `Recommendation` line is mandatory. A finding phrased as a question still closes with a concrete action; a clarification request names the action to take once answered ("If X, remove Y; if Z, document why").
- Pass bodies verbatim — `%`, backticks, and quotes need no escaping, since the script passes arguments without a shell.

**`line`** is the line in the file at the PR head commit — never an offset into a diff or patch. An agent reviewing a `.diff` resolves it from the hunk header `@@ -a,b +c,d @@` or a bounded `grep -n` of the anchor text.

**`anchor`** is the exact text of that line, copied verbatim: one line, trimmed, no ellipsis, no paraphrase. The agent already has the file open when it writes the finding, so copying costs nothing. Without it the publisher cannot trust `line` and re-derives it the expensive way — measured across four real runs, that verification pass re-read 20–31 source files, 13–35% of the step's token cost and 2.1–4.0 minutes of critical path. A finding whose line cannot be resolved returns `line: null` with `anchor` populated; `post` resolves it. **Never `Read` whole source files to check line numbers** — `post` checks every anchor itself.

## Review Stage: `post`

1. Write `post.json`:
   ```
   {"owner": "<owner>", "repo": "<repo>", "pr": <N>,
    "comments": [{"path": "src/a.py", "line": 18, "body": "**[Security — S1, High]** ...", "anchor": "..."}]}
   ```
   Every finding left after Step 8's duplicate collapse — unfiltered, never by severity.
2. `python3 ~/.claude/skills/code-review/scripts/github_review.py post post.json`

What it does, in order: resolves the login, the PR, and this identity's existing pending review (`author: $me` — never another identity's); fetches the PR's diff hunks (`gh api repos/{owner}/{repo}/pulls/{N}/files --paginate --slurp`); checks each `anchor` against the file at the head commit, correcting `line` when the text sits elsewhere and marking the comment **unpostable** when the text is found nowhere; re-anchors a comment outside every hunk to the nearest in-hunk line of that file with a first line naming its true location (GitHub silently discards an out-of-hunk thread — `200`, a real id, no comment — which lost 9 of 44 findings on two real runs); marks a comment on a file the PR never touched **unpostable**; skips comments whose exact path, line, and body are already on the review; creates the pending review only if none exists; adds threads in batches of 10, 1 s apart. A per-alias GraphQL error skips only that comment. It then fetches the review again and retries, once, only comments from a request that failed as a whole — never one that returned `200` but didn't persist, and never one with its own alias error — then reconciles.

| Output field | Meaning |
|---|---|
| `anchor_corrected` | Line changed to where the anchor text actually is |
| `carried_over` | Comments already on this identity's pending review before this run |
| `duplicates_found` | Same comment on the review more than once — report, never delete |
| `missing` | Intended but not on the review after the retry |
| `posted_confirmed` | Threads confirmed added by the final fetch |
| `reanchored` | Moved into a hunk; the body names the real location |
| `errors` | Per-request or per-alias failures; a `request_failed` entry's comments were retried once |
| `unpostable` | Not posted (file not in the PR, no hunk data, anchor not found) — carry every one into the report by `path:line` |

`--dry-run` runs everything up to the first write and reports `would_post`.

## Checkpoint: `submit`

`python3 ~/.claude/skills/code-review/scripts/github_review.py submit <owner> <repo> <N>`

Submits this identity's pending review as `COMMENT` and confirms the state changed. No pending review (the user already submitted it), or a pending review with no comments left (the user deleted them all) → exit `0` with `"submitted": false` — continue; the fix stage fetches whatever is published.

## Fix Stage: Fetch Threads

The one read you run yourself. Run it exactly as written — real runs that improvised it got `review` instead of `pullRequestReview`, `-f` instead of `-F` for the `Int!` PR number (*"Could not coerce value to Int"*), and a heredoc form the worktree guard refuses.

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
  }' -f owner="<owner>" -f repo="<repo>" -F pr=<N>
```

Skip nodes where `isResolved: true`, and nodes whose comments all have `pullRequestReview.state: PENDING` (an unsubmitted review). Each surviving node's `id` (`PRRT_…`) is what `deliver` needs, and its `comments` array is the full exchange in order — read all of it. A thread a human deleted no longer exists here, which is what makes "only what remains is a finding" hold.

## Fix Stage: `deliver`

1. Write `delivery.json`:
   ```
   {"owner": "<owner>", "repo": "<repo>", "pr": <N>,
    "threads": {"PRRT_xxx": {"body": "<reply text>", "resolve": true}},
    "skipped": {"PRRT_yyy": "routed to @alice — awaiting her answer"}}
   ```
   **`threads` and `skipped` together must account for every in-scope thread** (published, not resolved). Every thread you reply to goes in `threads`; every thread you leave alone goes in `skipped` with a real reason.
2. `python3 ~/.claude/skills/code-review/scripts/github_review.py deliver delivery.json --dry-run` — checks coverage before any write.
3. The same command without `--dry-run`.

What it does: fetches a baseline; replies in batches of 10, 5 s apart; fetches again and confirms each reply landed exactly once; resolves only threads whose reply is confirmed, 1 s apart; fetches again to confirm `isResolved`. Re-running after a partial failure is safe — it skips threads that already carry your reply. A failed-looking request (`502`, truncated response, timeout) may have landed, which is why nothing is retried without a fresh fetch: one real run retried two such batches blind and posted 20 duplicate replies.

| Output field | Meaning |
|---|---|
| `duplicates_found` | A thread carries more than one reply from this run |
| `in_scope` | Published, unresolved threads on the PR |
| `replied_confirmed` / `resolved_confirmed` | Confirmed by re-fetch |
| `reply_missing` / `resolve_not_confirmed` | Intended but not on GitHub |
| `thread_page_truncated` | A thread had 100+ comments; say more may exist |
| `unaccounted` | In-scope threads in neither map — go back and classify them; never report around them |
| `unknown_threads` | Ids in `threads` that don't exist on the PR |

Resolving needs Contents: Read and Write permission on the token; a permissions error is reported, never left silent.
