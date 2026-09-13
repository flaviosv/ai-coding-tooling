# Sonar

Step 4.5: pulling SonarQube issues and coverage for the files under review, routing them to the agents that use them, and the report's `Sonar:` line. Loaded only when Step 2 resolved a `sonar_project_key`.

---

## Resolution

Runs after Step 4 (file lists known) and before Step 5. Tools come from the `sonarqube` MCP server.

```
IF sonarqube MCP tools are unavailable in this session:
    sonar_context = { status: 'skipped', skip_reason: 'MCP not installed' }
    GOTO Step 5

ATTEMPT:
    # one issues query over the files of every active scope
    # GitHub PR target: omit branch, pass pullRequest=<PR key>
    issues = search_sonar_issues_in_projects(
        projects=[sonar_project_key],
        branch=<current git branch>,
        issueStatuses=["OPEN"],
        files=[sonar_project_key + ":" + f for f in impl_files + test_files]   # active scopes only
    )

    # code scope
    security_issues = [i in issues on impl_files where "SECURITY" in i.impactSoftwareQualities]
    quality_issues  = [i in issues on impl_files where "RELIABILITY" or "MAINTAINABILITY" in i.impactSoftwareQualities]

    # tests scope
    test_issues = [i in issues on test_files where "MAINTAINABILITY" in i.impactSoftwareQualities]
    measures = get_component_measures(
        projectKey=sonar_project_key,
        branch=<current git branch>,
        metricKeys=["new_coverage", "new_lines_to_cover", "new_uncovered_lines"]
    )
    low_coverage_files = search_files_by_coverage(
        projectKey=sonar_project_key,
        branch=<current git branch>,
        maxCoverage=80
    )   # keep only files in impl_files

    sonar_context = {
        status: 'active',
        project_key, branch,
        issues_by_agent: {                              # each sorted by severity desc, cap 30
            security_reviewer:     security_issues,
            code_quality_reviewer: quality_issues,      # consumed by design-quality-reviewer when merged
            coverage_reviewer:     test_issues
        },
        coverage: { new_coverage_pct, new_lines_to_cover, new_uncovered_lines, low_coverage_diff_files },
        summary: { total, security, quality, test }
    }

ON server unreachable / connection error:  { status: 'skipped', skip_reason: 'server unreachable' }
ON empty result for this branch:            { status: 'skipped', skip_reason: 'no data for branch <branch> — run sonar-scanner first' }
ON measures unavailable, issues present:    status 'active', omit coverage, header shows 'active (partial)'
ON timeout:                                 { status: 'skipped', skip_reason: 'query timeout' }
```

Skip the measures and coverage calls when the tests scope isn't active, and the code-scope routing when the code scope isn't. In every skipped state the review proceeds exactly as without Sonar and no agent receives a Sonar block.

## Prompt Blocks

Injected into an agent's prompt only when `status == 'active'` and that agent has data — never as an empty block.

**Issues** (`security-reviewer`, the code-quality agent, `coverage-reviewer`):

```
## Sonar Findings
SonarQube detected the following issues on branch `<branch>` in files within this diff.
Use as additional signal — they do not replace your analysis.

| Type | Severity | Rule | File | Line | Message |
|------|----------|------|------|------|---------|
<one row per issue mapped to this agent, severity desc, max 30>
```

**Coverage** (`gap-detector`, or the Medium-tier tests agent when `impl_diff` is non-empty):

```
## Sonar Coverage Data
SonarQube coverage for new code on branch `<branch>`:
- New code coverage: <new_coverage_pct>%
- New lines to cover: <new_lines_to_cover>
- New uncovered lines: <new_uncovered_lines>

Files in this diff with coverage below 80%:
<low_coverage_diff_files>

Use this as a starting point — focus gap analysis on these uncovered areas.
```

## Report Line

Active segments are joined with ` · `, showing only the active scopes' parts:

| Condition | `Sonar:` line |
|---|---|
| Active | `active — N issues (S security, Q quality, T test) · new code coverage <N>% · branch <branch>` |
| Active, 0 issues | `active — 0 issues · branch <branch>` |
| Active, coverage unavailable | `active (partial) — issues only, coverage unavailable · branch <branch>` |
| MCP not installed | `skipped — MCP not installed` |
| No branch data | `no data for branch <branch> — run sonar-scanner first` |
| No project key | `skipped — no project key found` |
| Query timeout | `skipped — query timeout` |
| Server unreachable | `skipped — server unreachable` |
