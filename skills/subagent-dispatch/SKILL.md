---
name: subagent-dispatch
description: Reference for creating a subagent via the `Agent` tool — the two hard facts about the tool itself (model is one of four literal aliases, never a versioned ID; there is no reasoning-effort parameter), the four-field contract every dispatch prompt must carry (completion condition, observability prefix and scale estimate, return shape, delegation depth), and a pointer to this project's own model-tier matrix for named pipeline dispatch sites. Load before writing any `Agent` call, dispatching a subagent, spinning one up, or setting its `model` — inside build-feature, code-review, complete-review, fix-review, tests-code-review, architecture-evaluate, session-evaluate, tlc-spec-driven, or an ad hoc one-off dispatch. Do NOT use for designing a new named, persistent subagent persona (its own frontmatter, system prompt, tool grants) — that's subagent-creator; this skill governs how an already-decided dispatch call is written, not whether a new subagent type should exist.
license: CC-BY-4.0
metadata:
  author: flaviostudart@gmail.com
  version: 1.0.0
---

# Subagent Dispatch

The calling convention every `Agent`-tool dispatch in this project follows: which model to set, what the dispatch prompt must state, and how to wait for the result. A dispatching skill states its own step-specific completion condition and scale estimate; it points here for everything else rather than restating it.

## Two Hard Facts About the `Agent` Tool

**1. `model` takes one of four short aliases, verbatim: `sonnet`, `opus`, `haiku`, `fable`.** Never resolve an alias into a versioned model ID (`claude-haiku-4-5-…`, `claude-sonnet-5`, …) on the way to the call, however confidently the environment advertises one — the param only accepts the four aliases, so a versioned ID fails input validation and the subagent never starts. A launch rejected that way did nothing at all — no worktree, no checkout, no commit — so correct the param and relaunch; it doesn't consume any retry the dispatching skill allows.

**2. There is no reasoning-effort parameter.** Effort cannot be set on a dispatch. Where a step wants high effort, the only mechanism is an explicit instruction in the subagent's own prompt (e.g. "work at high effort: be thorough, verify every finding against the actual diff before including it"). Treat that as steering, not as a knob — two dispatch sites on the same model differ only by what their prompts say, never by cost or capability. When a step genuinely needs a different tier, change the **model**, not the prose.

A skill that dispatches an `Agent` **must** set `model` explicitly. Never omit it to let a subagent inherit the calling session's model — a dispatch site's tier is a property of the work, not of whoever happened to invoke it.

## The Dispatch Contract

Every `Agent` dispatch prompt states four things:

**1. Completion condition.** Tied to a concrete, checkable artifact — a file that now exists, a test suite that now passes, an API state that now reflects the intended change — never "when you're done" or "when you feel confident." If the work has a claimed end-state (a build that compiles, a set of GitHub threads marked resolved), the completion condition includes **verifying that end-state directly**, not just having attempted the actions that should produce it: "resolved" is true because a re-fetch shows `isResolved: true`, not because the mutation calls were made.

**2. Observability prefix and scale estimate — informational only, never a stop condition.** Open the prompt with a self-identifying tag (`[<skill>][phase:<name>]` or similar) so the dispatch is attributable after the fact, even when its cost lands inside another skill's wall-clock window. Alongside it, state a rough expected scale ("~1 tool call per finding", "on the order of 20-30 calls for a feature this size") purely so a human monitoring the run has a number to judge against. Never instruct the subagent to stop, truncate, or report partial results because it crossed this number — a human decides if something is taking too long; the subagent's job is to finish the completion condition.
- Wrong: "Stop at ~80 tool calls and report what remains unfinished."
- Right: "This is typically ~80 tool calls for a feature this size — if you're running far outside that range, say so in your final report, but keep working toward the completion condition regardless."

**3. Return shape.** Structured and bounded, not free prose: a `status` (`ok` / `blocked` / `question`), the artifacts produced (file paths, PR number, commit SHAs), and a `question`/`blocker` field for anything requiring a decision the subagent can't make itself. No inlined file contents, no diff excerpts over a few lines, no restating context the dispatcher already has. A skill that already documents its own return-shape convention should point to that convention rather than duplicate the wording here — the shapes are the same thing.

**4. Delegation depth.** State explicitly whether the dispatched agent may itself dispatch further subagents, and to what depth. Default to **no** unless the work genuinely requires it (e.g. a per-task or per-file fan-out that's already independent and bounded). When nesting is intentional, say so and say how deep, rather than leaving it to be discovered after the fact.

## Waiting on a Dispatched Subagent

If this dispatch needs to know when the subagent finishes before continuing — a single dispatch carries the same risk as a fan-out of several — load and apply [Agent Wait Protocol](../../templates/agent-wait-protocol.md) rather than inventing your own "wait for it to return" wording. Out of scope: a subagent invoked via the `Skill` tool rather than a direct `Agent` call — that skill's own dispatch, if it has any, already owns its own wait handling.

## This Project's Model Matrix

The four items above apply to any `Agent` dispatch, anywhere. If the dispatch site is one of this project's own named pipeline steps — `build-feature`, `code-review`, `complete-review`, `fix-review`, `tests-code-review`, `architecture-evaluate`, `session-evaluate`, or `tlc-spec-driven` — read [references/model-matrix.md](references/model-matrix.md) for the exact tier required at that specific site before setting `model`. A dispatch outside that list has no matrix row; pick the tier the work actually needs and apply the two hard facts above.

## Guardrails

### Scope
- Do not resolve a model alias into a versioned model ID before the call.
- Do not omit `model` on a dispatch to let a subagent inherit the calling session's model.
- Do not invent free-prose wait or return-shape wording where this contract already defines the shape.
- Do not use this skill to design a new persistent subagent's persona — use `subagent-creator` for that; this skill starts once the decision to dispatch is already made.

## Examples

### Example 1: a named pipeline site

`code-review` is about to dispatch a Step 6 dimension subagent. `references/model-matrix.md` names `sonnet` for this site regardless of what model the calling session runs on. The prompt opens with `[code-review][dimension:security]`, states a completion condition ("every checklist item in `## Before You Begin` checked against the diff, findings written and tagged"), a scale estimate ("~1 tool call per file touched by this dimension"), a return shape (findings only, tagged by dimension — never the diff itself), and delegation depth (none).

### Example 2: an ad hoc one-off dispatch

A session needs a single subagent to investigate a bug with no named pipeline site to look up. There's no matrix row, so the two hard facts and the four-field contract still apply directly: pick `sonnet` or `opus` based on how much reasoning the investigation needs, set it explicitly, and write the prompt with a completion condition ("root cause identified and confirmed by reproducing the failure"), an observability prefix, a bounded return shape (root cause, evidence, affected files — not a transcript), and delegation depth stated as none.
