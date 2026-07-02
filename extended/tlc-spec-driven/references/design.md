# Design — ai-coding-tooling Augmentation

Read this **after** the parent `references/design.md`. It augments the parent's `## Components`
and `## Tech Decisions` sections with a sequential ID for cross-referencing. It does not replace
the parent — every component still needs Purpose/Location/Interfaces/Dependencies/Reuses, and
every tech decision still needs Choice/Rationale.

## Design Component & Decision IDs: `DC-N`

<!-- AUG: ## Components -->
<!-- AUG: ## Tech Decisions -->

`DC-N` is **one shared sequence** across both sections, numbered in document order — Components
first, then Tech Decisions:

```markdown
### DC-1 — [Component Name]

- **Purpose**: [What this component does - one sentence]
...

### DC-2 — [Component Name]

- **Purpose**: [What this component does]
...
```

For Tech Decisions, add an `ID` column to the parent's table:

| ID   | Decision           | Choice           | Rationale      |
| ---- | ------------------ | ---------------- | --------------- |
| DC-3 | [What we decided]  | [What we chose]  | [Why - brief]   |

Numbering restarts at `DC-1` per feature and does not reset between the two sections. Use the ID
when cross-referencing a component or decision elsewhere — e.g. `tasks.md`'s Task Breakdown — per
`SKILL.extended.md` § Phase Artifact Numbering (e.g. "T2 implements DC-1").
