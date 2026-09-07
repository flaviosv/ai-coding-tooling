# STATE

## Decisions

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
