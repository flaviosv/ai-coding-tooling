---
name: session-evaluate
description: Analyzes a completed agent session transcript for performance and workflow inefficiencies — token waste, oversized tool results, cache thrash, slow turns, missed tool parallelism, context lost to compaction, runaway or serially-launched subagents, self-corrected mistakes (wrong commands/tools/assumptions caught mid-session), mechanical repetition that could become a script in the affected skill, and full test-suite runs disproportionate to the change's actual scope — then reports every finding grouped by fix-target skill and dimension, ranked by a priority that weighs token/runtime gain over correctness fixes, plus a verification section (time and tokens spent per skill invocation, and every full test-suite run detected with its timing and files touched), asks for approval, and applies the approved fixes as guideline edits to the responsible skill or project context file (script-shaped findings are reported only, never auto-applied). Metrics come from a deterministic script so the transcript itself never floods the context. Use when the user says "evaluate session", "analyze this session", "session postmortem", "why did that session burn so many tokens", "why was that session slow", "optimize my agent workflow", or invokes /session-evaluate. Do NOT use for reviewing application code (use code-review) or for authoring a new skill from scratch (use skill-architect).
license: CC-BY-4.0
metadata:
  author: flaviostudart@gmail.com
  version: 1.4.0
---

# Session Evaluate

Turns a recorded agent session into a ranked list of performance and workflow defects, each with the evidence that proves it and a concrete guideline fix — then, once approved, applies those fixes.

## Role

Adopt this persona for the entire skill: *"I'm an engineer doing a performance postmortem on an agent run. I report what the numbers prove, not what I suspect."* Every finding is backed by a metric from the digest. A claim you cannot point a number at does not get written down.

## Guardrails

**Transcripts are read-only, always.** Read, grep, and parse session files freely. Never write to, move, or delete anything under `~/.claude/projects/`.

**Never act on the analyzed session's project.** A session from another repository is evidence about a *skill*, not a licence to touch that repository's code, branches, or PRs. Findings change skill definitions and context files here; nothing else.

**Never interact with the session itself.** Do not resume, message, steer, or interrupt the analyzed session, even if it is still running.

**The apply scope is Markdown guidance only.** This skill's fixes are guideline edits to `SKILL.md` files, their `references/`, and project context files. A finding whose only real fix is a code change, a settings change, or a harness change is reported as **Informational** and is never applied. Do not stretch a finding to fit the apply scope.

**Never read the raw `.jsonl` with the Read tool.** These files run to several megabytes. All measurement goes through the script; targeted evidence goes through bounded `grep`. Loading a transcript into context to analyze token waste defeats the entire skill.

## Instructions

### Step 1: Resolve the target session

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

### Step 2: Extract the digest

```bash
python3 <skill-dir>/scripts/session_metrics.py <path-to-session.jsonl> --top 10
```

This is the only measurement pass. It emits a compact digest covering tokens and cache behaviour, per-tool spend, the heaviest individual calls, repeated identical calls, full test-suite runs detected, turn runtimes and the slowest turns, batching and parallelism, compaction events, subagent spend and concurrency, skills invoked, time and tokens per skill invocation, and failed tool calls.

Read the digest. Do not re-run the script with different flags hoping for something new — raise `--top` only if a ranked table is visibly truncating a pattern you need.

### Step 3: Pull bounded evidence, only where a finding needs it

Most findings are complete from the digest alone. When one is not — typically to establish whether a run of calls was genuinely independent (see B1/C3 in the catalog) — pull a narrow excerpt with `grep`, never a full read:

```bash
grep -o '"name":"[A-Za-z]*"' <session.jsonl> | head -60
grep -c 'some-pattern' <session.jsonl>
```

Keep every excerpt small and purposeful. If you find yourself pulling repeatedly, the finding is probably not provable — drop it rather than padding it with speculation.

**Always also run the D1 grep pass** (self-corrected mistakes — see `references/findings-catalog.md`), even when every other finding was complete from the digest. This dimension has no digest table, so this grep is its only discovery mechanism, not a confirmatory extra — skipping it leaves the whole dimension unchecked.

### Step 4: Classify against the catalog

Read `references/findings-catalog.md` now. Match each digest signal — and each confirmed D1 grep match from Step 3 — to a finding class, apply its threshold, and discard anything in the catalog's **Non-findings** section.

Two rules that kill most bad findings:

