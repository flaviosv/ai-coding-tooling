# STATE

## Decisions

> **Note on token figures.** Absolute token counts in the entries below were produced by
> `session-evaluate`'s `session_metrics.py` before the counting fix recorded in that skill's
> STATE.md AD-006, and are inflated by roughly 2x (measured 1.98x-2.64x, varying with per-turn
> parallelism). Counts, rates and shares — findings fixed, duplication rate, invalid rate, turn
> counts, share of spend — are unaffected, and no decision below rests on an absolute total.
> Read the token magnitudes as approximate and about half of what is written.

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

### AD-005
- **Decision**: Two fixes to `scripts/session_metrics.py`. (1) The full-suite detector's patterns no longer anchor so tightly that real full-suite runs escape them: `go test ./...` now matches whatever flags follow it, test-runner patterns accept flags carrying values (`-m "not integration"`), and `uv`/`poetry`/`pipenv`/`pdm`/`hatch run` prefixes are recognised. Scoped runs still do not match, because a bare flag value may not contain `/` — so `pytest tests/unit/` and `go test ./internal/logger` remain correctly excluded. (2) When `--skill <name>` finds no top-level window, the script now checks the subagent rollup before declaring the skill absent, and when it finds it there, reports that skill's real runs/tokens/turns and points at `<session-dir>/subagents/` instead of saying it never ran.
- **Reason**: Both were measured failing during this session's own audits, which is how they were found. The detector reported "no full-suite runs detected" for two sessions that had in fact run `go test ./... -v` (spinning up Docker testcontainers after six files changed) and `uv run pytest -x -m "not integration"` (642 tests for four touched files) — the exact F1 violations this dimension exists to catch, missed because of a trailing `-v` and a flag with a value. The `--skill` message returned "No invocation of fix-review found in this session. Skills invoked: grilling, rename" for a session where `fix-review` ran twice and consumed 97.6M tokens; it hit **6 of the 9 audits run in this session**, and every one had to work around it by hand. The old message was not merely unhelpful — it asserted absence, which is false, and an analyst who believed it would conclude the skill never ran.
- **Trade-off**: The looser test patterns trade a little precision for recall — a command like `pytest -k something` with no path is now correctly caught, but so would be an exotic invocation that happens to take only flags while meaning something narrower. Given the failure being fixed is false negatives on the exact violations this dimension exists to detect, and the report already labels this table heuristic, that is the right direction. The `--skill` fallback adds a subagent-rollup computation to a path that previously returned early; negligible, since the rollup was already computed for the same call.
- **Date**: 2026-09-06
- **Status**: active

### AD-006
- **Decision**: Fix `token_totals` in `scripts/session_metrics.py` to deduplicate by `requestId`, counting each real API call once for both token totals and the turn count, instead of summing per assistant JSONL record. Peak context is computed before the dedup guard, since duplicated records carry identical usage and the maximum is unaffected. Records without a `requestId` fall back to being counted individually. Added a recalibration note to the findings catalog's C2 entry, whose "tens of millions billed" and "over ~150 turns" thresholds were both set against the inflated numbers.
- **Reason**: Claude Code writes one assistant record per *content block*, and every block of a single API response repeats that response's identical `usage` object — so a turn emitting thinking plus text plus ten parallel `tool_use` blocks was counted twelve times. Verified directly on a real worker transcript: 132 assistant records resolving to 54 distinct `requestId`s, 41 of which carried duplicates, with one example showing three records each reporting the same 36,800 tokens. The measured inflation across four subagent transcripts was 1.98x, 2.22x, 2.27x and 2.64x — it scales with how parallel each turn happened to be, so it did not even cancel when comparing two runs against each other. The script already knew this fact and applied it correctly elsewhere: `collect_tool_calls` groups by `requestId` precisely because "Claude Code writes one assistant record per content block". `token_totals` was simply never updated to match, making the file self-inconsistent. The practical damage was large — this metric is the headline number of every report this skill produces, and one investigation spent real effort on an apparent paradox ("44 findings for 26.09M vs 18 findings for 27.58M") that dissolved once the counts were corrected to 9.89M and 12.41M.
- **Trade-off**: Every historical figure produced by this script is ~2x too high and is not retroactively comparable with post-fix output — including the numbers behind several decisions recorded in other skills' STATE files this same day. Those decisions were checked and none reverse: they rest on counts, ratios and rates (findings fixed, duplication rate, invalid rate, share of spend) rather than absolute token totals, and the shares are computed from an inflated numerator over an equally inflated denominator. The absolute savings quoted in them are overstated by roughly the same factor and should be read as such. The C2 thresholds genuinely do change meaning and are flagged as provisional rather than silently rescaled, since guessing a new constant would repeat the original error of setting one without measurement.
- **Date**: 2026-09-06
- **Status**: active

