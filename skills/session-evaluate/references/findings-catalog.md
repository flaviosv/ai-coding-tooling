# Findings Catalog

Diagnostic heuristics for `session-evaluate`. Read this after the digest is on screen, then match each digest signal against the classes below.

Every class states: the **signal** (where it shows up in the digest), the **threshold** that makes it worth reporting, what it **implies**, and the **fix shape** — the kind of guideline edit that actually closes it. Only findings with a viable `.md` fix shape go into the Apply set; the rest are reported as Informational.

Thresholds are defaults, not laws. A threshold crossed for a defensible reason is not a finding — say why and drop it.

## Contents

- [A. Token consumption](#a-token-consumption)
- [B. Runtime](#b-runtime)
- [C. Workflow and orchestration](#c-workflow-and-orchestration)
- [D. Non-findings](#d-non-findings)

---

## A. Token consumption

### A1 — Oversized tool results landing in the caller's context

**Signal:** `Heaviest individual calls` — any single result over ~15k est. tokens. Also `Tool spend` where one tool's total dominates.

**Implies:** Raw material was pulled into the main context when a filtered read, a targeted `grep`, or a subagent would have returned the same conclusion at a fraction of the cost. The classic offenders are whole-file `Read`s of large docs, unbounded `git diff`, and `gh pr view` on a big PR.

**Fix shape:** Add a guideline to the responsible skill telling it to bound the read — `sed -n 'A,Bp'`, `grep` with context, `--json` with an explicit field list, `| head` — or to delegate the bulk read to a subagent that returns only findings. Name the specific call in the guideline so it is unambiguous.

### A2 — Repeated identical work

**Signal:** `Repeated identical calls` — same tool + same target 3 or more times.

**Implies:** The agent re-derived something it already had. Usually one of: no instruction to reuse an earlier result, a re-read after an edit that the harness already confirmed, or a loop where each pass re-establishes the same context.

**Fix shape:** A file-deduplication rule ("if you already read this file this session, use what is in context"), or an explicit instruction to capture the result once into a variable/scratch file. Note that the user's global `CLAUDE.md` already carries a deduplication directive — if a skill still repeats reads, the fix belongs in that skill, restating the rule at the point of use.

### A3 — Cache thrash

**Signal:** `cache hit ratio` under 85%, or `cache-write share` over 15%.

**Implies:** The stable prefix of the prompt keeps changing, so the cache is rebuilt instead of read. Common causes: a skill injecting volatile content (timestamps, `git status`, changing file lists) early in its instructions, or reference files being loaded mid-session in varying order.

**Fix shape:** Move volatile content later in the skill's flow; load reference files at a fixed, early point rather than opportunistically. Flag as Informational if the session was short — cache ratios are unstable below a few dozen turns.

### A4 — Context high-water mark

**Signal:** `peak context` above roughly 60% of the model's window.

**Implies:** The session was running close to the edge, which is what makes compaction (C1) inevitable later.

**Fix shape:** A guideline in the governing skill to offload a phase to a subagent, or to write intermediate state to a file and drop it from context. Pair this finding with C1 when both appear — they are usually one problem.

---

## B. Runtime

### B1 — Missed parallelism

**Signal:** `Batching / parallelism` — a high `single-call` share, and `longest consecutive run of single-call turns` above ~8.

**Implies:** Independent tool calls were issued one per round-trip, each paying full model latency. This is the single most common runtime finding.

**Critical caveat:** a long solo run is only a finding if the calls were genuinely **independent**. Sequential calls where each input depends on the previous output are correct and must not be reported. Verify by looking at the actual call sequence before writing the finding — check the `Slowest turns` tool mix and, if needed, grep the transcript for that window.

**Fix shape:** A batching guideline in the responsible skill naming the specific calls that should have gone out together ("read all three context files in one message"). Generic "batch your calls" advice is worthless — cite the actual sequence.

### B2 — Slow turns dominated by one tool

**Signal:** `Slowest turns` where a single turn exceeds several minutes and its tool mix is concentrated.

**Implies:** Either a genuinely long-running command, or a long serial chain inside one turn.

**Fix shape:** If a long-running command: a guideline to run it in the background and poll. If a serial chain: same fix as B1. If it is irreducibly slow work, report as Informational — not every slow turn is a defect.

### B3 — Unbatched deferred-tool loading

**Signal:** `ToolSearch` line showing calls that load a single tool, 2 or more times.

**Implies:** Each `ToolSearch` is a wasted round-trip. The harness explicitly instructs batching every expected tool into one `select:a,b,c` call.

**Fix shape:** A guideline in the skill that uses those tools, listing the exact tool set it needs so the skill loads them in one call.

---

## C. Workflow and orchestration

### C1 — Context loss from compaction

**Signal:** `Context loss (compaction)` with any row.

**Implies:** Distinguish sharply by `trigger`:
- `auto` — the session overflowed. This is a real defect: the governing skill let context grow past the window, and everything after the boundary lost fidelity. Look at `cumulative dropped` for the magnitude.
- `manual` — the user chose it. Much weaker signal; report only if it happened repeatedly, which suggests the workflow inherently outgrows its context.

**Fix shape:** Make the skill checkpoint durable state to a file (the way `build-feature` uses `progress.md`) so a compaction cannot destroy it, and/or delegate the context-heavy phase to a subagent. A skill that carries long-lived state only in conversation is the root cause.

### C2 — Runaway subagent

**Signal:** `Subagents` table — a single subagent with very high billed input (tens of millions) or a high turn count (over ~150).

**Implies:** The subagent was launched without a bounded objective and kept working. It also means its cost is invisible in the caller's own token line, so this is easy to miss without the digest.

**Fix shape:** A guideline tightening the launch prompt: a concrete completion condition, an explicit step budget, and a defined return shape. Vague delegation ("investigate X") is the usual root cause.

### C3 — Serial fan-out

**Signal:** `Agent/Task launches` of 3 or more with `max concurrency: 1`.

**Implies:** Independent subagents ran one after another when they could have run together.

**Same caveat as B1** — only a finding if the subagents were independent. A pipeline where each stage consumes the previous stage's output is correct.

**Fix shape:** A guideline instructing the skill to launch the independent set in a single message.

### C4 — Uncontrolled nesting

**Signal:** `transcripts found` substantially exceeding `Agent/Task launches`.

**Implies:** Subagents spawned their own subagents. The gap is the nesting. This can be legitimate, but it makes cost and failure modes hard to reason about.

**Fix shape:** A guideline stating whether the delegated agent may itself delegate, and to what depth. Report as Informational when the nesting was clearly by design.

### C5 — Recurring tool failures

**Signal:** `Failed tool calls` above roughly 5% of total calls, or the same failure repeating.

**Implies:** A knowable constraint the agent kept rediscovering — a symlink guard, a refused command shape, a missing flag, a permission denial.

**Fix shape:** Encode the constraint as a guideline so it is known up front. Repeated permission denials specifically may instead warrant a settings change — that is outside this skill's apply scope, so report it as Informational with a pointer to `update-config`.

---

## D. Non-findings

Do not report these. Each one burns the user's attention for nothing:

- A threshold crossed once in a short session — small samples are noise.
- Sequential calls that were genuinely dependent (see B1, C3).
- Token spend that bought a proportionate result. Expensive is not the same as wasteful; the question is always cost *per unit of outcome*.
- Anything whose only fix is a code change to a tool, the harness, or the CLI — this skill's apply scope is `.md` guidance only.
- Restating the digest. A metric is not a finding until it has a cause and a fix.
- Speculation about intent that the transcript does not support. If the evidence is not in the digest or a targeted excerpt, do not assert it.
