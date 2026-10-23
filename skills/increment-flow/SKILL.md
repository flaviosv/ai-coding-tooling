---
name: increment-flow
description: Runs a heavy feature or research as small numbered increments under docs/research/TOPIC/ — starts a new research (pending.md with the initial item, folder 001-slug, AGENTS.md), opens the next increment folder in order, manages pending.md (add, update, close, remove items, keep the increments table and the items table consistent and validated by script), and keeps progress.md, a short running summary of each increment's decisions, completed tasks, changes, customizations and additions. Use when the user says "start a new research", "new research on X", "add a pending item", "add to pending.md", "mark item N done", "update the status of item N", "open a new increment", "next increment", "IC 3", "where was I in the research", "log this in progress", "what has been done so far", "nova pesquisa", "adiciona no pending", "abre o próximo incremento", "registra no progresso". Do NOT use to run discovery, planning or implementation themselves, or for TODO lists, backlogs or work items outside a docs/research folder.
license: CC-BY-4.0
metadata:
  author: flaviostudart@gmail.com
  version: 1.6.0
---

# Increment Flow

Keeps a heavy piece of work small: one research folder, a `pending.md` that tracks the status of each increment and lists everything still to do, a `progress.md` that summarizes what each increment has done so far, and numbered increment folders that each answer one small, verifiable question or delivery.

## Always, before anything else

1. **Resolve the active research.** It is the `docs/research/<topic>/` folder this conversation is working in. "The pending.md", "add an item", "item 4" always mean that folder's `pending.md`. If the conversation, memory or context points at more than one research folder or `pending.md` and nothing in the current request settles which, stop and ask. Never pick one, and never write to a `pending.md` you found by searching.
2. **Read the research's `AGENTS.md`** unless it is already in context. Claude Code skips a subfolder's `AGENTS.md` when the repository has a `CLAUDE.md` above it, so do not count on it having loaded.
3. **Read the active `pending.md` before editing it.** Edit it in place and keep everything you do not change byte-identical. If it has no increments table, create it before anything else (see The increments table).
4. **Read `progress.md` when resuming or entering an increment you did not start**, to learn what was decided and done so far. A research that has none yet is not an error: see Log progress.
5. **Validate after every edit to `pending.md` or `progress.md`:** `python3 <this skill>/scripts/pending.py check <pending.md>`, which checks both files. Fix every reported line before replying. Use `pending.py next <pending.md>` for the next item number and the next increment number; never count by eye.

## Layout

```text
docs/research/<topic>/
├── AGENTS.md          rules and map for agents (from assets/AGENTS.<lang>.md)
├── pending.md         increments table + items table + one section per item (from assets/pending.<lang>.md)
├── progress.md        short summary per increment of what was decided and done (from assets/progress.<lang>.md; the file is always named progress.md)
├── 001-<slug>/        the initial research
└── 002-<slug>/ …      one folder per increment, in the order they open
```

Increment folders are `NNN-<slug>`: three digits, then a short ASCII kebab-case slug (no accents) in the research's language. Everything an increment produces lives in its folder. An increment does not need the full RPI flow; a small fix can go straight to work.

**`IC <x>` means increment `<x>`**, in either language and however it is written (`IC 3`, `IC03`, `IC-003`): the folder `003-<slug>/` and the Increment column value `003`. It never means item `<x>`.

## The increments table

Sits right above the items table, under `## Increments` (pt-BR `## Incrementos`). One row per increment folder, in ascending order, columns `Increment Number | Title | Status` (pt-BR: `Número do Incremento | Título | Estado`):

| Column | Holds |
|---|---|
| Increment Number | the 3-digit number of the folder `NNN-<slug>/` |
| Title | a short title of what the increment does |
| Status | `Open` (`Aberto`): the folder exists and nothing has been done in it. `In Progress` (`Em Andamento`): anything has been done in it, such as a discovery, a plan or any work. `Done` (`Feito`): closed, with every item pointing at it closed and its work committed |

`pending.py check` fails when the table is missing, an increment folder has no row, a row has no folder, an `Open` increment has an item past `Open`, or a `Done` increment has an item that is not closed.

**A `pending.md` without this table** (a research created before it existed) is evaluated before anything else is done to it: insert `## Increments` and the table right above the items table's heading (`## Items`, pt-BR `## Itens`), one row per increment folder. Title is the title of the one item that carries that increment, else the slug as words. Status comes from the evidence, never from the table's absence:
- an item with that increment in a working status, or any entry in its `progress.md` section, or documents inside the folder: `In Progress`;
- every item pointing at it closed and at least one: `Done`;
- otherwise `Open`.

Name every inferred status in the reply and ask about the ones the evidence does not settle. Then run `check`.

