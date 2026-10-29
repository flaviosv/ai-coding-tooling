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

### AD-009
- **Decision**: Adding an item starts with a duplicate check against every item, open or closed (row and section), by goal and scope rather than wording. A duplicate gets no new row or section: its new details go into the existing item's section as a dated paragraph. A closed match is reopened only with the user's say; a partial match splits; an unclear match is asked.
- **Reason**: User's rule: an item already present is never added again, only enriched with the request's new details.
- **Trade-off**: Detection stays in model judgment; `pending.py check` does not flag duplicate titles, because a duplicate is a matter of meaning and an exact-title check would catch only the cases the judgment already catches.
- **Date**: 2026-10-14
- **Status**: active

### AD-010
- **Decision**: When adding an item, the agent may fill Depends on with an existing item the user did not name, but only when confident the new item cannot be done or verified until that item is `Done`; topical relation is not enough, and every inferred link is named in the reply.
- **Reason**: User's rule: a new item can be linked to another one when the link is certainly true.
- **Trade-off**: A wrong inferred dependency would hide the item from "Where was I"'s ready list; the confidence bar and naming the link in the reply keep that visible and cheap to undo.
- **Date**: 2026-10-14
- **Status**: active

### AD-011
- **Decision**: One `progress.md` per research (not per increment), with a `## Increment NNN — <slug>` section per increment and one-line dated entries typed `decision`, `done`, `change`, `customization` or `addition` (text ≤ 200 characters). Two templates (`assets/progress.<lang>.md`) with localized heading and types, but the created file is always plain `progress.md`. It is validated by `pending.py check` beside `pending.md`, written on meaningful events and reviewed when an increment closes. A research already running without the file gets it created at that point, with an origin line saying earlier events are not recorded; history is never reconstructed.
- **Reason**: User's call: a general research-level summary an agent can locate to understand what was done so far, like `pending.md`. Grouping by increment keeps an increment's entries findable as the file grows; extending `check` keeps one validation command and removes format drift from model judgment.
- **Trade-off**: The file grows over the whole research, so agents read the relevant increment section rather than all of it. Researches started before this change have a partial `progress.md` by design.
- **Date**: 2026-10-16
- **Status**: active

### AD-012
- **Decision**: `pending.md` carries an auxiliary increments table (`Increment Number | Title | Status`; `Open`, `In Progress`, `Done`) right above the items table. `In Progress` means anything has been done in the increment (a discovery, a plan, any work), not only that an item is being implemented. `pending.py check` requires the table, one row per increment folder, and consistency with the items (`Open` has no item past `Open`; `Done` has every item closed). A `pending.md` without the table is evaluated and given one before any other edit, statuses inferred from the items, `progress.md` and folder contents and named in the reply.
- **Reason**: User's call: see each increment's progress at a glance, and have older researches pick the table up. Making `check` fail on a missing table means the evaluation happens on the first edit of an old file, instead of depending on the agent remembering a prose rule.
- **Trade-off**: Every existing `pending.md` fails `check` until it gets the table. The increment status is kept by hand and only cross-checked against item statuses, so an `In Progress` that should be `Done` (or the reverse, with all items closed) is not caught.
- **Date**: 2026-10-23
- **Status**: active

### AD-013
- **Decision**: An increment closes (`Done`) only when its work is committed. Closing starts with `git status --short`; anything the increment changed or produced and is still uncommitted keeps it `In Progress`. A research kept out of git is exempt for its own folder only.
- **Reason**: User's rule: `Done` has to mean the work is recoverable from history, not only present in a working tree.
- **Trade-off**: Prose rule in the procedure, not a script check: `pending.py` can't tell which uncommitted files belong to the increment, and the research is often git-excluded.
- **Date**: 2026-10-23
- **Status**: active

### AD-014
- **Decision**: `Done` items live in a separate Done table (`## Done Items`, same columns as the items table) right below the items table; the items table holds none. Closing an item as `Done` includes moving its row there, unchanged and keeping its `#`; finding `Done` rows in the items table triggers the same move, creating the table when missing. `Declined` and `Rejected` stay in the items table. `pending.py check` fails on a `Done` row in the items table, on a non-`Done` row in the Done table, and on a number in both tables; a missing Done table is an error only while there is a `Done` item to put in it.
- **Reason**: User's call: the main table should show only what is still ahead, with finished work kept apart, and a definition of done that includes the move.
- **Trade-off**: Supersedes AD-001's single table: a closed item now changes tables, and cross-table rules (unique numbers, dependencies, section matching) are checked over both. Same columns keep the move a pure cut and paste, at the cost of a Status column that is always `Done`.
- **Date**: 2026-10-26
- **Status**: active

### AD-015
- **Decision**: `Rejected` items move to the Done table together with `Done` ones; only `Declined` stays in the items table. `pending.py check` flags a `Rejected` row in the items table and any status outside `Done`/`Rejected` in the Done table.
- **Reason**: User's call: an item left for another time is not work ahead, so it leaves the main table too.
- **Trade-off**: The `## Done Items` heading now also holds `Rejected` rows, and `Declined` is the one closed status that stays in the items table; the status column tells them apart.
- **Date**: 2026-10-26
- **Status**: active

### AD-016
- **Decision**: On Azure DevOps repos only (`wit.py ado` checks the git remotes; any other host skips every ADO step silently), each increment can be linked to an ADO Task under a User Story. The user is asked once when the increment opens (or when it first goes `In Progress` if it has no `wit.md`); the answer lives in `NNN-<slug>/wit.md` (`none` when there is no User Story, so it is never asked again). The Task follows the increment: `Open` → `New`, `In Progress` → `Active`, `Done` (after the commit check) → `Resolved`; `Closed` is the user's. Title and description are always pt-BR. A Feature request starts a chat (Feature, User Stories, planned Tasks) and nothing is created in ADO before the user approves the tree. The mechanical steps are `scripts/wit.py` (`az boards` via argument arrays); the conversations stay in the SKILL.md.
- **Reason**: User's call: ADO traceability without forcing it on GitHub repos or on increments that have no User Story. A script keeps the create/relate/state sequence out of model judgment; `none` in `wit.md` is the "asked" marker, so absence means not asked.
- **Trade-off**: `wit.md` is English-only and unchecked by `pending.py check`. State names are fixed to New/Active/Resolved, which is the user's process, not every ADO process (a rejected state is reported, not substituted). `wit.py` was tested against a fake `az`, not a live organization; the JSON shape it reads (`fields`, `_links.html.href`) is unverified against a real tenant.
- **Date**: 2026-10-29
- **Status**: active

### AD-017
- **Decision**: Text written to Azure DevOps (titles and descriptions of Features, User Stories, Tasks) describes only the card, in pt-BR: no `IC`, increment numbers or slugs, item numbers, research names, `.md` files or paths. The Task title is the work's own title (no `IC NNN —` prefix). `wit.py` refuses text matching `IC <n>`, `increment(o) NNN`, a `.md` file or `docs/research`.
- **Reason**: User's rule: ADO must not know the increment strategy; anyone reads a card and understands it without leaving ADO.
- **Trade-off**: The guard is a regex over obvious markers; subtler leaks (a slug, an item number written as prose) are left to the SKILL.md rule. The card has no pointer back to its increment; the link lives only in `wit.md`.
- **Date**: 2026-10-29
- **Status**: active
