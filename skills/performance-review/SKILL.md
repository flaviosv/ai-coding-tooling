---
name: performance-review
description: >
  Identify performance bottlenecks, memory issues, and optimization opportunities in any codebase.
  Technology agnostic — adapts to the project's stack using context files. Use when the user says
  "performance review", "performance audit", "optimize performance", "slow code", or "performance
  bottleneck". Do NOT trigger for general code review — this skill is invoked by code-review
  automatically for its performance section.
metadata:
  version: "1.0.0"
  triggers:
    - "performance review"
    - "performance audit"
    - "optimize performance"
    - "performance bottleneck"
    - "slow code"
    - "slow query"
---

# Performance Review

Identify performance bottlenecks, memory issues, and optimization opportunities in the codebase.

## Operating Modes

### Mode 1: Proactive Optimization (Default)
Apply performance best practices when writing new code. Write performant code from the start.

### Mode 2: Passive Detection
While reviewing code, flag critical performance issues without being asked. Focus on high-impact
findings — not micro-optimisations.

### Mode 3: Performance Audit Report
When explicitly requested, produce a comprehensive performance report across the codebase.

---

## Review Process

### Step 1: Load references

Always load the generic performance baseline:
- `references/performance-checklist.md`

Then identify the project's language and framework from `.agents/PROJECT_DETAILS.md` and load
**all** matching technology-specific reference files from the same `references/` directory.

Reference files follow the naming convention `<language>-<framework>-*.md`. Load every file that
matches the detected stack — for example, if the stack is Python + Django, load both
`python-performance-best-practices.md` and `django-performance-best-practices.md`.

Apply all loaded sources together — the generic checklist sets the baseline, technology-specific
references deepen it.

### Step 2: Apply the checklist to the target scope

- In **passive / code-review mode**: scope findings strictly to the changed files
- In **audit mode**: review the full codebase

### Step 3: Report findings

In **passive / code-review mode**: surface findings as rows in the review table with appropriate
severity.

In **audit mode**: produce a structured report (see Report Format below).

---

## Report Format

When producing a full audit report:

### Executive Summary
- Overall performance assessment
- Count of critical issues
- Estimated impact of top fixes

### Critical Findings (P0)
Issues that significantly impact performance and must be fixed immediately.

```
[ID] [Title]
Impact: <description of performance impact>
Location: <File:Line>
Current: <what is happening now>
Recommendation: <specific fix>
Expected Improvement: <estimated benefit>
```

### High Priority (P1)
Issues with measurable performance impact.

### Medium Priority (P2)
Optimisations that would improve performance moderately.

### Low Priority (P3)
Minor optimisations and best-practice suggestions.

Write the report to `performance_review_report.md` or a user-specified location.

---

## Example

User says: "Can you do a performance audit of the orders module?"

1. Load `references/performance-checklist.md`
2. Detect stack from `.agents/PROJECT_DETAILS.md` (e.g. Python + Django)
3. Load ALL matching stack-specific files: `references/python-performance-best-practices.md` AND `references/django-performance-best-practices.md`
4. Scan changed or scoped files for issues
5. Produce a structured report written to `performance_review_report.md` with findings grouped by P0/P1/P2/P3

## When No References Match

If no technology-specific reference file exists for the detected stack:
- Apply the generic `references/performance-checklist.md` in full
- Note in the report that stack-specific guidance was not available
- Focus findings on universal performance principles (algorithmic complexity, I/O, memory, caching)

## Principles

**Do:**
- Focus on measurable, high-impact issues
- Provide specific, actionable recommendations
- Consider whether code is in a hot path before flagging it
- Balance performance with readability and maintainability
- Suggest profiling when the bottleneck is unclear

**Do not:**
- Micro-optimise cold code paths
- Sacrifice readability without clear benefit
- Recommend changes without evidence of impact
- Optimise the 80% that does not matter
