# STATE

## Decisions

### AD-001
- **Decision**: Compressed three near-duplicate lines in `SKILL.md` into one-line pointers back to their source steps: the Example 3 Actions line → Step 1's "ask, never guess" rule; the "Jira MCP not connected or ticket not found" troubleshooting line → Step 2's stop/no-fabricate rule; the "Posting to Jira fails" troubleshooting line → Step 7's posting-failure rule.
- **Reason**: Each restated its source step almost verbatim, flagged as Ship-priority findings `C032`, `C033`, `C036` by the 2026-09-12 harness-eval run (`docs/harness-evaluation.md` rows #23-#25).
- **Trade-off**: Example 3 and the Troubleshooting section now depend on Steps 1, 2, and 7 for their full wording instead of standing alone — acceptable since both sections already sit right after the numbered Steps in the same file.
- **Date**: 2026-09-12
- **Status**: active

### AD-002
- **Decision**: Replaced the `[gh Account Resolution](../../templates/gh-account-resolution.md)` reference with a one-line `gh` account resolution: opt-in tag. The mechanism itself moved to the user's global `CLAUDE.md` (`CLAUDE.global.md`, symlinked to `~/.claude/CLAUDE.md`) as a standing rule; this skill only states its own opt-in application decision now.
- **Reason**: Same rationale as `build-feature`'s AD-009 and `complete-review`'s AD-005 — the `gh` multi-account mechanism is a fact about the user's own environment, not this skill, so it belongs in global `CLAUDE.md` (closing the ad-hoc-`gh`-usage gap outside all consuming skills); only the per-skill mandatory/opt-in decision stays local.
- **Trade-off**: Same as the sibling entries above — this tag depends on the user's global `CLAUDE.md` being loaded wherever this skill runs.
- **Date**: 2026-09-13
- **Status**: superseded by AD-003

### AD-003
- **Decision**: Removed the `gh` account resolution: opt-in tag from Step 3. The `scripts/hooks/resolve-gh-account.sh` hook (SessionStart + CwdChanged, `config/hooks.json`) now scopes the session's `gh` calls to the current repo's account through `GH_TOKEN`.
- **Reason**: The tag's trigger ("actually hits the multi-account problem") was not checkable at runtime and contradicted the global rule it relied on (`docs/harness-evaluation.md` Skills #118); that global prose procedure has been replaced by the hook.
- **Trade-off**: The hook resolves from the session's current repo, so a `gh pr view` for a PR in an unrelated repo whose access differs by account still runs as that repo's account (or the active one outside a GitHub repo) and falls back to a ticket-only plan when it fails.
- **Date**: 2026-09-14
- **Status**: active
