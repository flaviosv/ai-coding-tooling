# Skill STATE.md — Per-Skill Decision Log

Every skill in `skills/` (built here) or `extended/` (overlay on a vendor skill) keeps its own `STATE.md` — an append-only log of the decisions that shaped that skill. Skills are self-contained, so the log is per skill, not project-wide: `skills/code-review/STATE.md` only tracks decisions about `code-review`, and so on.

This mirrors the `## Decisions` log that `tlc-spec-driven` keeps in `.specs/STATE.md` for feature work, scoped here to one skill instead of one project. It does **not** carry that file's `## Handoff` section — skills aren't paused/resumed mid-task the way a feature spec is, so there's no in-flight snapshot to track.

> **For agents:** whenever you modify a skill's `SKILL.md`, `references/`, or scripts (in `skills/` or `extended/`), check that skill's `STATE.md` before you start — conform to its active decisions or knowingly supersede one — and append an entry when the change reflects a real decision. This is a manual convention; `fsvskills` does not create, update, or track this file.

## Where it lives

- `skills/<skill>/STATE.md` — skills built in this project.
- `extended/<skill>/STATE.md` — overlays on a vendor skill. Tracks decisions about the overlay only; the base vendor skill is read-only and out of scope (see [Skill Modification Rules](../CLAUDE.md#skill-modification-rules)).

Not to be confused with this repo's own `.specs/STATE.md`, which is `tlc-spec-driven`'s project-level decision log for feature work done *on this repo* — unrelated to any individual skill's history.

## When to write

| Trigger | Operation |
| ------- | --------- |
| Before modifying a skill | **Read** — review active decisions so the change conforms to, or knowingly supersedes, one |
| After a change driven by a real decision (an approach chosen over an alternative, a trade-off accepted, a constraint discovered) | **Append** — new `AD-NNN` entry |
| Trivial edit (typo, wording clarity, no behavior or trade-off change) | none — leave `STATE.md` untouched |

Heuristic for "real decision": would a future change to this skill need to know this, to avoid re-litigating a settled question or repeating a mistake? If yes, log it.

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

**Supersession rule:** when a new decision replaces an old one, append a new `AD-NNN` entry and update the old entry's `status` field to `superseded by AD-NNN`. Never delete old entries — the history is the audit trail.

## AD-NNN numbering

- Sequential and permanent — never reused — but scoped to that skill's own `STATE.md`, not shared across skills.
- Check the skill's existing entries before assigning the next number; the counter starts at `AD-001`.
- If the skill has no `STATE.md` yet, create it with the `## Decisions` header and its first entry as `AD-001`.

## File shape

```markdown
# STATE

## Decisions

[AD-NNN entries…]
```
