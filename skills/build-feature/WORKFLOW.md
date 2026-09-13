# build-feature — Workflow Diagram

Not loaded by `SKILL.md` at runtime — this is a human-facing reference for understanding or modifying the skill, not agent-facing instruction. See `SKILL.md` for the actual steps and `references/progress-schema.md` for resume mechanics.

```mermaid
flowchart TD
    Start([Invocation]) --> Step0{progress.md<br/>exists?}

    Step0 -- no --> S1[Step 1: Worktree + branch<br/>EnterWorktree, native]
    Step0 -- "yes, complete,<br/>PR merged/closed" --> Cleanup[Sweep + remove worktrees<br/>across ALL completed specs]
    Step0 -- "yes, complete,<br/>PR open" --> ReEntry[code-review fix-existing-findings entry,<br/>existing worktree]
    Step0 -- "yes, in-progress" --> Resume[Resume at first<br/>incomplete step]

    Cleanup --> End1([Stop])
    ReEntry --> Step12b[architecture-evaluate<br/>if commits pushed]
    Step12b --> End2([Stop])

    S1 --> SY[Step 1b: Sync docs/codebase into worktree<br/>only if untracked/ignored in the repo]
    SY --> S2[Step 2: Push branch — empty,<br/>no PR yet]
    S2 --> S3[Step 3: Arch-eval gate — decision only<br/>Haiku subagent, dispatched — not awaited]
    S3 -.background.-> S6aWait
    S2 --> S4[Step 4: Grilling<br/>live in this conversation, not a subagent]
    S4 --> S5[Step 5: Create feature folder<br/>+ grilling-session.md]

    S5 --> S6aWait[Collect Step 3's result<br/>Agent Wait Protocol]
    S6aWait --> S6a[Step 6a: Specify — Sonnet]
    S6a --> CP1{human_review<br/>and spec not excluded?}
    CP1 -- yes --> Wait1[Pause: approve spec.md]
    CP1 -- no --> S6b
    Wait1 --> S6b[Step 6b: Design — Sonnet<br/>reads spec.md fresh]

    S6b --> CP2{Design ran AND<br/>human_review AND<br/>design not excluded?}
    CP2 -- yes --> Wait2[Pause: approve design.md]
    CP2 -- no --> S7
    Wait2 --> S7[Step 7: Tasks — Haiku<br/>reads spec.md + design.md fresh]

    S7 --> S8[Step 8: Commit + push spec artifacts,<br/>open draft PR now — first real commit]
    S8 --> S9[Step 9: Execute — Sonnet<br/>tlc-spec-driven owns gate checks + Verifier]
    S9 --> S10[Step 10: Push Execute's commits +<br/>rewrite PR description]

    S10 --> CR[Step 11: code-review via Skill, in this conversation<br/>review worker posts a pending review]
    CR --> CP3{code-review checkpoint:<br/>human_review and<br/>code-review not excluded?}
    CP3 -- yes --> Wait3[Record code_review: pending, end turn<br/>user edits on GitHub, replies<br/>resume: continue-after-checkpoint entry]
    Wait3 --> SubmitCR
    CP3 -- no --> SubmitCR[code-review submits<br/>COMMENT]
    SubmitCR --> Fix[code-review fix worker — Sonnet<br/>same worktree, fixes, pushes, replies, resolves]

    Fix --> S12[Step 12: architecture-evaluate<br/>Incremental always — Sonnet]
    S12 --> SYB[Sync docs/codebase back to main tree<br/>only if Step 1b copied it in]
    SYB --> DSCheck{".design-sync/config.json<br/>exists?"}
    DSCheck -- yes --> S13a[Step 13: design-sync handoff<br/>nothing run — user runs it after]
    DSCheck -- no --> S14
    S13a --> S14[Step 14: merge check, gh pr ready<br/>progress.md → complete]
    S14 --> End3([Worktree stays —<br/>signal-driven cleanup only])
```

## Key architectural notes (not in SKILL.md, kept here for maintainers)

- **The models in this diagram are a restatement, not the source of truth.** Every dispatch site's model lives in the `subagent-dispatch` skill's model matrix; `SKILL.md`'s step headings and this diagram both mirror that table. Retune there first, then update both mirrors — this diagram in particular is the one that silently drifts, since nothing at runtime reads it.

