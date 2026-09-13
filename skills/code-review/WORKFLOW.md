# code-review — Workflow

For human review and maintenance. Never loaded at runtime: `SKILL.md` and `references/` are the source of truth, and this file must be updated alongside them.

## Entry Routing

```mermaid
flowchart TD
    Req([Request]) --> R{Step 1: entry}
    R -- "sweep + fix wording" --> BF[Batch fix sweep<br/>batch-mode.md]
    R -- "sweep + review wording" --> BR[Batch review sweep<br/>batch-mode.md]
    R -- "continue the code review on PR #N" --> CT[Continue after checkpoint<br/>submit → Stage 3]
    R -- "fix wording only" --> FX{PR?}
    R -- "review commits …" --> MC[Multi-commit]
    R -- "PR # in conversation" --> PR[GitHub PR]
    R -- default --> LW[Local workspace]

    FX -- "yes, submitted review" --> S3[Stage 3: fix]
    FX -- "yes, only pending" --> Stop1([Stop: submit it first])
    FX -- "yes, no review" --> CF{Findings in<br/>conversation?}
    CF -- yes --> S3
    CF -- no --> Stop2([Stop: nothing published — offer review])
    FX -- no --> S3

    MC --> S1[Stage 1: review]
    PR --> S1
    LW --> S1
    BF --> BFW[One fix worker per PR<br/>own threads only]
    BR --> BRW[Per PR: review → checkpoint → fix]
```

## The Chain

```mermaid
flowchart TD
    S1[Stage 1: review worker<br/>Steps 2–8: context, diff, tiers,<br/>dimension agents, duplicate collapse, report] --> Failed{Every agent failed?}
    Failed -- yes --> EndFail([Report failures — nothing posted])
    Failed -- no --> T{PR?}
    T -- "yes, findings" --> Post[Step 9: github_review.py post<br/>anchors checked, re-anchored, pending review]
    T -- "yes, zero findings" --> EndR
    T -- no --> Rep[Full report returned to root]
    Post --> CP{Stage 2 — human_review?}
    Rep --> CP

    CP -- true --> Pause[Show summary, end turn<br/>PR: user edits / deletes / submits on GitHub<br/>Local: user drops finding IDs]
    Pause -- "user replies" --> JR
    CP -- false --> JR

    JR{just review?} -- "yes, true" --> EndPending([End — PR review stays pending])
    JR -- "yes, false" --> SubOnly[submit on a PR] --> EndR([End])
    JR -- no --> Remain{Findings remain?}
    Remain -- no --> EndR
    Remain -- "yes, PR" --> Sub[github_review.py submit<br/>COMMENT]
    Remain -- "yes, local" --> F
    Sub --> F[Stage 3: fresh fix worker<br/>fetch → classify → re-fetch → fix item by item]
    F --> Gate[Validation gate<br/>build + touched files' tests + conflict markers]
    Gate --> Where{PR?}
    Where -- yes --> Push[git push] --> Del[github_review.py deliver<br/>reply → confirm → resolve → confirm]
    Where -- no --> Loc[Uncommitted: edits only<br/>Commits/branch: commit per fix, no push]
    Del --> Final([Final report])
    Loc --> Final
```

## Batch Sweeps

```mermaid
flowchart TD
    B([Batch entry]) --> Repo[Resolve repo + login]
    Repo --> Cand[Search candidates<br/>fix: reviewed-by · review: review-requested]
    Cand --> Filt[Drop reply-reviews<br/>reply-review-filter.md]
    Filt --> Q{Sweep}

    Q -- fix --> FQ[Latest non-reply review is CHANGES_REQUESTED]
    FQ --> FW[Fix workers in one message<br/>isolation: worktree, own threads only]
    FW --> FR[Report each PR as it lands<br/>remove its worktree] --> FT([Summary table])

    Q -- review --> RQ[No non-reply review by you]
    RQ --> RW[Review workers in one message<br/>each posts a pending review]
    RW --> HR{human_review?}
    HR -- true --> Tbl[After all report: one table, end turn<br/>user replies continue / continue #12, #14]
    Tbl --> SubB[submit + fix worker per continued PR]
    HR -- false --> Each[As each reports:<br/>submit + fix worker immediately]
    SubB --> RR[Report each PR as it lands] --> RT([Summary table])
    Each --> RR
```

## Entries

| Entry | Trigger | Stages | Findings for the fix stage |
|---|---|---|---|
| Batch fix sweep | "fix the PRs I requested changes on" | 3, per PR | Unresolved threads with a comment by you |
| Batch review sweep | "review my pending PRs" | 1 → 2 → 3, per PR | All threads remaining after the checkpoint |
| Continue after checkpoint | "continue the code review on PR #N" (`build-feature` resume) | `submit` → 3 | Every published unresolved thread |
| Fix existing findings | "fix the review comments on PR #N", "fix Q1, H2" | 3 | PR with a submitted review: every published unresolved thread · PR with no review, or no PR: the named or all conversation findings |
| GitHub PR | PR number established in the conversation | 1 → 2 → 3 | Threads remaining after the checkpoint |
| Local workspace | Default | 1 → 2 → 3 | Report findings not dropped at the checkpoint |
| Multi-commit | "review commits …" | 1 → 2 → 3 | Report findings not dropped at the checkpoint |

The PR's author is never checked — every PR follows the same flow.

## Parameters

| Parameter | Default | Values | Controls |
|---|---|---|---|
| `human_review` | `false` | `true` · `false` | Whether Stage 2 pauses for the user. `build-feature` passes its own value, or `false` when `code-review` is in its `human_review_exclude` |
| `scope` | `both` | `both` · `code` · `tests` | Which files the review stage covers |

