# Performance Baseline — review pipeline, 2026-09-06

Measured state of `complete-review` / `code-review` / `tests-code-review` / `fix-review`
**before** the fixes committed on 2026-09-06, with the predictions those fixes make.

The point of this file is comparison: run the pipeline again on a real PR, re-measure, and
check the predictions in [§4](#4-what-the-fixes-predict). A prediction that fails is more
useful than one that passes — it means a fix was reasoned about rather than verified.

## 1. How these numbers were produced

Four real `build-feature` PRs, two codebases (Go and Python), all four the same feature
shape (structured logging ×2, OTel tracing ×2):

| Session | PR | Files | Diff lines |
|---|---|---|---|
| APLYR-25 | applyr#28 | 19 | 1,958 |
| APLYR-26 | applyr#29 | 21 | 1,454 |
| RA-1 | reimbursement-analyzer#1 | 39 | 2,648 |
| RA-2 | reimbursement-analyzer#2 | 40 | 3,231 |

> **Token figures.** Worker figures below are **deduplicated per API call** — the true
> numbers. Fan-out figures in §3 are **not**: they were collected before
> `session-evaluate`'s AD-006 counting fix and are inflated ~2× (measured 1.98×–2.64×,
> varying with per-turn parallelism). They are kept because their *ratios* are still
> informative; treat their absolute magnitudes as roughly double reality, and re-derive
> them with the fixed script when comparing.

## 2. The `complete-review` Step-2 worker — the critical path

The worker is the single subagent that invokes both review skills, collects the dimension
agents' findings, and posts them. It is **essentially the entire wall clock** of a
`complete-review` run; the dimension fan-out is parallel and finishes inside it.

| Session | Wall | Turns | True billed | Peak context | Findings posted |
|---|---|---|---|---|---|
| APLYR-25 | 17.4m | 47 | 7.57M | 225k | 15 (+9 accidental duplicates) |
| APLYR-26 | 20.1m | 79 | 12.41M | 227k | 16 |
| RA-1 | 23.4m | 52 | 9.89M | 317k | 43 |
| RA-2 | 23.3m | 54 | 9.70M | 293k | 43 |

**The worker's own working time is constant.** Subtracting time spent idle waiting on the
fan-out leaves 1041s / 1021s / 1068s / 1048s — **σ ≈ 20s, CV 1.9%**, across PRs varying
2.1× in file count and 2.9× in findings. All apparent variation with PR size is idle time,
not work.

**Cost tracks turns × context, not findings.** A trapezoid model
`billed ≈ turns × (ctx_first + ctx_last)/2` fits at r = 0.952. Turns alone: r = +0.93.
Final context alone: r = **−0.03**. Every turn re-bills the whole conversation as
cache-read (99% of billed input).

**59–71% of wall is model latency**, spread thin — median turn 5–8s, with only 2–4 tool
calls per run exceeding 20s. The lever is fewer turns, not faster commands.

### Phase split (wall time)

| Phase | APLYR-25 | APLYR-26 | RA-1 | RA-2 |
|---|---|---|---|---|
| Setup | 2.1m | 1.9m | 1.8m | 2.7m |
| Dispatch + collect (mostly idle) | 0.9m | 6.8m | 8.0m | 8.0m |
| **Line-number verification pass** | *(folded)* | **2.1m** | **4.6m** | **4.0m** |
| Assemble + build batches | 2.4m | 2.8m | 4.4m | 4.3m |
| Posting loop + repair | 4.5m | 6.6m | 4.7m | 4.3m |

## 3. Dimension fan-out (figures inflated ~2×, ratios valid)

29 dimension-agent runs, joined against all 117 resulting GitHub threads and `fix-review`'s
recorded disposition on each.