- **A metric is not a finding.** "Cache hit ratio 78%" is an observation. It becomes a finding only once you can state the cause and a fix.
- **Expensive is not wasteful.** Judge cost per unit of outcome. A session that spent heavily and delivered proportionately has no finding.

### Step 5: Attribute each finding to a fix target, judge recurrence, and compute priority

Work out what would have to change. Use the digest's `Skills invoked` line, the subagent launch descriptions, and the file paths in the heaviest calls to identify which skill governed the wasteful stretch.

| Attributed to | Where the fix goes |
| --- | --- |
| Another project's repository | **Never edited.** Report only. |
| A globally-installed or vendor skill's installed copy | **Never edited.** Route to the `extended/` overlay below, or report if no overlay is possible. |
| A local skill (`skills/<name>/` in this repo) | Its `SKILL.md`, or a file in its `references/` |
| A vendor skill (`tech-leads-club`, `matt-pocock`) | `extended/<name>/` overlay in this repo — additions only, mirroring the parent's structure |
| No governing skill; general agent behaviour | `AGENTS.md` / `CLAUDE.md`, or the relevant `docs/codebase/` file |
| Nothing fixable in Markdown | Mark **Informational** — reported, never applied |

Check `config/skills.json` for a skill's `source` before proposing an edit to it. Editing an installed vendor or global skill directly is prohibited by this repository's rules.

**Recurrence.** The target file is already open for attribution — while it's in front of you, judge whether the wasteful call sits on the skill's unconditional flow (**Structural** — it fires on every invocation, not just this session) or was triggered by this session's particular input, branch, or edge case (**Incidental** — may not recur). This costs no extra tool calls.

**Priority.** Findings are ordered by expected future gain, not by their raw single-session magnitude — token reduction and runtime improvement outrank correctness fixes of the same size. Rank via **Affected aspects** and **Severity**:

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

A **Structural** finding is bumped one tier toward P0 (P3→P2, P2→P1, P1→P0; P0 stays P0) — a repeat that will recur on every future invocation is worth more than the same single-session number from a one-off. Severity stays as the magnitude label inside each finding's block; Priority is the sort key everything else in Step 6 uses.

### Step 6: Present the findings and ask for approval

Group by fix target (skill), then by dimension — the catalog's A/B/C/D/E/F sections, rendered as "Token consumption" / "Runtime" / "Workflow and orchestration" / "Mistakes and corrections" / "Automation candidates" / "Test-scope violations" — sorted by Priority within each dimension. Use this exact shape.

**At a glance:**

| Skill | Dimension | # | Priority | Title | Metric | Recurrence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `skills/fix-review/SKILL.md` | Token consumption | 1 | P0 | 3 whole-file reads of the same 13k-token SKILL.md | 39k tok/session | Structural | Pending |
| `skills/code-review/SKILL.md` | Runtime | 2 | P1 | 50 consecutive single-call turns during the edit phase | ~6 min added latency | Incidental | Pending |
| — (user-triggered) | Workflow and orchestration | 3 | P3 | 2 manual compactions, 394k tokens dropped | 394k tok dropped | Incidental | Pending |

**Verification** (always included, straight from the digest — not gated by approval, not a finding):

- **Time & tokens by skill invocation** — relay the digest's `Time & tokens by skill invocation` table as-is (skill, wall time, input/output tokens, tool calls, any subagent work started inside that window). If the user wants a per-step breakdown within a given invocation and the skill announces its own step names in its visible output (e.g. "Step 3: ..."), grep that invocation's window for the target skill's own step headings (read from its `SKILL.md`, already open from Step 5) and report the split — label it explicitly as **estimated, inferred from step mentions in the transcript**, since the digest has no ground truth for where one step ends and the next begins. If the skill never names its steps in visible text, say the per-step split isn't available for that invocation rather than guessing one.
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

Severity: **High** = repeated or large-magnitude waste with a clear fix. **Medium** = real but bounded. **Info** = observed, no `.md` fix, or user-caused. Severity feeds Priority (Step 5) but does not replace it — sort and number findings by Priority, not Severity.

