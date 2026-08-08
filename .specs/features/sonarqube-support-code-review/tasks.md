# SonarQube Support — Code Review Tasks

## Execution Protocol (MANDATORY — do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Design**: `.specs/features/sonarqube-support-code-review/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec. Guidelines found: `docs/codebase/TESTING.md` — no test framework installed; `.md` skill content is reviewed manually; no automated gate exists.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
|------------|-------------------|---------------------|-----------------|-------------|
| `skills/*.md` skill instructions | none — manual behavioral verification | Each modified skill behaves per spec ACs: correct output when Sonar active; correct degradation in all 4 skip conditions | `skills/code-review/SKILL.md`, `skills/tests-code-review/SKILL.md` | Manual: run skill, inspect output |
| `docs/UNINSTALL_SONAR.md` | none — manual execution | Every artifact removed; every verification command confirms absence | `docs/UNINSTALL_SONAR.md` | Manual: follow guide, run verification commands |
| `design.md` update | none — review | Exact MCP tool names replace placeholders | `.specs/features/sonarqube-support-code-review/design.md` | Manual: inspect tool names are real, not placeholder |

## Parallelism Assessment

> Generated from codebase.

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
|-----------|---------------|-----------------|---------|
| Manual behavioral (skill runs) | Yes | Each skill invocation is independent; no shared state | Skills are stateless markdown instructions |
| Manual uninstall execution | Yes | Uninstall is destructive but isolated to the Sonar integration artifacts | No shared state with other tasks |

## Gate Check Commands

> Generated from codebase.

| Gate Level | When to Use | Command |
|------------|-------------|---------|
| Syntax check | After any `bin/skills.mjs` change (none in this feature) | `node --check bin/skills.mjs` |
| Behavioral verify | After each skill SKILL.md edit | Run `code-review` / `tests-code-review` in a project with Sonar configured; inspect report header and agent output |
| Uninstall verify | After `docs/UNINSTALL_SONAR.md` is written | Follow the guide; run each verification command; confirm all artifacts absent |

---

## Execution Plan

### Phase 1: Discovery (Sequential)

T1 must complete first — MCP tool names and artifact list are inputs to all Phase 2 tasks.

```
T1
```

### Phase 2: Documentation + Skill Edits (Parallel)

All three tasks depend on T1 and are independent of each other.

```
        ┌→ T2 (docs/UNINSTALL_SONAR.md)
T1 ─────┼→ T3 (code-review/SKILL.md)
        └→ T4 (tests-code-review/SKILL.md)
```

---

## Task Breakdown

### T1: Install `sonar integrate claude --global`, discover MCP tool names and artifact list, update design

**What**: Run `sonar integrate claude --global`, capture every file and config entry it creates, identify exact MCP tool names, update `design.md` Step 4.5 with real tool names replacing placeholders (`sonar_list_issues`, `sonar_get_coverage`).

**Where**:
- Run: `sonar integrate claude --global` (interactive or `--non-interactive`)
- Inspect: `~/.claude/settings.json` (MCP entry), global git hook paths, `sonar context` output
- Update: `.specs/features/sonarqube-support-code-review/design.md` — Step 4.5 tool name placeholders

**Depends on**: None

**Reuses**: `sonar system status` (already verified healthy in this session)

**Requirements**: SNQ-01, SNQ-02, SNQ-03, SNQ-04

**Tools**:
- MCP: none
- Skill: none

**Done when**:
- [ ] `sonar integrate claude --global` completes without error
- [ ] `sonar system status` reports `SYSTEM CHECK: Healthy` with active token
- [ ] MCP server entry is present in `~/.claude/settings.json` under `mcpServers` — confirm with: `grep -i sonar ~/.claude/settings.json`
- [ ] Git hook files installed globally — document exact paths and whether `git config --global core.hooksPath` was set
- [ ] `sonar context` reports installed (not "not installed")
- [ ] Exact MCP tool names noted (replace `sonar_list_issues` / `sonar_get_coverage` placeholders in `design.md` with real names)
- [ ] Full artifact list (every path, every config key set) recorded in `design.md` under a new `## Installed Artifacts` section — this list is the authoritative input for T2

**Tests**: none (investigation task — output is observed state + design update)
**Gate**: Manual inspection of each "Done when" check above

**Commit**: `chore(sonarqube): run sonar integrate claude --global, document MCP tools and artifacts`

---

