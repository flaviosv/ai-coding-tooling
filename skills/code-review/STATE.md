# STATE

## Decisions

> **Note on token figures.** Absolute token counts in the entries below were produced by
> `session-evaluate`'s `session_metrics.py` before the counting fix recorded in that skill's
> STATE.md AD-006, and are inflated by roughly 2x (measured 1.98x-2.64x, varying with per-turn
> parallelism). Counts, rates and shares — findings fixed, duplication rate, invalid rate, turn
> counts, share of spend — are unaffected, and no decision below rests on an absolute total.
> Read the token magnitudes as approximate and about half of what is written.

### AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) at Step 6's Medium/Large-tier dispatches — explicit completion condition (every checklist item in `## Before You Begin` checked, findings written), a return shape restricted to findings only, and delegation depth: none.
- **Reason**: Part of a repo-wide retrofit, following a `session-evaluate` audit that found `complete-review`'s own dispatch (which delegates to this skill) running with no completion condition at all. Applied here preventively, in the same pass, since this skill has the identical dispatch shape (dimension agents returning findings).
- **Trade-off**: None identified.
- **Date**: 2026-09-02
- **Status**: active

### AD-002
- **Decision**: Add Merge Rule 2 to Step 6's parallel dispatch: when both `regression-reviewer` and `requirements-tracer` are in the active dimension set, they dispatch as a single `intent-regression-reviewer`, union of both checklists, findings returned tagged by original dimension — the same shape as the existing `design-quality-reviewer` merge, and with the same downstream handling (separate at-a-glance rows preserved; a merged-agent failure marks both rows not-executed). Either dispatches standalone when the other isn't active, which is also what happens in Performance Audit mode, where `requirements-tracer` is skipped outright. Takes the general-content, all-dimensions-active case from 6 agents to 4.
- **Reason**: A measurement pass over 29 dimension-agent runs across four real PRs, joined against all 117 resulting GitHub threads and `fix-review`'s recorded disposition on each, found these two the lowest-yield dimensions by a wide margin. Together: 8 runs, 31.9M billed input (27.9% of all fan-out spend), 12 findings, 7 fixed — of which 4 duplicated another dimension's finding and 3 were factually wrong (`regression` 29% invalid, `requirements-tracer` 20%). `requirements-tracer` cost 6.92M per fixed finding against a 1.68M fleet average, found nothing at all on one PR, and its two fixed findings were both duplicates; `regression`'s single most expensive run in the dataset (9.59M) produced zero unique actionable findings. Every Critical or High either produced was independently found by 2–4 other dimensions in the same run, so the expected loss is bounded to low-severity and housekeeping items. They are also the same shape of check — does the change still do what was intended, and does it break what already worked — which is what makes one agent coherent rather than merely cheaper.
- **Trade-off**: Two dimensions now share one agent's attention, so a merged run has less budget per dimension than two separate runs did; the measured saving (~18M, ~8.6% of a `complete-review` run) is a token saving only — the fan-out runs in parallel and is not the wall-clock bottleneck, so this buys no wall time. Whether merging preserves findings or simply produces fewer is not established: `tests-code-review`'s equivalent merged agent was the most efficient run in the whole dataset, but that is a single observation on the smallest diff in the set. Revisit if `intent-regression`-tagged findings drop disproportionately rather than proportionally.
- **Date**: 2026-09-06
- **Status**: active

