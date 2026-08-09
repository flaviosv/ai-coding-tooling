# Ship-Spec Review & Fix-Triage Redesign Specification

## Problem Statement

`ship-spec`'s Step 6 posts `code-review` and `tests-code-review` findings sequentially inside one wrapper subagent, delaying feedback and coupling the two skills' completion times. Separately, its Comment-Triage Mode (the "fix findings" flow) classifies fixes by *which skill* produced a finding rather than by *whether the user actually commented on it*, processes threads one at a time with no written plan, and runs every fix on `sonnet` even though the fix direction is already fully decided before dispatch. This session's grilling exercise (2026-08-08) redesigned both: real parallel review publishing, and a leaner, cheaper, plan-driven fix-triage flow.

## Goals

- [ ] `code-review` and `tests-code-review` run concurrently in Step 6, each publishing its own pending review independently — no longer gated on the other finishing first
- [ ] Fix-triage classifies purely by comment presence/content (no comment / question / suggestion) instead of finding origin, applied uniformly to both skills' findings
- [ ] Fix-triage writes an explicit, lightweight plan (`fix-code-review.md`) before executing, without adding a user-approval gate between plan and execution
- [ ] Independent fixes are drafted concurrently (capped at 4) while all git writes stay serialized on the shared checkout — no worktree isolation, no git corruption risk
- [ ] Fix drafting runs on Haiku (classification/replies stay on the default model) to cut cost, since the fix direction is already decided before dispatch

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| --- | --- |
| Batching GitHub *write* operations (replies, resolves) across independent threads | GitHub's GraphQL API has no such batching — `resolveReviewThread`/`addPullRequestReviewThreadReply` each take a single thread ID; confirmed a hard platform limitation during grilling, not a design gap |
| Following `tlc-spec-driven`'s literal sub-agent mechanism (one worker, sequential batches) for fix execution | That pattern exists for context-window sizing, not concurrency — deliberately diverged from to get real parallelism, which the user explicitly requested |
| A live/synchronous "does this finding still exist" check per fix item | Replaced by one batched re-fetch immediately before execution (SSF-11), which achieves the same correctness at a fraction of the cost |
| A user-approval gate on the plan file before execution (a "Stop Point 2") | Explicitly considered and rejected by the user after direct discussion — "fix the findings" is itself the authorization; only the pre-existing GitHub manual-review stop remains |
| Worktree isolation for concurrent fix agents | Rejected in favor of split-phase (parallel drafting, serial commits) — same wall-clock benefit without the added complexity of per-item worktree setup/teardown and a merge-back step |
| Fixing the existing 100-thread / 50-comment-per-thread GraphQL page-size cap | Pre-existing limitation of `github-delivery.md`, unchanged by and unrelated to this feature; now explicitly surfaced in reporting (Edge Cases) rather than silently truncated |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here — nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Concurrent fix-commit safety mechanism | Split-phase: draft concurrently (no git writes), commit serially, one at a time | Resolves a real conflict between requested concurrency and the existing "share the checkout, no worktree" rule (safe only when strictly sequential); gets most of the wall-clock win since LLM reasoning dominates over `git commit` cost | y (AskUserQuestion) |
| Step 6 partial failure (one of the two concurrent skill dispatches fails) | Report which skill succeeded/failed; never re-run the one that already posted (avoids a duplicate pending review); surface the failure reason instead of silently stopping | Directly extends the existing duplicate-avoidance guardrail's intent to the new concurrent-dispatch shape | n (inline default, low-stakes) |
| GitHub API failure at any point (fetch, post, resolve, reply) | Report to the user; never silently retry indefinitely or swallow the error | Matches the existing convention already in `github-delivery.md` for resolve-thread permission errors | n (inherited convention) |
| Zero unresolved threads found at fix-time | Still write `fix-code-review.md` noting zero items, then stop | Keeps the audit-trail guarantee consistent regardless of outcome, at negligible cost | n (inline default, low-stakes) |
| GraphQL 100-thread page cap | Unchanged; explicitly note in the fix-trigger report if the page may be truncated | Pre-existing, out-of-scope limitation; silently truncating without saying so was the actual gap, not the cap itself | n (inline default, low-stakes) |
| GitHub API concurrency risk from this feature | None — Step 6's two subagents do no GitHub writes at all (analysis only); the single merged pending-review POST is the only GitHub write in Step 6, issued once, after both finish. Fix-drafting agents (up to 4) also do no GitHub calls under split-phase; commit/resolve/reply calls remain serialized | Superseded by the one-pending-review-per-PR constraint below — removes the concurrency-risk question entirely rather than mitigating it | n (derived from confirmed decision) |
| Step 6 publish mechanism, given GitHub allows only one pending review per user per PR at a time (HTTP 422 on a second concurrent/sequential attempt — confirmed via GitHub REST API docs and community reports) | Both skills' analysis runs concurrently (no GitHub writes); findings are merged into one `comments` array and posted as a single pending review in one `POST .../reviews` call | The only mechanism GitHub's API actually supports for two skills contributing line-anchored findings to one PR without auto-submitting; also flags that the currently-shipped Step 6 (claiming two separate pending reviews) doesn't match documented GitHub behavior and should be checked against real usage independent of this feature | y (confirmed after web verification + AskUserQuestion) |

