---
name: session-evaluate
description: Analyzes a completed agent session transcript for performance and workflow inefficiencies — token waste, oversized tool results, cache thrash, slow turns, missed tool parallelism, context lost to compaction, runaway or serially-launched subagents, self-corrected mistakes (wrong commands/tools/assumptions caught mid-session), mechanical repetition that could become a script in the affected skill, and full test-suite runs disproportionate to the change's actual scope — either across the whole session by default or scoped to one or more named skills within it on request — then reports every finding grouped by fix-target skill and dimension, ranked by a priority that weighs token/runtime gain over correctness fixes, plus a verification section (time and tokens spent per skill invocation, and every full test-suite run detected with its timing and files touched), asks for approval, and applies the approved fixes as guideline edits to the responsible skill or project context file (script-shaped findings are reported only, never auto-applied). Metrics come from a deterministic script so the transcript itself never floods the context; a large session's classification work fans out to one Sonnet subagent per finding dimension, mirroring how code-review parallelizes across review dimensions. Use when the user says "evaluate session", "analyze this session", "session postmortem", "why did that session burn so many tokens", "why was that session slow", "optimize my agent workflow", "evaluate how <skill> did in that session", or invokes /session-evaluate. Do NOT use for reviewing application code (use code-review) or for authoring a new skill from scratch (use skill-architect).
license: CC-BY-4.0
metadata:
  author: flaviostudart@gmail.com
  version: 1.7.0
---

# Session Evaluate

Turns a recorded agent session into a ranked list of performance and workflow defects, each with the evidence that proves it and a concrete guideline fix — then, once approved, applies those fixes. Evaluates the whole session by default, or one or more named skills within it on request.

## Role

Adopt this persona for the entire skill: *"I'm an engineer doing a performance postmortem on an agent run. I report what the numbers prove, not what I suspect."* Every finding is backed by a metric from the digest. A claim you cannot point a number at does not get written down.

## Guardrails

**Transcripts are read-only, always.** Read, grep, and parse session files freely. Never write to, move, or delete anything under `~/.claude/projects/`.

**Never act on the analyzed session's project.** A session from another repository is evidence about a *skill*, not a licence to touch that repository's code, branches, or PRs. Findings change skill definitions and context files here; nothing else.

**Never interact with the session itself.** Do not resume, message, steer, or interrupt the analyzed session, even if it is still running.

**The apply scope is Markdown guidance only.** This skill's fixes are guideline edits to `SKILL.md` files, their `references/`, and project context files. A finding whose only real fix is a code change, a settings change, or a harness change is reported as **Informational** and is never applied. Do not stretch a finding to fit the apply scope.

**Never read the raw `.jsonl` with the Read tool.** These files run to several megabytes. All measurement goes through the script; targeted evidence goes through bounded `grep`. Loading a transcript into context to analyze token waste defeats the entire skill.

**Subagent Model (hard requirement).** Every subagent this skill dispatches — Step 6's single covering-agent or its per-dimension agents, in every tier — **must run on `sonnet`**, per [Subagent Models](../../templates/subagent-models.md), set explicitly on each `Agent` call and never inherited from the calling session. The `Agent` tool has no reasoning-effort parameter, so where a dimension needs more thoroughness than another, that's an instruction in the subagent's own prompt, never a model change.

## Memory

This skill keeps a lightweight, append-only memory of past runs at `.session-evaluate/` in this repo's root — git-ignored (see `.gitignore`), since these are local working notes, not tracked content. A completed run (one that reached Step 10) writes one file: `.session-evaluate/<YYYYMMDD-HHMM>_<session-name>.md`, where `<session-name>` is the evaluated session's custom title if it has one (sanitized to `[A-Za-z0-9_-]`), else the first 8 characters of its session id. Keep the format terse — a future instance of this skill reads it, not a person:

```
# <session-name> — <YYYY-MM-DD>

Project: <path>   Session: <id>   Mode: <Full|Scoped(<skills>)>   Tier: <Small|Medium|Large>

## Findings
- [<dimension letter>][<priority>] <title> → <fix target> — <Applied|Skipped|Informational|Pending>: <one-line outcome or reason>
```

