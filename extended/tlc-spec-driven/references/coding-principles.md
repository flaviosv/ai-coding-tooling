# Coding Principles — ai-coding-tooling Augmentation

Read this **after** the parent `references/coding-principles.md`. It augments the parent's
behavioral bias with concrete style references and routes security/UI work to dedicated skills.
It does not replace the parent — the parent's Before/During/After rules stay in force.

Apply these **before every implementation**, alongside the parent file.

## Software Design Principles (always load)

Load `coding-guidelines/best-practices-coding-guidelines.md` from this directory whenever you
write or review code. It covers SOLID, DRY, KISS, YAGNI, Separation of Concerns, Low
Coupling/High Cohesion, Composition over Inheritance, Law of Demeter, Fail Fast, Convention over
Configuration, Readability over Cleverness, and the Boy Scout Rule.

Treat violations as **design defects, not style suggestions**. Run its pre-completion checklist
(end of the file) before marking any task complete — this folds into the parent's post-gate
"would a senior engineer flag this?" check.

## Observability (always load)

Load `coding-guidelines/observability-coding-guidelines.md` when writing code. Instrument with
logging at write time, per its rules — not as an afterthought.

## Stack-Specific Style (conditional)

Detect the stack from `docs/codebase/STACK.md` (fall back to `.specs/codebase/STACK.md`, then legacy
`docs/codebase/PROJECT_DETAILS.md` / `docs/PROJECT_DETAILS.md`). Then load **only**
matching `coding-guidelines/<language>-*.md` / `coding-guidelines/<language>-<framework>-*.md`
files from this directory (e.g. `php-coding-guidelines.md` for a PHP stack). Skip non-matching
files. Apply [Reference Loading Constraint](../../../templates/reference-loading-constraint.md).

If no stack-specific file matches, proceed with the always-load set above.

## Security → `security-best-practices` skill

For any task touching authentication/authorization, input handling, secrets, serialization/
deserialization, file or network I/O, or other external trust boundaries: invoke the
`security-best-practices` skill and apply its stack-matched references **before** the gate check
and commit. Security is not covered by the style references above — it is delegated to that skill.

## Web / UI → `web-design-guidelines` skill

If the change includes **HTML or CSS** — template files, JSX/TSX with `className`, inline styles,
or `.css`/`.scss`/`.less` files — also invoke the `web-design-guidelines` skill and apply its
rules to the markup/styling changes.
