---
name: subagent-dispatch-contract
description: Shared shape every `Agent`-tool dispatch prompt should carry — a completion condition, an observability prefix and scale estimate, a bounded return shape, and an explicit delegation-depth statement — for any skill that dispatches one or more subagents.
type: template
---

## Why this exists

A dispatch prompt that only names the job ("review this PR", "run the Execute phase") leaves the subagent to invent its own stopping point, its own idea of what to report back, and its own judgment on whether it may delegate further. Measured consequences of that gap, from real runs: a review subagent run for 156 turns and 23.0M tokens with no completion condition to aim at; four phase subagents in one session couldn't be attributed to their own phase afterward because nothing in their prompt self-identified; and a `fix-review` run reported "40 threads fixed" while never having executed the GitHub-side reply/resolve calls it claimed, because nothing in its own return shape required it to verify that claim before reporting success. None of these are model failures — they're missing prompt structure.

This template is the fix: four things a dispatch prompt states, once, regardless of which skill is doing the dispatching. A skill adopts it by referencing this file at its dispatch section rather than restating the four fields in its own prose.

## The four fields

Every `Agent` dispatch prompt should state:

**1. Completion condition.** Tied to a concrete, checkable artifact — a file that now exists, a test suite that now passes, an API state that now reflects the intended change — never "when you're done" or "when you feel confident." If the work has a claimed end-state (a build that compiles, a set of GitHub threads marked resolved), the completion condition includes **verifying that end-state directly**, not just having attempted the actions that should produce it. This is what would have caught the `fix-review` gap above: "resolved" is not true because the mutation calls were made, it's true because a re-fetch shows `isResolved: true`.

**2. Observability prefix and scale estimate — informational only, never a stop condition.** Open the prompt with a self-identifying tag (`[<skill>][phase:<name>]` or similar) so the dispatch is attributable after the fact, even when its cost lands inside another skill's wall-clock window (see the Troubleshooting note in `session-evaluate`'s own `SKILL.md` about nested spend). Alongside it, state a rough expected scale for the work ("~1 tool call per finding", "on the order of 20-30 calls for a feature this size") purely so a human monitoring the run — via `/tasks`, a progress file, or watching notifications — has a number to judge against. **Never instruct the subagent to stop, truncate, or report partial results because it crossed this number.** A human actively monitoring long runs decides if something is taking too long; the subagent's job is to finish the completion condition, not to self-police a budget. State the estimate as calibration for the *observer*, explicitly not as a ceiling for the *agent*.
- Wrong: "Stop at ~80 tool calls and report what remains unfinished."
- Right: "This is typically ~80 tool calls for a feature this size — if you're running far outside that range, say so in your final report, but keep working toward the completion condition regardless."

**3. Return shape.** Structured and bounded, not free prose: a `status` (e.g. `ok` / `blocked` / `question`), the artifacts produced (file paths, PR number, commit SHAs — whatever the work calls for), and a `question` or `blocker` field for anything requiring a decision the subagent can't make itself. No inlined file contents, no diff excerpts over a few lines, no restating context the dispatcher already has. A skill that already documents its own return-shape convention (e.g. `build-feature`'s State ownership section) should point here rather than duplicate the wording — this template's shape and that convention are the same thing.

**4. Delegation depth.** State explicitly whether the dispatched agent may itself dispatch further subagents, and to what depth. Default to **no** unless the work genuinely requires it (e.g. a per-task or per-file fan-out that's already independent and bounded) — undeclared nesting is why a session can show `transcripts found` far exceeding `Agent`/`Task launches` with no way to attribute the gap (see `session-evaluate`'s C4). When nesting is intentional, say so and say how deep, rather than leaving it to be discovered after the fact.

## Adopting this in a skill

Reference this file at the point a skill documents its dispatch mechanics (a "State ownership" or "Guardrails" section is the usual place), and require every dispatch prompt at every call site to carry the four fields — don't restate them per call site if one central rule already covers every dispatch the skill makes. A skill whose subagents do meaningfully different kinds of work (e.g. `build-feature`'s phase dispatches vs. its merge-conflict-resolution dispatch) can state the completion condition and scale estimate per site while pointing to this file for the shape of what's required.