- **The draft PR opens at Step 8, not right after the branch is pushed.** An earlier version opened it immediately after Step 2's push, as a stub with an empty body — but `gh pr create` unconditionally rejects a branch with zero commits ahead of `base_branch` (`No commits between <base> and <head>`), so that call failed on every single run. Moving it to Step 8 — right after the spec/design/tasks artifacts are committed and pushed, the branch's first real commit — fixes this at the root instead of papering over it with an empty placeholder commit just to satisfy GitHub earlier. The cost is that everything from the old Step 4 onward renumbered by one (see `progress-schema.md`'s `Step Log`, which now logs the PR's own line under Step 8 instead of a standalone Step 3).
- **Steps 6a/6b are two separate subagent calls, not one.** A single subagent call returns once, at the end — it can't pause mid-conversation for a `human_review` checkpoint. Making `spec` and `design` independently gate-able requires two calls, the second reading `spec.md` fresh off disk rather than sharing conversation state with the first.
- **Grilling (Step 4) is not a subagent dispatch, deliberately.** An `Agent`-tool subagent runs once, in the background, to completion — it cannot pause mid-run for a real reply from the user, and grilling's whole mechanic is multi-round back-and-forth with the user. So Step 4 runs `grilling` directly, in this conversation, via the `Skill` tool. Step 3 (the quick arch-eval gate) is still a background subagent — dispatched at the start of Step 3, then collected only once Step 4's conversation concludes, right before Step 6a. Fire-and-collect-later, not concurrent-and-awaited-together as it was before this design's fix — the two steps don't need to finish at the same moment, only before Step 6a needs Step 3's result.
- **The orchestrator never writes large file content into its own context.** Every subagent gets metadata and paths; it does its own reads. This is what keeps a 15+ step run from blowing the orchestrator's context window.
- **`progress.md` is written by a script, not hand-edited.** `scripts/progress.mjs` bumps `last_completed_step`, writes the `Step Log` line, and applies any `Run State` field updates in one call. A measured run hand-edited it 24 times (2-3 `Edit` calls per step, each re-anchoring on the full previous `Step Log` line just to append one more) — ~12 avoidable round-trips the script collapses into one call per step, and it's idempotent on a re-run of the same step, which raw `Edit` calls were not.
- **The worktree's deferred tools (`EnterWorktree`/`ExitWorktree`/`Monitor`) load together, once, at Step 1.** A measured run loaded each with its own `ToolSearch` call at the moment it was first needed instead — a few extra full-conversation round-trips for something knowable up front, since every normal run uses all three (enter at Step 1, exit in the cleanup sweep, `Monitor` for Step 14's `UNKNOWN`-mergeability wait).
- **Step 11 calls `code-review` via `Skill` from the orchestrator; every other delegated step dispatches a subagent.** Steps 11 and 12 used to both dispatch wrapper subagents, because a separate fix skill kept classification, fixing, and thread replies in whatever context invoked it — invoked from the orchestrator, that cost 39–60% of the entire main session on four production runs (16.6M / 30.3M / 40.8M / 42.7M cache-read). `code-review` now owns review and fix as one run and, from a root conversation, does its heavy work only in its own review and fix workers, so invoking it here costs the orchestrator only compact results. It has to run here: its `human_review` checkpoint ends the turn, and a subagent cannot pause for the user. Step 12 (the old fix step) is gone and Steps 13–15 became 12–14; see STATE.md AD-014.
- **`docs/codebase/` is synced into the worktree and back out.** A fresh `EnterWorktree` checkout carries neither untracked nor ignored files, so when a repo keeps its context docs untracked the worktree looks like a project with none. That misfired at both ends: Step 3's gate escalated to a Full brownfield scan (41 minutes in one measured run), and Step 12's output then died with the worktree because the path was gitignored — 7 of 9 files lost in one run, ~13.6M tokens of documentation that never reached a PR in another. Copy-in happens at Step 1 from the repo's *main* working tree (never a sibling worktree, which may hold a different run's stale copy); copy-out happens right after Step 12, not at Step 14, so an early stop still lands the docs, and it refuses to overwrite a source that changed mid-run. When the repo tracks `docs/codebase/`, none of this runs — which is the better arrangement, and worth saying so to the user.
- **`human_review` is passed through to `code-review`, which owns the pause.** `code-review` always posts its review as pending first; with `human_review: true` (and `code-review` not in `human_review_exclude`) its checkpoint shows the summary and ends this turn so the user can edit, delete, or submit comments on GitHub before anything is fixed; otherwise it continues. Whatever the user removed is no longer a finding — the fix worker fetches threads fresh.
- **`code-review` submits the review itself before fixing.** A pending review's threads are invisible to the fix stage, so `code-review` submits it as `COMMENT` (never `APPROVE`/`REQUEST_CHANGES` — no verdict) after its checkpoint, whether or not it paused. `build-feature` no longer submits anything on its behalf. A resumed run with `code_review: pending` waits for the user again, then calls `code-review`'s continue-after-checkpoint entry, which submits and fixes without re-running the review.
- **Recovery depends on what failed.** `code-review` retries each failure once itself: a failed review is re-run, a failed post is re-run from the same `post.json`, a failed submit or delivery goes through continue-after-checkpoint. If `code-review` still reports a failure, Step 11 stops on a review or posting failure — the continue entry never posts, so using it there would mark a PR ready with its findings lost — and retries the continue entry once only for a submit or delivery failure, with its fix worker told that already-pushed commits are fixes still owed a reply.
- **Step 10 also pushes now.** Step 9 (Execute) only commits locally — nothing pushed those commits to origin before `code-review` (Step 11) reviewed the PR, so it could review a stale remote branch. Step 10 now pushes first, before rewriting the PR description.
- **Worktree cleanup is signal-driven, not automatic-on-completion.** A PR merged via the GitHub UI, with build-feature never re-invoked, would otherwise leave the worktree on disk forever — the sweep at Step 0 checks every tracked spec's worktree, not just the current one.
