# Findings Catalog

Diagnostic heuristics for `session-evaluate`. Read this after the digest is on screen, then match each digest signal against the classes below.

Every class states: the **signal** (where it shows up in the digest), the **threshold** that makes it worth reporting, what it **implies**, and the **fix shape** — the kind of guideline edit that actually closes it. Only findings with a viable `.md` fix shape go into the Apply set; the rest are reported as Informational.

Thresholds are defaults, not laws. A threshold crossed for a defensible reason is not a finding — say why and drop it.

## Contents

- [A. Token consumption](#a-token-consumption)
- [B. Runtime](#b-runtime)
- [C. Workflow and orchestration](#c-workflow-and-orchestration)
- [D. Mistakes and corrections](#d-mistakes-and-corrections)
- [E. Automation candidates](#e-automation-candidates)
- [F. Test-scope violations](#f-test-scope-violations)
- [G. Non-findings](#g-non-findings)

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

## D. Mistakes and corrections

Unlike A/B/C, this dimension has no digest table — the signal is textual, not numeric. Run the dedicated grep pass from Step 3 every session, not just when a finding needs it; skipping it means this whole dimension goes unchecked.

### D1 — Self-corrected mistake

**Signal:** A bounded grep pass over the transcript for correction language, scanning `text` (assistant/user turns), `prompt`, and `description` (an `Agent`/`Task` tool's own dispatch fields — where an orchestrator names a prior failure when launching a recovery subagent, and `text`-only scanning structurally cannot see it), e.g.:
```
grep -inoE '"(text|prompt|description)":"[^"]{0,400}\b(mistake|that.?s wrong|incorrect|should have (used|run|done)|my bad|let me (fix|correct|redo)|actually,? the (right|correct) way|left (the |it |the branch |the codebase )?in an? broken|left .{0,40}broken state|leftover .{0,30}(marker|conflict)|prior .{0,40}(pass|run) left|still (failing|broken)|broken state)\b[^"]{0,400}"' <session.jsonl>
```
Every match is a candidate, not a finding — read the surrounding turn to confirm it names a real wrong action and a specific right one. Discard incidental phrasing (documentation text, a hypothetical, a mistake that was the user's own rather than the agent's command/tool/assumption choice). A `prompt`/`description` hit naming a prior skill's broken output is a *stronger* candidate than most `text` hits: it's not the agent second-guessing itself mid-thought, it's a downstream check (another skill, or a later validation step) catching a real defect the responsible skill's own process missed — usually worth a higher severity for exactly that reason.

**Implies:** The agent (or a skill it ran) took a wrong action — wrong command, wrong tool, wrong file, wrong assumption, or a process step with no final-state validation — and either it, the user, or a later step in the same session caught it. The correction that resolved it is exactly the guideline a future session is currently missing.

**Fix shape:** State the correct approach as an explicit, specific guideline in the responsible skill, placed at the point where the wrong path was taken — name the wrong action and the right one plainly enough that the same wrong turn can't recur. Apply the same duplicate-check as any other fix (Step 7) — sharpen an existing line rather than adding a near-duplicate.

**Affected aspects:** Correctness by default (Rank C in Step 5's priority table). If the wrong action also burned tokens or time to recover from (e.g. it triggered a large re-read or a redone phase), tag the token/runtime aspect too and let the higher rank apply.

---

## E. Automation candidates

### E1 — Scriptable repetition

**Signal:** `Tool spend` / call counts show one tool invoked many times in the session (5+ is a working default) with **varying** labels/targets but the same *shape* — same tool, same kind of input, same kind of transformation each time (N `Edit` calls each making the same one-line change in a different file, N `Bash` calls each fetching a different URL with the same flags, N `Read`+`Edit` pairs walking a fixed file list). Confirm with a bounded grep sample of those calls' inputs (Step 3) — if the sample shows no case-by-case judgment between calls (no branching on content, no different action taken per result), it's mechanical.

**Implies:** Work with no per-call decision content is pure round-trip overhead — every one of the N calls paid full prompt/response framing (and a full model turn) for a transformation a short script performs in one call. This is a different waste than A2 (identical repeated work): here every call is legitimately doing *something different*, just following a fixed pattern.

**Fix shape:** Not Markdown guidance — **always Informational**, per this skill's apply scope (a script is code, not a guideline). Report it in full: the loop's shape, its inputs, a one-line spec of the script that would replace it and where it would live (`skills/<name>/scripts/`), and how many round-trips it collapses into one. Building it is left to the user or a follow-up request — Step 7 never writes code, regardless of approval.

**Affected aspects:** Tokens and Runtime (Rank A). Severity and Priority still follow the normal Step 5 table by magnitude (N and per-call size) — a large N deserves a high Priority number even though it can never move past Informational — but the at-a-glance `Status` column is set to `Informational` from the start, not `Pending`, since Step 7 cannot act on it.

---

## F. Test-scope violations

### F1 — Full-suite run disproportionate to change scope

**Signal:** The digest's `Full test-suite runs` table, specifically `files touched since last run` — a full-suite invocation where that count is small (1-2 files, especially docs/single-module touches) relative to the cost of running the whole suite. Cross-check the actual file paths against `Heaviest individual calls`/`Tool spend` to confirm they're narrow and unrelated to shared code, not just few in number.

**Implies:** The governing skill (or the agent's own judgment at that point) defaulted to full-suite verification where a scoped test run would have proven the same thing just as well — the exact over-verification pattern the user's own Test Execution Scope convention exists to prevent. Every unwarranted full run pays the whole suite's runtime and token cost for a change that didn't need it.

**Fix shape:** Add or sharpen a test-scoping guideline in the responsible skill's verification step, naming the specific full-suite command it ran and the scoped alternative it should have used instead (the targeted test file/pattern covering the files actually touched). If the skill already defers to a shared scope-decision convention (e.g. `~/.claude/templates/test-execution-scope.md`) and still ran the full suite, the fix is tightening the skill's own instruction to actually invoke that convention at the point of verification — not restating the convention itself.

**Affected aspects:** Runtime and Tokens (Rank A) — the full run's own cost is the magnitude; severity scales with how disproportionate the run was (files touched vs. suite size/duration), not with the raw run count.

---

## G. Non-findings

Do not report these. Each one burns the user's attention for nothing:

- A threshold crossed once in a short session — small samples are noise.
- Sequential calls that were genuinely dependent (see B1, C3).
- Token spend that bought a proportionate result. Expensive is not the same as wasteful; the question is always cost *per unit of outcome*.
- Anything whose only fix is a code change to a tool, the harness, or the CLI — this skill's apply scope is `.md` guidance only.
- Restating the digest. A metric is not a finding until it has a cause and a fix.
- Speculation about intent that the transcript does not support. If the evidence is not in the digest or a targeted excerpt, do not assert it.
- Ordinary edit-test-fix iteration (see D1). A test failing and getting fixed is normal development, not a mistake — only report a wrong *action* (wrong command, tool, file, assumption), not a wrong first draft of code under test.
- A repeated tool call that involved real per-call judgment — a different action taken depending on what the previous result showed (see E1). That's normal iterative work, not a scriptable loop.
- A full-suite run following a genuinely cross-cutting change — shared modules, several subsystems, a contract between components (see F1). The Test Execution Scope convention explicitly calls for widening in that case; a high `files touched` count next to the run is what should stop F1 from firing, not the presence of a full-suite command by itself.