### AD-007
- **Decision**: Six changes, all derived from this skill's own failures during a large multi-session audit it performed on 2026-09-06. (1) The Classification procedure gains a **mandatory "does this rule already exist?" check** before any finding whose fix is "add a guideline": grep the attributed file first, and if the rule is there, report it as a rule that did not bind — a different diagnosis — choosing from a table of five structural fix shapes (make it a precondition, move it into a script, re-key it to a structural fact rather than wording, escalate the tier, or consolidate a duplicated/contradicted rule). Three or more prior `STATE.md` decisions on one failure class is itself a P0 finding. (2) Any claim about how a skill is *designed* must be verified against that skill's own `SKILL.md`, not inferred from observed runs. (3) Each finding's block now states token saving and wall-clock saving **separately**, with `~0` written where honest. (4) Catalog E1 changes from "always Informational" to "Informational by default", with an escalation rule when a script has been proposed before and a prose fix for the same failure has since been applied and failed. (5) `session_metrics.py` prints a dedup self-check (assistant records per API call) and the full-suite section now says "no matches — the patterns did not fire, NOT that no run happened" instead of "none detected". (6) Step 7 gains cross-session consolidation: group by defect rather than session, carry a session count, and treat recurrence across independent sessions as the Structural test.
- **Reason**: Each traces to a specific failure in that audit. It produced 42 findings that collapsed to ~20 distinct defects, of which ~11 proposed adding rules the target skill already contained — the target had six prior decisions on one failure class, every one of them adding prose, with the failure recurring after each; the fix that finally held was a script, which this catalog had been filing as permanently Informational. The report told the user a parallel fan-out was "where the remaining cost lives", true of 39–63% of tokens and exactly wrong about time, because that fan-out ran inside a serial step that was ~100% of the critical path. It asserted `code-review` "does not tier its fan-out" from seeing five agents in every sampled run, when it does tier and every sampled PR simply landed in the two tiers that share an execution mode. Its own token metric was overstated 1.98x–2.64x (AD-006) and survived because nothing in the report exposed the ratio that would have shown it. Its full-suite line read "none detected" while missing two real violations. And eight parallel analysts rediscovered the same handful of defects independently, with no step that merges across sessions.
- **Trade-off**: The classification procedure is longer and now requires a grep of the attributed file before writing a whole category of finding — real per-finding cost, accepted because that category was the majority of the noise in the audit that motivated it. The E1 escalation deliberately loosens a rule that existed for a good reason (a script is a maintenance surface, and this skill's remit is guidance); the guard is that escalation requires *both* a prior proposal and a measured prose failure, so it cannot fire on a first sighting. The separate token/wall columns will often both be small, which is the point — a finding that saves neither should be visible as such.
- **Date**: 2026-09-06
- **Status**: active

### AD-008
- **Decision**: Three wording fixes to `SKILL.md`. (1) `SKILL.md:12`'s body intro (under "# Session Evaluate") is now a distinct one-line tagline oriented on when to reach for the skill, rather than a paragraph nearly restating the YAML `description`. (2) `SKILL.md:177` (Step 6's attribution table, the `config/skills.json` source check) now points to root `CLAUDE.md`'s Skill Modification Rules section instead of restating its contents. (3) `SKILL.md:308` (Step 10's commit/push line) now points to root `CLAUDE.md`'s Change Request Workflow section instead of restating its contents.
- **Reason**: 2026-09-12 harness-eval run (`docs/HARNESS-EVALUATION.md` rows #26-#28) flagged all three: row #26 as a near-duplicate of the frontmatter `description`, rows #27/#28 as restating root `CLAUDE.md` sections that are already loaded globally every session, making a pointer sufficient.
- **Trade-off**: none — the two pointer lines rely on root `CLAUDE.md` being loaded every session (already true, per this repo's own setup), so no coverage is lost; the tagline is pure rewording with no behavior change. Row #29 (re-running Track B/C with `--include-doc` for this skill's two `references/` files) is a separate, still-`Pending` item and was left untouched.
- **Date**: 2026-09-12
- **Status**: active
