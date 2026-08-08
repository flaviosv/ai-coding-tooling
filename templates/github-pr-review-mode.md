---
name: github-pr-review-mode
description: Shared GitHub PR mode workflow for review skills — detection (Step A) and posting (Step B).
type: template
---

## Step A: GitHub PR Mode Detection

1. Extract the PR number from the user's message.
2. **Require the `gh` CLI.** Check with `gh auth status`; if it succeeds, use `gh` for all GitHub PR operations in this session.
3. Fetch PR metadata and diff via `gh`: `gh pr view <PR> --json title,body,baseRefName,headRefName,files` for metadata and changed files; `gh pr diff <PR>` for the diff content.
4. If `gh` is not installed or not authenticated, stop immediately and inform the user: "No way to reach GitHub — install/authenticate `gh` (`gh auth status` must succeed) before running GitHub PR mode."

---

## Step B: Post Findings to GitHub PR

Runs **only** when the user explicitly requests after reviewing findings locally.

### B1. User Selects Findings

Wait for user to specify which findings to post:
- By number: "post 1, 3, 5"
- By filter: "post all", "post all P0", "post all Critical"

### B2. Create Pending Review Comments

**Use `gh`** for consistency with Step A.

**NEVER create GitHub Issues.** All findings must be posted as inline PR review comments — never as standalone issues. This is a hard requirement with no exceptions.

- `gh api repos/{owner}/{repo}/pulls/{PR}/reviews --method POST --input payload.json`, where `payload.json` holds the `comments` array (each with `path`, `line`, `body`) and **omits the `event` field entirely** — omitting `event` is what leaves the review in `PENDING` state; passing `event: PENDING` is not a valid value and will error. Each comment must be anchored to the **exact line number** identified in the finding — never posted as a top-level PR comment or at the top of the file.

If `gh` is not available or not authenticated, stop and inform the user.

### B3. Confirm Result

Report:
- Number of comments added to pending review
- Link to the PR
- Reminder: "Review is pending — submit manually on GitHub."

**Never submit the review.** No `APPROVE`, `REQUEST_CHANGES`, or `COMMENT` event. Pending only.
