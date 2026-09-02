# Example report — target output for Step 8

A full, real Step 8 output (from a `build-feature` session, Large tier, Parallel execution), kept as the concrete target for level of detail and shape. This is **one report** — the at-a-glance table is the complete finding list, the verification section and finding blocks that follow reference the same row numbers, and the closing question asks about the `Pending` rows from that same table. Never split this into a "preview" and a separate "real" report.

---

📊 Session evaluate — Complexity: **Large** (7,776 total records, 4h10m span) · Active: A, B, C, D, E · Parallel — 5 agents

## At a glance

| Skill | Dimension | # | Priority | Title | Metric | Recurrence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `skills/fix-review/SKILL.md` | Workflow and orchestration | 1 | P0 | Serial per-cluster git reintegration inflates fix-review's own orchestration cost | 68% of orchestrator's Bash calls (48/71) = fetch+cherry-pick loop over 16 clusters; 254 turns, 29.5M tokens | Structural | Pending |
| `extended/tlc-spec-driven/` (Execute phase) | Token consumption | 2 | P1 | Frontend source file re-read after edits the harness had already confirmed | 4× identical Read + 4× identical `cd`; ~24-32k avoidable tokens | Incidental | Pending |
| `~/.claude/CLAUDE.md` | Mistakes and corrections | 3 | P2 | Manual shell backgrounding (`&`/`disown`) stacked with `run_in_background: true` produces a false completion signal | 1 self-corrected mistake; stated fix never actually executed | Structural | Pending |
| — (built-in `design`/design-sync) | Token consumption | 4 | P3 | Repeated, oversized reads of design-sync bundle/config files | 11×/9× repeated reads; 162.9k tokens = 68% of all Read spend; 2 failed path-guess reads | Structural (inferred) | Informational |
| — (built-in `DesignSync` tool) | Runtime | 5 | P3 | Independent screenshot reads issued one-per-turn during design review | 143 single-call turns inside one 30m07s turn | Structural (inferred) | Informational |
| — (execution deviation, `complete-review`) | Workflow and orchestration | 6 | P3 | Duplicate review-comment posting required 9 serial deletes after harness blocked the batched delete | 156 turns, 23.0M tokens, 9 serial `deletePullRequestReviewComment` calls | Incidental | Informational |

## Verification

**Time & tokens by skill invocation:**

| skill | # | wall time | input tok | output tok | tool calls | subagent (n, billed) |
| --- | --- | --- | --- | --- | --- | --- |
| resume | 1 | 7m59s | 45.3k | 295 | 0 | - |
| design | 1 | 11m16s | 4.0M | 89.6k | 17 | 1, 2.8M |
| artifact-capabilities | 1 | 7m28s | 9.0M | 48.1k | 22 | 1, 493.8k |
| build-feature | 1 | 5m04s | 12.8M | 22.1k | 30 | 1, 202.5k |
| grilling ⚠ | 1 | 3h39m | 118.2M | 359.3k | 234 | 41, 314.4M |

⚠ **grilling** #1: also contains subagent work for `tlc-spec-driven`, `fix-review`, `complete-review`, `architecture-evaluate`, `code-review`, and 12 others — this window's own totals are not this skill's real cost. See the digest's `Subagent spend by named skill/phase` table for the real per-skill breakdown (e.g. `tlc-spec-driven`: 5 runs, 52.2M tokens, 415 turns; `fix-review`: 2 runs, 30.9M tokens, 287 turns).

**Full test-suite runs:**

| # | time | command | failed | files touched since last run |
| --- | --- | --- | --- | --- |
| 1 | 22:33:04 | `npm run test -- --run 2>&1 \| tail -40` | no | 22 |
| 2 | 22:33:42 | `go test ./... 2>&1 \| tail -40` | no | 0 |

Both ran inside the `tlc-spec-driven` Execute-phase subagent's Build gate after a genuinely cross-cutting change (22 files touched across frontend+backend) — proportionate, not an F1 finding.

---

## `skills/fix-review/SKILL.md`

### Workflow and orchestration

#### 1. Serial per-cluster git reintegration inflates fix-review's own orchestration cost — P0

**Context:** fix-review's own orchestrator (running fix-review on PR #22, 16 fix clusters) reintegrates each isolated-worktree cluster's commits back into the base checkout one cluster at a time — fetch, cherry-pick, remove worktree — with no batching, even though the skill already batches its GitHub GraphQL reply/resolve calls 10-per-request.

