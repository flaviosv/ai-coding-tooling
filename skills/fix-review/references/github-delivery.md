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

## Replying to a Thread (GitHub Mode Step 6)

```
gh api graphql -f query='
  mutation($threadId: ID!, $body: String!) {
    addPullRequestReviewThreadReply(input: { pullRequestReviewThreadId: $threadId, body: $body }) {
      comment { id }
    }
  }' -f threadId="<PRRT_... thread id>" -f body="<reply text>"
```

## Resolving a Thread (GitHub Mode Step 6)

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
