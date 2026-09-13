# STATE

## Decisions

> **Note on token figures.** Absolute token counts in the entries below were produced by
> `session-evaluate`'s `session_metrics.py` before the counting fix recorded in that skill's
> STATE.md AD-006, and are inflated by roughly 2x (measured 1.98x-2.64x, varying with per-turn
> parallelism). Counts, rates and shares — findings fixed, duplication rate, invalid rate, turn
> counts, share of spend — are unaffected, and no decision below rests on an absolute total.
> Read the token magnitudes as approximate and about half of what is written.

### AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) for Single PR Mode's review subagent and Batch Mode's per-PR subagents — explicit completion condition (PR's pending review posted, or findings returned when `human_review` withholds it), bounded return shape (already documented, now pointed at rather than restated), delegation depth (may invoke `code-review`/`tests-code-review` via `Skill`, no nesting beyond their own Step 6).
- **Reason**: A `session-evaluate` run against a real APLYR-19 build-feature session measured this skill's Single PR Mode dispatch at 156 turns / 23.0M tokens — the longest-running agent in the whole session — with no completion condition in its prompt beyond "review PR #N." Part of a repo-wide retrofit applied to every skill in `skills/` that dispatches subagents.
- **Trade-off**: None identified — this only adds structure to a prompt that was already being written by hand.
- **Date**: 2026-09-02
- **Status**: active

### AD-002
- **Decision**: Single PR Mode Step 2b must collapse same-root-cause duplicates across dimensions before posting, keeping the clearest instance of each cluster and folding the others' detail into it, and Step 2c must report the number of clusters collapsed (explicitly `0` when none). Framed as merging, never severity filtering — nothing is dropped for being minor, only for being another finding restated.
- **Reason**: Step 2b previously said only "merge both `comments` arrays into one," and the sole dedup rule anywhere in the skill is Posting Mechanics' exact `path`+`line`+`body` match against an existing pending review — which cannot catch two agents describing one defect in different words at different lines. Measurement across four real PRs shows that is the common case, not an edge case: `code-review` and `tests-code-review` fan out 5–9 agents over an overlapping diff, and ~17% of raw findings were another dimension's finding restated (a lower bound — it counts only duplication someone explicitly flagged). Downstream the effect is larger: on one PR `fix-review` collapsed 43 posted threads into 25 distinct fixes, writing one shared reply across multiple threads ten times; a single bug was reported independently by five dimensions and another by four. Workers were already doing this ad hoc and inconsistently — 0%, 5%, 13% and 15% dedup rates across the four runs — and two of the four reported no merges at all while posting duplicates that `fix-review` then had to reconcile.
- **Trade-off**: Adds a judgment pass over the merged findings array at the point where the worker's context is already largest, and a wrong merge loses a genuinely distinct finding — which is why the rule keeps the clearest instance and folds detail in rather than discarding, and why the collapsed count is reported rather than silent. Reporting `0` explicitly is deliberate: it distinguishes a run that looked and found nothing from one that never looked.
- **Date**: 2026-09-06
- **Status**: active

