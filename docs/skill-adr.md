# Skill Decision Log (STATE.md)

Every skill in `skills/` or `extended/` keeps its own `STATE.md` — an append-only log of the decisions that shaped it, scoped to that one skill.

**For agents:** before modifying a skill's `SKILL.md`, `references/`, or scripts, read its `STATE.md` and conform to (or knowingly supersede) its active decisions. After a change driven by a real decision, append an entry. This is a manual convention — `fs-harness` does not create, update, or track it.

## Where it lives

- `skills/<skill>/STATE.md` — skills built in this project.
- `extended/<skill>/STATE.md` — overlays on a vendor skill; tracks decisions about the overlay only, since a vendor skill's own source is never modified directly.

## When to write

| Trigger | Operation |
| ------- | --------- |
| Before modifying a skill | **Read** — conform to, or knowingly supersede, an active decision |
| After a change driven by a real decision (an approach chosen over an alternative, a trade-off accepted, a constraint discovered) | **Append** — new `AD-NNN` entry |
| Trivial edit (typo, wording clarity, no behavior/trade-off change) | none |

Heuristic: would a future change need this, to avoid re-litigating a settled question or repeating a mistake? If yes, log it.

## Format

```markdown
# STATE

## Decisions

### AD-001
- **Decision**: [what was decided — one sentence]
- **Reason**: [why this option was chosen]
- **Trade-off**: [what was given up]
- **Date**: YYYY-MM-DD
- **Status**: active | superseded by AD-NNN
```

- Numbering is sequential and permanent per skill (never reused, never shared across skills), starting at `AD-001`.
- When a new decision replaces an old one, append a new entry and set the old one's `Status` to `superseded by AD-NNN` — never delete an entry.
- If the skill has no `STATE.md` yet, create it with the header above and its first entry as `AD-001`.
