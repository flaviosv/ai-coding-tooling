# Example report — target output for Step 8

A Step 8 output for a real `build-feature` session (Large tier, Parallel execution), kept as the concrete target for level of detail and shape. Digest figures were regenerated with the current `session_metrics.py`; the collapsed-duplicates count and the finding block's **Costs** line are illustrative. This is **one report** — the at-a-glance table is the complete finding list, and everything after it references the same row numbers.

---

📊 Session evaluate — Complexity: **Large** (7,776 total records, 4h10m span) · Active: A, B, C, D, F · Parallel — 5 agents

## At a glance

| Skill | Dimension | # | Priority | Title | Metric | Recurrence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `skills/example-fixer/SKILL.md` | Workflow and orchestration | 1 | P0 | Serial per-cluster git reintegration inflates the fixer skill's own orchestration cost | 68% of orchestrator's Bash calls (48/71) = fetch+cherry-pick loop over 16 clusters; 100 turns, 12.0M tokens | Structural | Pending |
| `extended/tlc-spec-driven/` (vendor overlay, Execute phase) | Token consumption | 2 | P1 | Frontend source file re-read after edits the harness had already confirmed | 4× identical Read + 4× identical `cd`; ~24-32k avoidable tokens | Incidental | Pending |
| Instruction file that governed Bash usage (path from the transcript) | Mistakes and corrections | 3 | P2 | Manual shell backgrounding (`&`/`disown`) stacked with `run_in_background: true` produces a false completion signal | 1 self-corrected mistake; stated fix never actually executed | Structural | Pending |
| — (built-in `design`/design-sync) | Token consumption | 4 | P3 | Repeated, oversized reads of design-sync bundle/config files | 11×/9× repeated reads; 162.9k tokens = 68% of all Read spend; 2 failed path-guess reads | Structural (inferred) | Informational |
| — (built-in `DesignSync` tool) | Runtime | 5 | P3 | Independent screenshot reads issued one-per-turn during design review | 143 tool calls inside one 30m07s turn | Structural (inferred) | Informational |
| — (execution deviation, `code-review`) | Workflow and orchestration | 6 | P3 | Duplicate review-comment posting required serial deletes after harness blocked the batched delete | 9 serial `deletePullRequestReviewComment` calls | Incidental | Informational |

Collapsed 2 duplicate findings across the 5 dimension agents. Dimension F returned no finding (see Full test-suite runs below).

## Verification

**Time & tokens by skill invocation:**

| skill | # | wall time | input tok | output tok | tool calls | subagent (n, billed) |
| --- | --- | --- | --- | --- | --- | --- |
| resume | 1 | 7m59s | 45.3k | 295 | 0 | - |
| design ⚠ | 1 | 11m16s | 2.1M | 43.0k | 17 | 1, 794.9k |
| artifact-capabilities ⚠ | 1 | 7m28s | 4.6M | 19.6k | 22 | 1, 214.9k |
| build-feature ⚠ | 1 | 5m04s | 7.1M | 11.5k | 30 | 1, 79.7k |
| grilling ⚠ | 1 | 3h39m | 64.8M | 173.6k | 234 | 41, 150.3M |

- ⚠ **design** #1: also contains subagent work for pixel-perfectly. ⚠ **artifact-capabilities** #1: design. ⚠ **build-feature** #1: architecture-evaluate.
- ⚠ **grilling** #1: also contains subagent work for `tlc-spec-driven`, `code-review`, `fix-review`, `architecture-evaluate`, and 14 others — this window's own totals are not this skill's real cost.

**Subagent spend by named skill/phase** (relayed in full in the real report; top rows shown):

| skill/phase | runs | billed input | output | turns | confidence |
| --- | --- | --- | --- | --- | --- |
| phase-batch | 3 | 42.3M | 4.0k | 230 | 0/3 direct |
| tlc-spec-driven | 5 | 23.5M | 1.6k | 175 | 4/5 direct |
| fix-review | 2 | 12.6M | 657 | 115 | 1/2 direct |
| code-review | 1 | 11.7M | 1.4k | 74 | 1/1 direct |

