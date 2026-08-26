GitHub operations `fix-review` needs for GitHub Mode — fetching review threads, replying, and resolving. Load this file at GitHub Mode steps 1 and 6.

REST does not expose threaded review conversations — everything here uses GraphQL.

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

## Batching the Writes (GitHub Mode Step 6)

Both write operations below take a single thread id per call, but a GraphQL document can carry many aliased mutations — so **10 per request** is the unit here, not one. Never loop one request per thread when several are ready; a lone reply is simply a batch of one. Pace batches at least 1 second apart, GitHub's own documented remedy for bulk writes.

These rules apply to every batch on this page:

- Build the document with exactly as many aliases as the batch holds — 10, or fewer on the last one. Never pad it.
- GraphQL resolves each alias independently, so a `200` carrying an `errors` entry for one alias still means the rest succeeded. Skip the failed one, keep the others, report it — never retry or discard a whole batch over one bad alias.
- If the whole request fails (secondary rate-limit `403`, transport error), none of that batch landed: retry the identical batch once after 60 seconds, then skip it and report exactly which threads it covered. Never abort the run over one failed batch.
- 10 is the standing default, matching `complete-review`'s own posting batch size. If the user names a different size, use theirs — don't silently revert or auto-tune down after a failure.

## Replying to Threads (GitHub Mode Step 6)

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

## Resolving Threads (GitHub Mode Step 6)

Batch the same way, and only for threads whose reply landed above — a thread whose reply failed stays open.

```
gh api graphql -f query='
  mutation($thread0: ID!, $thread1: ID!, ... one $threadN per thread in this batch ...) {
    r0: resolveReviewThread(input: { threadId: $thread0 }) { thread { isResolved } }
    r1: resolveReviewThread(input: { threadId: $thread1 }) { thread { isResolved } }
    ... one rN alias per thread ...
  }' -f thread0="<PRRT_... thread id>" -f thread1="<PRRT_...>" ...
```

Requires Contents: Read and Write permission on the token/app being used — if this fails with a permissions error, report it rather than silently leaving the threads unresolved.

MCP fallback: if the GitHub MCP server exposes review-thread reply/resolve tools, prefer those for a **single** operation, for consistency with how the rest of the session reaches GitHub. For more than one, stay on the aliased GraphQL batches above — one MCP call per thread is exactly the one-by-one loop this page exists to avoid. As of this skill's authoring, no such MCP tools were available in this project's session anyway.