**Metrics:** The orchestrating subagent ran 254 turns, 29.5M billed input tokens, 28.4k output, 22m33s. Of its own 71 Bash calls, 21 are `git fetch` and 27 are `git cherry-pick` — 48/71 (68%) is this exact two-command loop repeated per cluster.

**Affected aspects:** Tokens, Cost, Runtime.

**Severity:** High — 254 turns is 69% over the ~150-turn runaway-subagent threshold, and 68% of the orchestrator's own tool calls are one repeated shape.

**Recurrence:** Structural — confirmed in the SKILL.md text itself (per-cluster fetch/cherry-pick/remove loop with no batching instruction), unlike the already-batched GraphQL calls a few paragraphs away. Will recur on every fix-review run with more than a handful of clusters.

**Root cause:** fix-review already applies "batch, don't loop one call at a time" to its GitHub-side writes but never extended that principle to the git-side reintegration step.

**Proposed solution:** After the Guardrails sentence describing the per-cluster loop, add: *"Do this as one scripted pass over every surviving cluster, not one Bash call per cluster — write a single shell loop that fetches, cherry-picks, and removes the worktree for each cluster with commits in sequence, then run it once."*

---

## `extended/tlc-spec-driven/` (vendor overlay)

### Token consumption

#### 2. Frontend source file re-read after edits the harness had already confirmed — P1

**Context:** During the tlc-spec-driven Execute phase, the same frontend source file was read 4 separate times with an identical target, paired with 4 identical `cd .../frontend` calls — consistent with re-reading a file to confirm an edit the Edit tool had already reported back.

**Metrics:** `Repeated identical calls`: same frontend-file Read target ×4, same `cd .../frontend` Bash target ×4. Read tool's mean cost is 8.0k tokens/call, so 3 of the 4 reads being redundant is ~24-32k avoidable tokens.

**Affected aspects:** Tokens, Cost.

**Severity:** Medium — real but bounded against a 144.0M-token session.

**Recurrence:** Incidental (inferred) — only 4 occurrences in one file during one Execute-phase pass; not enough evidence this is unconditional on every Execute run.

**Root cause:** The edit-verify loop appears to re-Read a file's full content after editing it instead of trusting the diff the Edit tool already returned.

**Proposed solution:** Add to `extended/tlc-spec-driven/`, restating the dedup rule at the point of use: *"After editing a file, do not re-Read it to confirm the change — the Edit tool's own diff output is the confirmation."*

---

## `~/.claude/CLAUDE.md`

### Mistakes and corrections

#### 3. Manual shell backgrounding stacked with `run_in_background: true` produces a false completion signal — P2

**Context:** A Bash call launching a long-running resync process set `run_in_background: true` *and* backgrounded itself inside the command string (`... & \necho "PID: $!"\ndisown`). The wrapper shell exited immediately, so the harness reported completion for the trivial wrapper exit, not the real process. The agent caught this immediately but never actually executed the stated fix.

**Metrics:** 1 confirmed D1 candidate (of 1 grep match across the whole session). Bounded recovery cost.

**Affected aspects:** Correctness (tool-usage reliability).

**Severity:** Medium — real, confirmed wrong action with a specific, correct fix named by the agent itself, but bounded recovery cost.

**Recurrence:** Structural — generic Bash-tool misuse that can recur in any skill backgrounding a long command.

**Root cause:** The command duplicated backgrounding semantics — `run_in_background: true` already handles detachment and completion notification; adding shell-native `&`/`disown` makes the *tracked* process (the wrapper) exit instantly.

**Proposed solution:** *"When passing `run_in_background: true` to the Bash tool, write the command in plain foreground form — never add `&`, `nohup ... &`, or `disown` inside the command string."* (Attributed to the user's global `CLAUDE.md`, not any skill in this repo, because the root cause is general Bash-tool usage.)

---

## Informational (reported, not applied)

**4. Repeated, oversized reads of design-sync bundle/config files** (Token consumption, P3) — governed by the built-in `design`/design-sync capability, not a skill in this repo's registry.

**5. Independent screenshot reads issued one-per-turn during design review** (Runtime, P3) — same attribution, built-in `DesignSync` tool.

**6. Duplicate review-comment posting required 9 serial deletes after the harness blocked a batched delete** (Workflow and orchestration, P3) — execution deviation from already-correct guidance in `complete-review`, compounded by a harness permission-classifier block; not a documentation gap.

---

Which of the 3 `Pending` findings should I apply — **all**, **none**, or a list of numbers (1, 2, 3)?
