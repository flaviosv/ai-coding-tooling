---
name: subagent-dispatch
description: Reference for the lifecycle of a subagent created via the `Agent` tool — the hard facts about the tool (model is one of four literal aliases, never a versioned ID; concurrent subagents are capped; the agent type goes in `subagent_type` and is never `fork`), the four-field dispatch-prompt contract (completion condition, observability prefix/scale estimate, return shape, delegation depth), and the protocol for waiting on a dispatched subagent without polling or stopping it early. Load before writing an `Agent` call, dispatching or waiting on a subagent, or setting its `model`. Do NOT use for designing a new named, persistent subagent persona (frontmatter, system prompt, tool grants); this governs how an already-decided dispatch is written and waited on, not whether a new subagent type should exist.
license: CC-BY-4.0
metadata:
  author: flaviostudart@gmail.com
  version: 2.0.0
---

# Subagent Dispatch

The calling convention every `Agent`-tool dispatch follows: how to set the model and agent type, what the dispatch prompt must state, and how to wait for the result. A dispatching skill states its own step-specific model tier, completion condition, and scale estimate; it points here for everything else rather than restating it.

## Hard Facts About the `Agent` Tool

**1. `model` takes one of four short aliases, verbatim: `sonnet`, `opus`, `haiku`, `fable`.** Never resolve an alias into a versioned model ID (`claude-haiku-4-5-…`, `claude-sonnet-5`, …) on the way to the call, the param only accepts the four aliases, anthing different faills input validation and the subagent never starts. A launch rejected that way did nothing at all — no worktree, no checkout, no commit — so correct the param and relaunch; it doesn't consume any retry the dispatching skill allows.

**2. Concurrent subagents are capped.** The default is 20 running at once (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`); nesting depth is capped separately by `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`. On `Concurrent subagent limit reached`, don't retry immediately: launch the rest once your own running agents report, and never drop the unlaunched work.

**3. The agent type goes in `subagent_type`, never `agentType`.** Use `general-purpose` for skill work, and never `"fork"`: a fork inherits the parent's full context and model and ignores `model`, which floods the subagent's context and defeats the point of dispatching.

Set `model` explicitly on every dispatch, using one of the literal aliases above. Never omit it to let a subagent inherit the calling session's model — a dispatch's tier is a property of the work, not of whoever happened to invoke it. Each dispatching skill states its own tier at its dispatch site; an ad hoc dispatch picks the tier the work actually needs.what other types 

## The Dispatch Contract

Every `Agent` dispatch prompt states four things:

**1. Completion condition.** Tied to a concrete, checkable artifact — a file that now exists, a test suite that now passes, an API state that now reflects the intended change — never "when you're done" or "when you feel confident." If the work has a claimed end-state (a build that compiles, a set of GitHub threads marked resolved), the completion condition includes **verifying that end-state directly**, not just having attempted the actions that should produce it: "resolved" is true because a re-fetch shows `isResolved: true`, not because the mutation calls were made.

**2. Observability prefix and scale estimate — informational only, never a stop condition.** Open the prompt with a self-identifying tag (`[<skill>][phase:<name>]` or similar) so the dispatch is attributable after the fact, even when its cost lands inside another skill's wall-clock window. 

**3. Return shape.** Structured and bounded, not free prose: a `status` (`ok` / `blocked` / `question`), the artifacts produced (file paths, PR number, commit SHAs), and a `question`/`blocker` field for anything requiring a decision the subagent can't make itself. No inlined file contents, no diff excerpts over a few lines, no restating context the dispatcher already has. A skill that already documents its own return-shape convention should point to that convention rather than duplicate the wording here — the shapes are the same thing.

**4. Delegation depth.** State explicitly whether the dispatched agent may itself dispatch further subagents, and to what depth. Default to **no** unless the work genuinely requires it (e.g. a per-task or per-file fan-out that's already independent and bounded). When nesting is intentional, say so and say how deep, rather than leaving it to be discovered after the fact. 

## Waiting on a Dispatched Subagent

Applies once a dispatch needs to know when the subagent finishes before continuing — a single dispatch carries the same risk as a fan-out of several. Out of scope: a subagent invoked via the `Skill` tool rather than a direct `Agent` call — that skill's own dispatch, if it has any, already owns its own wait handling.

1. **After dispatching, do nothing else.** No polling loop (`sleep`/`echo` in Bash, repeated `Monitor` or status-check calls) to watch for completion. Expect at least one notification per dispatched agent, in whatever order they actually finish: track completion by task id, and skip a repeat notification for an agent already collected. Collect each result as its notification arrives, whether that means proceeding once every agent has reported or acting on each one as it lands (the dispatching skill's own step defines which).

2. **Waiting costs zero tool calls — end the turn with plain text and nothing else.** The notification wakes the conversation on its own; nothing has to be called to make that happen, and no tool call is needed to "hand the turn back". A no-op placeholder (`true`, `echo`, `:`, an empty `Monitor`) is the same anti-pattern as polling and carries the same per-call price. If a turn has nothing to do but wait, say so in one line and stop.

3. **A subagent reports back when it finishes — never stop it early.** If one runs unusually long, tell the user in one line and keep waiting. Never stop or re-dispatch it without the user's go-ahead: an idle transcript or a quiet task list looks the same for a finished agent as for a stuck one, and work an agent genuinely completed must never be dropped because the wait for it was mishandled.

### Why This Matters

- **Polling:** every `sleep`/`echo` loop iteration or repeated `Monitor`/status-check call re-sends the full conversation, to watch for a notification that was already going to arrive on its own.
- **No-op yield calls:** a tool call made only to end the turn feels free but costs exactly what a poll costs.
- **Acting on silence:** a finished agent's transcript stops growing just like a stuck one's, so stopping, retrying, or discarding on that signal throws away completed work.

## Guardrails

- Do not invent free-prose wait or return-shape wording where this contract already defines the shape.

## Examples

### Example 1: a parallel fan-out

A skill is about to dispatch one analysis subagent per changed module. Its own step names `sonnet` as the tier, so every dispatch sets `subagent_type: general-purpose` and `model: sonnet` regardless of what model the calling session runs on. Each prompt opens with `[<skill>][module:<name>]`, states a completion condition ("every file in the module checked against the checklist, findings written and tagged"), a scale estimate ("~1 tool call per file in the module"), a return shape (findings only, tagged by module — never the diff itself), and delegation depth (none). If the fan-out exceeds the concurrency cap, the remaining dispatches launch as earlier ones report, tracked by task id.

### Example 2: an ad hoc one-off dispatch

A session needs a single subagent to investigate a bug, with no dispatching skill stating a tier. The hard facts and the four-field contract still apply directly: pick `sonnet` or `opus` based on how much reasoning the investigation needs, set it explicitly, and write the prompt with a completion condition ("root cause identified and confirmed by reproducing the failure"), an observability prefix, a bounded return shape (root cause, evidence, affected files — not a transcript), and delegation depth stated as none.

### Validation

Mandatory steps before dispatch the subagent, any invalid item from the checkilist must block the trigger of the subagent and responde with an error

- [ ] The subagent model is `sonnet`, `opus`, `haiuke` or `fable`, versioned model ID nor allowed, like `claude-sonnet-5`
- [ ] The subagent_type parameter is `general-purpose`