# Specify — ai-coding-tooling Augmentation

Patches the parent's `## User Stories` template with a `US-N` id.

## User Story IDs: `US-N`

<!-- AUG: ## User Stories -->

Prefix every story heading with a sequential `US-N` id, numbered in document order (P1 stories
first, then P2, then P3). The priority tier stays in the heading alongside it:

```markdown
### US-1 — P1: [Story Title] ⭐ MVP

### US-2 — P2: [Story Title]

### US-3 — P3: [Story Title]
```

Numbering restarts at `US-1` per feature. Use the ID (not the title) when cross-referencing a
story elsewhere — e.g. `design.md`'s Components section or a task's title/description in
`tasks.md` (the `**Requirement**` field keeps the parent's `[FEAT]-NN`) — per
`SKILL.extended.md` § Phase Artifact Numbering (e.g. "T2 implements US-1").

`US-N` is independent from the parent's `[FEAT]-NN` Requirement Traceability ID: `US-N` identifies
the story itself, `[FEAT]-NN` tracks a requirement's phase status across Design/Tasks/Validate.
Both IDs appear on the same story — they answer different questions.
