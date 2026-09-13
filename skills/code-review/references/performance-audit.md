# Performance Audit

A full-codebase performance scan with its own dispatch rules and report. Loaded only when Step 1 resolves a Performance Audit target.

---

## Scope and Dispatch

- **Code scope only**, regardless of any `scope` value — test files are never reviewed in this mode.
- **No diff for the scan** — the full codebase is scanned; EXCLUDE does not apply to it.
- **Step 5 is skipped** — always parallel dispatch, one agent per dimension, no tier or banner beyond `🔍 Code review — Performance Audit · Parallel — N agents`.
- `architecture-reviewer` and `performance-reviewer` scan the full codebase. `code-quality-reviewer`, `regression-reviewer`, and `security-reviewer` scope to changed files only.
- `requirements-tracer` is skipped, so Merge rule 2 never fires and `regression-reviewer` always dispatches alone.
- **Merge rule 1 does not apply** — architecture and code quality intentionally use different scopes here (full codebase vs changed files), so they dispatch as separate agents.
- Checklists and codebase docs per agent are as in [Code Dimensions](code-dimensions.md); `architecture-reviewer` loads the `code-quality-reviewer` set.

## Report

Replaces the standard report.

### Executive Summary
- Overall assessment (1–2 sentences)
- Count of critical issues
- Top-3 highest-impact fixes

### P0 — Critical (fix immediately)

```
[ID] Title
Impact: <description>
Location: <File:Line>
Current: <what is happening>
Recommendation: <specific fix>
```

### P1 — High Priority (fix soon)
### P2 — Medium Priority (moderate improvement)
### P3 — Low Priority (minor / best-practice)
