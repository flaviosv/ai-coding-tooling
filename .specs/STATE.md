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

## Handoff

- **Feature**: `.specs/features/review-dispatch-efficiency` (RD-EFFICIENCY) — implementation complete, Verifier PASS
- **Phase / Task**: Post-implementation validation pending (not a tasks.md task — a real-world measurement step deferred to a future session)
- **Completed**: T1, T2, T3, T4 (all committed and Verifier-passed, 2 iterations — see `validation.md`). Related, already-shipped same-day: the Medium-tier regression fix (`5ecaacd`, `91ff220`), separate from this feature.
- **In-progress**: none — feature is fully done; only the deferred measurement below remains
- **Next step**: Run `python3 ~/.claude/tools/review-token-usage.py --json .specs/features/review-dispatch-efficiency/after-fix.jsonl` once fresh `code-review`/`tests-code-review` usage exists in the recargapay project (post commits `cc829ab`/`39a47c7`/`80b44de`/`82f91b8`/`0766349`). Compare against `.specs/features/review-dispatch-efficiency/baseline-before-fix.jsonl`. Full instructions in `spec.md`'s "Pending Validation" section.
- **Blockers**: none — purely waiting on real future usage data to exist; nothing to fix or decide
- **Uncommitted files**: none (working tree clean; `.specs/` itself is gitignored by project convention, so its contents — including this file — are local-only, not pushed)
- **Branch**: main
