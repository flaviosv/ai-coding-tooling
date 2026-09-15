# STATE

## Decisions

### AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) at this skill's one dispatch site (the off-Sonnet subagent launch) — completion condition tied to the selected mode's context files existing on disk, return shape restricted to file paths plus a short summary, delegation depth: none.
- **Reason**: Part of a repo-wide retrofit applied to every skill in `skills/` that dispatches subagents, following a `session-evaluate` audit of a real `build-feature` run.
- **Trade-off**: None identified.
- **Date**: 2026-09-02
- **Status**: superseded by AD-006

### AD-002
- **Decision**: Compressed the three fully-narrated Incremental Mode worked-example traces (Go `auth.go` update, Magento `Shipping` package-mode, Go `internal/notifications` decline) into one merged compact example; removed all three `docs/TECH_DEBTS.md` cross-references (Shared Guardrails out-of-scope bullet, Step 11 Tone instruction, Step 6 Holistic Sweep do-not-modify list) since the file is not in use; deleted two duplicate/generic Step 12 instruction lines — the secrets/tokens restatement (near-duplicate of the fuller "never write secret values" statement in Shared Guardrails) and the content-free "only include sections with evidence" platitude.
- **Reason**: Applying three approved fixes (rows #1–#3, `skills/architecture-evaluate`) from this repo's 2026-09-12 harness-eval run (`docs/HARNESS-EVALUATION.md`) — both Track B judges scored the example traces and the two Step 12 lines REDUNDANT, and `docs/TECH_DEBTS.md` no longer exists/is in use in this repo.
- **Trade-off**: The merged example demonstrates only the new-package-confirmed path directly; the decline branch is now a one-line parenthetical instead of its own full walkthrough.
- **Date**: 2026-09-12
- **Status**: active

### AD-003
- **Decision**: Replace the `templates/subagent-models.md` and `templates/subagent-dispatch-contract.md` links (Shared Guardrails Sonnet-pin and Model Pinning dispatch contract) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked files.
- **Trade-off**: Same dependency as `code-review`'s AD-007 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: superseded by AD-006

### AD-004
- **Decision**: Full mode's Step 13 report says agents load the context files when the project's session-start context list references them, instead of claiming they load "via the directive in CLAUDE.global.md".
- **Reason**: User decision (harness-evaluation #18 scope): naming a file outside the skill as the source of a behavior is a dependency. `CLAUDE.global.md` is this harness repo's file name and does not exist in the projects this skill maps, so the claim was false there; registration is already handled by Additional Context Files & Registration.
- **Trade-off**: The report no longer names where the loading directive lives.
- **Date**: 2026-09-14
- **Status**: superseded by AD-008

### AD-005
- **Decision**: Added `scripts/context_scan.py` (Python 3 stdlib, JSON to stdout) as the single source of the facts mode decisions depend on — `baseline`, `misplaced`, `pipeline`, `deliverables`, and `changes` (working tree, or `<base>...HEAD` with `--base`). It replaces the two duplicated `ls`/`find` misplaced-file blocks and the Incremental `git diff`/`git ls-files` commands. Full Step 1 and the new Incremental Step 0 (baseline and misplaced-file check) run it; the ambiguity rule picks Incremental only when `changes.changed` is non-empty and `baseline.exists` is true, otherwise Full, and asks if still unclear; the `docs/` traversal guardrail names the scan as the one sanctioned way to locate canonical files elsewhere, reading only the paths it returns.
- **Reason**: User decisions on harness-evaluation Skills #6, #8, #10, #13 — the scan was duplicated and could drift, Incremental never ran it, the traversal guardrail contradicted a project-wide `find`, and ambiguous requests fell to the costliest mode. A script takes these mechanical checks out of model judgment.
- **Trade-off**: The skill depends on `python3` being available; the scan's exclusion list (`.git`, `node_modules`, vendor/build dirs, nested checkouts) and pipeline locations are fixed in code and need a script change to extend.
- **Date**: 2026-09-14
- **Status**: active

### AD-006
- **Decision**: The skill no longer mentions any other skill (`subagent-dispatch`, `tlc-spec-driven`, `mermaid-studio`, `build-feature`, `codenavi`) and no longer defers rules to files outside itself. The Sonnet pin, the `.specs/` out-of-scope rule, and Mermaid diagrams stay, stated without an owner or skill condition (the ASCII fallback went with the `mermaid-studio` condition). The dispatch uses `subagent_type: general-purpose`, `model: sonnet`, and states only this skill's completion condition and return shape (`status` ok/blocked/question, file paths, `questions`). Pointer registration and post-migration reference updates no longer enumerate `CLAUDE.global.md`/root `CLAUDE.md`/`AGENTS.md` — the agent identifies which root context files hold the list or reference old paths — and Incremental's root-file review is generic. The `codenavi` sentence was deleted after installing `codenavi` via fs-harness.
- **Reason**: User decisions on harness-evaluation Skills #4, #7, #12, #18: a skill never mentions other skills, and naming outside files as a rule's source is a dependency that breaks in projects without them (`agentType` was also the wrong parameter name).
- **Trade-off**: The dispatch no longer inherits the shared contract's observability prefix, scale estimate, or delegation-depth field; diagram tooling is left to whatever loads on its own.
- **Date**: 2026-09-14
- **Status**: active

### AD-007
- **Decision**: The skill writes its `.md` files itself; the "delegate every `.md` write to docs-writer" guardrail and all its echoes (the Full exploration step's write note, Incremental Step 7 heading and quote, verify/report lines, worked example, Package mode write step) were removed with no replacement rule.
- **Reason**: User decision under the no-other-skills rule (harness-evaluation Skills #18); the delegation carried no concrete formatting or link-integrity rule of its own worth restating.
- **Trade-off**: Formatting consistency now rests on this skill's own templates and the Update Merge Strategy rather than a dedicated writing skill.
- **Date**: 2026-09-14
- **Status**: active

### AD-008
- **Decision**: Mode and deliverable changes: Incremental accepts a caller-supplied base ref and syncs `<base>...HEAD` (frontmatter: "inspects the git workspace or a caller-supplied commit range"); Full mode's deliverables are the eight always-required files plus `PIPELINE.md` only when CI/CD or pipeline config exists (reported as skipped otherwise), and the subagent completion condition checks that list instead of "nine"; the off-Sonnet pre-flight resolves only the migration question before dispatch, while pointer registration, new-package scaffolding, and extra-doc refreshes come back as `questions` the parent asks afterward; the `/init` bootstrap step was deleted and steps renumbered (Full Steps 1–12); the report closes with "Agents load these files on demand, as each task needs them."; "Keeping Docs Up to Date" gained a first row "No `docs/codebase/` baseline exists → Full mode". Also: context-files table sorted alphabetically, CONCERNS Tone bullet and "Read the existing file first" removed.
- **Reason**: User decisions on harness-evaluation Skills #1, #2, #3, #5, #9, #14–#17 — a post-push caller found no working-tree changes, "nine on disk" was unreachable for CI-less projects, the pre-flight claimed to resolve a question it could not, `/init` risked clobbering a hand-edited `CLAUDE.md` for marginal value, and the report misdescribed loading behavior.
- **Trade-off**: A base-ref run ignores uncommitted working-tree changes; the report no longer says where loading is configured.
- **Date**: 2026-09-14
- **Status**: active

### AD-009
- **Decision**: Removed the Full-mode analysis-depth budget ("10–15 files for small/medium projects; 25–30 for monorepos, one representative module per layer"); sampling stays guided by "sample representative files — breadth over depth" and Step 3's per-category counts.
- **Reason**: User decision on harness-evaluation Skills #11: the budget contradicted Step 3's per-category counts, and sizing a project up front isn't reliable — the Full/Incremental split is the only dimensioning the skill needs.
- **Trade-off**: No overall cap on files read in Full mode; cost is bounded only by the per-category guidance.
- **Date**: 2026-09-14
- **Status**: active

### AD-010
- **Decision**: Removed the 25-item `metadata.triggers` YAML array from frontmatter; folded its 7 phrases not already in `description` ("initial architecture", "setup project docs", "run architecture-evaluate", "generate docs", "keep docs in sync", "api documentation") into `description`'s own "Use when..." list.
- **Reason**: `/claude-api prompt-audit` — `metadata.triggers` is read by no script in this repo (`validate_skill.py` checks trigger phrases in `description`, never `metadata.triggers`); the two lists had drifted apart (7 phrases existed only in `metadata.triggers`), so consolidating into the one list the validator and routing actually use removes a source of disagreement, not just redundancy.
- **Trade-off**: `description` is now longer (1284/1024 chars per `validate_skill.py`, worsening a pre-existing description_length failure that predates this change) — folding the phrases in kept trigger coverage but did not fix that separate, already-failing check; still open if the user wants it addressed.
- **Date**: 2026-09-14
- **Status**: active