## The items table

One table, columns `# | Item | Status | Depends on | Increment | Details` (pt-BR: `# | Item | Estado | Depende de | Incremento | Detalhe`). Each cell holds only what its column defines, and `pending.py check` enforces it:

| Column | Holds | Never |
|---|---|---|
| `#` | the section number; never changes, never reused | a reordering index |
| Item | the short title, identical to the section title (without the status suffix) | `§N` prefixes |
| Status | exactly one value from the status table in `pending.md` | notes, increment names, dates |
| Depends on | item numbers only (`3`, `3, 5`) or `—` | "merge in main", links, prose; external blockers go in the section |
| Increment | the increment number only (`002`) or `—` | links, two numbers; when an item moves to a new increment, the column shows the current one and the section lists the earlier ones |
| Details | a short summary of what needs to be done, up to 200 characters | commits, dates, history; those go in the section |

Sections are `## N — <Item>`. A closed item's title ends with its status in lowercase parentheses: `(done)`, `(declined)`, `(rejected)`; pt-BR `(feito)`, `(recusado)`, `(rejeitado)`.

Dates are always `YYYY-MM-DD`, in both languages.

## Language

**An existing `pending.md` decides the language.** Detect it from the table header and write everything in that research (rows, sections, `AGENTS.md`, increment documents) in it. Never translate or switch an existing research, whatever the user, the repository or the other signals below say.

**A new research is en-US unless the signals say pt-BR.** Look for them before creating anything: instruction files in force (the repository's `AGENTS.md`/`CLAUDE.md` at any level, the user's global instructions) that set pt-BR as the language for documents; the repository's own docs or its other `docs/research/` folders written in pt-BR; the user writing in pt-BR or asking for it. When you create the research, name the language and the signal that chose it in one line.

Status values follow the file's language: en-US Open, Researching, Researched, Planning, Planned, Implementing, Done, Declined, Rejected; pt-BR Aberto, Em Pesquisa, Pesquisado, Em Planejamento, Planejado, Desenvolvimento, Feito, Recusado, Rejeitado.

## Procedures

### Start a new research

Trigger: the user starts work on a topic that has no folder under `docs/research/`.

1. Agree on the topic name and slug (kebab-case). If `docs/research/<slug>/` already exists, it is not new: stop and ask whether to continue it.
2. Choose the language (see Language).
3. Check whether git ignores the folder: `git check-ignore -q docs/research/<slug>/pending.md`. If it is ignored, keep it local and say so. If it is not, ask whether the research should be pushed with the repository. On "no", add `docs/research/` to `.git/info/exclude` (local, changes no versioned file) unless the user prefers `.gitignore`.
4. Create `pending.md` from `assets/pending.<lang>.md` (it carries the increments table with row `001`): `{{TOPIC}}` = topic name, `{{DATE}}` = today, `{{SUMMARY}}` = one line of what the research must answer (200 characters max), `{{QUESTION}}` = the question in the user's words.
5. Create `001-<slug>/` (en-US slug `initial-research`, pt-BR `pesquisa-inicial`, unless the user names it).
6. Create `progress.md` (never `progress.<lang>.md`) from `assets/progress.<lang>.md`, with `{{TOPIC}}`, `{{INCREMENT}}` = `001`, `{{SLUG}}` = the folder slug from step 5 and `{{ORIGIN}}` = `Started with the research.` (pt-BR `Começou junto com a pesquisa.`).
7. Create `AGENTS.md` from `assets/AGENTS.<lang>.md`, with `{{VERSIONED}}` filled from step 3 (see the next block).
8. Run `pending.py check`. Then offer to start the discovery with `tlc-discover`.

`{{VERSIONED}}` values:
- Pushed: en-US `yes — committed with the repository.`; pt-BR `sim — vai para o repositório com o resto do código.`
- Local: en-US ``no — excluded from git. Files outside this folder never cite `docs/research/`, its paths or its item numbers: the link dies for every other reader. The reasoning goes into an ADR or the project docs.``; pt-BR ``não — fora do git. Arquivo fora desta pasta nunca cita `docs/research/`, os caminhos dela nem os números de item: o link morre para qualquer outro leitor. O porquê vai para um ADR ou para a documentação do projeto.``

### Add an item

1. **Check for a duplicate first.** Compare each item the user asks to add against every item in `pending.md`, open or closed, reading its row and its section. Same goal and scope is a duplicate even when worded differently.
   - **Already present:** add no row and no section. Append what the request brings that the section does not already say, as a dated paragraph (`YYYY-MM-DD: …`) in that item's section; if it brings nothing new, change nothing. Tell the user it is already item N and what you added. Shorten the Details cell only as in Update an item, then run `check`.
   - **Present but closed** (Done, Declined, Rejected): tell the user and ask whether to reopen it; never reopen it or register a new item on your own.
   - **Partly covered:** the covered part goes to the existing item's section as above; only the uncovered rest becomes a new item.
   - **Unsure whether it is the same item:** ask.