### AD-003
- **Decision**: Every finding a dimension agent returns now carries an `anchor` — the verbatim text of the line it points at, one line, trimmed, no ellipsis or paraphrase — alongside `File:Line`, which is restated as always being the line at the PR head and never an offset into a diff artifact. The same requirement is added to `tests-code-review` and to the shared [GitHub PR Mode B2' Return-Only Variant](../../templates/github-pr-review-mode.md) that both route through; a finding whose line genuinely cannot be resolved returns `line: null` with the anchor still populated. `complete-review`'s merge step is correspondingly instructed to confirm anchors with a bounded `grep -n` of that text and explicitly forbidden from `Read`ing whole source files to check line numbers.
- **Reason**: A phase measurement of `complete-review`'s Step-2 worker across four real PRs found that every worker independently invented the same unspecified phase — re-reading 20 to 31 source files to verify the `file:line` values its dimension agents had returned, because it had no cheaper way to trust them, and in two cases because agents had in fact returned diff-relative offsets. It cost 13–35% of the worker's entire token budget and 2.1–4.0 minutes of the critical path, and did lasting damage beyond its own phase: the full-file reads inflated the worker's context by 21k–102k tokens at exactly the point it still had to hold every finding and drive posting, and that surcharge re-billed on every remaining turn (cost tracks turns × context at r = 0.952). The dimension agent already has the file open when it writes the finding, so capturing the line costs nothing there and eliminates the entire downstream phase. This is the largest single lever the measurement identified, and it was untouched by every fix specced before it — the diff-hunk anchor validation added the same day addresses whether a line is *postable*, not whether it is *correct*.
- **Trade-off**: A few extra tokens per finding on the producing side, against a phase that measured 13–35% of the consuming side. The contract is now wider, so a consumer written against the old shape will ignore an unfamiliar field rather than break — but a *producer* that omits `anchor` silently reverts the consumer to re-reading files, and nothing mechanically enforces that it was populated. That is the weak point: the rule is prose, in a skill whose prose rules have a mixed record. If the verification phase reappears in a future measurement, the honest next step is to make the merge step reject an anchor-less finding rather than to restate the rule.
- **Date**: 2026-09-06
- **Status**: active

### AD-004
- **Decision**: Applied five redundancy fixes from the 2026-09-12 harness-eval run (`docs/HARNESS-EVALUATION.md` rows #6–#10): (1) compressed the 37-claim Examples section from four full 8–9-step walkthroughs into one mode→step-delta table (Local workspace / GitHub PR / Performance Audit / Multi-commit columns: example invocation, Step 4 diff source, Step 5/6 delta, Step 8/9 delta) since Steps 1–9 are already fully specified earlier in the file; (2) deleted the verbatim-duplicate "Reviewer Stance" block at the agent-dispatch section, replacing it with a one-line pointer back to the single Reviewer Stance section near the top; (3) rephrased the opening line so it orients the reader on how to use the skill (follow the steps in order) instead of restating the frontmatter `description` almost verbatim; (4) single-sourced the Performance Audit trigger-phrase list — both the Guardrails bullet and the Step 1 mode-detection table now point at frontmatter `metadata.triggers` instead of repeating the phrase list inline; (5) replaced two cross-file/cross-doc verbatim restatements with pointers — the anchor-line guardrail paragraph (identical to `tests-code-review/SKILL.md`'s Step 6 statement of it) now points at that file as canonical, and the Merge Rule 2 cost/finding stats (copied from this file's own AD-002) now point at AD-002 instead of repeating the numbers.
- **Reason**: harness-eval's dual-judge pass flagged all five as corroborated duplicates or near-verbatim restatements of content that already exists once, either earlier in this same file, in `tests-code-review/SKILL.md`, or in this skill's own STATE.md — each a drift risk if one copy is updated without the other, and in the Examples case, pure token cost with no independent information beyond what Steps 1–9 already specify.
- **Trade-off**: The Examples table is denser and requires reading the base Steps 1–9 to make sense of the deltas — a reader can no longer follow one mode top-to-bottom without cross-referencing. The Merge Rule 2 and anchor-line pointers mean this file is no longer self-contained for those two guardrails; a reader must open `STATE.md` or `tests-code-review/SKILL.md` to get the full text or numbers.
- **Date**: 2026-09-12
- **Status**: active

### AD-007
- **Decision**: Replace the `templates/subagent-models.md` and `templates/subagent-dispatch-contract.md` links (Subagent Model guardrail and Step 6 execution) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) instead of two linked files — the generic dispatch-contract content matches the shape of self-loading vendor skills like `subagent-creator`/`workflow-authoring`, so callers point at the skill rather than a markdown link.
- **Trade-off**: This file's Sonnet-pinning and dispatch-contract sentences now depend on `subagent-dispatch` existing and staying installed; removing that skill without updating this file would leave a stale pointer.
- **Date**: 2026-09-13
- **Status**: active

### AD-008
- **Decision**: Replace the `templates/agent-wait-protocol.md` link (Step 6 wait instruction) with a reference to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch` (see `skills/subagent-dispatch/STATE.md` AD-002) alongside the model-matrix/dispatch-contract content already consolidated there (AD-007).
- **Trade-off**: Same dependency as AD-007 — this sentence now assumes `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active

### AD-009
- **Decision**: Merge `tests-code-review` and `complete-review` into this skill (v3.0.0) and delete both. One pipeline runs Steps 1–4 once for both scopes (one context map, one union EXCLUDE list, one diff classified into `impl_diff`/`test_diff`, one Sonar query), assesses a tier per scope in Step 5, dispatches every scope's agents in one parallel message, and consolidates into one report. New parameters: `scope` (`both` default, `code`, `tests` — narrowed only by explicit wording), `post` (`false` default; `true` publishes one pending review; Batch Mode always posts), and `findings_path` (replaces `complete-review`'s `human_review: true` hold, with Publish Mode unchanged). `SKILL.md` keeps only what every run executes; mode-conditional content moved to `references/` — `batch-mode.md`, `code-dimensions.md`, `performance-audit.md`, `posting-mechanics.md` (which absorbs `templates/github-pr-review-mode.md`, now deleted), `pr-publishing.md`, `report-format.md`, `sonar.md`, `test-dimensions.md`. Checklists are renamed with a scope suffix — `<topic>.code.md` for this skill's own, `<topic>.tests.md` for those from `tests-code-review`, and stack-specific `<stack>.code.md` / `<stack>-performance.code.md` / `<stack>.tests.md`; extracted orchestration references carry no suffix. Behavior changes deliberately taken with the merge: (1) a GitHub PR review reports locally unless `post: true`, and a user's post-report selection publishes through Posting Mechanics' GraphQL batches instead of the old REST bulk POST; (2) same-root-cause duplicate collapsing (CPR-AD-002) runs in Step 8 on every report, not only before posting; (3) the ≥80% confidence rule covers test findings too; (4) a failed dimension agent is re-dispatched once before being marked not executed, replacing `complete-review`'s whole-skill scoped retry; (5) the tests Performance zone letter is `E`, since `P` is the code scope's; (6) `test-review-checklist.md` became `review-checklist.tests.md`; (7) the tests scope still runs `gap-detector` when implementation changed but no test file did; (8) Sonar's low-coverage file list is intersected with implementation files rather than the tests scope's file list, and the coverage block also reaches the Medium-tier tests agent, since that agent performs `gap-detector`'s analysis; (9) a `findings_path` hold from a root conversation runs in the publishing worker, as `human_review: true` did; (10) Performance Audit's standalone `architecture-reviewer` loads the code-quality checklist set (previously unspecified), and its changed-files agents take their file list from the local workspace diff. Imported decision logs keep their entries verbatim under `TCR-`/`CPR-` prefixes so numbering never collides; CPR-AD-001, CPR-AD-002 and CPR-AD-004 are superseded by this entry. AD-004 item (4) is reversed: frontmatter `metadata.triggers` now mixes every target's phrases, so Step 1's table names each target's trigger phrases itself.
- **Reason**: Three skills covered one job. `complete-review` existed only to run the other two against a PR and merge their output, which cost a worker that invoked two full skills, each collecting its own diff, running its own Sonar step, fanning out its own agents, and writing a report nobody read before a second merge pass. Duplicates across the two were collapsed only at posting time, and the rule text for the GitHub constraints, dispatch contract, wait protocol, EXCLUDE list, tier table, Sonar key lookup, legend, and iterative review existed in two or three copies each. One pipeline collects once, dispatches once, and deduplicates once. Splitting mode-conditional content into references means a local code-only review never loads Batch Mode or Posting Mechanics, and a publishing worker receives one file path for the posting procedure instead of the inlined section or `sed` range CPR-AD-003 had to prescribe.
- **Trade-off**: Callers change — `build-feature` must now pass `post: true` explicitly (the PR default no longer publishes) and its `human_review_exclude` value is `code-review`; `/complete-review` and `/tests-code-review` no longer exist, with no aliases. Understanding one mode now takes `SKILL.md` plus that mode's reference. Merging the two scopes' reports means one Complex scope's caveat now sits in a report that may also carry a Small scope's findings. Checklists no longer follow the repo-wide `<technology>-<skill-name>.md` rule, so `tech-reference-add` and the `skill-architect` overlay each needed an exception for skills that declare scoped variants.
- **Date**: 2026-09-13
- **Status**: active

