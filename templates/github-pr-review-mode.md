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

**Body format (required, no exceptions):** every comment's `body` must open with the same structured tag the finding already carries in the skill's local zoned-format report — do not post bare prose. Use:

```
**[<Zone/Dimension> — <Finding ID>, <Severity>]** <explanation>

**Recommendation:** <concrete, actionable fix>
```

- `<Zone/Dimension>` and `<Finding ID>` are the same zone name/letter and `<ZoneLetter><N>` ID (e.g. `A1`, `Q3`, `S2` for `code-review`; `C1`, `V3`, `G2` for `tests-code-review`) already assigned in Step 8's zoned report — carry them through verbatim, never renumber or rename for the GitHub post.
- `<Severity>` is one of Critical / High / Medium / Low, matching that finding's row in the local report.
- **The `Recommendation` line is mandatory on every comment, no exceptions** — even a finding phrased as a question ("Why do you need a rollback here?") must still close with a concrete recommendation (e.g. "Remove the rollback — no write precedes it in this branch."). If the finding is genuinely a request for clarification rather than a defect, phrase the recommendation as the specific action to take once answered (e.g. "If X, remove Y; if Z, document why it's needed"), rather than omitting the line — never leave a comment without a next action.
- A finding merged in from an already-pending review (see `complete-review`'s merge guardrail) that predates this format — e.g. a bare human-authored draft comment — is carried over as-is; do not retrofit a tag or recommendation onto content you didn't generate.

This applies uniformly to every comment in the payload — including Requirements/Coverage-Gap findings and Performance-Audit-style items — so a reviewer scanning the pending review never hits an untagged, unscannable comment next to tagged ones.

If `gh` is not available or not authenticated, stop and inform the user.

### B2'. Return-Only Variant

Used only when the invoking caller explicitly requests it (e.g. `complete-review`'s own merged-post flow, which needs to combine this skill's findings with another skill's before issuing a single `POST`). This is an alternative to B2, not a step that runs after it.

Assemble the exact same `comments` array B2 would (`path`, `line`, `body` per finding, each anchored to the exact line number, each `body` opening with the B2 structured tag) — but do **not** issue the `gh api ... POST` call. Return the assembled array to the caller instead. B1's finding-selection step still applies as normal (or is satisfied by the caller the same way it is for B2). Skip B3 entirely in this variant — nothing has been posted yet, so there is no result to confirm here; the caller is responsible for confirming once it completes its own `POST`.

### B3. Confirm Result

Report:
- Number of comments added to pending review
- Link to the PR
- Reminder: "Review is pending — submit manually on GitHub."

**Never submit the review.** No `APPROVE`, `REQUEST_CHANGES`, or `COMMENT` event. Pending only.