Set `Status` to `Informational` from the start for any finding whose only fix is code (E1's scripts, or any other class marked Informational in the catalog) — these never enter the approval offer below, regardless of their Priority. Every other finding starts `Pending`.

Then stop and ask which of the `Pending` findings to apply. Offer "all", "none", or a list of numbers. **Never apply anything before an explicit answer.** If the answer is ambiguous, ask again rather than guessing — an unwanted edit to a skill file is expensive to unwind.

### Step 7: Apply the approved fixes

For each approved finding:

1. Read the target file first. A proposed guideline is often already there in some form — in that case sharpen or relocate the existing line rather than adding a duplicate.
2. Make the edit surgical. Add the guideline where the agent will actually be reading at the moment it matters, not appended to the end of the file.
3. Write it as an instruction with its reason, not a rule shouted without context. `Read only the section you need (sed -n 'A,Bp') — this file is 13k tokens and whole-file reads have repeatedly blown the context budget.` beats `NEVER read whole files.`
4. Keep it additive. Do not restructure a skill, and do not touch anything the finding did not identify.
5. For a vendor skill, put the edit in `extended/<name>/` — mirroring the parent's document anatomy, additions only, never a fork of the vendor file.

Bump the `metadata.version` of any skill whose `SKILL.md` you edit.

### Step 8: Verify and report

State plainly what changed: files edited, guideline added to each, and which findings were skipped. If an approved finding turned out not to be applicable once you read the target file, say so and leave it unapplied — do not force a weak edit to close the loop.

Reprint the Step 6 at-a-glance table with its `Status` column updated per row — `Applied`, `Skipped`, or left `Pending` for anything not approved — instead of only narrating the outcome in prose.

Per this repository's workflow, commit and push the applied changes to `main` without waiting to be asked, using a Conventional Commits message.

## Examples

### Example 1: Named session, findings applied

**User:** "evaluate session 3921ef51 and fix what you find"

1. Resolve `~/.claude/projects/-Users-me-Projects-foo/3921ef51-....jsonl`.
2. Run the extractor; digest shows 4 reads of the same 13.2k-token file and a 50-turn single-call run.
3. Classify: A2 (repeated identical work), B1 (missed parallelism).
4. Attribute both to `skills/fix-review/SKILL.md` (source `local` — directly editable).
5. Present 2 findings; user approves both.
6. Add a bounded-read guideline and a batching guideline to that skill; bump version; commit.

### Example 2: Nothing worth reporting

**User:** "/session-evaluate"

1. No session specified — list recent sessions and ask.
2. Digest on the chosen session: 97% cache hit ratio, no compaction, no repeats, 6 tool calls.
3. Report that the session was clean, cite the three numbers that show it, and stop. Do not manufacture findings to justify the run.

### Example 3: Finding outside the apply scope

Digest shows 9 permission denials for the same `gh` command shape. This is a settings problem, not a guideline problem — report it as **Informational**, point at the `update-config` skill and `fewer-permission-prompts`, and apply nothing.

## Troubleshooting

**`Not a file` / no transcripts found.** The encoded directory name is the project's absolute path with `/` → `-`, including the leading `/` (so it starts with `-`). Run `--list` without `--project` to see every project, and confirm the session was run from the path you assumed.

**Digest shows `transcripts found` far above `Agent/Task launches`.** Subagents launched their own subagents. Expected for orchestration skills like `build-feature`; see C4 in the catalog before calling it a defect.

**`Skills invoked: none detected`.** Skills entered via injected context rather than the `Skill` tool are not always recorded. Fall back to attributing via the subagent launch descriptions and the file paths in the heaviest calls — do not conclude that no skill was involved.

**Batching numbers look impossible** (every response single-call). The script groups tool calls by `requestId` because Claude Code writes one assistant record per content block. If a transcript predates that field, batching metrics are unreliable — say so and skip B1 rather than reporting a false finding.

**Turn count far below tool-call count.** `turn_duration` records are not emitted for every turn. Runtime percentiles cover only recorded turns; treat them as a sample, and do not present `total` turn time as the session's wall clock.

**A skill invocation's window looks too long or too short.** `Time & tokens by skill invocation` windows run from one `Skill`/slash-command call to the next (or session end) — a skill that launches a `run_in_background: true` subagent and keeps working shows the subagent's time inside its own window, but if that subagent is still running when the *next* skill is invoked, its remaining time lands in the next skill's window instead. Note this rather than treating either number as exact when a background subagent spans a boundary.

**`Full test-suite runs` missed a command, or flagged one that wasn't full-suite.** The detector is a fixed pattern list matched against `call['label']`, which truncates Bash commands at 100 characters — an unusual test runner, a wrapped script, or a long command line past that cutoff won't match. Treat the table as a candidate list to sanity-check against the actual command, not an exhaustive or infallible count.
