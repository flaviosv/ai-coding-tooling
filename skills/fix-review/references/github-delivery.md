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

## Replying to Threads (GitHub Mode Step 6)

Every reply this run posts belongs to **one** review. `addPullRequestReviewThreadReply` called without a `pullRequestReviewId` makes GitHub wrap each reply in a review of its own, auto-submitted — a run that answers five threads leaves five separate `flaviosv reviewed` entries on the PR instead of one. Batch them: resolve or create a single pending review, thread every reply into it, submit it once at the end.

Skip this whole section when the run has no replies to post — never create a review just to leave it empty.

**1. Resolve the PR node id and your own existing pending review, in one query:**

```
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!, $me: String!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        id
        reviews(first: 1, states: PENDING, author: $me) {
          nodes { id comments(first: 1) { totalCount } }
        }
      }
    }
  }' -f owner="<owner>" -f repo="<repo>" -F pr=<pr number> -f me="<gh login>"
```

`$me` comes from `gh api user --jq .login`. A non-empty `reviews.nodes` is your own unsubmitted review — reuse its `id` in step 3 rather than creating a second one. If its `comments.totalCount` is non-zero it already holds draft comments that step 4's submit will publish alongside this run's replies; say so in the final report.

**2. Create the pending review, only if step 1 found none:**

```
gh api graphql -f query='
  mutation($prId: ID!) {
    addPullRequestReview(input: { pullRequestId: $prId }) { pullRequestReview { id } }
  }' -f prId="<PR_... node id>"
```

`event` omitted → the review stays pending, which is what lets the replies accumulate in it.

**3. Post each reply into that review** — one call per thread, `pullRequestReviewId` always set:

```
gh api graphql -f query='
  mutation($reviewId: ID!, $threadId: ID!, $body: String!) {
    addPullRequestReviewThreadReply(input: { pullRequestReviewId: $reviewId, pullRequestReviewThreadId: $threadId, body: $body }) {
      comment { id }
    }
  }' -f reviewId="<PRR_... review id>" -f threadId="<PRRT_... thread id>" -f body="<reply text>"
```

**4. Submit the review once, after the last reply** — replies stay invisible to everyone else until this runs:

```
gh api graphql -f query='
  mutation($reviewId: ID!) {
    submitPullRequestReview(input: { pullRequestReviewId: $reviewId, event: COMMENT }) {
      pullRequestReview { state }
    }
  }' -f reviewId="<PRR_... review id>"
```

`event: COMMENT` only — never `APPROVE` or `REQUEST_CHANGES`. This skill fixes findings; passing verdict on the PR isn't its call.

If the submit fails, leave every thread unresolved and report it — the replies survive as a recoverable pending review, a thread resolved with nothing visible on it doesn't.

## Resolving a Thread (GitHub Mode Step 6)

Only after the submit in the previous section succeeded — a thread resolved while its reply is still pending reads as closed with nothing said on it.

```
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: { threadId: $threadId }) {
      thread { isResolved }
    }
  }' -f threadId="<PRRT_... thread id>"
```

Requires Contents: Read and Write permission on the token/app being used — if this fails with a permissions error, report it rather than silently leaving the thread unresolved.

MCP fallback: if the GitHub MCP server exposes review-thread reply/resolve tools, prefer those over raw `gh api graphql` for consistency with how the rest of the session reaches GitHub. As of this skill's authoring, no such MCP tools were available in this project's session — treat the GraphQL commands above as the primary path, not a fallback, until that changes.
