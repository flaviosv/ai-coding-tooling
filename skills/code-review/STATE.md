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