**Open questions:** none — all resolved or logged above.

---

## User Stories

### P1: Concurrent analysis, single merged pending review ⭐ MVP

**User Story**: As a developer running `ship-spec`, I want `code-review` and `tests-code-review` to analyze concurrently so I get feedback faster, with their findings published together as soon as both are ready.

**Why P1**: Core to the "performant, cost-saving, ideally parallel" ask — without it, Step 6 is unchanged from today. Revised mid-Design after confirming GitHub allows only **one pending (unsubmitted) review per user per PR at a time** — a second `POST .../reviews` call while one is still pending returns HTTP 422 ("A review cannot be created because a pending review already exists"), and there is no API to incrementally add comments to an already-open pending review. This makes two independently-published pending reviews impossible regardless of dispatch order (sequential or parallel) — confirmed against GitHub's REST API docs and community reports, not merely assumed. It also means the *current, shipped* Step 6 text (claiming two separate pending reviews get created) does not match documented GitHub behavior and should be treated as a latent risk independent of this feature — worth confirming against real usage.

**Acceptance Criteria**:

1. WHEN Step 6 begins THEN `ship-spec` SHALL dispatch two subagents concurrently (in the same turn, not sequentially) — one running `code-review`'s analysis, one running `tests-code-review`'s analysis — against the PR from Step 5, with **neither subagent posting anything to GitHub itself**.
2. WHEN both subagents have returned their findings THEN `ship-spec` SHALL merge both skills' findings into a single `comments` array and issue exactly one `POST .../pulls/{PR}/reviews` call (event field omitted, landing PENDING) covering both skills' findings in one pending review.
3. WHEN one of the two subagents fails or crashes before returning findings THEN `ship-spec` SHALL report which skill succeeded and which failed with the failure reason, and SHALL post a single pending review containing only the succeeded skill's findings (never attempt a second separate pending-review call for a retried/failed skill while the first is still pending).
4. WHEN the merged pending review has been posted (or the partial-failure case in AC3 applies) THEN `ship-spec` SHALL proceed to Step 7 (report PR URL + finding counts) and stop, waiting for the user — unchanged from today's behavior.

**Independent Test**: Run `ship-spec` through Step 6 on a real PR with real findings in both dimensions; confirm exactly one pending review appears on GitHub containing line-anchored comments from both skills, and that the two subagents' analysis work visibly overlaps in time (not one fully finishing before the other starts).

---

### P1: Comment-presence-driven fix classification

**User Story**: As a developer, I want fix decisions based on whether I left a comment (and what kind), not on which skill produced the finding, so triage behavior is consistent and predictable regardless of source.

**Why P1**: This is the rule the user explicitly confirmed replaces today's origin-based classification — the flow doesn't work as intended without it.

**Acceptance Criteria**:

1. WHEN a review thread has no user comment THEN `ship-spec` SHALL classify it as auto-fix, applying the same rule whether the finding came from `code-review` or `tests-code-review`.
2. WHEN a review thread's user comment is phrased as a question THEN `ship-spec` SHALL classify it as answer-only — it SHALL reply with an answer and SHALL NOT fix unless the answer itself implies a change.
3. WHEN a review thread's user comment suggests an approach and that approach validates as sound THEN `ship-spec` SHALL classify it as apply-as-directed.
4. WHEN a review thread's user comment suggests an approach that does not hold up on validation THEN `ship-spec` SHALL classify it as pushback — it SHALL NOT apply the suggested approach uncritically.
5. WHEN a standalone comment exists with no anchored code-review/tests-code-review finding THEN `ship-spec` SHALL apply the same apply-as-directed-or-pushback treatment as a suggested-approach comment on a finding.