### T2: Write `docs/UNINSTALL_SONAR.md` [P]

**What**: Author `docs/UNINSTALL_SONAR.md` with a dedicated removal section for every artifact discovered in T1 — MCP server, git hooks, context augmentation, and any others — each with exact removal commands and a verification command.

**Where**: `docs/UNINSTALL_SONAR.md` (new file)

**Depends on**: T1 (artifact list from `design.md` `## Installed Artifacts`)

**Reuses**: Artifact list from T1's `design.md` update

**Requirements**: SNQ-05, SNQ-06, SNQ-07, SNQ-08, SNQ-09

**Tools**:
- MCP: none
- Skill: none

**Done when**:
- [ ] `docs/UNINSTALL_SONAR.md` exists and is readable
- [ ] Section: **MCP server removal** — exact JSON key to remove from `~/.claude/settings.json` + verification: `grep -i sonar ~/.claude/settings.json` returns no match
- [ ] Section: **Git hooks removal** — exact hook file paths to delete; if `core.hooksPath` was set, command to unset it (`git config --global --unset core.hooksPath`); verification command confirms no Sonar hook active
- [ ] Section: **Context augmentation removal** — exact command to uninstall; verification: `sonar context` reports "not installed"
- [ ] Section for every additional artifact found in T1, each with removal + verification command
- [ ] Section: **Nuclear option** — `sonar system reset --force` documented with explicit warning: "This also removes your auth token. Run `sonar auth login` afterwards to restore access."
- [ ] Each verification command is independently executable (no "check after all steps" — each step has its own check)
- [ ] Manually verify: follow at least the MCP removal section on the installed machine; confirm verification command returns the expected absent state; re-run `sonar integrate claude --global` to restore

**Tests**: none (documentation + manual execution)
**Gate**: Uninstall verify (follow at least one section, confirm verification command passes, then reinstall)

**Commit**: `docs(sonarqube): add UNINSTALL_SONAR.md with complete removal guide`

---

### T3: Add Sonar enrichment to `skills/code-review/SKILL.md` [P]

**What**: Modify `skills/code-review/SKILL.md` at four points — Step 2 (project key resolution), new Step 4.5 (Sonar context resolution), Step 6 (agent injection), Step 8 (report header status line) — using the real MCP tool names from T1.

**Where**: `skills/code-review/SKILL.md`

**Depends on**: T1 (real MCP tool names)

**Reuses**: Existing Step 2 availability map pattern; existing Step 6 `## Before You Begin` injection pattern; existing Step 8 report header format

**Requirements**: SNQ-10, SNQ-11, SNQ-12, SNQ-13, SNQ-14

**Tools**:
- MCP: none
- Skill: none

**Done when**:
- [ ] **Step 2 augmented**: `sonar-project.properties` and `.sonarlint/connectedMode.json` presence checks added to context collection; `sonar_project_key` resolved and added to availability map
- [ ] **Step 4.5 added**: new section after Step 4, before Step 5; uses real MCP tool names (not placeholders); handles all 4 skip conditions (no key, MCP not installed, server unreachable, no branch data) with correct `skip_reason`; builds `sonar_context` with `issues_by_agent` mapping (vulnerabilities → `security-reviewer`, bugs+smells → `code-quality-reviewer`)
- [ ] **Step 6 augmented**: `## Sonar Findings` block injected into `security-reviewer` and `code-quality-reviewer` prompts when `sonar_context.status == active` and that agent has mapped issues; block omitted entirely when no issues for that agent; 30-issue cap noted
- [ ] **Step 8 augmented**: `Sonar:` line added after `Mode:` line; all 5 header variants present (active, skipped-MCP, skipped-unreachable, skipped-no-key, no-data-for-branch)
- [ ] Behavioral verify (active path): in a project with `sonar-project.properties` and a scanned branch, run `code-review` — report header shows `Sonar: active — N issues` and security/quality agents reference Sonar findings
- [ ] Behavioral verify (degraded — MCP not installed): temporarily disable the Sonar MCP entry, run `code-review` — header shows `Sonar: skipped — MCP not installed`; review proceeds normally
- [ ] Behavioral verify (no project key): in a project without `sonar-project.properties` or `.sonarlint/`, run `code-review` — header shows `Sonar: skipped — no project key found`

**Tests**: none (skill is a `.md` file; verified behaviorally)
**Gate**: Behavioral verify — all three paths above pass

