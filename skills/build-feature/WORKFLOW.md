# build-feature — Workflow Diagram

Not loaded by `SKILL.md` at runtime — this is a human-facing reference for understanding or modifying the skill, not agent-facing instruction. See `SKILL.md` for the actual steps and `references/progress-schema.md` for resume mechanics.

```mermaid
flowchart TD
    Start([Invocation]) --> Step0{progress.md<br/>exists?}

    Step0 -- no --> S1[Step 1: Worktree + branch<br/>EnterWorktree, native]
    Step0 -- "yes, complete,<br/>PR merged/closed" --> Cleanup[Sweep + remove worktrees<br/>across ALL completed specs]
    Step0 -- "yes, complete,<br/>PR open" --> ReEntry[fix-review only,<br/>existing worktree]
    Step0 -- "yes, in-progress" --> Resume[Resume at first<br/>incomplete step]

    Cleanup --> End1([Stop])
    ReEntry --> Step14b[architecture-evaluate<br/>if commits pushed]
    Step14b --> End2([Stop])

    S1 --> S2[Step 2: Push branch]
    S2 --> S3[Step 3: Draft PR — stub body]
    S3 --> S4a[Step 4a: Quick arch-eval gate<br/>Sonnet]
    S3 --> S4b[Step 4b: Grilling<br/>Opus]
    S4a --> S6
    S4b --> S6[Step 6: Create feature folder<br/>+ grilling-session.md]

    S6 --> S7a[Step 7a: Specify — Opus]
    S7a --> CP1{human_review<br/>and spec not excluded?}
    CP1 -- yes --> Wait1[Pause: approve spec.md]
    CP1 -- no --> S7b
    Wait1 --> S7b[Step 7b: Design — Opus<br/>reads spec.md fresh]

    S7b --> CP2{Design ran AND<br/>human_review AND<br/>design not excluded?}
    CP2 -- yes --> Wait2[Pause: approve design.md]
    CP2 -- no --> S8
    Wait2 --> S8[Step 8: Tasks — Sonnet<br/>reads spec.md + design.md fresh]

    S8 --> S9[Step 9: Commit + push spec artifacts]
    S9 --> S10[Step 10: Execute — Sonnet<br/>tlc-spec-driven owns gate checks + Verifier]
    S10 --> S11[Step 11: Rewrite PR description]

    S11 --> S12{human_review and<br/>complete-review<br/>not excluded?}
    S12 -- yes --> CR1[complete-review<br/>human_review: true]
    CR1 --> Wait3[Pause: approve findings]
    Wait3 --> CR2[complete-review<br/>Publish Mode]
    S12 -- no --> CR3[complete-review<br/>publishes immediately]
    CR2 --> S13
    CR3 --> S13[Step 13: fix-review<br/>same worktree, no new one]

    S13 --> S14[Step 14: architecture-evaluate<br/>Full — Sonnet]
    S14 --> S15{".design-sync/config.json<br/>exists?"}
    S15 -- yes --> S15a[Step 15: design-sync — Sonnet]
    S15 -- no --> S16
    S15a --> S16[Step 16: gh pr ready<br/>progress.md → complete]
    S16 --> End3([Worktree stays —<br/>signal-driven cleanup only])
```

## Key architectural notes (not in SKILL.md, kept here for maintainers)

- **Steps 7a/7b are two separate Opus subagent calls, not one.** A single subagent call returns once, at the end — it can't pause mid-conversation for a `human_review` checkpoint. Making `spec` and `design` independently gate-able requires two calls, the second reading `spec.md` fresh off disk rather than sharing conversation state with the first.
- **Steps 4a/4b run concurrently** (two `Agent` calls in one turn) — safe because only 4a ever touches git; 4b (grilling) never pushes.
- **The orchestrator never writes large file content into its own context.** Every subagent gets metadata and paths; it does its own reads. This is what keeps a 15+ step run from blowing the orchestrator's context window.
- **Worktree cleanup is signal-driven, not automatic-on-completion.** A PR merged via the GitHub UI, with build-feature never re-invoked, would otherwise leave the worktree on disk forever — the sweep at Step 0 checks every tracked spec's worktree, not just the current one.