**Independent Test**: Manually create four review threads (no comment; a question; a sound suggestion; an unsound suggestion) on a test PR, run the fix trigger, and confirm each is classified per the rule above independent of which skill originated the underlying finding.

---

### P1: Lightweight plan generation with immediate execution

**User Story**: As a developer, I want a written plan of what will be fixed and how, generated cheaply and executed immediately without a second approval step, so triage stays fast while still leaving an audit trail.

**Why P1**: Directly implements the confirmed "no approval gate, but must handle removed findings" decision.

**Acceptance Criteria**:

1. WHEN the fix trigger is invoked AND the PR's review(s) are still PENDING (unsubmitted) THEN `ship-spec` SHALL report that the review is still pending and SHALL NOT fetch, classify, or fix anything.
2. WHEN the fix trigger is invoked AND the review(s) are submitted THEN `ship-spec` SHALL fetch all unresolved threads once via the existing GraphQL query, classify each per the P1 classification story, and write the result to `.specs/features/<feature>/fix-code-review.md` as a flat list grouped into a parallel-safe bucket and one or more sequential (same-file/thread) buckets — before any fix execution begins.
3. WHEN the plan file has been written THEN `ship-spec` SHALL NOT pause for user approval — execution SHALL proceed immediately in the same invocation.
4. WHEN execution is about to begin (immediately after the plan is written) THEN `ship-spec` SHALL perform exactly one additional GraphQL fetch of the same unresolved-threads query, diff it against the just-built plan, and silently drop from execution any item no longer present, already resolved, or changed since the first fetch — with no further per-item GitHub reads.
5. WHEN zero unresolved threads are found (at either fetch) THEN `ship-spec` SHALL still write `fix-code-review.md` noting zero items, and SHALL stop without dispatching any fix agents.

**Independent Test**: Trigger "fix" against a PR with several classified threads, confirm `fix-code-review.md` is written with correct grouping before any commit lands, and confirm a thread deleted between the two fetches is absent from what actually gets fixed.

---

### P1: Safe concurrent fix execution

**User Story**: As a developer, I want independent fixes computed in parallel for speed, but committed safely to my checkout without git corruption risk.

**Why P1**: Resolves the confirmed split-phase design — without it, concurrency (as requested) and the shared, non-worktree-isolated checkout (kept from today) directly conflict.

**Acceptance Criteria**:

1. WHEN the (post-re-fetch) plan's parallel-safe bucket contains items THEN `ship-spec` SHALL dispatch up to 4 concurrent subagents at a time, each performing only the investigation/fix-drafting for its one item — no file edits, no git operations — and returning its proposed change.
2. WHEN a drafting subagent's proposed change is ready THEN `ship-spec` SHALL apply that item's edit and commit it on the shared checkout one at a time — never two commits attempted concurrently against the same checkout.
3. WHEN the parallel-safe bucket has more than 4 items THEN `ship-spec` SHALL process them in batches of up to 4 concurrent drafts, with commits remaining fully serialized regardless of batch size.
4. WHEN the plan's sequential bucket has items (same file/thread dependencies) THEN `ship-spec` SHALL draft and commit them one at a time, honoring their required order — no concurrent drafting for this bucket.
5. WHEN a fix is committed THEN `ship-spec` SHALL run only that item's own directly relevant test(s) as its completion check — not the full project suite, not a full `tlc-spec-driven` gate/verify cycle.
6. WHEN a fix subagent cannot complete (blocked) THEN `ship-spec` SHALL record the blocker as that item's outcome in the final report instead of failing silently or halting the remaining items.
7. WHEN commits are applied THEN `ship-spec` SHALL reply/resolve each GitHub thread per its classification (silent resolve for auto-fix/apply-as-directed; reply-and-leave-open for pushback/question) and SHALL NOT set `isolation: worktree` on any of these subagents.