Step 8 reads this directory (if it exists) to surface repeat offenders when presenting findings; Step 11 writes to it once a run is fully resolved. Skip both silently if `.session-evaluate/` doesn't exist yet — create it on first write, don't pre-create it on read.

## Instructions

### Step 1: Mode Detection

1. If the invocation names one or more specific skills to evaluate within the session (e.g. "evaluate how `fix-review` did in that session", "/session-evaluate this session for code-review and build-feature") — **Scoped Mode**: restrict the entire evaluation to those skills' invocation window(s) only. Every other skill invoked in the session is out of scope, not just deprioritized.
2. Otherwise — **Full Session Mode** (default): evaluate the whole session, every skill it invoked, exactly as this skill has always worked.

Scoped Mode changes what's measured, not how it's judged — the catalog, the priority formula, and the apply scope all apply identically in both modes.

### Step 2: Resolve the target session

Sessions live at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`, where `<encoded-cwd>` is the project's absolute path with every `/` replaced by `-`. Subagent transcripts live in `~/.claude/projects/<encoded-cwd>/<session-id>/subagents/*.jsonl` and are picked up automatically.

In every command below, `<skill-dir>` is this skill's own base directory — the path announced when the skill is invoked (`~/.claude/skills/session-evaluate`, a symlink into this repo).

Resolve in this order:

1. An explicit path or session id in the invocation — use it directly.
2. A project named in the invocation ("the last session in applyr") — list that project's sessions and take the most recent.
3. Nothing specified — list recent sessions and **ask which one**. Never pick silently.

```bash
python3 <skill-dir>/scripts/session_metrics.py --list --project /Users/me/Projects/foo --limit 15
python3 <skill-dir>/scripts/session_metrics.py --list --limit 20    # across all projects
```

Prefer a **finished** session. The currently-running session's transcript is still being written and its last turn is incomplete — if the user asks for the live session anyway, proceed but say that the tail is truncated.

### Step 3: Extract the digest

```bash
python3 <skill-dir>/scripts/session_metrics.py <path-to-session.jsonl> --top 10
```

In **Scoped Mode**, add `--skill <name>` once per named skill (repeatable):

```bash
python3 <skill-dir>/scripts/session_metrics.py <path-to-session.jsonl> --top 10 --skill fix-review --skill code-review
```

If the script reports "No invocation of `<name>` found in this session," stop and say so plainly, listing the skills it did detect (the script includes them in the same message) — do not fall back to Full Session Mode or guess a different name.

This is the only measurement pass. It emits a compact digest covering tokens and cache behaviour, per-tool spend, the heaviest individual calls, repeated identical calls, full test-suite runs detected, turn runtimes and the slowest turns, batching and parallelism, compaction events, subagent spend and concurrency, skills invoked, time and tokens per skill invocation, and failed tool calls.

Read the digest. Do not re-run the script with different flags hoping for something new — raise `--top` only if a ranked table is visibly truncating a pattern you need. In Scoped Mode, every number in the digest is already confined to the named skill's window(s) — the script did the scoping, so nothing here needs filtering again by hand.

### Step 4: Pull the mandatory D1 evidence pass

**Always run the D1 grep pass** (self-corrected mistakes — see `references/findings-catalog.md`) before assessing complexity, regardless of tier. This dimension has no digest table, so this grep is its only discovery mechanism — skipping it leaves the whole dimension unchecked, and Step 5 needs its result to know whether dimension D is active.

```bash
grep -inoE '"text":"[^"]{0,400}\b(mistake|that.?s wrong|incorrect|should have (used|run|done)|my bad|let me (fix|correct|redo)|actually,? the (right|correct) way)\b[^"]{0,400}"' <session.jsonl>
```

In Scoped Mode, `grep` has no timestamp filter — discard any match whose surrounding turn falls outside the scoped skill's invocation window(s) before treating it as a D1 candidate.

Every other bounded evidence pull (typically to establish whether a run of calls was genuinely independent — see B1/C3 in the catalog) is finding-specific, not global: it happens during classification in Step 6, by whichever path performs it, not as a separate universal step here.

```bash
grep -o '"name":"[A-Za-z]*"' <session.jsonl> | head -60
grep -c 'some-pattern' <session.jsonl>
```

Keep every excerpt small and purposeful. If you find yourself pulling repeatedly, the finding is probably not provable — drop it rather than padding it with speculation.

### Step 5: Complexity assessment

Using the (possibly scoped) digest's `records` line — specifically the **total** (main + subagent records, already summed on that line) — and whether each catalog dimension shows any candidate signal at all, decide how Step 6 executes. This mirrors `code-review`'s own Step 5 — the same two axes, adapted to a transcript instead of a diff.

**Size tier → execution mode:**

| Tier | Condition (post-scoping) | Execution mode |
| --- | --- | --- |
| Small | <1,500 total records | **Inline** — evaluate directly, 0 agents |
| Medium | 1,500-5,000 total records | **Single agent** — 1 subagent covers every active dimension |
| Large | >5,000 total records | **Parallel** — 1 subagent per active dimension, dispatched together |

Use the **total** figure, not the bare main-thread `records` count — a heavily-delegated session (e.g. `build-feature`) can look small at the top level while its subagents did most of the actual work; the total is what the digest's own line already adds up.

**Calibrated against two real sessions** (2026-09-01), not guessed from first principles:

- **Large anchor:** a `build-feature` run (2,905 main records + 4,871 subagent records = 7,776 total; 601 assistant turns; 44 subagent transcripts; max concurrency 15; 5 skills invoked over 4h10m). Unambiguously Large — the Large cutoff sits ~2,800 total records of bandwidth below this anchor so sessions meaningfully smaller than this one extreme case still route correctly, rather than the boundary sitting exactly on the one sample available.
- **Small anchor:** a long single-thread session with no subagent delegation at all (858 total records over 1h44m). Unambiguously Small/Inline despite its length — record volume, not wall-clock time, is what drives the tier.
- **Medium is not yet confirmed by a real sample** — it's the gap between the two anchors, not derived from an observed medium session. If a session lands there, treat the tier assignment as a hypothesis and note in the report whether Single-agent execution actually matched the evidence-gathering cost Step 6 needed; adjust the boundary if it consistently doesn't.

**Active dimensions** — a dimension is active only if the digest (or the Step 4 grep pass) shows at least one candidate; an idle dimension is never dispatched:

| Dimension | Active if... |
| --- | --- |
| A. Token consumption | `Heaviest individual calls` has an entry over ~15k tokens, `Repeated identical calls` is non-empty, or cache/context metrics cross their thresholds |
| B. Runtime | `Batching / parallelism` or `Slowest turns` shows a qualifying pattern |
| C. Workflow and orchestration | `Context loss`, `Subagents`, or `Failed tool calls` shows a qualifying pattern |
| D. Mistakes and corrections | Step 4's D1 grep pass found at least one confirmed candidate |
| E. Automation candidates | `Tool spend` shows a tool called 5+ times (the E1 threshold) |
| F. Test-scope violations | `Full test-suite runs` is non-empty |

Print a one-line banner before Step 6 begins, the same way `code-review` does:

```
📊 Session evaluate — Complexity: **<Tier>** (<N> total records, <span>) · Active: <dimension letters> · <execution description>
```

Example: `📊 Session evaluate — Complexity: **Large** (11,400 total records, 2h14m) · Active: A, B, D, F · Parallel — 4 agents`

If no dimension is active, say the session was clean (citing the digest numbers that show it — see Example 2) and stop; there is nothing for Step 6 to dispatch.

### Step 6: Dispatch

Execute Step 5's plan. Every mode applies the same **Classification & Priority Procedure** below — only *who* performs it changes.

#### Classification & Priority Procedure

*Classify.* Read `references/findings-catalog.md` (in full for Inline/Single-agent; only the assigned dimension's section for a Parallel-tier subagent — see below). Match each digest signal — and each confirmed D1 grep match — to a finding class, apply its threshold, and discard anything in the catalog's **Non-findings** section. Two rules that kill most bad findings:

- **A metric is not a finding.** "Cache hit ratio 78%" is an observation. It becomes a finding only once you can state the cause and a fix.
- **Expensive is not wasteful.** Judge cost per unit of outcome. A session that spent heavily and delivered proportionately has no finding.

*Attribute.* Work out what would have to change. Use the digest's `Skills invoked` line, the subagent launch descriptions, and the file paths in the heaviest calls to identify which skill governed the wasteful stretch.

| Attributed to | Where the fix goes |
| --- | --- |
| Another project's repository | **Never edited.** Report only. |
| A globally-installed or vendor skill's installed copy | **Never edited.** Route to the `extended/` overlay below, or report if no overlay is possible. |
| A local skill (`skills/<name>/` in this repo) | Its `SKILL.md`, or a file in its `references/` |
| A vendor skill (`tech-leads-club`, `matt-pocock`) | `extended/<name>/` overlay in this repo — additions only, mirroring the parent's structure |
| No governing skill; general agent behaviour | `AGENTS.md` / `CLAUDE.md`, or the relevant `docs/codebase/` file |
| Nothing fixable in Markdown | Mark **Informational** — reported, never applied |

Check `config/skills.json` for a skill's `source` before proposing an edit to it. Editing an installed vendor or global skill directly is prohibited by this repository's rules.

*Judge recurrence.* The target file is already open for attribution — while it's in front of you, judge whether the wasteful call sits on the skill's unconditional flow (**Structural** — it fires on every invocation, not just this session) or was triggered by this session's particular input, branch, or edge case (**Incidental** — may not recur). This costs no extra tool calls.

*Compute priority.* Findings are ordered by expected future gain, not by their raw single-session magnitude — token reduction and runtime improvement outrank correctness fixes of the same size. Rank via **Affected aspects** and **Severity**:

| Gain rank | Affected aspects |
| --- | --- |
| A (highest) | Tokens, Cost, Runtime |
| B | Context integrity |
| C (lowest) | Correctness |

| Priority | Rule |
| --- | --- |
| P0 | Rank A + High severity |
| P1 | Rank A + Medium, or Rank B + High |
| P2 | Rank B + Medium, or Rank C + High |
| P3 | Everything else (Info, no numeric gain, user-caused) |

A **Structural** finding is bumped one tier toward P0 (P3→P2, P2→P1, P1→P0; P0 stays P0). Severity stays as the magnitude label inside each finding's block; Priority is the sort key Step 8 uses.

#### Small — Inline (0 agents)

Perform the procedure above yourself, directly in this conversation, across every active dimension. This is exactly how the skill worked before tiering existed — most invocations land here.

#### Medium — Single agent (1 agent, all active dimensions)

Dispatch **one** subagent (`Agent` tool, `model: sonnet`) whose prompt includes: the full digest, `references/findings-catalog.md` in full, the Step 4 D1 grep results, and the Classification & Priority Procedure above verbatim. Its task: apply the procedure across every active dimension and return findings in the shape Step 7 expects — nothing else. It never touches skill files or GitHub.

#### Large — Parallel (one agent per active dimension)

Fire one subagent per active dimension, **in a single message, never sequentially** (`Agent` tool, `model: sonnet` each). Each receives: the full digest, only its assigned dimension's section of `references/findings-catalog.md`, the Step 4 D1 grep results (only if dimension D is its assignment), and the Classification & Priority Procedure above verbatim. Each subagent applies the procedure to its dimension only and returns findings in the same fixed shape. None of them touch skill files or GitHub — Step 9 (Apply) happens later, in this conversation, after approval.

**Read [Agent Wait Protocol](../../templates/agent-wait-protocol.md) in full before the first dispatch, not once the first wait has already started.** Wait for every dispatched dimension agent to report before moving to Step 7; the 15-minute default stall ceiling applies (each dimension agent is single-purpose).

**Subagent return shape** (Medium and Large tiers): a list of findings, each carrying dimension, title, context, metrics, affected aspects, severity, recurrence, root cause, proposed solution, and the attributed fix-target skill/file — everything Step 7/8 need, pre-computed.

### Step 7: Consolidation

Inline mode has nothing to consolidate — go directly to Step 8 with what Step 6 produced.

For Single-agent and Parallel modes: merge every returned finding into one list. If a dimension's subagent failed or timed out (see the Wait Protocol), mark that dimension `⚠️ not executed — <reason>` in the report rather than silently omitting it — a dimension that never ran is not the same as a dimension with nothing to report. Do not retry a failed dimension automatically; note it and continue with what the others returned.

### Step 8: Present the findings and ask for approval

**Check memory for related past findings first.** If `.session-evaluate/` exists, grep its files (`grep -li` for each finding's fix-target skill name and dimension letter — cheap, bounded, no need to read a whole file unless a name matches) for prior runs that touched the same skill/dimension. A match is worth surfacing inline in that finding's block as `**Seen before:** <file>, <date> — <one-line prior outcome>` — a fix that was applied before and the same waste shows up again is a stronger signal (recurring despite a fix = the guideline didn't stick, or a new code path hit the same root cause) than a first occurrence, and is worth saying so explicitly. No match is not worth mentioning — don't pad a finding with "no prior occurrences found."

Group by fix target (skill), then by dimension — the catalog's A/B/C/D/E/F sections, rendered as "Token consumption" / "Runtime" / "Workflow and orchestration" / "Mistakes and corrections" / "Automation candidates" / "Test-scope violations" — sorted by Priority within each dimension. Use this exact shape.

**At a glance:**

| Skill | Dimension | # | Priority | Title | Metric | Recurrence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `skills/fix-review/SKILL.md` | Token consumption | 1 | P0 | 3 whole-file reads of the same 13k-token SKILL.md | 39k tok/session | Structural | Pending |
| `skills/code-review/SKILL.md` | Runtime | 2 | P1 | 50 consecutive single-call turns during the edit phase | ~6 min added latency | Incidental | Pending |
| — (user-triggered) | Workflow and orchestration | 3 | P3 | 2 manual compactions, 394k tokens dropped | 394k tok dropped | Incidental | Pending |

**Verification** (always included, straight from the digest — not gated by approval, not a finding):

- **Time & tokens by skill invocation** — relay the digest's `Time & tokens by skill invocation` table as-is (skill, wall time, input/output tokens, tool calls, any subagent work started inside that window). If the user wants a per-step breakdown within a given invocation and the skill announces its own step names in its visible output (e.g. "Step 3: ..."), grep that invocation's window for the target skill's own step headings (read from its `SKILL.md`, already open from Step 6's attribution) and report the split — label it explicitly as **estimated, inferred from step mentions in the transcript**, since the digest has no ground truth for where one step ends and the next begins. If the skill never names its steps in visible text, say the per-step split isn't available for that invocation rather than guessing one.
- **Full test-suite runs** — relay the digest's `Full test-suite runs` table in full (count, time, command, pass/fail, files touched since the last run), always, whether or not any row becomes an F1 finding. This is a heuristic pattern match, not exhaustive — say so. A row only becomes an F1 finding (see the catalog) when its `files touched` count is disproportionate to a full-suite run's cost; a full run on a genuinely cross-cutting change is not a finding (see Non-findings).

Then, grouped the same way (skill → dimension), one block per finding:

```
## <skill or fix-target path>

### <Dimension name>

#### N. [Title] — [Priority]

**Context:** What the session was doing when this happened, in one or two sentences.
**Metrics:** The exact numbers from the digest that prove it.
**Affected aspects:** Tokens / Runtime / Context integrity / Cost / Correctness.
**Severity:** High / Medium / Info — the single-session magnitude (see below).
**Recurrence:** Structural / Incidental, with the one-line reason.
**Root cause:** Why it happened — the missing or wrong guideline.
**Proposed solution:** The specific edit, naming the file and quoting the guideline text to add.
```

Severity: **High** = repeated or large-magnitude waste with a clear fix. **Medium** = real but bounded. **Info** = observed, no `.md` fix, or user-caused. Severity feeds Priority (Step 6) but does not replace it — sort and number findings by Priority, not Severity.

Set `Status` to `Informational` from the start for any finding whose only fix is code (E1's scripts, or any other class marked Informational in the catalog) — these never enter the approval offer below, regardless of their Priority. Every other finding starts `Pending`.

Then stop and ask which of the `Pending` findings to apply. Offer "all", "none", or a list of numbers. **Never apply anything before an explicit answer.** If the answer is ambiguous, ask again rather than guessing — an unwanted edit to a skill file is expensive to unwind.

### Step 9: Apply the approved fixes

Always performed here, in this conversation, sequentially, after approval — never dispatched to a subagent and never split across skills, regardless of which Step 6 tier produced the findings. The mutating step is small in volume and gated on a live human answer; there's nothing to parallelize.

For each approved finding:

1. Read the target file first. A proposed guideline is often already there in some form — in that case sharpen or relocate the existing line rather than adding a duplicate.
2. Make the edit surgical. Add the guideline where the agent will actually be reading at the moment it matters, not appended to the end of the file.
3. Write it as an instruction with its reason, not a rule shouted without context. `Read only the section you need (sed -n 'A,Bp') — this file is 13k tokens and whole-file reads have repeatedly blown the context budget.` beats `NEVER read whole files.`
4. Keep it additive. Do not restructure a skill, and do not touch anything the finding did not identify.
5. For a vendor skill, put the edit in `extended/<name>/` — mirroring the parent's document anatomy, additions only, never a fork of the vendor file.

Bump the `metadata.version` of any skill whose `SKILL.md` you edit.

### Step 10: Verify and report

State plainly what changed: files edited, guideline added to each, and which findings were skipped. If an approved finding turned out not to be applicable once you read the target file, say so and leave it unapplied — do not force a weak edit to close the loop.

Reprint the Step 8 at-a-glance table with its `Status` column updated per row — `Applied`, `Skipped`, or left `Pending` for anything not approved — instead of only narrating the outcome in prose.

Per this repository's workflow, commit and push the applied changes to `main` without waiting to be asked, using a Conventional Commits message.

### Step 11: Record the run in memory

Always run this step, whether the answer to Step 8 was "all", "none", or a partial list — the point is a durable record of what was found and decided, not just of what was applied. Write it after Step 10, once every decision and edit is final; never write a partial file mid-flow.

`mkdir -p .session-evaluate` (repo root) if it doesn't already exist, then write `.session-evaluate/<YYYYMMDD-HHMM>_<session-name>.md` per the [Memory](#memory) format — one line per finding (Pending/Informational findings included, not just Applied ones), each carrying its dimension letter, priority, title, fix target, and final status with a one-line reason. Do not narrate the investigation or repeat the digest — this file is a lookup table for Step 8's future memory search, not a second report.

## Examples

### Example 1: Named session, findings applied (Full Session Mode, Inline tier)

**User:** "evaluate session 3921ef51 and fix what you find"

1. Step 1: no skill named — Full Session Mode.
2. Resolve `~/.claude/projects/-Users-me-Projects-foo/3921ef51-....jsonl`.
3. Run the extractor; digest shows 4 reads of the same 13.2k-token file, a 50-turn single-call run, 340 total records — Small tier, Inline.
4. Classify: A2 (repeated identical work), B1 (missed parallelism).
5. Attribute both to `skills/fix-review/SKILL.md` (source `local` — directly editable).
6. Present 2 findings; user approves both.
7. Add a bounded-read guideline and a batching guideline to that skill; bump version; commit.

### Example 2: Nothing worth reporting

**User:** "/session-evaluate"

1. Step 1: no skill named — Full Session Mode.
2. No session specified — list recent sessions and ask.
3. Digest on the chosen session: 97% cache hit ratio, no compaction, no repeats, 6 tool calls — no dimension is active.
4. Report that the session was clean, cite the three numbers that show it, and stop. Do not manufacture findings to justify the run.

### Example 3: Finding outside the apply scope

Digest shows 9 permission denials for the same `gh` command shape. This is a settings problem, not a guideline problem — report it as **Informational**, point at the `update-config` skill and `fewer-permission-prompts`, and apply nothing.

### Example 4: Scoped Mode, one skill named

**User:** "evaluate how fix-review did in the last session in applyr"

1. Step 1: `fix-review` named — Scoped Mode.
2. Resolve the most recent session in the `applyr` project.
3. Run the extractor with `--skill fix-review`. It finds two `fix-review` invocations and returns a digest confined to those windows (612 records total) — Small tier, Inline.
4. Classify and attribute within that scope only — a large repeated-read pattern elsewhere in the session, outside `fix-review`'s windows, is invisible to this run by design.
5. Present findings scoped to `fix-review`; proceed as normal.

### Example 5: Large session, Parallel tier

**User:** "evaluate that build-feature session, it felt slow"

1. Step 1: no skill named — Full Session Mode.
2. Digest: 2,905 main + 4,871 subagent = 7,776 total records, 4h10m span — Large tier (this is the real calibration anchor from Step 5). Active dimensions: A (11 identical `cd .../SKILL.md` reads), C (one manual compaction dropping 312.8k tokens; max subagent concurrency 15), F (heuristic found none here, but would activate on a session that ran one).
3. Print the complexity banner, then dispatch 2 Sonnet subagents in one message, one per active dimension, each with the shared digest and its own catalog section.
4. Wait per the Agent Wait Protocol; both report back. Step 7 merges their findings into one list.
5. Present the consolidated report exactly as Example 1's Step 6 would, grouped by skill and dimension.

## Troubleshooting

**`Not a file` / no transcripts found.** The encoded directory name is the project's absolute path with `/` → `-`, including the leading `/` (so it starts with `-`). Run `--list` without `--project` to see every project, and confirm the session was run from the path you assumed.

**Digest shows `transcripts found` far above `Agent/Task launches`.** Subagents launched their own subagents. Expected for orchestration skills like `build-feature`; see C4 in the catalog before calling it a defect.

**`Skills invoked: none detected`.** Skills entered via injected context rather than the `Skill` tool are not always recorded. Fall back to attributing via the subagent launch descriptions and the file paths in the heaviest calls — do not conclude that no skill was involved. In Scoped Mode this also means `--skill <name>` will report no match even though the skill clearly ran — say so rather than guessing, and fall back to Full Session Mode only if the user agrees.

**Batching numbers look impossible** (every response single-call). The script groups tool calls by `requestId` because Claude Code writes one assistant record per content block. If a transcript predates that field, batching metrics are unreliable — say so and skip B1 rather than reporting a false finding.

**Turn count far below tool-call count.** `turn_duration` records are not emitted for every turn. Runtime percentiles cover only recorded turns; treat them as a sample, and do not present `total` turn time as the session's wall clock.

**A skill invocation's window looks too long or too short.** `Time & tokens by skill invocation` windows run from one `Skill`/slash-command call to the next (or session end) — a skill that launches a `run_in_background: true` subagent and keeps working shows the subagent's time inside its own window, but if that subagent is still running when the *next* skill is invoked, its remaining time lands in the next skill's window instead. Note this rather than treating either number as exact when a background subagent spans a boundary.

**`Full test-suite runs` missed a command, or flagged one that wasn't full-suite.** The detector is a fixed pattern list matched against `call['label']`, which truncates Bash commands at 100 characters — an unusual test runner, a wrapped script, or a long command line past that cutoff won't match. Treat the table as a candidate list to sanity-check against the actual command, not an exhaustive or infallible count.

**A Parallel-tier dimension agent comes back empty or off-topic.** It was likely given the whole catalog instead of just its assigned dimension's section, or the digest wasn't included in its prompt. Re-check the dispatch prompt against Step 6's Parallel description before assuming the dimension genuinely had nothing.
