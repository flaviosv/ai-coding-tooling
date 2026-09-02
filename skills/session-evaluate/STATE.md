# STATE

## Decisions

### AD-001
- **Decision**: Per-run memory is written to `.session-evaluate/<YYYYMMDD-HHMM>_<session-name>.md` in the repo root, git-ignored, one file per run — not appended to a single shared log, and not folded into this repo's own `.specs/STATE.md`.
- **Reason**: A run's findings are local working notes for a future run of this skill to grep, not project history; one file per run keeps each self-contained and avoids growing a single file forever.
- **Trade-off**: No built-in cross-run search beyond `grep` — acceptable since Step 8 only needs to check the same skill/dimension, not do general-purpose querying.
- **Date**: 2026-09-01
- **Status**: active

### AD-002
- **Decision**: A subagent's real governing skill/phase is resolved from its own transcript — a `Skill`-tool call it made itself (confident), falling back to a kebab-case token in its first user message (its dispatch prompt) — rather than correlating each subagent run to its launch call by nearest timestamp.
- **Reason**: Timestamp correlation breaks down for nested (depth-2/3) subagents, whose real launch call lives inside another subagent's own transcript, invisible to the main thread; scanning the subagent's own content sidesteps that and reuses the existing generic `skills_used()` helper.
- **Trade-off**: The fallback is lower-confidence and can surface noise (a task/branch name that happens to be a valid kebab phrase) — mitigated by excluding digits from the kebab regex, not eliminated. The digest reports a confidence ratio per row so this is visible, not hidden.
- **Date**: 2026-09-01
- **Status**: active

### AD-003
- **Decision**: Full-suite test detection scans tool calls merged from the main thread *and every subagent transcript*, and strips a command's trailing pipe/redirect before matching it against `FULL_SUITE_PATTERNS`.
- **Reason**: Confirmed on a real session that real full-suite runs happen inside subagents (where the actual test/build work runs in an orchestrated session) and are almost always piped (`| tail -40`, `2>&1`) — a main-thread-only, end-of-string-anchored detector missed both a confirmed frontend and a confirmed backend full-suite run in the same session.
- **Trade-off**: None material — broader scanning costs negligible extra script runtime; pattern precision is unchanged, only the strings tested against the patterns changed.
- **Date**: 2026-09-01
- **Status**: active

### AD-004
- **Decision**: A full worked example of Step 8's target output lives in `references/example-report.md`, not embedded inline in `SKILL.md`.
- **Reason**: The example is large (a full multi-finding report at production detail) and only needed as a format reference, not on every invocation — keeping it out of `SKILL.md` avoids inflating every load's token cost.
- **Trade-off**: One extra file to keep in sync if Step 8's shape changes again.
- **Date**: 2026-09-01
- **Status**: active

### AD-005
- **Decision**: D1's mandatory grep scans `text`, `prompt`, and `description` JSON fields together in one pass, with keywords for downstream-discovered breakage ("left ... broken", "leftover ... marker/conflict", "prior ... pass left", "still failing/broken") added alongside the existing self-correction language — kept generic to any skill, not naming a specific one.
- **Reason**: `prompt`/`description` are where an orchestrator explains a prior step's output was broken when it dispatches a recovery subagent — content a `text`-only grep is structurally blind to, confirmed missing a real recovery-dispatch case in a sample session.
- **Trade-off**: Broader field scanning risks catching unrelated dispatch prompts that merely mention similar words without a real defect — mitigated by keeping every match a candidate, not a finding (per the catalog's existing read-the-surrounding-turn rule), not by narrowing the grep.
- **Date**: 2026-09-01
- **Status**: active

### AD-006
- **Decision**: Every subagent Step 6 dispatches is pinned to `model: opus` (was `sonnet`); the change is a local edit to this skill's own Guardrails, not to the shared `templates/subagent-models.md` matrix.
- **Reason**: The classification work (matching a digest signal to a catalog class, judging Structural vs Incidental, attributing a fix target) is reasoning-dense enough to warrant the stronger model; the shared matrix only covers `build-feature`'s own pipeline and doesn't list this skill, so retiering here doesn't touch any other skill's dispatch tier.
- **Trade-off**: Higher per-agent cost and latency for Medium/Large-tier runs, accepted for classification quality. The orchestrating conversation itself stays unpinned, as before.
- **Date**: 2026-09-01
- **Status**: active

### AD-007
- **Decision**: Point Step 6's existing subagent return-shape documentation at the new shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) template, and add the two fields it didn't already state explicitly — completion condition (every candidate in the assigned dimension classified against the catalog) and delegation depth (none).
- **Reason**: This skill's own dogfooding of the run it was auditing (a `build-feature` session) is what surfaced the dispatch-contract gap in the first place; retrofitting this skill's already-close-to-compliant shape is part of the same repo-wide pass applied to every other skill in `skills/` that dispatches subagents.
- **Trade-off**: None identified — the existing return shape already matched the template closely, so this is a pointer plus two short additions, not a restructure.
- **Date**: 2026-09-02
- **Status**: active