**Commit**: `feat(code-review): add SonarQube enrichment — Step 2 key resolution, Step 4.5 context fetch, Step 6 injection, Step 8 status line`

---

### T4: Add Sonar enrichment to `skills/tests-code-review/SKILL.md` [P]

**What**: Modify `skills/tests-code-review/SKILL.md` at four points — Step 2 (project key resolution), new Step 4.5 (Sonar coverage + test-smell query), Step 6 (inject into `gap-detector` and `coverage-reviewer`), Step 8 (report header coverage line) — using real MCP tool names from T1.

**Where**: `skills/tests-code-review/SKILL.md`

**Depends on**: T1 (real MCP tool names)

**Reuses**: Same four-point pattern as T3; Step 2 availability map; Step 6 agent prompt injection; Step 8 header format

**Requirements**: SNQ-15, SNQ-16, SNQ-17, SNQ-18

**Tools**:
- MCP: none
- Skill: none

**Done when**:
- [ ] **Step 2 augmented**: identical to T3 — `sonar_project_key` resolution added to availability map
- [ ] **Step 4.5 added**: queries Sonar for test-scoped code smells AND coverage data for new code; builds `sonar_context` with `issues_by_agent` (smells → `coverage-reviewer`) and `coverage` object (`new_code_coverage_pct`, `uncovered_lines`); handles all 4 skip conditions
- [ ] **Step 6 augmented**: coverage data injected into `gap-detector` as an uncovered-lines block; coverage metrics + test smells injected into `coverage-reviewer`; blocks omitted when no data available
- [ ] **Step 8 augmented**: `Sonar:` line uses coverage format (`Sonar: active — new code coverage N% · branch <branch>`); same 5 degraded variants as T3
- [ ] Behavioral verify (active path): in a project with coverage data scanned, run `tests-code-review` — header shows `Sonar: active — new code coverage N%` and gap-detector/coverage-reviewer output references Sonar data
- [ ] Behavioral verify (degraded): in a project without Sonar configuration, run `tests-code-review` — skill behaves identically to pre-integration (no errors, no Sonar references in output)

**Tests**: none (skill is a `.md` file; verified behaviorally)
**Gate**: Behavioral verify — both paths above pass

**Commit**: `feat(tests-code-review): add SonarQube enrichment — Step 2 key resolution, Step 4.5 coverage fetch, Step 6 injection, Step 8 status line`

---

## Parallel Execution Map

```
Phase 1 (Sequential):
  T1 — Install sonar integrate claude --global, discover MCP tools + artifacts

Phase 2 (Parallel — all depend on T1, none depend on each other):
  T1 complete, then:
    ├── T2 [P] — docs/UNINSTALL_SONAR.md
    ├── T3 [P] — skills/code-review/SKILL.md
    └── T4 [P] — skills/tests-code-review/SKILL.md
```

---

## Task Granularity Check

| Task | Scope | Status |
|------|-------|--------|
| T1: Install + discover + update design | 1 investigation + 1 design.md section update | ✅ Granular — atomic discovery unit |
| T2: Write `docs/UNINSTALL_SONAR.md` | 1 new documentation file | ✅ Granular |
| T3: Modify `code-review/SKILL.md` | 1 file, 4 coordinated touch points within it | ✅ Granular — same file, interdependent edits |
| T4: Modify `tests-code-review/SKILL.md` | 1 file, 4 coordinated touch points within it | ✅ Granular — same file, interdependent edits |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
|------|----------------------|---------------|--------|
| T1 | None | Start node | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T1 | T1 → T3 | ✅ Match |
| T4 | T1 | T1 → T4 | ✅ Match |
| T2 vs T3 | No dependency | No arrow between them | ✅ Match |
| T2 vs T4 | No dependency | No arrow between them | ✅ Match |
| T3 vs T4 | No dependency | No arrow between them | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
|------|----------------------------|----------------|-----------|--------|
| T1 | `design.md` update | none — manual review | none — behavioral inspection | ✅ OK |
| T2 | `docs/UNINSTALL_SONAR.md` (new doc) | none — manual execution | none — manual execution | ✅ OK |
| T3 | `skills/code-review/SKILL.md` | none — manual behavioral | none — behavioral verify | ✅ OK |
| T4 | `skills/tests-code-review/SKILL.md` | none — manual behavioral | none — behavioral verify | ✅ OK |
