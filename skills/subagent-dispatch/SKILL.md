---
name: subagent-dispatch
description: Reference for creating a subagent via the `Agent` tool — the two hard facts about the tool (model is one of four literal aliases, never a versioned ID; no reasoning-effort parameter), the four-field dispatch-prompt contract (completion condition, observability prefix/scale estimate, return shape, delegation depth), the protocol for waiting on a dispatched subagent without polling or false-stall detection, and this project's model-tier matrix for named pipeline sites. Load before writing an `Agent` call, dispatching or waiting on a subagent, or setting its `model` — in build-feature, code-review, architecture-evaluate, session-evaluate, tlc-spec-driven, or an ad hoc dispatch. Do NOT use for designing a new named, persistent subagent persona (frontmatter, system prompt, tool grants) — that's subagent-creator; this governs how an already-decided dispatch is written and waited on, not whether a new subagent type should exist.
license: CC-BY-4.0
metadata:
  author: flaviostudart@gmail.com
  version: 1.1.0
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

Applies once a dispatch needs to know when the subagent finishes before continuing — a single dispatch carries the same risk as a fan-out of several. Out of scope: a subagent invoked via the `Skill` tool rather than a direct `Agent` call — that skill's own dispatch, if it has any, already owns its own wait handling.

1. **After dispatching, do nothing else.** No polling loop (`sleep`/`echo` in Bash, repeated `Monitor` or status-check calls) to watch for completion. If N agents were dispatched, expect N notifications, in whatever order they actually finish — collect each result as its notification arrives, whether that means proceeding once every one has reported or acting on each one as it lands (the dispatching skill's own step defines which).

2. **Waiting costs zero tool calls — end the turn with plain text and nothing else.** The notification wakes the conversation on its own; nothing has to be called to make that happen, and no tool call is needed to "hand the turn back". A no-op placeholder (`true`, `echo`, `:`, an empty `Monitor`) is the same anti-pattern as polling and carries the same per-call price — a hundred of them is a hundred full context re-sends, not a hundred free ones. If a turn has nothing to do but wait, say so in one line and stop.

3. **Never infer a stall from an idle transcript or a quiet task list.** A finished agent looks the same as a stalled one by that measure.

4. **If a notification hasn't arrived after a generous ceiling** (the dispatching skill's own step sets this — as a default, 15 minutes for a single-purpose subagent, longer for one doing substantial file work), confirm the agent is actually still running with one non-blocking `TaskOutput(task_id, block: false)` call before treating it as stalled.

5. **Never call `TaskStop` on an agent whose status wasn't just confirmed** via step 4. A dimension, finding set, or fix that an agent genuinely completed must never be dropped because the wait for it was mishandled.

### Waiting on a Clock, Not an Agent

Sometimes the wait is for wall-clock time rather than a subagent — a rate-limit cooldown, a deliberate pace between API batches. Foreground `sleep` is blocked, and that block is exactly what tempts a session into a yield loop: one no-op call every two seconds until enough time has passed. That is the same mistake, in its most expensive form — a three-minute cooldown spent this way cost 183 calls in one real run.

Spend **one** call on the whole interval instead: `Monitor` with a single plain sleeping command (`sleep 180 && echo done`, `timeout_ms` a little above the sleep). It returns immediately with a task id and notifies when the sleep ends — so end the turn right there and wait for that event exactly as for an agent. Keep the command plain: a worktree-isolated session refuses compound loops (`while`/`$(( ))`), a plain `sleep` it accepts.

**This section is for a clock, never for an agent.** If what you are waiting on is a dispatched subagent, none of it applies: that agent's notification already arrives on its own, so a `Monitor` sleep adds a second thing to wait for and buys nothing. Reaching for it there is not a compliant substitute for the wait rules above — it is their violation wearing a sanctioned mechanism. One real run of the standalone fix skill that preceded `code-review`'s fix stage made exactly that substitution: 23 `Monitor{sleep 600}` calls, each killed by a `TaskStop` the moment a real completion notification arrived — 44 turns whose only purpose was to wait. Alongside 169 `Bash: echo idle` calls in the same invocation, **46% of its turns produced nothing**, at roughly 187k of context re-sent per turn. A `Monitor` sleep is correct only when the thing being waited on is time itself.

### Why This Matters

An `Agent` tool call runs in the background and delivers its own task notification the instant it finishes — that notification is what "done" means, and it costs nothing to wait for. Left unspecified, orchestrators invent their own wait: a Bash `sleep`/`echo` loop, or repeated `Monitor`/status-check calls, polling for a completion that was already going to arrive on its own. Every one of those calls re-sends the full accumulated conversation as cached input — in one real run this was the single largest cost driver for the entire skill invocation, an order of magnitude more expensive than the actual review work.

The second failure doesn't look like polling at all: emitting a **no-op tool call purely to end the turn** — `Bash true`, `echo waiting`, a `Monitor` heartbeat, whatever the description calls "yield turn". It feels free, because it does nothing and returns instantly. It costs exactly what a poll costs: the whole conversation, re-sent, per call. In one real `build-feature` run, 345 of these burned **77.6M input tokens** waiting — 327 of them inside a single run of that fix skill, roughly 30% of that invocation's entire cost, spent on `true`.

The third, sharper failure: treating a quiet transcript as evidence of a stall. A **finished** agent's transcript stops growing too — that's indistinguishable from a stalled one by size or elapsed time alone. Acting on that false signal (stopping the agent, retrying, discarding its output) has thrown away already-completed, valid work — twice, on two independent passes, in a real run — and the recovery afterward cost more than either wasted pass.

## This Project's Model Matrix

The four items above apply to any `Agent` dispatch, anywhere. If the dispatch site is one of this project's own named pipeline steps — `build-feature`, `code-review`, `architecture-evaluate`, `session-evaluate`, or `tlc-spec-driven` — read [references/model-matrix.md](references/model-matrix.md) for the exact tier required at that specific site before setting `model`. A dispatch outside that list has no matrix row; pick the tier the work actually needs and apply the two hard facts above.

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