2. `pending.py next` gives the number N.
3. Append the row at the end of the table: Status `Open` (`Aberto`), Depends on and Increment as the user said or `—`, Details as a short summary. Beyond what the user said, link the new item to an existing one in Depends on only when you are confident the new item cannot be done or verified until that item is `Done`; being on a related topic is not enough. Name every link you inferred in the reply.
4. Append the section `## N — <Item>` at the end of the file: first line `Registered on YYYY-MM-DD.` (`Registrado em YYYY-MM-DD.`), then the full request, quoting the user's words when they set scope.
5. Run `check`.

### Update an item

Move the status the moment the work moves, not when the increment closes:

| Event | Status (en-US / pt-BR) |
|---|---|
| `tlc-discover` starts on the item | Researching / Em Pesquisa |
| `tlc-discover` completes with a verdict | Researched / Pesquisado |
| `tlc-plan` starts | Planning / Em Planejamento |
| `tlc-plan` completes | Planned / Planejado |
| `tlc-implement` starts, or work starts on an item without RPI | Implementing / Desenvolvimento |

The first time an item of an increment leaves `Open`, set that increment to `In Progress` in the increments table. It also becomes `In Progress` the moment anything else is done in it, such as a discovery, a plan or any work without an item.

Any new fact (a decision, a blocker, a note from the user) goes into the item's section as a dated paragraph. Only shorten the Details cell when it would otherwise stop describing what is left. Run `check`.

### Close an item

1. Set the status: `Done` when delivered and proven, `Declined` when decided not to do, `Rejected` when out of the current scope.
2. Add the suffix to the section title: `(done)`, `(declined)` or `(rejected)`.
3. Right under the title, add one line pointing to what was delivered or why it closed: increment folder, commit, date.
4. A `Done` item from an increment with independent verification closes only with no open gap: each gap is fixed in the same increment, or goes to the user and enters `pending.md` as a new item only with their acceptance recorded in its section.
5. Run `check`.

### Remove an item

Only for an item registered by mistake: no work started, not cited elsewhere. Delete its row and its section. Anything else is closed as `Declined`, never removed, because "item N" may be cited in sections or increment documents. Run `check`.

### Open an increment

1. Read the initial research (`001-*/`) and `pending.md`. Decisions closed in the initial research are input; reopening one needs a named reason.
2. Prefer one increment at a time. If another increment is `In Progress`, say so and open the new one only if the user confirms.
3. `pending.py next` gives the increment number; create `NNN-<slug>/` and append its row to the increments table: Title, Status `Open` (`Aberto`).
4. Set the Increment column to `NNN` on every item the increment works, and move their status as the work starts.
5. Append the section `## Increment NNN — <slug>` (pt-BR `## Incremento NNN — <slug>`) at the end of `progress.md`, with the same slug as the folder; create the file first if the research has none (see Log progress).
6. When the increment runs RPI, its documents go in `NNN-<slug>/`.

### Close an increment

1. **Check the work is committed.** `git status --short` must show nothing the increment changed or produced: code, tests, docs outside the research and, when the research is versioned, its folder and files. Anything uncommitted: stop, tell the user what is pending, and leave the increment `In Progress` until it is committed. A research kept out of git is exempt for its own folder; the changes outside it still count.
2. Close its items (see Close an item) and set the increment to `Done` (`Feito`) in the increments table.
3. Reread its `progress.md` section against what the increment actually did and add any decision, change, customization or addition that is missing.
4. Feed the learning back: update the affected decision, item or evidence in the initial research (`001-*/`) and point to the increment folder.
5. If the research is local (not versioned), check that nothing the increment changed outside `docs/research/` cites the research, its paths or its item numbers.

### Log progress

Trigger: inside an increment, a decision is made, a task finishes, something changes, is customized or is added, and a later reader would need it to understand where the work stands.

1. Append one line at the end of that increment's section in `progress.md`: `- YYYY-MM-DD · <type> · <text>`. Types, en-US / pt-BR: `decision` / `decisão`, `done` / `feito`, `change` / `mudança`, `customization` / `customização`, `addition` / `adição`.
2. The text is one sentence of up to 200 characters. Say what was decided or done and, when useful, point to the file or item (`item 4`) instead of repeating it. Not a transcript: no attempts, no reasoning, nothing already clear from a commit or the item's section.
3. Entries go in the order they happen and are never rewritten; a later decision that reverses an earlier one is a new `decision` line.
4. Run `check`.

