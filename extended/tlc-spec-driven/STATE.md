# STATE

## Decisions

### AD-001
- **Decision**: Replace the `templates/subagent-models.md` link in the Phase Models section with a reference to the new `subagent-dispatch` skill's model matrix (`references/model-matrix.md`).
- **Reason**: `templates/subagent-models.md` was consolidated, together with `templates/subagent-dispatch-contract.md`, into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked template files.
- **Trade-off**: This overlay's Phase Models sentence now assumes `subagent-dispatch` stays installed; removing that skill without updating this file would leave a stale pointer.
- **Date**: 2026-09-13
- **Status**: superseded by AD-005

### AD-002
- **Decision**: Replace the `Code Comments (always apply)` body in `references/coding-principles.md` with a pointer to the global `CLAUDE.md` Coding Style comment rule, stated as overriding this overlay's previous comment rule and any parent-skill comment guidance.
- **Reason**: The overlay restated the global rule with narrower exceptions (dropped "when explicitly requested", narrowed to "business logic"), so the two disagreed on edge cases inside tlc-spec-driven runs, where the global file is always loaded anyway (harness-eval `docs/harness-evaluation.md` Root Context Files row #14; same precedent as `skills/code-review/STATE.md` FR-AD-009, which shortened its copy to a pointer).
- **Trade-off**: The overlay now depends on the global `CLAUDE.md` being loaded; in an environment without it, tlc-spec-driven runs carry no comment rule.
- **Date**: 2026-09-14
- **Status**: superseded by AD-003

### AD-003
- **Decision**: `references/coding-principles.md` Code Comments restates the comment rule inline (comments only for genuinely complex or non-obvious logic, or when explicitly requested; never to narrate a variable, a config value, or a single line) instead of pointing at the global `CLAUDE.md` Coding Style rule, and still overrides the parent skill's comment guidance.
- **Reason**: User decision (harness-evaluation #18 scope): a skill must not defer its instructions to a file outside its directory, mentions included. The substance matches the global rule, so AD-002's disagreement problem does not return.
- **Trade-off**: The rule now lives in two places (this file and `CLAUDE.global.md`, kept by user choice) and can drift; a change to one must be mirrored in the other.
- **Date**: 2026-09-14
- **Status**: superseded by AD-009

### AD-004
- **Decision**: Removed the per-feature `commits.md` commit log: `SKILL.md`'s `## Commit Log` section and its item in the frontmatter description, and the whole `references/implement.md` overlay (qualifies/doesn't-qualify rules, format, Verifier cross-check), with its row in the Reference Extension Convention table.
- **Reason**: User decision (`docs/harness-evaluation.md` Overridden Skills #33, #43, #44, #49): what was pushed can be read from the repository itself. The log also cited a "No Automatic Git Commit or Push" rule that never existed, never said when the log itself gets committed, and its Verifier cross-check never reached the dispatched Verifier.
- **Trade-off**: No feature-scoped list of task commits exists any more; a branch's commit range also includes commits not traced to a task.
- **Date**: 2026-09-14
- **Status**: active

### AD-005
- **Decision**: Deleted the `Planning Is Prioritized` and `Phase Models` sections from `SKILL.md`, with no replacement and no pointer to any other skill.
- **Reason**: User decision (Overridden Skills #34, #35): Planning Is Prioritized restated the parent's auto-sizing, and its confirm-before-code gate conflicted with the parent's step thresholds and with orchestrated no-pause runs. Phase Models duplicated a model matrix owned elsewhere and named other skills, which the overlay must not do.
- **Trade-off**: The overlay no longer states which model tier each phase is expected on, or that a directly invoked phase runs on the session model; callers carry that knowledge themselves.
- **Date**: 2026-09-14
- **Status**: active

### AD-006
- **Decision**: Trimmed `coding-guidelines/best-practices-coding-guidelines.md` to concrete, checkable rules: deleted Boy Scout Rule, DRY, KISS, YAGNI, Low Coupling/High Cohesion, Composition over Inheritance, and Readability over Cleverness; collapsed SOLID to its concrete rules under a precedence line (DI, extension points, and polymorphism only where a second implementation, a test seam, or an existing project pattern needs them, otherwise the parent's "No abstractions for single-use code" wins); cut Separation of Concerns, Law of Demeter, and Fail Fast to one line each and Convention over Configuration to "document deviations"; renumbered the Pre-Completion Checklist to 6 items with the OCP/DIP items scoped by the same precedence. `coding-principles.md` no longer enumerates the principle names, and `observability-coding-guidelines.md` rule 4 is one line.
- **Reason**: User decision (Overridden Skills #32, #36, #37, #38, #50, #51, #52): the Boy Scout Rule contradicted the parent's Surgical Changes rules, the SOLID rules pulled against the parent's Simplicity rules with no stated winner, and the rest restated the parent or textbook theory on an always-loaded file.
- **Trade-off**: The file no longer carries the textbook definitions or the non-obvious DRY extraction heuristic; an agent relies on its own knowledge of them.
- **Date**: 2026-09-14
- **Status**: active

### AD-007
- **Decision**: `observability-coding-guidelines.md` rule 7 forbids logging passwords, tokens, session IDs, or card numbers at any level and requires redacting or hashing PII even at DEBUG, replacing the DEBUG-level sensitive-data allowance.
- **Reason**: User decision (Overridden Skills #39): DEBUG is often enabled in staging or during incidents and log stores keep data long, so the allowance was a real leak path. The same line in `skills/code-review/references/observability.code.md` was fixed together (code-review AD-015).
- **Trade-off**: Development diagnostics can no longer log raw PII at DEBUG.
- **Date**: 2026-09-14
- **Status**: active

### AD-008
- **Decision**: `coding-principles.md` Stack-Specific Style detects the project's stack without naming context-file paths or fallbacks, and loads `coding-guidelines/<technology>-coding-guidelines.md` files whose `<technology>` is a language or framework slug from that stack (e.g. `php`, `django`, `go-gin`).
- **Reason**: User decision (Overridden Skills #40, #41): the `PROJECT_DETAILS.md` and `.specs/codebase/` fallbacks pointed at files outside the skill that no generator produces, and project context is already loaded by the harness; the old `<language>-*.md` glob skipped framework-named guideline files.
- **Trade-off**: The overlay no longer tells the agent where stack information lives; a project with no loaded context leaves stack detection to the agent's own inspection.
- **Date**: 2026-09-14
- **Status**: active

### AD-009
- **Decision**: The overlay keeps exactly one comments statement, in `coding-principles.md` Code Comments (always apply), which now also allows language- or framework-mandated doc comments (e.g. Go `godoc` on exported identifiers); `best-practices-coding-guidelines.md`'s `## Comments` section was deleted.
- **Reason**: User decision (Overridden Skills #42): two always-loaded statements with different exceptions gave inconsistent guidance; the doc-comment exception was the only delta worth keeping from the second.
- **Trade-off**: The "explain why or what constraint, never what the code does" framing from the deleted section is gone.
- **Date**: 2026-09-14
- **Status**: active

### AD-010
- **Decision**: `SKILL.md` adds a Batch Worker Payload rule: a dispatched batch worker's payload includes `references.extended/coding-principles.md` and the `references.extended/coding-guidelines/` files it loads, alongside the parent's `references/coding-principles.md`.
- **Reason**: User decision (Overridden Skills #44, remaining part): the parent's batch-worker payload lists only `references/coding-principles.md`, and a fresh worker has no instruction to follow the Reference Extension Convention, so the overlay's design, observability, stack-style, and security rules silently dropped out whenever Execute delegated.
- **Trade-off**: Batch-worker payloads grow by the overlay files; the Verifier payload is unchanged, since the overlay no longer adds Verifier rules.
- **Date**: 2026-09-14
- **Status**: active

### AD-011
- **Decision**: Removed the load-order restatements: `SKILL.md`'s opener is one line (parent stays in force except where this file overrides a point), and each reference overlay's preamble is one line naming the parent section it patches. The Reference Extension Convention rule stays, with its table sorted alphabetically.
- **Reason**: User decision (Overridden Skills #46, #47): the "augments, never replaces" restatements repeated the convention in every file; the convention itself is the only instruction that makes `references.extended/` load, so it is kept.
- **Trade-off**: Reference overlays no longer restate which parent fields still apply; the reader takes that from the parent template.
- **Date**: 2026-09-14
- **Status**: active

### AD-012
- **Decision**: `references/specify.md` cross-references a `US-N` story in a task's title or description, not in `tasks.md`'s `**Requirement**` field, which keeps the parent's `[FEAT]-NN`.
- **Reason**: User decision (Overridden Skills #45): writing `US-N` into the Requirement field broke the parent's requirement-to-task traceability, and contradicted the overlay's own statement that the two IDs are independent.
- **Trade-off**: Story-to-task links live in free text rather than a structured field.
- **Date**: 2026-09-14
- **Status**: active
