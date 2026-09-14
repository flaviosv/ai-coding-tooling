# Coding Principles — ai-coding-tooling Augmentation

Patches the parent's `## During Implementation` and `## After Each Change` with comment, design, observability, and stack-style rules.

## Code Comments (always apply)

Write a comment only for genuinely complex or non-obvious logic, when explicitly requested, or
when the language or framework mandates a doc comment (e.g. Go `godoc` on exported identifiers) —
never to narrate a variable, a config value, or a single line; if code needs that, make the code
clearer instead. This overrides any comment guidance from the parent skill, which has no rule on
when to write comments (its Surgical Changes bullet against "improving" adjacent comments still
applies).

## Software Design Principles (always load)

Load `coding-guidelines/best-practices-coding-guidelines.md` from this directory whenever you
write or review code.

Treat violations as **design defects, not style suggestions**. Run its pre-completion checklist
(end of the file) before marking any task complete — this folds into the parent's
`## After Each Change` check.

## Observability (always load)

Load `coding-guidelines/observability-coding-guidelines.md` when writing code. Instrument with
logging at write time, per its rules — not as an afterthought.

## Stack-Specific Style (conditional)

Detect the project's stack. Then load **only** the `coding-guidelines/<technology>-coding-guidelines.md`
files from this directory whose `<technology>` — a language or framework slug from the detected
stack (e.g. `php`, `django`, `go-gin`) — matches. Skip non-matching files.

If no stack-specific file matches, or the stack cannot be determined, do not load any
tech-specific references — proceed with the always-load set above.
