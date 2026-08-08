# SonarQube Support — Code Review Specification

## Problem Statement

The `code-review` and `tests-code-review` skills rely on Claude's semantic analysis alone. SonarQube provides complementary deterministic static analysis — bugs, vulnerabilities, code smells, and coverage gaps — with exact file/line precision. These findings currently require a separate dashboard visit, breaking the review flow. Integrating Sonar's new-code findings as enrichment context into existing review agents closes this gap without disrupting the current report structure.

## Goals

- [ ] `sonar integrate claude --global` is run once to install the MCP server and Claude Code hooks globally
- [x] Claude Code hooks (secrets scanning on `Read` tool use and prompt submission) are active and verified after setup
- [~] Context augmentation (`sonar context`) — **Community-incompatible**: not available on SonarQube Server; only on SonarQube Cloud. Documented in `docs/UNINSTALL_SONAR.md` as N/A.
- [ ] SonarQube MCP tools, when available, enrich existing review agents with Sonar's new-code findings (no new zone created)
- [ ] Both `code-review` and `tests-code-review` skills benefit from the enrichment
- [ ] The report header always declares Sonar status (active with issue counts, or skipped with reason)
- [ ] `docs/UNINSTALL_SONAR.md` documents complete, step-by-step removal of every artifact installed by `sonar integrate claude --global`
- [ ] Graceful degradation when Sonar MCP is not installed, the server is unreachable, or no project data exists for the current branch

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Automated `sonar integrate claude` invocation | One-time user setup; the skill assumes MCP is already installed |
| Creating a new Sonar zone/dimension in the report | Option B chosen: enrich existing agents, not a separate output zone |
| Posting Sonar-specific comments to GitHub PRs | Findings surface through enriched agents, not as standalone output |
| Managing SonarQube project setup or quality profiles | Infrastructure concern, outside skill scope |
| Running `sonar-scanner` inside the skill pipeline | Scanner is a CI/manual step; the skill reads existing analysis results only |
| Scanning local workspace changes not yet pushed or analyzed | Skill reads server-side data; unscanned local-only changes will not appear |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here — nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
|----------------------|----------------|-----------|-----------|
| Integration mechanism | MCP server via `sonar integrate claude --global` | Cleaner than per-skill CLI invocations; native tool access during review | y |
| Pipeline position | Option B: Sonar findings enriched into existing agents, no new zone | Keeps report structure stable; avoids redundant output | y |
| Scanner invocation | Skill does NOT run `sonar-scanner` | Scanner is a CI/pre-review step; skill reads existing results | y |
| Scope | Both `code-review` and `tests-code-review` | User confirmed both | y |
| Project key resolution | Read `sonar.projectKey` from `sonar-project.properties`; fall back to `.sonarlint/connectedMode.json` | Matches Sonar CLI conventions | y |
| Branch targeting | Use current git branch when querying Sonar issues | Reviews are branch-scoped; aligns with `sonar list issues --branch` | y |
| No data for branch | Note `Sonar: no data for branch <X> — run sonar-scanner first` in report header; proceed without enrichment | Scan may not have run yet for new branches | y |
| Sonar MCP tool names | Unknown until `sonar integrate claude --global` is run; implementation discovers and documents them | Compiled binary; tools not yet inspected | n — discover at implement |
| Diff filtering | Inject only Sonar issues for files present in the current diff; discard issues on unrelated files | Review is scoped to changed code | y |
| `tests-code-review` enrichment | Coverage data → `gap-detector`; coverage metrics → `coverage-reviewer`; test smells → most relevant agent | Best fit with existing agent responsibilities | y |
| `architecture-reviewer` enrichment | Architecture-relevant Sonar bugs are P2 (after MVP) | Not critical for MVP; security/quality enrichment is higher value | y |
| Uninstall document location | `docs/UNINSTALL_SONAR.md` | User-specified | y |
| Uninstall document authoring | Written after running `sonar integrate claude --global` and inspecting what was installed | Cannot accurately document removal before observing the install | y |
| Reversibility | Manual artifact-by-artifact removal (surgical); `sonar system reset --force` as nuclear option | Nuclear option also removes auth tokens — must be clearly warned | y |

**Open questions:** none — all resolved or logged above.

---

## User Stories

### P1: SonarQube Integration Setup ⭐ MVP