**Full test-suite runs** (heuristic pattern match — not exhaustive, and it can mis-match):

| # | time | command | failed | files touched since last run |
| --- | --- | --- | --- | --- |
| 1 | 22:06:18 | `npm test -- AppShell.test 2>&1 \| head -100` | no | 15 |
| 2 | 22:06:41 | `npm test -- MiniCalendarWidget.test 2>&1 \| head -100` | no | 9 |
| 3 | 22:06:48 | `npm test -- layoutOverlaps.test 2>&1` | yes | 2 |
| 4 | 22:07:15 | `npm test -- CalendarPage.test` | yes | 6 |
| 5 | 22:07:42 | `npm test -- WeekView.test.tsx 2>&1 \| head -100` | no | 4 |
| 6 | 22:07:50 | `npm test -- WeekView.test` | yes | 1 |
| 7 | 22:33:04 | `npm run test -- --run 2>&1 \| tail -40` | no | 5 |
| 8 | 22:33:42 | `go test ./... 2>&1 \| tail -40` | no | 0 |

Rows 1-6 each name one test file after `--`, so they are scoped runs the heuristic mis-matched, not full-suite runs; because every detected row resets the files-touched count, rows 7-8's counts are understated too. Rows 7-8 ran inside the `tlc-spec-driven` Execute-phase subagent's Build gate after a cross-cutting frontend+backend change — proportionate, not an F1 finding.

---

## `skills/example-fixer/SKILL.md`

### Workflow and orchestration

#### 1. Serial per-cluster git reintegration inflates the fixer skill's own orchestration cost — P0

**Context:** the fixer skill's own orchestrator (running on PR #22, 16 fix clusters) reintegrates each isolated-worktree cluster's commits back into the base checkout one cluster at a time — fetch, cherry-pick, remove worktree — with no batching, even though the skill already batches its GitHub GraphQL reply/resolve calls 10-per-request.

**Metrics:** The orchestrating subagent ran 100 turns, 12.0M billed input tokens, 22m33s. Of its own 71 Bash calls, 21 are `git fetch` and 27 are `git cherry-pick` — 48/71 (68%) is this exact two-command loop repeated per cluster.

**Affected aspects:** Tokens, Cost, Runtime.

**Costs:** tokens — roughly the framing of 48 of the orchestrator's 100 API calls, each re-reading its whole context; wall-clock — most of the loop's share of 22m33s, since each of the 48 calls waited a full model round-trip before the next.

**Severity:** High — 68% of the orchestrator's own tool calls are one repeated shape.

**Recurrence:** Structural — confirmed in the SKILL.md text itself (per-cluster fetch/cherry-pick/remove loop with no batching instruction), unlike the already-batched GraphQL calls a few paragraphs away. Will recur on every fixer run with more than a handful of clusters.

**Root cause:** the fixer skill already applies "batch, don't loop one call at a time" to its GitHub-side writes but never extended that principle to the git-side reintegration step.

**Proposed solution:** After the Guardrails sentence describing the per-cluster loop, add: *"Do this as one scripted pass over every surviving cluster, not one Bash call per cluster — write a single shell loop that fetches, cherry-picks, and removes the worktree for each cluster with commits in sequence, then run it once."*

---

*(Blocks for findings 2 and 3 follow the same shape and are omitted here. Finding 2 is routed to the vendor skill's overlay location, never the installed copy; finding 3 has no governing skill, so it goes to the instruction file the transcript shows governing Bash usage.)*

## Informational (reported, not applied)

**4. Repeated, oversized reads of design-sync bundle/config files** (Token consumption, P3) — governed by the built-in `design`/design-sync capability, not an editable skill.

**5. Independent screenshot reads issued one-per-turn during design review** (Runtime, P3) — same attribution, built-in `DesignSync` tool.

**6. Duplicate review-comment posting required serial deletes after the harness blocked a batched delete** (Workflow and orchestration, P3) — execution deviation from already-correct guidance in `code-review`, compounded by a harness permission-classifier block; not a documentation gap.

---

Which of the 3 `Pending` findings should I apply — **all**, **none**, or a list of numbers (1, 2, 3)?