**Independent Test**: Build a plan with 5+ independent items and 2 sequential (same-file) items; confirm drafting happens concurrently (capped at 4), commits appear one at a time in git log with no interleaving/corruption, and the sequential pair lands in the required order.

---

### P2: Model tiering for fix drafting

**User Story**: As a developer, I want the mechanical fix-drafting step to run on a cheaper model since the fix direction is already decided, so triage costs less without sacrificing judgment quality where it matters.

**Why P2**: A cost optimization layered on top of already-correct P1 behavior — the flow is correct without it, just more expensive.

**Acceptance Criteria**:

1. WHEN a fix-drafting subagent is dispatched (per the Safe Concurrent Fix Execution story) THEN `ship-spec` SHALL use the Haiku model for it.
2. WHEN classification (auto-fix / question / apply-as-directed / pushback determination) or reply composition occurs THEN `ship-spec` SHALL use the orchestrator's default model — never Haiku — since these require judgment.

**Independent Test**: Inspect the `Agent` tool calls for a fix-triage run and confirm drafting subagents specify the Haiku model while the classification/reply logic in the orchestrator's own turn does not.

---

## Edge Cases

- WHEN more than 100 unresolved threads exist (the existing GraphQL page-size cap) THEN `ship-spec` SHALL process only the first page and SHALL explicitly note in its report that additional threads may exist beyond what was fetched.
- WHEN a GitHub API call fails at any point (posting, fetching, resolving, replying) THEN `ship-spec` SHALL report the failure to the user rather than silently continuing, swallowing the error, or retrying indefinitely.
- WHEN both Step 6 subagents fail THEN `ship-spec` SHALL report both failures explicitly and SHALL NOT proceed as if a review was successfully posted.
- WHEN the user invokes the fix trigger a second time after a prior run already resolved most threads THEN `ship-spec` SHALL naturally see only the remaining unresolved threads (existing `isResolved` filter, unchanged) and build a fresh plan from those alone.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SSF-01 | P1: Concurrent analysis, single merged pending review | Design | Pending |
| SSF-02 | P1: Concurrent analysis, single merged pending review | Design | Pending |
| SSF-03 | P1: Comment-presence-driven fix classification | Design | Pending |
| SSF-04 | P1: Comment-presence-driven fix classification | Design | Pending |
| SSF-05 | P1: Comment-presence-driven fix classification | Design | Pending |
| SSF-06 | P1: Comment-presence-driven fix classification | Design | Pending |
| SSF-07 | P1: Lightweight plan generation with immediate execution | Design | Pending |
| SSF-08 | P1: Lightweight plan generation with immediate execution | Design | Pending |
| SSF-09 | P1: Lightweight plan generation with immediate execution | Design | Pending |
| SSF-10 | P1: Lightweight plan generation with immediate execution | Design | Pending |
| SSF-11 | P1: Safe concurrent fix execution | Design | Pending |
| SSF-12 | P1: Safe concurrent fix execution | Design | Pending |
| SSF-13 | P1: Safe concurrent fix execution | Design | Pending |
| SSF-14 | P1: Safe concurrent fix execution | Design | Pending |
| SSF-15 | P1: Safe concurrent fix execution | Design | Pending |
| SSF-16 | P1: Safe concurrent fix execution | Design | Pending |
| SSF-17 | P2: Model tiering for fix drafting | Design | Pending |
| SSF-18 | P2: Model tiering for fix drafting | Design | Pending |

**ID format:** `SSF-[NUMBER]` (Ship-Spec Fix-triage)

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 18 total, 0 mapped to tasks yet, 18 unmapped ⚠️ (expected pre-Design)

---

## Success Criteria

How we know the feature is successful:

- [ ] Real `ship-spec` run shows one merged pending review posted (containing both skills' findings) after concurrent analysis, with no 422 "pending review already exists" error
- [ ] A fix-trigger run against a thread with no comment results in a silent fix + resolve, zero reply comments posted
- [ ] A fix-trigger run against a thread with a question results in a reply and the thread staying unresolved
- [ ] `fix-code-review.md` is written and correctly grouped (parallel vs. sequential) before any commit lands
- [ ] `git log` after a multi-item fix run shows no interleaved/corrupted commits — one commit per item, cleanly ordered
- [ ] Fix-drafting subagents are confirmed to run on Haiku; classification/replies confirmed to run on the default model