**User Story**: As a developer, I want to run a single command (`sonar integrate claude --global`) that installs the MCP server, git hooks, and context augmentation globally, so all three Sonar capabilities are active and verifiable in one step.

**Why P1**: The MCP enrichment, secrets scanning hooks, and context augmentation all depend on this setup. Nothing else in this spec works without it.

**Acceptance Criteria**:

1. WHEN `sonar integrate claude --global` is run THEN the Sonar MCP server SHALL be registered in `~/.claude.json` under `mcpServers` as `sonarqube` (**Note**: entry goes to `~/.claude.json`, not `~/.claude/settings.json`)
2. WHEN `sonar integrate claude --global` is run THEN Claude Code hooks for secrets scanning SHALL be installed in `~/.claude/settings.json`: a `PreToolUse` hook on `Read` and a `UserPromptSubmit` hook on `*`, both calling scripts in `~/.claude/hooks/sonar-secrets/build-scripts/` (**Note**: these are Claude Code lifecycle hooks, not git pre-commit/pre-push hooks)
3. Context augmentation — **Community-incompatible**: `sonar integrate claude --global` skips context augmentation on SonarQube Server Community. `sonar context` will report "not installed". This AC is N/A for Community edition.
4. WHEN setup is complete THEN `sonar system status` SHALL report `SYSTEM CHECK: Healthy` with an active token and connected server
5. WHEN setup is complete THEN each installed component (MCP server, Claude Code hooks) SHALL have a documented verification command in `docs/UNINSTALL_SONAR.md` confirming it is active

**Independent Test**: Run `sonar integrate claude --global` on a clean machine; verify all three components are present using the verification commands in `docs/UNINSTALL_SONAR.md`.

---

### P1: Complete Uninstall Documentation ⭐ MVP

**User Story**: As a developer, I want step-by-step instructions to cleanly remove each Sonar artifact individually so I can fully revert the integration — or remove only specific parts of it — at any time.

**Why P1**: Without uninstall documentation, reverting is risky — partial cleanup leaves broken hooks, lingering MCP entries, and orphaned context augmentation files. Each component must be independently removable.

**Acceptance Criteria**:

1. WHEN `sonar integrate claude --global` is run THEN all installed artifacts SHALL be inspected and every artifact type and file path SHALL be documented in `docs/UNINSTALL_SONAR.md` before any removal instructions are written
2. WHEN a developer follows the MCP server removal section of `docs/UNINSTALL_SONAR.md` THEN the Sonar entry SHALL be removed from `~/.claude.json` under `mcpServers`, and the wrapper script `~/.local/bin/sonar-mcp-wrapper.sh` SHALL be deleted; a verification command (`grep -i sonar ~/.claude.json`) SHALL confirm no entry remains
3. WHEN a developer follows the Claude Code hooks removal section of `docs/UNINSTALL_SONAR.md` THEN: the `PreToolUse[Read]` and `UserPromptSubmit[*]` hook entries SHALL be removed from `~/.claude/settings.json`; the hook scripts directory `~/.claude/hooks/sonar-secrets/` SHALL be deleted; a verification command SHALL confirm no Sonar hook entries remain in `~/.claude/settings.json`
4. Context augmentation removal — **N/A for Community edition**: `sonar context` reports "not installed" by default; no removal steps required. `docs/UNINSTALL_SONAR.md` SHALL document this condition.
5. WHEN any other artifacts are discovered during the install step (e.g. project-level config files, skill overrides, cache entries) THEN `docs/UNINSTALL_SONAR.md` SHALL include a dedicated removal section for each with its own verification command
6. WHEN a developer prefers a single-command nuclear option THEN `docs/UNINSTALL_SONAR.md` SHALL document `sonar system reset --force` with an explicit warning: this removes auth tokens in addition to all integration artifacts, requiring `sonar auth login` to restore access

**Independent Test**: Run `sonar integrate claude --global`, then follow each section of `docs/UNINSTALL_SONAR.md` independently (MCP, hooks, context augmentation); verify that after each section its specific verification command confirms the artifact is absent, and that the remaining sections' artifacts are still intact.

---

### P1: Sonar Enrichment in `code-review` ⭐ MVP

**User Story**: As a developer running a code review, I want Sonar's new-code findings automatically injected into the relevant review agents so that bugs, vulnerabilities, and code smells found by Sonar inform the review without creating a separate report zone.

