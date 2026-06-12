# Feature Spec — Code Review Quality Enhancements

**Feature ID:** CR-QUALITY  
**Status:** Specifying  
**Skill target:** `skills/code-review/SKILL.md`

---

## Problem

Three quality patterns found in `skills/code-review/reference.md` (a project-specific PR review skill from Fakeflix) are missing from the generic `code-review` SKILL.md:

1. **No second-pass coverage check** — subagents can silently miss files without justification.
2. **No regression/hallucination detection** — no agent specifically hunts AI-generated artifacts (phantom imports, unrelated deletions, weakened assertions).
3. **No false-positive guard** — subagents have a "villain" stance but no explicit confidence threshold, which can produce noisy findings.

These are generalizable patterns with no project-specific dependencies. `reference.md` can be deleted once they are internalized.

---

## Goal

Internalize three review quality patterns into `skills/code-review/SKILL.md`, then delete the now-redundant `reference.md`.

---

## Requirements

### REQ-01 — False-positive guard in Reviewer Stance

Add an explicit confidence threshold to the **Reviewer Stance** section (appears twice: at the top-level section and inside Step 6 "Reviewer Stance injected into every agent"):

> Only report a finding when confidence is ≥ 80%. If uncertain whether a pattern is a violation, skip it — do not guess.

Both occurrences must be updated identically.

### REQ-02 — Second-pass pattern in each subagent prompt template

Add a **Second Pass** instruction block to the agent prompt template in Step 6. It must appear in the template structure shared by all agents so every dispatched subagent follows it, not only specific ones:

> **Second pass:** After your initial pass, re-read the full diff from top to bottom. For every file or hunk you did not comment on, explicitly state either "clean — no violations in my dimension" or flag it. Only skip a file when you can state why it is clean.

This must be inside the `## Return format` block or as a required step before returning, so it is structurally enforced.

### REQ-03 — `regression-reviewer` as 8th subagent

Add a new `regression-reviewer` agent to:

1. **Agent Roster table** (Step 6) — new row:

   | Agent | Dimension | Required context | Optional context | Degrades without |
   |-------|-----------|-----------------|------------------|-----------------|
   | `regression-reviewer` | Unrelated deletions, phantom imports, AI hallucination artifacts, weakened assertions | `checklist_baseline` | `stack`, `concerns` | — |

2. **Agent description block** (Step 6, after the roster table) — new section named `regression-reviewer` covering:
   - Phantom imports (references to non-existent symbols)
   - Unrelated deletions (code removed outside the PR's stated purpose)
   - Duplicate logic that already exists in the module
   - Weakened error handling, validation, or test assertions
   - Dead code that is never called
   - `TODO`/`FIXME` left in production code
   - Type assertions hiding compiler errors

3. **Step 6 header** — update agent count from 7 to 8.

4. **Step 7 at-a-glance table** — add `Regression & Hallucination` row.

5. **Step 8 examples** — update any "7 agents" references to 8.

### REQ-04 — Delete `reference.md`

Remove `skills/code-review/reference.md` — all valuable patterns are now in SKILL.md.

---

## Out of Scope

- Jira integration (Fakeflix-specific)
- HTML comment markers (`<!-- cursor-review: -->`)
- E2E NestJS patterns
- Structural compliance checklist (Fakeflix modular architecture)
- "Mark resolved" comment behavior (Cursor IDE-specific)
- The "gap detection" / "files with no inline comments" section (minor value, adds noise)
- "Positive highlight" requirement per agent (contradicts villain stance)
- "≥80% confidence" as an absolute skip rule for the second pass (second pass reports findings regardless — threshold applies to initial pass only)

---

## Acceptance Criteria

- [ ] Both Reviewer Stance sections contain the false-positive guard rule.
- [ ] The Step 6 prompt template structure includes a second-pass instruction applied to all agents.
- [ ] `regression-reviewer` appears in the roster table, has a description block, and is reflected in all count references.
- [ ] `reference.md` is deleted.
- [ ] SKILL.md is internally consistent (all count references say 8).
