---
name: github-pr-review-mode
description: Shared GitHub PR mode workflow for review skills — detection (Step A) and posting (Step B).
type: template
---

## Step A: GitHub PR Mode Detection

1. Extract the PR number from the user's message.
2. Check if GitHub MCP tools are available in the current session (search for tools matching `github`, `pull_request`, `gh`). MCP is preferred — it respects per-project configuration.
3. Fetch PR metadata and diff:
   - **MCP available**: use the GitHub MCP tools to get PR details, changed files, and diff content.
   - **MCP unavailable**: fall back to `gh` CLI:
     ```bash
     gh pr view <number> --json title,body,baseRefName,headRefName,files
     gh pr diff <number>
     ```
4. If both MCP and `gh` fail, report the error and stop.

---

## Step B: Post Findings to GitHub PR

Runs **only** when the user explicitly requests after reviewing findings locally.

### B1. User Selects Findings

Wait for user to specify which findings to post:
- By number: "post 1, 3, 5"
- By filter: "post all", "post all P0", "post all Critical"

### B2. Create Pending Review Comments

Use GitHub MCP tools if available (preferred), fall back to `gh` CLI.

**Using GitHub MCP**: use the MCP tool for creating pull request reviews. Pass selected comments as inline review comments with `PENDING` event.

**Using `gh` CLI fallback**:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/reviews \
  --input - <<'EOF'
{
  "event": "PENDING",
  "comments": [
    {"path": "<file>", "line": <line>, "body": "**[Severity/Priority]** Title\n\nExplanation\n\n**Suggestion:** fix"}
  ]
}
EOF
```

Parse `{owner}/{repo}` from `gh repo view --json nameWithOwner -q '.nameWithOwner'`.

### B3. Confirm Result

Report:
- Number of comments added to pending review
- Link to the PR
- Reminder: "Review is pending — submit manually on GitHub."

**Never submit the review.** No `APPROVE`, `REQUEST_CHANGES`, or `COMMENT` event. Pending only.
