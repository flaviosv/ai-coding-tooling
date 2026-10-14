# STATE

## Decisions

### AD-001
- **Decision**: `pending.md` has one table with every item, open or closed; `#` is the section number and is never renumbered or reused.
- **Reason**: The validated reference (`sys-ai-sdlc` research `monorepo-plugin/pending.md`) grew four tables only because it was reorganized after many increments; with one table the move-to-done and renumber steps disappear, and "item N" stays stable everywhere it is cited.
- **Trade-off**: A long research mixes closed and open rows in one table; the "Where was I" procedure filters by status instead.
- **Date**: 2026-10-14
- **Status**: active

### AD-002
- **Decision**: Cell content is strict (Status only a status, Depends on only item numbers, Increment only a 3-digit number, Details ≤ 200 characters, Item equal to the section title) and enforced by `scripts/pending.py check`, not by prose.
- **Reason**: In the reference file the cells accumulated commits, dates, links and blockers in prose ("merge em main"), which made the table unreadable; the user asked for strictly limited columns. A script removes table consistency from model judgment.
- **Trade-off**: External blockers (a merge, a person) can't appear in Depends on; they live in the item's section.
- **Date**: 2026-10-14
- **Status**: active

### AD-003
- **Decision**: en-US statuses translate the pt-BR ones literally, including `Rejeitado` → `Rejected` (meaning "out of current scope, another time"), and `Desenvolvimento` → `Implementing`.
- **Reason**: User's choice over `Deferred`, keeping the validated pt-BR meanings one-to-one.
- **Trade-off**: In English, `Rejected` reads close to `Declined`; the status table in `pending.md` carries the distinction.
- **Date**: 2026-10-14
- **Status**: active

### AD-004
- **Decision**: Removing an item is allowed only for an item registered by mistake; anything else closes as `Declined`.
- **Reason**: Numbers are cited across sections and increment documents; deleting a cited item breaks those references, and `next` could reuse the highest number.
- **Trade-off**: Mistaken-but-cited items stay visible as `Declined`.
- **Date**: 2026-10-14
- **Status**: active

### AD-005
- **Decision**: The research folder gets only `AGENTS.md`, no `CLAUDE.md`; the skill reads the research's `AGENTS.md` itself as its first steps.
- **Reason**: User's call: Claude Code reads `AGENTS.md` natively (v2.1.277+). Measured in the docs on 2026-10-14: with the default `claude-md-or-agents-md`, Claude skips every `AGENTS.md` when a `CLAUDE.md` exists in the working directory or above, which is the case in repositories that have a root `CLAUDE.md`. Reading it from the skill covers that case.
- **Trade-off**: Without the skill loaded, the research's `AGENTS.md` only auto-loads in repositories without a `CLAUDE.md`, or with Project instructions set to `claude-md-and-agents-md`.
- **Date**: 2026-10-14
- **Status**: active

### AD-006
- **Decision**: The skill and its templates name `tlc-discover`, `tlc-plan` and `tlc-implement` only as events (start, completion) that move an item's status; they never say where those skills write or how they run.
- **Reason**: User's rule: how those skills behave is theirs to define. The earlier artifact-path mapping (`research.md`, `tasks.md`, `checks.md`) is gone; an increment folder holds whatever the increment produces.
- **Trade-off**: Statuses and the initial research are described by phase, not by file, so `pending.py` can't check that a phase's document exists.
- **Date**: 2026-10-14
- **Status**: active

### AD-007
- **Decision**: An existing `pending.md` fixes the research's language; a new research is en-US unless signals say pt-BR (instruction files in force, repository docs, other research folders, the user's language). Dates are `YYYY-MM-DD` in both languages.
- **Reason**: User's corrections: pt-BR is detected, not only requested; an existing file is never translated; one date format.
- **Trade-off**: none identified.
- **Date**: 2026-10-14
- **Status**: active

### AD-008
- **Decision**: `IC <x>` is the user's shorthand for increment `<x>` (folder `NNN-<slug>/`, Increment column `NNN`), in both languages and any spelling (`IC 3`, `IC03`, `IC-003`); it never means item `<x>`. The skill and the `AGENTS.md` templates both state it.
- **Reason**: User's convention for referring to increments; item numbers and increment numbers overlap, so the alias must be pinned to increments explicitly.
- **Trade-off**: The alias is read-only: documents and the table still write `increment NNN`, not `IC`.
- **Date**: 2026-10-14
- **Status**: active