**Why P1**: Core value of the integration — deterministic static analysis enriches Claude's semantic review with file/line-precise signal.

**Acceptance Criteria**:

1. WHEN `code-review` runs AND Sonar MCP tools are available AND a `sonar.projectKey` is resolvable THEN the skill SHALL query Sonar for open issues on the current branch before agent dispatch
2. WHEN Sonar issues are fetched THEN only issues for files present in the current diff SHALL be retained; issues for files outside the diff SHALL be discarded
3. WHEN Sonar issues are injected into an agent THEN each agent SHALL receive a structured `## Sonar Findings` block listing: issue type, severity, rule key, file path, line number, and message
4. WHEN vulnerabilities are present in the filtered Sonar issues THEN they SHALL be injected into `security-reviewer`'s prompt
5. WHEN bugs or code smells are present in the filtered Sonar issues THEN they SHALL be injected into `code-quality-reviewer`'s prompt
6. WHEN Sonar enrichment is active THEN the report header SHALL include `Sonar: active — N issues (B bugs, V vulnerabilities, S smells) · branch <branch>`
7. WHEN Sonar MCP tools are not installed THEN the skill SHALL proceed without enrichment and note `Sonar: skipped — MCP not installed` in the report header
8. WHEN the Sonar server is unreachable THEN the skill SHALL proceed without enrichment and note `Sonar: skipped — server unreachable` in the report header
9. WHEN no Sonar data exists for the current branch THEN the skill SHALL note `Sonar: no data for branch <branch> — run sonar-scanner first` in the report header and proceed without enrichment
10. WHEN no `sonar.projectKey` can be resolved THEN the skill SHALL note `Sonar: skipped — no project key found` in the report header and proceed without enrichment

**Independent Test**: With Sonar MCP installed and a branch scanned, run `code-review`; verify the report header shows "Sonar: active" and that security/quality agent output references Sonar-sourced issues with file:line.

---

### P1: Sonar Enrichment in `tests-code-review` ⭐ MVP

**User Story**: As a developer running a test code review, I want Sonar's coverage data and test quality issues injected into the relevant test review agents so coverage gaps and test smells from Sonar inform the review.

**Why P1**: `gap-detector` and `coverage-reviewer` directly benefit from Sonar's coverage data — this is complementary signal not derivable from the test diff alone.

**Acceptance Criteria**:

1. WHEN `tests-code-review` runs AND Sonar MCP tools are available AND a `sonar.projectKey` is resolvable THEN the skill SHALL query Sonar for coverage data and test-related issues on the current branch before agent dispatch
2. WHEN Sonar coverage data for new code is available THEN it SHALL be injected into `gap-detector`'s context (uncovered lines/branches on new code) and `coverage-reviewer`'s context (new code coverage percentage and metrics)
3. WHEN Sonar test quality issues (test smells, fragile tests, test-scoped code smells) are available THEN they SHALL be injected into the most relevant test review agent's context
4. WHEN Sonar enrichment is active THEN the report header SHALL include `Sonar: active — new code coverage N%`
5. WHEN Sonar MCP tools are unavailable, the server is unreachable, no project key is found, or no branch data exists THEN the same graceful degradation rules as `code-review` (AC7–AC10 above) SHALL apply

**Independent Test**: With Sonar configured and coverage data analyzed for a scanned branch, run `tests-code-review`; verify the report header shows "Sonar: active — new code coverage N%" and that gap-detector findings reference Sonar's uncovered line data.

---

### P2: Architecture-Reviewer Enrichment

**User Story**: As a developer, I want Sonar's architecture-level bugs injected into the `architecture-reviewer` agent so structural issues detected by Sonar are considered alongside Claude's architectural analysis.

**Why P2**: Useful enrichment but lower priority than security/quality/coverage signal for MVP.

**Acceptance Criteria**:

1. WHEN Sonar issues of type `BUG` associated with architecture-related rule keys are present in the filtered issue set THEN they SHALL be injected into `architecture-reviewer`'s context
2. WHEN no architecture-relevant Sonar issues exist THEN `architecture-reviewer` SHALL run without a Sonar block (no empty block injected)

**Independent Test**: With Sonar issues on architecture rules present in the diff, run `code-review`; verify `architecture-reviewer` output references those issues.

