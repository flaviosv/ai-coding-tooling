---
name: agent-wait-protocol
description: Shared protocol for waiting on background `Agent`-tool subagents — no manual polling, no false-stall detection — for any skill that dispatches one or more and then needs to know when they're done.
type: template
---

## Why this exists

An `Agent` tool call runs in the background and delivers its own task notification the instant it finishes — that notification is what "done" means, and it costs nothing to wait for. Left unspecified, orchestrators invent their own wait: a Bash `sleep`/`echo` loop, or repeated `Monitor`/status-check calls, polling for a completion that was already going to arrive on its own. Every one of those calls re-sends the full accumulated conversation as cached input — in one real run this was the single largest cost driver for the entire skill invocation, an order of magnitude more expensive than the actual review work.

The second failure doesn't look like polling at all: emitting a **no-op tool call purely to end the turn** — `Bash true`, `echo waiting`, a `Monitor` heartbeat, whatever the description calls "yield turn". It feels free, because it does nothing and returns instantly. It costs exactly what a poll costs: the whole conversation, re-sent, per call. In one real `build-feature` run, 345 of these burned **77.6M input tokens** waiting — 327 of them inside a single `fix-review` invocation, roughly 30% of that invocation's entire cost, spent on `true`.

The third, sharper failure: treating a quiet transcript as evidence of a stall. A **finished** agent's transcript stops growing too — that's indistinguishable from a stalled one by size or elapsed time alone. Acting on that false signal (stopping the agent, retrying, discarding its output) has thrown away already-completed, valid work — twice, on two independent passes, in a real run — and the recovery afterward cost more than either wasted pass.

## Protocol

1. **After dispatching, do nothing else.** No polling loop (`sleep`/`echo` in Bash, repeated `Monitor` or status-check calls) to watch for completion. If N agents were dispatched, expect N notifications, in whatever order they actually finish — collect each result as its notification arrives, whether that means proceeding once every one has reported or acting on each one as it lands (the dispatching skill's own step defines which).

2. **Waiting costs zero tool calls — end the turn with plain text and nothing else.** The notification wakes the conversation on its own; nothing has to be called to make that happen, and no tool call is needed to "hand the turn back". A no-op placeholder (`true`, `echo`, `:`, an empty `Monitor`) is the same anti-pattern as polling and carries the same per-call price — a hundred of them is a hundred full context re-sends, not a hundred free ones. If a turn has nothing to do but wait, say so in one line and stop.

3. **Never infer a stall from an idle transcript or a quiet task list.** A finished agent looks the same as a stalled one by that measure.

4. **If a notification hasn't arrived after a generous ceiling** (the dispatching skill's own step sets this — as a default, 15 minutes for a single-purpose subagent, longer for one doing substantial file work), confirm the agent is actually still running with one non-blocking `TaskOutput(task_id, block: false)` call before treating it as stalled.

5. **Never call `TaskStop` on an agent whose status wasn't just confirmed** via step 4. A dimension, finding set, or fix that an agent genuinely completed must never be dropped because the wait for it was mishandled.

## Waiting on a clock, not an agent

Sometimes the wait is for wall-clock time rather than a subagent — a rate-limit cooldown, a deliberate pace between API batches. Foreground `sleep` is blocked, and that block is exactly what tempts a session into a yield loop: one no-op call every two seconds until enough time has passed. That is the same mistake, in its most expensive form — a three-minute cooldown spent this way cost 183 calls in one real run.

Spend **one** call on the whole interval instead: `Monitor` with a single plain sleeping command (`sleep 180 && echo done`, `timeout_ms` a little above the sleep). It returns immediately with a task id and notifies when the sleep ends — so end the turn right there and wait for that event exactly as for an agent. Keep the command plain: a worktree-isolated session refuses compound loops (`while`/`$(( ))`), a plain `sleep` it accepts.
