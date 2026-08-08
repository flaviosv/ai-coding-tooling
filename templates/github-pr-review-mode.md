---
name: github-pr-review-mode
description: Shared GitHub PR mode workflow for review skills — detection (Step A) and posting (Step B).
type: template
---

## Step A: GitHub PR Mode Detection

1. Extract the PR number from the user's message.
2. **Prefer the `gh` CLI when available and authenticated.** Check with `gh auth status`; if it succeeds, use `gh` for all GitHub PR operations in this session. Fall back to the GitHub MCP tools only if `gh` is not installed or not authenticated.
3. Fetch PR metadata and diff:
   - **Via `gh`**: `gh pr view <PR> --json title,body,baseRefName,headRefName,files` for metadata and changed files; `gh pr diff <PR>` for the diff content.
   - **Via GitHub MCP** (fallback): get PR details, changed files, and diff content using the MCP tools.
4. If neither `gh` nor the GitHub MCP is available, stop immediately and inform the user.

---

## Step B: Post Findings to GitHub PR

Runs **only** when the user explicitly requests after reviewing findings locally.

### B1. User Selects Findings

Wait for user to specify which findings to post:
- By number: "post 1, 3, 5"
- By filter: "post all", "post all P0", "post all Critical"

### B2. Create Pending Review Comments

**Use the same tool selected in Step A** (`gh` if it was available and authenticated, otherwise GitHub MCP) for consistency within the session.

**NEVER create GitHub Issues.** All findings must be posted as inline PR review comments — never as standalone issues. This is a hard requirement with no exceptions.

- **Via `gh`**: `gh api repos/{owner}/{repo}/pulls/{PR}/reviews --method POST --input payload.json`, where `payload.json` holds the `comments` array (each with `path`, `line`, `body`) and **omits the `event` field entirely** — omitting `event` is what leaves the review in `PENDING` state; passing `event: PENDING` is not a valid value and will error. Each comment must be anchored to the **exact line number** identified in the finding — never posted as a top-level PR comment or at the top of the file.
- **Via GitHub MCP** (fallback): use the MCP tool for creating pull request reviews. Pass selected comments as inline review comments with `PENDING` event, each anchored to the exact line number.

If neither `gh` nor the GitHub MCP is available, stop and inform the user.

### B3. Confirm Result

Report:
- Number of comments added to pending review
- Link to the PR
- Reminder: "Review is pending — submit manually on GitHub."

**Never submit the review.** No `APPROVE`, `REQUEST_CHANGES`, or `COMMENT` event. Pending only.
