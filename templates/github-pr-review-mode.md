---
name: github-pr-review-mode
description: Shared GitHub PR mode workflow for review skills — detection (Step A) and posting (Step B).
type: template
---

## Step A: GitHub PR Mode Detection

1. Extract the PR number from the user's message.
2. **GitHub MCP is mandatory for all GitHub PR operations.** Do NOT use the `gh` CLI for fetching PR data or diffs — ever.
3. Fetch PR metadata and diff using the GitHub MCP tools: get PR details, changed files, and diff content.
4. If the GitHub MCP is unavailable or fails, stop immediately and inform the user — do not attempt any `gh` fallback.

---

## Step B: Post Findings to GitHub PR

Runs **only** when the user explicitly requests after reviewing findings locally.

### B1. User Selects Findings

Wait for user to specify which findings to post:
- By number: "post 1, 3, 5"
- By filter: "post all", "post all P0", "post all Critical"

### B2. Create Pending Review Comments

**GitHub MCP is mandatory.** Do NOT use the `gh` CLI — not even as a fallback.

**NEVER create GitHub Issues.** All findings must be posted as inline PR review comments — never as standalone issues. This is a hard requirement with no exceptions.

Use the GitHub MCP tool for creating pull request reviews. Pass selected comments as inline review comments with `PENDING` event. Each comment must be anchored to the **exact line number** identified in the finding — never posted as a top-level PR comment or at the top of the file.

If the GitHub MCP is unavailable, stop and inform the user — do not attempt any `gh` workaround.

### B3. Confirm Result

Report:
- Number of comments added to pending review
- Link to the PR
- Reminder: "Review is pending — submit manually on GitHub."

**Never submit the review.** No `APPROVE`, `REQUEST_CHANGES`, or `COMMENT` event. Pending only.