### AD-003
- **Decision**: Fifteen changes from a four-session `session-evaluate` audit, in four groups. **Corrections of text that was wrong:** `agentType` → `subagent_type` (the tool's real parameter, and Batch Mode already used the correct name, so the file contradicted itself); every `run_in_background` reference deleted, since the `Agent` tool has no such parameter and every dispatch is asynchronous; the claim built on it that "Single PR Mode's Step 2 subagent is synchronous and returns before the conversation continues" replaced with the truth, that its subagent is equally long-lived and routable; and the Guardrails advice to blame a short comment count on pagination replaced, since the real cause is the silent hunk-drop below and checking pagination first sends a run down a dead end. **Posting Mechanics gains** step 3a (validate every anchor against the PR's diff hunks before batching; re-anchor with a note, or mark unpostable, never drop), step 3b (the one `gh` invocation shape that works, with six confirmed-failing forms named), a ban on re-issuing a posting mutation for any reason, a ban on placeholder content and on `printf`-escaping `%`, two further failure shapes in step 4 (200-with-a-real-id-but-nothing-persists, and a local classifier denial that never reached GitHub), a restated `author: $me` invariant, and a new mandatory step 6 reconciling the review's real comment count against what was intended. **Step 2 gains** a mechanical inline-if-you-are-a-subagent rule, an Agent Wait Protocol pointer that must also be restated in the dispatched subagent's own prompt, and a requirement that the dispatch prompt carry Posting Mechanics inline rather than by name. **The return-shape contract** now carries three counts through every relay hop — re-anchored, unpostable, collapsed — plus verbatim relay of a Complex-tier caveat. Also added: a note on how this file's own `../../templates/` links resolve, and that the Reply-Review Filter is Batch-Mode-only. `templates/github-pr-review-mode.md` separately defines `line` as the source-file line at PR head, never a diff-artifact offset.
- **Reason**: Each traces to measured behaviour across four real `build-feature` PRs. Two runs each lost 9 of 44 findings to the silent hunk-drop, one of them a Critical, and detection depended on an agent choosing to run an unprompted verification query. One run duplicated 9 comments by re-sending an identical batch just to read its error text. One took six attempts and ~5 minutes to find a working `gh` invocation. The Agent Wait Protocol was referenced only from Batch Mode, so Single PR Mode's subagent — which fans out 5–9 dimension agents of its own — had no wait rule: one run spent 31 consecutive turns on `echo "waiting"`, 4.36M tokens, 15.8% of its budget, for no output. The dispatch prompt named Posting Mechanics without supplying it, costing one run ~1.2M tokens and 8 round-trips of `find` probes and a full self-re-read to recover it. The unconditional second dispatch cost 715k–820k tokens and 20–24 minutes of idle relay on every measured run, and the fix uses `fix-review`'s AD-006 mechanical form deliberately, because the self-classifying version of that rule was already proven unreliable there. The relay dropped 8 re-anchored findings including a Critical because the closed return-shape contract had no field for them.
- **Trade-off**: Posting Mechanics is materially longer, and step 3a adds a diff-hunk fetch plus a per-finding check before any batch — real cost on every publishing run, accepted because the alternative is silently losing a fifth of the findings with no error to notice. Step 6's reconciliation adds one query per run. The inline-if-subagent rule removes a layer of context isolation on the `build-feature` path; that is the point, since the wrapper it removes held nothing but the dispatch, but it does mean a future caller that dispatches this skill *and* has other work in its context must not be a subagent itself, or it will get inline execution it did not want.
- **Date**: 2026-09-06
- **Status**: active

### AD-004
- **Decision**: Two trims from the 2026-09-12 `harness-eval` run (`docs/HARNESS-EVALUATION.md` rows #11-#12). (1) Collapse Examples 1, 2, 6, 7, 8 in `## Examples` to single-line traces of the form "Example N: `<input>` → `<mode>`, proceeds as Step X" — Examples 5, 10, 11 are left as full walkthroughs. (2) Single-source the report-string phrasing template: Single PR Mode Step 3 stays the one place the full template is spelled out; Examples 4, 5, and 10's Publish Mode step now say "reports per its own template (see Step 3: Report)" instead of reprinting the string.
- **Reason**: Both judges in the harness-eval Track B run scored Examples 1/2/6/7/8 REDUNDANT-GENERAL at cost 0 — each is a mechanical one-line replay of the mode-detection/repo-resolution rule already stated once in Step 1, with no independent information (claims `C001`, `C108/C113/C126/C133/C138/C143`, 14 one-line mode-detection traces). Examples 5, 10, 11 were scored KEEP-COMPRESSED by both judges, since each combines multiple cross-section rules and would take real effort to reassemble — left untouched. Separately, `C112`'s report-string phrasing template was found repeated verbatim across 5 locations (`C083/C112/C121/C125/C156`); collapsing Example 1 under item (1) removed the `C112` copy directly, leaving `C121`, `C125`, `C156` to be re-pointed at the canonical `C083` copy (Single PR Mode Step 3).
- **Trade-off**: The collapsed examples no longer show the concrete banner text (finding counts, complexity tiers) inline — a reader now has to open Step 3 to see the exact phrasing, in exchange for not maintaining five copies of the same string that could drift independently (Step 3's own copy is the only one anyone needs to keep current).
- **Date**: 2026-09-12
- **Status**: active

### AD-005
- **Decision**: Replaced the `[gh Account Resolution](../../templates/gh-account-resolution.md)` reference with a one-line `gh` account resolution: opt-in tag. The mechanism itself moved to the user's global `CLAUDE.md` (`CLAUDE.global.md`, symlinked to `~/.claude/CLAUDE.md`) as a standing rule; this skill only states its own opt-in application decision now.
- **Reason**: Same rationale as `build-feature`'s AD-009 — the `gh` multi-account mechanism is a fact about the user's own environment, not this skill, so it belongs in global `CLAUDE.md` (closing the ad-hoc-`gh`-usage gap outside all consuming skills); only the per-skill mandatory/opt-in decision stays local.
- **Trade-off**: Same as `build-feature`'s AD-009 — this tag depends on the user's global `CLAUDE.md` being loaded wherever this skill runs.
- **Date**: 2026-09-13
- **Status**: active

### AD-010
- **Decision**: Replace the three `templates/subagent-models.md` / `templates/subagent-dispatch-contract.md` links (Guardrails Sonnet-pin, dispatch contract, and effort-parameter note) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked files.
- **Trade-off**: Same dependency as `code-review`'s AD-007 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active

### AD-011
- **Decision**: Replace the three `templates/agent-wait-protocol.md` links (Step 2's wait instruction, Batch Mode's per-PR wait, and Single PR Mode's Step 2 wait) with references to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch` (see `skills/subagent-dispatch/STATE.md` AD-002) alongside the content already consolidated there (AD-010).
- **Trade-off**: Same dependency as AD-010 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active
