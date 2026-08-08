GitHub operations `ship-spec` needs beyond what `code-review`/`tests-code-review` already cover (fetching a PR diff, posting pending review comments) — opening the PR itself, and the comment-triage round. Load this file at Step 5 (open PR) and at Comment-Triage Mode steps 1 and 5.

## Opening the Draft PR (Step 5)

Preferred — `gh`:

```
gh pr create --draft --base <base> --head feature/<task_id> --title "<title>" --body "<body>"
```

Fallback — GitHub MCP: use the MCP server's pull-request-creation tool with the same fields (`draft: true`, `base`, `head`, `title`, `body`).

Fallback — `gh api graphql` (only if neither of the above is available):

```
gh api graphql -f query='
  mutation($repoId: ID!, $base: String!, $head: String!, $title: String!, $body: String!) {
    createPullRequest(input: {
      repositoryId: $repoId, baseRefName: $base, headRefName: $head,
      title: $title, body: $body, draft: true
    }) { pullRequest { number url } }
  }' -f repoId="<repository node id>" -f base="<base>" -f head="feature/<task_id>" -f title="<title>" -f body="<body>"
```

Get the repository node id first with `gh api graphql -f query='{ repository(owner:"<owner>", name:"<repo>") { id } }'`.

## Fetching Review Threads (Comment-Triage Step 1)

REST does not expose threaded review conversations — use GraphQL `reviewThreads`:

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
              nodes { id body path line author { login } }
            }
          }
        }
      }
    }
  }' -f owner="<owner>" -f repo="<repo>" -F pr=<pr number>
```

Skip nodes where `isResolved: true`. Each surviving node's `id` (a `PRRT_...` thread id) is what Step 5 (reply) and Step 6 (resolve) below need.

## Replying to a Thread

```
gh api graphql -f query='
  mutation($threadId: ID!, $body: String!) {
    addPullRequestReviewThreadReply(input: { pullRequestReviewThreadId: $threadId, body: $body }) {
      comment { id }
    }
  }' -f threadId="<PRRT_... thread id>" -f body="<reply text>"
```

## Resolving a Thread

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
