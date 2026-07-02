# Execute — ai-coding-tooling Augmentation

Read this **after** the parent `references/implement.md`. It augments the parent's Atomic Git
Commit (step 7) and Feature-Level Validation (step 10) steps with a persisted commit log. It does
not replace the parent — every parent rule (one atomic commit per task, Conventional Commits
format, gate-before-commit) stays in force.

## Commit Log: `.specs/features/[feature]/commits.md`

Every feature that produces at least one atomic commit maintains a commit log at
`.specs/features/[feature]/commits.md`. This applies at **every scope tier** — Small and Medium
features commit too (per the parent's inline Execution Plan when `tasks.md` is skipped), not just
Large/Complex ones with a formal `tasks.md`.

**Create it on the first commit for the feature** — never earlier. An empty log has nothing to
prove; there's nothing to write until a commit hash actually exists.

Because this project's "No Automatic Git Commit or Push" rule (see `SKILL.extended.md`) means
commits only land after explicit user go-ahead, append the log entry **immediately after** that
commit lands — never speculatively, never in advance of the actual `git commit`.

### What qualifies (add to the log)

- Any atomic commit from step 7 for a task belonging to this feature's `tasks.md` or inline
  Execution Plan.
- Fix-task commits from the Verifier's fix→re-verify loop (parent `validate.md` step 8 /
  `sub-agents.md` Verifier) for this feature.
- A commit made in a later, resumed session that still implements a task, fix, or gap traced back
  to this feature — the time gap since the original implementation cycle does not matter, only
  traceability to one of this feature's tasks or fix tasks.

### What does NOT qualify (do not add to the log)

- Commits made outside the context of this feature's work — unrelated fixes, other features, or
  ad hoc changes the user makes that this skill did not orchestrate and that don't trace to one of
  this feature's tasks or fix tasks.
- A commit is "out of context" the moment it can't be pointed at a specific task/fix-task ID for
  this feature. When in doubt, don't add it — a missing entry is a smaller error than a
  misattributed one.

### Format

A flat, sequential list — one line per commit, in the order the commits landed. No table.

```markdown
# [Feature] Commit Log

- `abc1234`
- `def5678`
- `9a8b7c6`
- `1c2d3e4`
```

Short hash only (`git rev-parse --short HEAD` right after the commit lands). Append one line per
commit, immediately after it lands — never batched, never reordered.

### Verifier cross-check (parent step 10)

When the Verifier writes `validation.md`'s **Diff range**, cross-check every commit hash in that
range that belongs to this feature against `commits.md`. Any hash missing from the log is a gap —
flag it before returning a PASS verdict.
