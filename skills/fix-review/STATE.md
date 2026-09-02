# STATE

## Decisions

### AD-001
- **Decision**: Remove GitHub Mode's per-cluster subagent dispatch and worktree-fetch-cherry-pick-back mechanism. Process every surviving cluster's items sequentially, inline, in whatever context is already running GitHub Mode — the outer dispatch that invoked this skill (`build-feature`'s own subagent, or a Batch Mode per-PR subagent), or, only for a live direct invocation with no outer dispatch already isolating it, one whole-run Haiku subagent (never one per cluster).
- **Reason**: A real APLYR-19 run (found via `session-evaluate`) proved this mechanism doubly broken: (1) a cherry-pick conflict got committed to the branch as a literal unresolved `<<<<<<<` marker, requiring a whole separate recovery subagent (~10.6M tokens, 8.7min stall) because nothing validated the merged composite state before replying/resolving/pushing; (2) the top-level agent, consumed by hand-resolving those conflicts (itself a violation of the "never implement a fix directly" guardrail this mechanism was supposed to enforce), never reached the reply/resolve step at all — it pushed 28 commits and reported "40 threads fixed, 0 blocked" while 0 of 41 GitHub review threads were ever actually replied to or resolved. Since `build-feature` and Batch Mode already dispatch this skill as one isolated subagent per invocation, the per-cluster isolation was a second, redundant layer recreating protection that already existed one level up — and that redundant layer is what produced both failures.
- **Trade-off**: Loses intra-PR parallelism across independent, unrelated clusters — a PR with many small unrelated fixes now processes them one after another instead of concurrently. Given individual review-comment fixes are typically small and fully specified by the thread, this is expected to cost some wall-clock time, not token/reliability cost of the prior mechanism's failure modes.
- **Date**: 2026-09-02
- **Status**: active

### AD-002
- **Decision**: Add a mandatory validation gate (new GitHub Mode step 6) — build/typecheck plus the tests covering every touched file, and a conflict-marker scan — after the fixing pass and before any GitHub write (reply, resolve, or push).
- **Reason**: Closes the same session's build-breakage half of the bug: step 5's per-item test runs each confirmed one fix in isolation but never the state left behind once every fix landed together. This is the one point in the flow where a wider-than-single-item run is warranted, and it doesn't contradict [Test Execution Scope](../../templates/test-execution-scope.md) for that reason.
- **Trade-off**: One additional build/test run per invocation with any commits — real cost, but bounded and the alternative (a broken build reaching GitHub) is strictly worse.
- **Date**: 2026-09-02
- **Status**: active

### AD-003
- **Decision**: Move `git push` earlier (new step 7, before reply/resolve, was step 7 after reply/resolve at old step 6) and add a mandatory post-resolve verification (new step 9) that re-fetches `reviewThreads` and confirms `isResolved: true` for every thread this run claims to have resolved, before the final report may count it as such.
- **Reason**: Directly closes the GitHub-side half of the bug: nothing previously checked that the reply/resolve mutations were even called, let alone that they landed. Pushing before replying also means a crash between the two leaves the remote branch already reflecting the fix, rather than resolved-looking threads pointing at commits that were never pushed.
- **Trade-off**: None identified — this is strictly additional verification with no new failure mode of its own.
- **Date**: 2026-09-02
- **Status**: active

### AD-004
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) at this skill's two remaining dispatch sites (Batch Mode's per-PR runs, the whole-run wrapper for a live invocation) — completion condition tied to step 9's confirmed outcome, not step 8's attempted one; delegation depth: none.
- **Reason**: Same session-evaluate audit; part of a repo-wide retrofit applied to every skill in `skills/` that dispatches subagents.
- **Trade-off**: None identified.
- **Date**: 2026-09-02
- **Status**: active