## Imported from tests-code-review

> Merged into this skill by AD-009. Entries are verbatim; IDs carry a `TCR-` prefix so they
> never collide with this log's own sequence. File and step names refer to that skill as it was.

### TCR-AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) at Step 6's Medium/Large-tier dispatches — explicit completion condition (every checklist item in `## Before You Begin` checked, findings written), a return shape restricted to findings only, and delegation depth: none.
- **Reason**: Part of a repo-wide retrofit, following a `session-evaluate` audit that found `complete-review`'s own dispatch (which delegates to this skill) running with no completion condition at all. Applied here preventively, in the same pass, since this skill has the identical dispatch shape as `code-review` (dimension agents returning findings).
- **Trade-off**: None identified.
- **Date**: 2026-09-02
- **Status**: active

### TCR-AD-002
- **Decision**: Delete the "Key Reminders" footer (`C127`–`C131`) entirely rather than compress it.
- **Reason**: 2026-09-12 harness-eval run (`docs/HARNESS-EVALUATION.md` row #35) flagged the footer as pure software-engineering truisms with zero repo-specific content — dual-judge REDUNDANT and cheaply rediscoverable. Nothing in it added skill-specific guidance beyond what the Reviewer Stance section already establishes.
- **Trade-off**: None identified — no repo-specific content was lost.
- **Date**: 2026-09-13
- **Status**: active

### TCR-AD-003
- **Decision**: Replace the `templates/subagent-models.md` and `templates/subagent-dispatch-contract.md` links (Subagent Model guardrail and Step 6 execution) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked files, mirroring `code-review`'s identical change (AD-007).
- **Trade-off**: Same dependency as `code-review`'s AD-007 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active

### TCR-AD-008
- **Decision**: Replace the `templates/agent-wait-protocol.md` link (Step 6 wait instruction) with a reference to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch` (see `skills/subagent-dispatch/STATE.md` AD-002) alongside the content already consolidated there (AD-007), mirroring `code-review`'s identical change (AD-008).
- **Trade-off**: Same dependency as AD-007 — this sentence now assumes `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active

## Imported from complete-review

> Merged into this skill by AD-009. Entries are verbatim; IDs carry a `CPR-` prefix. The note on
> token figures at the top of this file applies to these entries too. File and step names refer
> to that skill as it was — Posting Mechanics now lives in `references/posting-mechanics.md`.

### CPR-AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) for Single PR Mode's review subagent and Batch Mode's per-PR subagents — explicit completion condition (PR's pending review posted, or findings returned when `human_review` withholds it), bounded return shape (already documented, now pointed at rather than restated), delegation depth (may invoke `code-review`/`tests-code-review` via `Skill`, no nesting beyond their own Step 6).
- **Reason**: A `session-evaluate` run against a real APLYR-19 build-feature session measured this skill's Single PR Mode dispatch at 156 turns / 23.0M tokens — the longest-running agent in the whole session — with no completion condition in its prompt beyond "review PR #N." Part of a repo-wide retrofit applied to every skill in `skills/` that dispatches subagents.
- **Trade-off**: None identified — this only adds structure to a prompt that was already being written by hand.
- **Date**: 2026-09-02
- **Status**: superseded by AD-009

### CPR-AD-002
- **Decision**: Single PR Mode Step 2b must collapse same-root-cause duplicates across dimensions before posting, keeping the clearest instance of each cluster and folding the others' detail into it, and Step 2c must report the number of clusters collapsed (explicitly `0` when none). Framed as merging, never severity filtering — nothing is dropped for being minor, only for being another finding restated.
- **Reason**: Step 2b previously said only "merge both `comments` arrays into one," and the sole dedup rule anywhere in the skill is Posting Mechanics' exact `path`+`line`+`body` match against an existing pending review — which cannot catch two agents describing one defect in different words at different lines. Measurement across four real PRs shows that is the common case, not an edge case: `code-review` and `tests-code-review` fan out 5–9 agents over an overlapping diff, and ~17% of raw findings were another dimension's finding restated (a lower bound — it counts only duplication someone explicitly flagged). Downstream the effect is larger: on one PR `fix-review` collapsed 43 posted threads into 25 distinct fixes, writing one shared reply across multiple threads ten times; a single bug was reported independently by five dimensions and another by four. Workers were already doing this ad hoc and inconsistently — 0%, 5%, 13% and 15% dedup rates across the four runs — and two of the four reported no merges at all while posting duplicates that `fix-review` then had to reconcile.
- **Trade-off**: Adds a judgment pass over the merged findings array at the point where the worker's context is already largest, and a wrong merge loses a genuinely distinct finding — which is why the rule keeps the clearest instance and folds detail in rather than discarding, and why the collapsed count is reported rather than silent. Reporting `0` explicitly is deliberate: it distinguishes a run that looked and found nothing from one that never looked.
- **Date**: 2026-09-06
- **Status**: superseded by AD-009

### CPR-AD-003
- **Decision**: Fifteen changes from a four-session `session-evaluate` audit, in four groups. **Corrections of text that was wrong:** `agentType` → `subagent_type` (the tool's real parameter, and Batch Mode already used the correct name, so the file contradicted itself); every `run_in_background` reference deleted, since the `Agent` tool has no such parameter and every dispatch is asynchronous; the claim built on it that "Single PR Mode's Step 2 subagent is synchronous and returns before the conversation continues" replaced with the truth, that its subagent is equally long-lived and routable; and the Guardrails advice to blame a short comment count on pagination replaced, since the real cause is the silent hunk-drop below and checking pagination first sends a run down a dead end. **Posting Mechanics gains** step 3a (validate every anchor against the PR's diff hunks before batching; re-anchor with a note, or mark unpostable, never drop), step 3b (the one `gh` invocation shape that works, with six confirmed-failing forms named), a ban on re-issuing a posting mutation for any reason, a ban on placeholder content and on `printf`-escaping `%`, two further failure shapes in step 4 (200-with-a-real-id-but-nothing-persists, and a local classifier denial that never reached GitHub), a restated `author: $me` invariant, and a new mandatory step 6 reconciling the review's real comment count against what was intended. **Step 2 gains** a mechanical inline-if-you-are-a-subagent rule, an Agent Wait Protocol pointer that must also be restated in the dispatched subagent's own prompt, and a requirement that the dispatch prompt carry Posting Mechanics inline rather than by name. **The return-shape contract** now carries three counts through every relay hop — re-anchored, unpostable, collapsed — plus verbatim relay of a Complex-tier caveat. Also added: a note on how this file's own `../../templates/` links resolve, and that the Reply-Review Filter is Batch-Mode-only. `templates/github-pr-review-mode.md` separately defines `line` as the source-file line at PR head, never a diff-artifact offset.
- **Reason**: Each traces to measured behaviour across four real `build-feature` PRs. Two runs each lost 9 of 44 findings to the silent hunk-drop, one of them a Critical, and detection depended on an agent choosing to run an unprompted verification query. One run duplicated 9 comments by re-sending an identical batch just to read its error text. One took six attempts and ~5 minutes to find a working `gh` invocation. The Agent Wait Protocol was referenced only from Batch Mode, so Single PR Mode's subagent — which fans out 5–9 dimension agents of its own — had no wait rule: one run spent 31 consecutive turns on `echo "waiting"`, 4.36M tokens, 15.8% of its budget, for no output. The dispatch prompt named Posting Mechanics without supplying it, costing one run ~1.2M tokens and 8 round-trips of `find` probes and a full self-re-read to recover it. The unconditional second dispatch cost 715k–820k tokens and 20–24 minutes of idle relay on every measured run, and the fix uses `fix-review`'s AD-006 mechanical form deliberately, because the self-classifying version of that rule was already proven unreliable there. The relay dropped 8 re-anchored findings including a Critical because the closed return-shape contract had no field for them.
- **Trade-off**: Posting Mechanics is materially longer, and step 3a adds a diff-hunk fetch plus a per-finding check before any batch — real cost on every publishing run, accepted because the alternative is silently losing a fifth of the findings with no error to notice. Step 6's reconciliation adds one query per run. The inline-if-subagent rule removes a layer of context isolation on the `build-feature` path; that is the point, since the wrapper it removes held nothing but the dispatch, but it does mean a future caller that dispatches this skill *and* has other work in its context must not be a subagent itself, or it will get inline execution it did not want.
- **Date**: 2026-09-06
- **Status**: active

### CPR-AD-004
- **Decision**: Two trims from the 2026-09-12 `harness-eval` run (`docs/HARNESS-EVALUATION.md` rows #11-#12). (1) Collapse Examples 1, 2, 6, 7, 8 in `## Examples` to single-line traces of the form "Example N: `<input>` → `<mode>`, proceeds as Step X" — Examples 5, 10, 11 are left as full walkthroughs. (2) Single-source the report-string phrasing template: Single PR Mode Step 3 stays the one place the full template is spelled out; Examples 4, 5, and 10's Publish Mode step now say "reports per its own template (see Step 3: Report)" instead of reprinting the string.
- **Reason**: Both judges in the harness-eval Track B run scored Examples 1/2/6/7/8 REDUNDANT-GENERAL at cost 0 — each is a mechanical one-line replay of the mode-detection/repo-resolution rule already stated once in Step 1, with no independent information (claims `C001`, `C108/C113/C126/C133/C138/C143`, 14 one-line mode-detection traces). Examples 5, 10, 11 were scored KEEP-COMPRESSED by both judges, since each combines multiple cross-section rules and would take real effort to reassemble — left untouched. Separately, `C112`'s report-string phrasing template was found repeated verbatim across 5 locations (`C083/C112/C121/C125/C156`); collapsing Example 1 under item (1) removed the `C112` copy directly, leaving `C121`, `C125`, `C156` to be re-pointed at the canonical `C083` copy (Single PR Mode Step 3).
- **Trade-off**: The collapsed examples no longer show the concrete banner text (finding counts, complexity tiers) inline — a reader now has to open Step 3 to see the exact phrasing, in exchange for not maintaining five copies of the same string that could drift independently (Step 3's own copy is the only one anyone needs to keep current).
- **Date**: 2026-09-12
- **Status**: superseded by AD-009

### CPR-AD-005
- **Decision**: Replaced the `[gh Account Resolution](../../templates/gh-account-resolution.md)` reference with a one-line `gh` account resolution: opt-in tag. The mechanism itself moved to the user's global `CLAUDE.md` (`CLAUDE.global.md`, symlinked to `~/.claude/CLAUDE.md`) as a standing rule; this skill only states its own opt-in application decision now.
- **Reason**: Same rationale as `build-feature`'s AD-009 — the `gh` multi-account mechanism is a fact about the user's own environment, not this skill, so it belongs in global `CLAUDE.md` (closing the ad-hoc-`gh`-usage gap outside all consuming skills); only the per-skill mandatory/opt-in decision stays local.
- **Trade-off**: Same as `build-feature`'s AD-009 — this tag depends on the user's global `CLAUDE.md` being loaded wherever this skill runs.
- **Date**: 2026-09-13
- **Status**: active

### CPR-AD-010
- **Decision**: Replace the three `templates/subagent-models.md` / `templates/subagent-dispatch-contract.md` links (Guardrails Sonnet-pin, dispatch contract, and effort-parameter note) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked files.
- **Trade-off**: Same dependency as `code-review`'s AD-007 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active

### CPR-AD-011
- **Decision**: Replace the three `templates/agent-wait-protocol.md` links (Step 2's wait instruction, Batch Mode's per-PR wait, and Single PR Mode's Step 2 wait) with references to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch` (see `skills/subagent-dispatch/STATE.md` AD-002) alongside the content already consolidated there (AD-010).
- **Trade-off**: Same dependency as AD-010 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active