**A research already in progress with no `progress.md`:** create it at that point from `assets/progress.<lang>.md` (language from `pending.md`; the created file is named `progress.md`), with `{{INCREMENT}}` and `{{SLUG}}` of the increment in play and `{{ORIGIN}}` = `Started on YYYY-MM-DD, in the middle of the research: earlier events are not recorded here; see pending.md and the increment folders.` (pt-BR `Criado em YYYY-MM-DD, com a pesquisa em andamento: os eventos anteriores não estão registrados aqui; veja o pending.md e as pastas dos incrementos.`). Do not reconstruct history or fill in earlier increments. Tell the user the file starts mid-flow. If the increment in play itself began before the file, its section is partial by design; log from now on.

### Where was I

Read `pending.md` and the section of the latest increment in `progress.md`, and report, briefly: the increment `In Progress`, then items in a working status with their increment, then `Open` items whose dependencies are all `Done`, then blocked items with what blocks them. Recommend the next one.

## Examples

**Start.** User: "start a new research on the billing retry redesign". Actions: no `docs/research/billing-retry-redesign/`; no pt-BR signal (instructions, docs and the user all in English), so en-US; `git check-ignore` says not ignored, ask whether to push, user says keep local, add `docs/research/` to `.git/info/exclude`; create `pending.md` with item 1 `Initial research: billing retry redesign`, `001-initial-research/`, and `AGENTS.md` with `Versioned: no …`; `check` prints `ok`; offer `tlc-discover`.

**Add with ambiguity.** User: "add a pending item: drop the legacy webhook". Context shows work in both `docs/research/billing-retry-redesign/` and `docs/research/tests-suite/`, and the request names neither. Actions: stop and ask which research. After the answer, `next` gives `item=7`; append row 7 and section `## 7 — Drop the legacy webhook`; `check`.

**Duplicate.** User: "add a pending item: retries must stop after 5 attempts, and log the last error". Item 4 `Cap retries at 5` is `Open` and its section does not mention logging. Actions: no new row or section; append `2026-10-14: log the last error when retries stop.` to section 4; reply that it is already item 4 and the logging detail was added; `check`.

**Log progress.** User: "we decided to keep one progress file per research". Active research has increment 003 in play. Actions: append `- 2026-10-16 · decision · One progress.md per research, one section per increment.` under `## Increment 003 — <slug>`; `check` prints `ok`.

**Research already running.** User: "log that the retry cap is done" in a research with `pending.md` and `001-`/`002-` folders but no `progress.md`. Actions: create `progress.md` from the template with section `## Increment 002 — <slug>` and the mid-research origin line; append the `done` entry; tell the user the file starts today and earlier events are not recorded; `check`.

**Existing language wins.** User, writing in English: "add an item to cap retries at 5" in a research whose `pending.md` header is `# | Item | Estado | …`. Actions: write the row and section in pt-BR (`Aberto`, `Registrado em 2026-10-14.`); never translate the file.

**Table missing.** User: "mark item 3 done" in a research whose `pending.md` has only the items table and folders `001-` and `002-`. Actions: before the edit, insert `## Increments` above `## Items` with rows `001` and `002`; item 1 is `Done`, so `001` is `Done`; item 3 is `Implementing` with Increment `002`, so `002` is `In Progress`; say both were inferred; then close item 3, `check`.

**Close.** User: "item 3 is done, commit a1b2c3d". Actions: Status `Done`; title `## 3 — <title> (done)`; under it `Done in increment 004 (a1b2c3d, 2026-10-14).`; `check`.

## Troubleshooting

- `no increments table`: the research predates the table, or the header was renamed. Create it as described in The increments table.
- `increment NNN has a folder but no row in the increments table`: add the row. `no folder … next to pending.md`: create the folder or fix the number.
- `is Open but item #N is …` / `is Done but item #N is …`: the increment status and its items disagree. Set `In Progress`, or close the item or move it to the increment that works it.
- `expected exactly one item table, found 0`: the header row differs from the template (renamed column, extra column). Restore the template's header for the file's language.
- `Item '…' differs from section title '…'`: the row and the section drifted. Make them identical; the section title wins unless the user renamed the item.
- `Increment NNN has no folder`: create the folder, or fix the number; never point at an increment that does not exist.
- `progress.md line N: …`: an entry or section heading in `progress.md` breaks the format. Entries are `- YYYY-MM-DD · <type> · <text>` with a type from the file's language; headings are `## Increment NNN — <slug>` with the slug of an existing folder.
- `section N has no row in the table`: an item was half-removed. Restore the row, or finish the removal (see Remove an item).
