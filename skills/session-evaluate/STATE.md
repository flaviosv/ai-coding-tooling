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
- **Status**: superseded by AD-016 (location only; one local notes file per run remains active)

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
- **Status**: superseded by AD-015

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
- **Reason**: 2026-09-12 harness-eval run (`docs/harness-evaluation.md` rows #26-#28) flagged all three: row #26 as a near-duplicate of the frontmatter `description`, rows #27/#28 as restating root `CLAUDE.md` sections that are already loaded globally every session, making a pointer sufficient.
- **Trade-off**: none — the two pointer lines rely on root `CLAUDE.md` being loaded every session (already true, per this repo's own setup), so no coverage is lost; the tagline is pure rewording with no behavior change. Row #29 (re-running Track B/C with `--include-doc` for this skill's two `references/` files) is a separate, still-`Pending` item and was left untouched.
- **Date**: 2026-09-12
- **Status**: superseded by AD-013 (items 2-3 only; item 1, the tagline, remains active)

### AD-009
- **Decision**: Replace the two `templates/subagent-models.md` / `templates/subagent-dispatch-contract.md` links (the "not part of `build-feature`'s pipeline" note and the return-shape justification) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked files. This skill still isn't part of `build-feature`'s model matrix (still pinned independently to `opus`), but the skill's shared "two hard facts" section still applies, same as before.
- **Trade-off**: Same dependency as `code-review`'s AD-007 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: superseded by AD-015

### AD-010
- **Decision**: Replace the `templates/agent-wait-protocol.md` link (Step 6's wait instruction) with a reference to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch` (see `skills/subagent-dispatch/STATE.md` AD-002) alongside the content already consolidated there (AD-009).
- **Trade-off**: Same dependency as AD-009 — this sentence now assumes `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: superseded by AD-015

### AD-011
- **Decision**: Catalog A2's fix-shape guidance (`references/findings-catalog.md`) no longer claims the user's global `CLAUDE.md` carries a file-deduplication directive; it now just says a repeated-reads fix belongs in the skill that repeats them, stated at the point of use.
- **Reason**: The global `CLAUDE.md`'s File Deduplication section was deleted (2026-09-13 harness-eval, `docs/harness-evaluation.md` Root Context Files row #6, user decision to delete rather than rewrite), so the claim became false and would steer classification toward a baseline rule that no longer exists.
- **Trade-off**: A2 findings can no longer lean on a global baseline; any dedup rule must live in the affected skill.
- **Date**: 2026-09-14
- **Status**: active

### AD-012
- **Decision**: Catalog F1 (`references/findings-catalog.md`) and its Non-findings counterpart no longer cite the Test Execution Scope convention: Implies drops the "pattern the convention exists to prevent" clause, Fix shape now says to tighten a skill's existing scoped-test instruction rather than invoke the convention, and the cross-cutting non-finding says widening is warranted there on its own terms. F1's full-test-suite detection itself is unchanged.
- **Reason**: By the user's decision, the global Test Execution Scope rule set (the `CLAUDE.global.md` subsection and `references/test-execution-scope.md`) was removed from the harness, so citing it would steer classification toward a rule that no longer exists.
- **Trade-off**: F1 findings can no longer lean on a global scoping baseline; any test-scoping rule a fix proposes must live in the affected skill.
- **Date**: 2026-09-14
- **Status**: active

### AD-013
- **Decision**: Step 6's source check and Step 10's commit line state their behavior inline (only a `local` skill is edited in place, other sources are routed per the attribution table; commit directly to `main` and push to `origin` without waiting to be asked) instead of linking root `CLAUDE.md` Skill Modification Rules and Change Request Workflow.
- **Reason**: User decision (harness-evaluation #18 scope): a skill must not link or defer its instructions to a file outside its directory. The `../../CLAUDE.md` links also resolve against the installed location, not the repo.
- **Trade-off**: The two behaviors are duplicated from root `CLAUDE.md` and can drift if that workflow changes.
- **Date**: 2026-09-14
- **Status**: superseded by AD-014 (source-check item only; the inline commit/push line remains active, narrowed by AD-014)

### AD-014
- **Decision**: The skill is project-agnostic. It no longer names `AGENTS.md`, `CLAUDE.md`, `CLAUDE.global.md`, or `docs/codebase/`; a new Guardrail says which skills, references, and instruction files to read is decided by the transcript, never a fixed list. The attribution table sends a fix with no governing skill to "the file that governed that behaviour in the session (identified from the transcript)", Informational when none can be identified. The `config/skills.json` source check becomes an origin check (use the hosting repo's skills registry if it has one, otherwise ask); vendor routing keeps the overlay (e.g. `extended/<name>/`) only where the hosting repo provides one. Step 10 still commits and pushes, except edits inside the analyzed session's own project, which are left uncommitted. The example report's `~/.claude/CLAUDE.md` finding is genericized. Settles harness-evaluation #130 by dropping the AGENTS.md/CLAUDE.md choice instead of disambiguating it.
- **Reason**: User decision (2026-09-14 harness-eval, Skills rows #127-#145): the skill is used from any project and evaluates sessions from any project, so hardcoded context-file names were wrong wherever those files don't exist and pointed fixes at files the analyzed session never loaded.
- **Trade-off**: Attribution for general behaviour now needs evidence from the transcript instead of a default target, so some findings that used to get a named target become Informational. Letting a non-skill fix land in an instruction file inside another project is why that edit is left uncommitted.
- **Date**: 2026-09-14
- **Status**: active

### AD-015
- **Decision**: All subagent lifecycle handling is removed: the wait-protocol load instruction and 15-minute stall ceiling, the model-matrix and `subagent-dispatch` references, the dispatch-contract field accounting (completion condition, observability prefix and scale estimate), and the "do not retry a failed dimension" rule. What stays is only what this skill's flow needs: Inline dispatches none, Medium dispatches one agent for every active dimension, Large dispatches one agent per active dimension in a single message, all on `model: opus`, each receiving named inputs and returning a fixed finding shape, and none editing files, touching GitHub, or dispatching agents of its own. Step 7 still marks a dimension that returned nothing usable as `not executed` in the report. The catalog's detection classes for inefficient subagents in an analyzed session (C2 runaway, C3 serial fan-out, C4 nesting) are kept, since they are analysis rather than lifecycle management. Settles harness-evaluation #131, #133 and #141 by removal.
- **Reason**: User decision: dispatched subagents trigger skills that manage their own lifecycle, so restating it here duplicated another skill and drifted from it (#133 found a false "not in the model matrix" claim, #141 a stale protocol name).
- **Trade-off**: Waiting and failure handling for this skill's own dimension agents now rely on whatever the calling harness and loaded skills provide. A later session-evaluate run over a session-evaluate run has no observability tag to attribute its dimension agents by and falls back to prompt-text inference.
- **Date**: 2026-09-14
- **Status**: active

### AD-016
- **Decision**: Remaining harness-evaluation fixes. (1) Scoped Mode D1 filtering is mechanical: `session_metrics.py` prints each scoped window's start and end on the `scoped to:` line in transcript timestamp format, and Step 4 gets each match's timestamp with `sed -n 'Np'` plus a `json` one-liner (#127). (2) Dimension E activates only after a bounded input-shape sample, not on a raw 5+ call count (#128). (3) Parallel agents receive their catalog section plus section G and any section theirs points to (#129). (4) Apply reads the target skill's `STATE.md` when it has one and appends an entry in that file's own format, without hardcoding any ADR doc path (#132). (5) Example 5 matches the example report (A, B, C, D, F, 5 agents) and points to Step 8 (#134). (6) Step 3 covers the script's subagent-only branch, and the script now lists those subagents' transcript paths to re-run on (#135). (7) The D1 regex exists only in SKILL.md (#136). (8) The example report was regenerated with the current script on its original session, gained Costs, heuristic, and collapsed-count lines, and was cut to one finding block (#137, #138, #144). (9) Catalog step references use step names (#139). (10) An escalated script finding gets a separate build yes/no in Step 8 and is still never applied (#140). (11) Memory moves to the fixed absolute `~/.claude/session-evaluate/` (#142). (12) History clauses dropped (#143). (13) A4 derives the context window from evidence (auto compaction, or peak above 200k), otherwise a 120k absolute threshold, because transcripts don't record window size (#145).
- **Reason**: 2026-09-14 harness-eval rows #127-#129, #132, #134-#140, #142-#145. Each was an instruction the agent couldn't carry out from the data it had, a contradiction between files, or stale content.
- **Trade-off**: Two small script changes (window bounds, transcript paths), and the script has no tests. The regenerated example's test-suite table now shows the detector's false positives (`npm test -- <file>` matches as full-suite), which is kept as a sanity-check lesson and not fixed here. Memory written before this change stays in the old repo-root `.session-evaluate/` and is not migrated. A4 below 200k peak with no auto compaction uses an assumed window and says so.
- **Date**: 2026-09-14
- **Status**: active; point (11) superseded by AD-017

### AD-017
- **Decision**: Three fixes. (1) The skill names no other skill: Example 3 now says to name the permission settings that would allow the denied command shape instead of naming two settings skills, and every other named skill in `SKILL.md`, the catalog, the example report, and the script's docstrings is replaced with a generic description or an `example-*`/`<skill>` placeholder. (2) Memory location reverted to `<project root>/.session-evaluate/` by user decision, where the project root is `git rev-parse --show-toplevel` of the directory the skill runs from, or that directory when it is not a git repository; this supersedes AD-016 point (11). (3) `session_metrics.py`'s full-suite detector no longer reports a scoped run as full. Root cause: `_FLAG` let any flag, including the bare `--` separator (its name pattern `[\w-]+` matched `-`), take a space-separated bare value, and only a `/` stopped that, so `npm test -- AppShell.test` or `pytest -q test_x.py` parsed as flags alone. Flag names must now start with a letter or digit, a space-separated bare value may not contain `/` or `.`, a `=` value may contain anything, and a name filter (`-k`, `-t`, `--testNamePattern`, `-run`, `--filter`, `--tests`, `-Dtest`) makes a run scoped. `is_full_suite_run()` holds the check and `scripts/tests/test_session_metrics.py` covers it; the example report's test-suite table drops its six mis-matched rows.
- **Reason**: User rules that a skill never mentions other skills and links nothing outside its own directory; the user's memory-location decision; the false positives AD-016 recorded in the example report.
- **Trade-off**: Placeholder names make the examples less concrete. A bare space-separated flag value without `/` or `.` is still indistinguishable from a positional target (`npm test -v WeekView` counts as full), and a bare value with a `.` (`--timeout 1.5`) now counts as scoped. Only runners the script already knew were changed; vitest and jest invoked directly are still undetected.
- **Date**: 2026-09-14
- **Status**: active

### AD-018
- **Decision**: Step 6's Medium and Large dispatch prompts no longer paste `references/findings-catalog.md` (in full, or per-dimension section) or the Classification & Priority Procedure verbatim into the subagent's prompt. Each dispatch instead sends only the run-specific inputs (digest, D1 grep results) plus a Read instruction naming the catalog section(s) to open and pointing at this file's own `#### Classification & Priority Procedure` section.
- **Reason**: A harness-wide audit of `Agent`-tool dispatches found this skill was the one dispatcher in the repo still inlining static reference-file content instead of pointing a subagent at it to read itself — `code-review` already treats its own checklists this way ("Never inline checklist or doc content — `## Before You Begin` is a Read instruction"), and `subagent-dispatch`'s contract discourages restating content the subagent can fetch on its own. The catalog is ~17.5KB; the procedure section is ~6KB — both add up across a Large-tier fan-out for no benefit, since every dispatched subagent already has Read access and a known `<skill-dir>`.
- **Trade-off**: None identified — the digest and D1 grep results stay inlined as before, since they are run-specific computed artifacts (not static files a path can point to) and are already kept compact by design; this decision only moves the two static documents from paste to Read.
- **Date**: 2026-09-14
- **Status**: active
