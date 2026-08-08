# Tasks — Code Review Quality Enhancements (CR-QUALITY)

**Status:** Ready  
**File:** `skills/code-review/SKILL.md`

---

## Task List

### T1 — Add false-positive guard to both Reviewer Stance sections

**What:** Append the false-positive rule to the `## Reviewer Stance` section (top-level, before Step 1) and to the `### Reviewer Stance (injected into every agent)` block inside Step 6.

**Rule to add (identical in both places):**
> Only report a finding when confidence is ≥ 80%. If uncertain whether a pattern is a violation, skip it — do not guess.

**Where:**
- Line ~35: top-level `## Reviewer Stance` block (after the 5 bullet points)
- Line ~204: `### Reviewer Stance (injected into every agent)` block (after the 5 bullet points)

**Done when:** Both stances end with the confidence rule. Grepping for "80%" returns exactly 2 matches in SKILL.md.

---

### T2 — Add second-pass instruction to Step 6 prompt template

**What:** Insert a `## Second Pass` section into the agent prompt template in Step 6 (the fenced code block showing the four sections: Role / Context / Diff / Return format).

**Where:** After the `## Return format` section within the template block (around line 186).

**Text to add inside the template:**
```
## Second Pass
After your initial findings pass, re-read the full diff from top to bottom.
For every file or hunk you did not comment on, explicitly state either
"clean — no violations in my dimension" or flag it. Only skip a file
when you can state concretely why it is clean for your dimension.
```

**Done when:** The Step 6 prompt template code block contains a `## Second Pass` section visible to all subagents.

---

### T3 — Add `regression-reviewer` row to Agent Roster table

**What:** Add a new row to the `### Agent Roster` table in Step 6.

**Row to add (alphabetical position — after `requirements-tracer`, since R comes after P):**

| `regression-reviewer` | Unrelated deletions, phantom imports, AI hallucination artifacts, weakened assertions | `checklist_baseline` | `stack`, `concerns` | — |

**Also update:** Step 6 header from "All 7 agents MUST be fired..." to "All 8 agents MUST be fired..."

**Done when:** Roster table has 8 rows; header says 8.

---

### T4 — Add `regression-reviewer` description block

**What:** Add a new subagent description block after the existing `### Performance Audit mode exception` block (or in dimension order after `docs-comments-reviewer`).

**Content:**

```markdown
### Agent: regression-reviewer

**Dimension:** Regression & Hallucination Detection  
**Marker context:** unrelated-deletion | phantom-import | hallucination | duplicate | weakened-assertion | dead-code

Review the diff for changes that are unrelated to the PR's stated purpose or that show signs of AI-generated artifacts:

- **Phantom imports** — references to symbols that do not exist in the codebase.
- **Unrelated deletions** — code removed that has no connection to the stated change (🚨 Critical).
- **Duplicate logic** — functionality that already exists in the module, re-implemented.
- **Weakened assertions** — error handling, validation rules, or test assertions made less strict.
- **Dead code** — functions or branches introduced that are never called.
- **`TODO`/`FIXME` in production** — leftover markers not resolved before merge.
- **Type assertions hiding errors** — `as any`, forced casts masking real type errors.
```

**Done when:** Description block exists and matches the roster entry's dimension name.

---

### T5 — Update at-a-glance table in Step 8

**What:** Add `Regression & Hallucination` row to the at-a-glance table in Step 8 (Consolidation).

**Row to add (after `Performance`, before `Docs & Comments`):**

| Regression & Hallucination | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |

**Also update:** Any "7 agents" text in Step 8 examples to "8 agents".

**Done when:** At-a-glance table has 8 dimension rows; all example references say 8.

---

### T6 — Delete `reference.md`

**What:** Delete `skills/code-review/reference.md`.

**Done when:** File no longer exists in the repo.

---

### T7 — Commit and push

**What:** Stage all changes, commit with clear message, push to `sdd-migration-tlc-spec-driven`.

**Commit message:**
```
feat(code-review): add second-pass, regression detection, and false-positive guard

- Add ≥80% confidence threshold to both Reviewer Stance sections
- Add second-pass coverage check to Step 6 prompt template
- Add regression-reviewer as 8th subagent (phantom imports, unrelated deletions,
  weakened assertions, hallucination artifacts)
- Delete reference.md (all patterns internalized)
```

**Done when:** `git status` is clean; branch is pushed.

---

## Execution Order

T1 → T2 → T3 → T4 → T5 → T6 → T7 (all sequential — single file edits)

T3 and T4 can be done together (both are additions to Step 6).