| Dimension | Runs | Billed¹ | Findings | Fixed | Invalid |
|---|---|---|---|---|---|
| tests (1 merged agent) | 1 | 2.7M | 5 | 5 | 0% |
| craft | 2 | 9.7M | 18 | 13 | 0% |
| coverage | 2 | 9.6M | 18 | 10 | 0% |
| design-quality | 4 | 22.8M | 28 | 18 | 4% |
| performance | 4 | 10.6M | 13 | 7 | 6% |
| security | 4 | 12.3M | 12 | 8 | 17% |
| execution | 2 | 5.6M | 9 | 3 | 0% |
| gap-detector | 2 | 9.3M | 6 | 4 | 0% |
| regression | 4 | 18.1M | 7 | 5 | **29%** |
| requirements-tracer | 4 | 13.8M | 5 | 2 | **20%** |

¹ inflated ~2×

**Duplication:** ~17% of raw findings restated another dimension's finding (lower bound).
Downstream on RA-1, `fix-review` collapsed **43 posted threads into 25 distinct fixes
(−42%)** — one bug found independently by five dimensions, another by four.

**Agent counts:** 5 / 6 / 9 / 9. All four PRs landed in `code-review`'s Large or Complex
tier, which share an execution mode — so its tiering existed but never engaged in this
sample. Variance came entirely from `tests-code-review`, which does tier (0/1/4).

## 4. What the fixes predict

Re-measure and check these. Each names the fix responsible.

| # | Prediction | Baseline | Fix |
|---|---|---|---|
| P1 | Worker turns stay ≲50 even on a large PR | 47–79 (APLYR-26: 30 turns were `echo "waiting"`) | Agent Wait Protocol in Single PR Mode |
| P2 | No line-number verification phase at all | 2.1–4.6m, 13–35% of worker cost | `anchor` field in the finding contract |
| P3 | Peak context ≲200k | 225–317k | P2's removal of full-file re-reads |
| P4 | Worker wall (excluding fan-out idle) < 15m | ~17.4m constant | P1 + P2 combined |
| P5 | Zero silently-dropped findings; any drop is reported | 9 of 44 lost twice, silently | Diff-hunk anchor validation + mandatory reconciliation |
| P6 | Zero duplicate comments posted | 9 duplicated on APLYR-25 | Never re-issue a posting mutation |
| P7 | ≤4 dimension agents on general content | 5–6 | `intent-regression-reviewer` merge |
| P8 | Posted threads ≈ distinct fixes needed | 43 → 25 on RA-1 | Cross-dimension dedup |
| P9 | No `gh` form debugging turns | 13 turns / 191s on APLYR-26 | "Issuing the Call" section |
| P10 | No template/Posting-Mechanics hunting | ~5 turns, 0.35M per run | Posting Mechanics inlined in dispatch prompt |
| P11 | `fix-review` needs one run, not two | 3 of 4 sessions ran it twice | `deliver.py` + coverage reconciliation |

## 5. Known-unaddressed

- **The Bash permission classifier on `gh api graphql`** cost 3 of 4 runs ~2–3 minutes each
  (blocked calls, 43–80s timeouts). This is a settings/allowlist problem, not skill content
  — see `update-config` / `fewer-permission-prompts`.
- **`code-review`'s Large vs Complex tiers share an execution mode.** Whether Large should
  fan out less is untested: no sampled PR was small enough to exercise the difference.
- **Whether merging dimensions preserves findings** or merely produces fewer is unknown.
  The one merged-agent data point was the most efficient run in the set, but n=1 and it ran
  on the smallest diff.

## 6. Re-measuring

```bash
python3 ~/.claude/skills/session-evaluate/scripts/session_metrics.py <session.jsonl> --top 10
```

The Step-2 worker is the subagent that issues `Skill: code-review` — find it under
`<session-dir>/subagents/`. Scope to it directly; `--skill complete-review` against the main
session transcript will not see it, and will say so.

Note that `session_metrics.py`'s token and turn counts changed on 2026-09-06 (AD-006):
figures produced before that date are ~2× higher than post-fix figures for identical work,
so only compare like with like.
