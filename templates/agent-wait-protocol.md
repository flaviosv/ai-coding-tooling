---
name: agent-wait-protocol
description: Shared protocol for waiting on background `Agent`-tool subagents — no manual polling, no false-stall detection — for any skill that dispatches one or more and then needs to know when they're done.
type: template
---

## Why this exists

An `Agent` tool call runs in the background and delivers its own task notification the instant it finishes — that notification is what "done" means, and it costs nothing to wait for. Left unspecified, orchestrators invent their own wait: a Bash `sleep`/`echo` loop, or repeated `Monitor`/status-check calls, polling for a completion that was already going to arrive on its own. Every one of those calls re-sends the full accumulated conversation as cached input — in one real run this was the single largest cost driver for the entire skill invocation, an order of magnitude more expensive than the actual review work.

The second, sharper failure: treating a quiet transcript as evidence of a stall. A **finished** agent's transcript stops growing too — that's indistinguishable from a stalled one by size or elapsed time alone. Acting on that false signal (stopping the agent, retrying, discarding its output) has thrown away already-completed, valid work — twice, on two independent passes, in a real run — and the recovery afterward cost more than either wasted pass.

## Protocol

1. **After dispatching, do nothing else.** No polling loop (`sleep`/`echo` in Bash, repeated `Monitor` or status-check calls) to watch for completion. If N agents were dispatched, expect N notifications, in whatever order they actually finish — collect each result as its notification arrives, whether that means proceeding once every one has reported or acting on each one as it lands (the dispatching skill's own step defines which).

2. **Never infer a stall from an idle transcript or a quiet task list.** A finished agent looks the same as a stalled one by that measure.

3. **If a notification hasn't arrived after a generous ceiling** (the dispatching skill's own step sets this — as a default, 15 minutes for a single-purpose subagent, longer for one doing substantial file work), confirm the agent is actually still running with one non-blocking `TaskOutput(task_id, block: false)` call before treating it as stalled.

4. **Never call `TaskStop` on an agent whose status wasn't just confirmed** via step 3. A dimension, finding set, or fix that an agent genuinely completed must never be dropped because the wait for it was mishandled.
