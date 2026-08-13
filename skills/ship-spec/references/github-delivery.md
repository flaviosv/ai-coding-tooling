GitHub operations `ship-spec` needs beyond what `complete-review`/`fix-review` already cover — opening the PR itself. Load this file at Step 5 (open PR).

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