---

## Edge Cases

- WHEN `sonar-project.properties` and `.sonarlint/connectedMode.json` are both absent THEN the skill SHALL skip Sonar enrichment with `Sonar: skipped — no project key found`
- WHEN the Sonar MCP query takes longer than a reasonable timeout THEN the skill SHALL proceed without enrichment and note `Sonar: skipped — query timeout` in the report header
- WHEN Sonar returns partial data (e.g. issues but no coverage) THEN the skill SHALL inject what is available and note the partial state in the report header
- WHEN the current branch has no open issues but coverage data is present THEN `code-review` notes `Sonar: active — 0 issues` and `tests-code-review` injects coverage data normally
- WHEN the skill runs in GitHub PR mode THEN Sonar branch targeting SHALL use the PR's head branch name, not the local branch

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story | Phase | Status |
|---------------|-------|-------|--------|
| SNQ-01 | P1: Setup — MCP server registered in `~/.claude.json` under `mcpServers.sonarqube` | Design | Pending |
| SNQ-02 | P1: Setup — Claude Code hooks installed (`PreToolUse[Read]` + `UserPromptSubmit[*]`) in `~/.claude/settings.json` | Design | Pending |
| SNQ-03 | P1: Setup — context augmentation (**Community-incompatible**: N/A on SonarQube Server) | Design | N/A |
| SNQ-04 | P1: Setup — `sonar system status` healthy post-install | Design | Pending |
| SNQ-05 | P1: Uninstall — artifact identification: all paths and types listed in `docs/UNINSTALL_SONAR.md` | Design | Pending |
| SNQ-06 | P1: Uninstall — MCP server removal section with verification command | Design | Pending |
| SNQ-07 | P1: Uninstall — Claude Code hooks removal (`~/.claude/settings.json` entries + `~/.claude/hooks/sonar-secrets/` dir) with verification command | Design | Pending |
| SNQ-08 | P1: Uninstall — context augmentation section documenting Community-incompatibility (no removal steps needed; `sonar context` already reports not installed) | Design | Pending |
| SNQ-09 | P1: Uninstall — additional artifacts removal sections + nuclear option with auth-loss warning | Design | Pending |
| SNQ-10 | P1: `code-review` — Sonar MCP detection + project key resolution | Design | Pending |
| SNQ-11 | P1: `code-review` — diff-filtered issue fetching | Design | Pending |
| SNQ-12 | P1: `code-review` — structured `## Sonar Findings` injection per agent | Design | Pending |
| SNQ-13 | P1: `code-review` — report header Sonar status line | Design | Pending |
| SNQ-14 | P1: `code-review` — graceful degradation (4 skip conditions) | Design | Pending |
| SNQ-15 | P1: `tests-code-review` — coverage data injection into gap-detector + coverage-reviewer | Design | Pending |
| SNQ-16 | P1: `tests-code-review` — test quality issue injection | Design | Pending |
| SNQ-17 | P1: `tests-code-review` — report header Sonar coverage line | Design | Pending |
| SNQ-18 | P1: `tests-code-review` — graceful degradation (mirrors SNQ-14) | Design | Pending |
| SNQ-19 | P2: `architecture-reviewer` enrichment with architecture-tagged Sonar bugs | - | Pending |

**Coverage:** 19 total, 0 mapped to tasks, 19 unmapped ⚠️

---

## Success Criteria

How we know the feature is successful:

- [ ] `sonar integrate claude --global` completes and all three components (MCP server, git hooks, context augmentation) are verified active via documented commands
- [ ] A commit with a hardcoded secret triggers the pre-commit secrets hook and is blocked
- [ ] Running `code-review` on a branch with Sonar analysis shows `Sonar: active — N issues` in the header and Sonar findings appear in security/quality agent output with file:line references
- [ ] Running `tests-code-review` on a branch with coverage data shows `Sonar: active — new code coverage N%` in the header
- [ ] When Sonar MCP is not installed, both skills run identically to their pre-integration behavior (no errors, no Sonar references)
- [ ] Following `docs/UNINSTALL_SONAR.md` completely removes all Sonar artifacts; each verification command confirms absence
- [ ] All four graceful degradation conditions (MCP not installed, server unreachable, no branch data, no project key) produce the correct header line and do not break the review
