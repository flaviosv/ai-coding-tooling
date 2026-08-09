# STATE

## Decisions

### AD-001
- **Decision**: Token-cost reduction for `code-review`/`tests-code-review` is pursued via agent-count reduction (single-agent tiers, dimension merges) — never via per-dimension model-tier downgrades.
- **Reason**: Real usage data showed agent count (each dispatched agent independently re-primes the same diff/checklists/docs) is the dominant cost driver, not model choice. A cheaper model on some dimensions would trade review quality for a smaller saving than fixing agent count.
- **Trade-off**: None taken — this was the higher-leverage, zero-quality-cost option; model tiering was evaluated and explicitly rejected.
- **Scope**: `skills/code-review/`, `skills/tests-code-review/`, and any future skill using the same subagent-dispatch pattern.
- **Date**: 2026-08-08
- **Status**: active

### AD-002
- **Decision**: `ship-spec`'s subagent-wrapper around `code-review`/`tests-code-review` (Step 6) is an intentional context-isolation boundary, not overhead to eliminate. Future token-optimization work must not propose relocating that work into `ship-spec`'s own main-session context.
- **Reason**: The wrapper's cost is the same Steps 1–9 orchestration cost any invocation of these skills pays somewhere; removing the subagent would only relocate ~19M tokens into a context that persists for the rest of the delivery conversation, and would violate the guardrail this step already had ("neither skill belongs in ship-spec's own context").
- **Trade-off**: A small, real inefficiency (double cold-start context-priming when running two sequential wrapper subagents) was fixed instead (RD-EFFICIENCY, commit `80b44de`) — merged into one subagent that runs both skills sequentially, preserving the isolation boundary.
- **Scope**: `skills/ship-spec/`, and any future orchestrating skill that delegates to `code-review`/`tests-code-review` via a subagent.
- **Date**: 2026-08-08
- **Status**: active

### AD-003
- **Decision**: GitHub allows only **one pending (unsubmitted) PR review per user per PR at a time**. Any skill/flow that posts GitHub PR review comments as a pending review — regardless of how many logical sources of findings contribute to it — must merge everything into a single `comments` array and issue exactly one `POST .../pulls/{PR}/reviews` call (event omitted). A second such call while one is still pending returns HTTP 422 ("A review cannot be created because a pending review already exists"), and there is no API to incrementally append to an already-open pending review. This holds regardless of dispatch timing (sequential or parallel) — it is not a race condition to work around, it's a hard one-per-PR ceiling.
- **Reason**: Confirmed against GitHub's REST API docs and community-reported behavior while designing `ship-spec-review-fix-flow` (2026-08-08). Discovered because the then-current `ship-spec` Step 6 text claimed two skills (`code-review`, `tests-code-review`) each produce their own separate pending review — that claim does not match documented GitHub behavior and should be treated as an unverified/likely-latent-bug risk in the shipped skill, independent of this feature.
- **Trade-off**: Any flow wanting to publish findings from multiple independent analysis sources on one PR must run the analysis concurrently (cheap to parallelize, no GitHub writes) and defer merging + the single publish call until all sources are ready — you lose "publish as each source finishes independently," which is a real, permanent constraint of the platform, not a temporary design choice.
- **Scope**: Any current or future skill posting GitHub PR review comments as a pending review (`skills/ship-spec/`, `skills/code-review/`, `skills/tests-code-review/`, and their shared `templates/github-pr-review-mode.md`).
- **Date**: 2026-08-08
- **Status**: active

### AD-004
- **Decision**: AD-001's prohibition on model-tier downgrades is scoped to **analytical/judgment-bearing agents** (e.g. review dimension agents, classification/validation steps) where output quality depends on model capability. It does **not** extend to subagents performing **purely mechanical execution of an already-fully-decided change** — where the judgment call (what to change, and why) was already made by a default-model step before dispatch, and the subagent's job is just to apply it and run a narrow, already-identified test. Those may use a cheaper tier (e.g. Haiku).
- **Reason**: Surfaced while designing `ship-spec-review-fix-flow`'s fix-drafting subagents (2026-08-08) — the fix direction is fully decided by classification (default model) before the drafting subagent is ever dispatched, making this categorically different from AD-001's concern (a reviewer's own judgment determining review quality).
- **Trade-off**: None taken — this clarifies AD-001's boundary rather than weakening it; judgment-bearing steps (classification, pushback validation, question-answering) still stay on the default model under both decisions.
- **Scope**: Any current or future skill dispatching subagents to execute an already-decided change (`skills/ship-spec/` Comment-Triage fix-drafting today; any future skill with the same shape).
- **Date**: 2026-08-08
- **Status**: active

## Handoff

- **Feature**: `.specs/features/ship-spec-review-fix-flow` — implementation complete, Verifier PASS (2 iterations)
- **Phase / Task**: Post-implementation real-world validation pending (not a tasks.md task — spec.md's Success Criteria all require a live `ship-spec` run, deferred to a future session)
- **Completed**: T1–T9 (T9 = post-Verifier fix round; all committed, Verifier-passed 2 iterations — see `validation.md`). Also: `AD-003` (GitHub one-pending-review-per-PR limit) and `AD-004` (model-tier scope boundary) recorded; 3 new candidate lessons distilled (L-003, L-004, L-005).
- **In-progress**: none — feature is fully done; only the deferred real-run validation below remains
- **Next step**: Next time `/ship-spec` runs a real delivery (Step 6) and a real comment-triage round, check spec.md's 6 Success Criteria boxes against what actually happens: one merged pending review (no HTTP 422), silent resolve for no-comment findings, reply+leave-open for questions, `fix-code-review.md` written and correctly grouped before execution, clean serialized `git log` (no interleaved commits), and Haiku confirmed on the fix-drafting subagents. Check each box off individually against real evidence, not assumed from the spec text.
- **Blockers**: none — purely waiting on a real future `ship-spec` invocation; nothing to fix or decide
- **Uncommitted files**: none (working tree clean; `.specs/` is now tracked in git per repo convention as of the `review-dispatch-efficiency` feature — this file and the whole feature folder are committed and pushed-eligible)
- **Branch**: main

---

- **Prior feature**: `.specs/features/review-dispatch-efficiency` (RD-EFFICIENCY) — implementation complete, Verifier PASS. Real-world token-usage validation still deferred (see `spec.md`'s "Pending Validation" section: run `python3 ~/.claude/tools/review-token-usage.py --json .specs/features/review-dispatch-efficiency/after-fix.jsonl` once fresh usage exists in the recargapay project, compare against `baseline-before-fix.jsonl`). Unrelated to and unaffected by `ship-spec-review-fix-flow` above.