Wording, not parameters: "just review" ends after Stage 2; "and update the Jira ticket" turns on Jira sync.

## Stage 2 Behavior

| Target | `human_review: true` | `human_review: false` | "Just review" |
|---|---|---|---|
| GitHub PR | Pending review; end turn; user edits on GitHub and replies → `submit` → fix | `submit` → fix | `true`: stays pending, run ends · `false`: `submit`, run ends |
| Any, review failed or zero findings | No pause, no `submit`, no fix — report | Same | Same |
| Local / commits | Report shown; end turn; user drops IDs and replies → fix | Fix every finding | Run ends after the report |

## Workers

| Worker | Dispatched by | Model | Isolation | Dispatches | Returns to root |
|---|---|---|---|---|---|
| Dimension agent | Review worker | `sonnet` | — | Nothing | Findings with `anchor` |
| Fix worker (batch) | Root | `sonnet` | `worktree` always | Nothing | Outcomes, `deliver` JSON counts, commits, gate |
| Fix worker (single) | Root | `sonnet` | `worktree` when not on the PR branch; none when on it, or local | Nothing | Outcomes, `deliver` JSON counts, commits, gate |
| Review worker | Root | `sonnet` | — | Dimension agents | Local: full report · PR: URL, banner, counts, `post` JSON counts, unpostable list |

The root is a live conversation, or `build-feature`'s orchestrator invoking this skill via `Skill`. When a subagent executes this skill outside that structure, it runs the stages inline: `human_review: false` goes straight through; `true` stops after Stage 1 with `awaiting_approval: true`.

## Fix Outcomes on a PR

| Outcome | Decided at | Commit | Reply | Resolve |
|---|---|---|---|---|
| Answer-only | Classification | No (unless the answer implies a change) | The answer | No — the user resolves it |
| Blocked | Fix time (no clear remedy, stale file state) | No | Only a specific question, else skipped with reason | No |
| Fixed | Fix time (finding holds) | Yes, with test impact | What changed, why, test impact | Yes |
| Rejected | Fix time (stale, wrong, or contradicts a stated requirement) | No | The reasoning | Yes |
| Routed to a person | Classification (addressed to @someone) | No | None — skipped with reason | No |
| Unclear | Classification or fix time | No | Only a specific question, else skipped with reason | No |

`deliver` fails the run if any published, unresolved thread is in neither `threads` nor `skipped`.

## GitHub Writes

| Write | Subcommand | Stage | Confirms by |
|---|---|---|---|
| Add review threads to a pending review | `post` | 1 (Step 9) | Re-fetching the review's comments; retries once only comments from a request that failed as a whole |
| Reply to and resolve threads | `deliver` | 3 | Re-fetching threads after replies and after resolves |
| Submit the pending review as `COMMENT` | `submit` | 2 | Re-fetching the review's state |

Shared mechanics: argv only (no shell), batches of 10, pacing (post 1 s, reply 5 s, resolve 1 s), 180 s back-off on GitHub's abuse block (at most twice), no blind retry, counts only from re-fetches, exit `0` confirmed / `1` partial / `2` fatal. The only GitHub read the model runs itself is the thread fetch in `github-writes.md`.

## Files Loaded per Run

| File | Loaded when |
|---|---|
| `SKILL.md` | Every run |
| `WORKFLOW.md` | Never at runtime |
| `references/<topic>.code.md`, `<stack>.code.md`, `<stack>-performance.code.md` | By code dimension agents |
| `references/<topic>.tests.md`, `<stack>.tests.md` | By test dimension agents |
| `references/batch-mode.md` | Batch entries |
| `references/code-dimensions.md` | Code scope active |
| `references/fix-stage.md` | Root before Stage 3; fix worker |
| `references/github-writes.md` | Review worker on a PR; fix worker on a PR |
| `references/jira-sync.md` | Fix worker, only when Jira sync is requested |
| `references/reply-review-filter.md` | Batch entries |
| `references/report-format.md` | Review worker |
| `references/sonar.md` | A Sonar project key exists |
| `references/test-dimensions.md` | Tests scope active |
| `scripts/github_review.py` | Every GitHub write |

## Design Notes

- **Review and fix are one run with an optional pause, not two skills.** The pause copies `build-feature`'s checkpoint: post, show a summary, end the turn, continue on the user's reply. With `human_review: false` nothing waits. See STATE.md AD-010.
- **Always two stage workers.** The fix stage starts in a fresh context. The old standalone fix skill's delivery failures happened when replying ran last at peak context (STATE.md FR-AD-007); a fresh worker removes that by construction and makes resuming identical with or without a pause.
- **Only the root dispatches stage workers.** Every nesting failure in the old fix skill's history came from a subagent deciding it was an exception (FR-AD-006). The rule is mechanical: workers never start workers.
- **GitHub is the hand-off.** The fix stage fetches threads fresh, so a comment deleted at the checkpoint is gone, and a human reviewer's comment is picked up the same way as this skill's own.
- **Every GitHub write is scripted.** Posting as prose silently lost 9 of 44 findings on two runs and duplicated 9 comments on another; replying as prose was reported done five times when nothing landed (CPR-AD-003, FR-AD-007). The script reports only what a re-fetch confirms.
- **The verdict is always `COMMENT`.** Approving or requesting changes is a human judgment; `build-feature` already submitted this way.
- **No separate full-codebase performance mode.** Performance is reviewed as a dimension of every review; the separate full-codebase mode added dispatch exceptions to both merge rules for a report nothing consumed.
- **Local uncommitted changes are never committed.** A commit includes whole files, so it would sweep the user's unfinished edits in with the fixes.
