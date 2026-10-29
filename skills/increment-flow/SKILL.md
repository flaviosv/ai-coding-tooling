---
name: increment-flow
description: Gerencia pesquisas e funcionalidades em incrementos numerados sob docs/research/TOPIC/, mantendo pending.md, progress.md e a criação de Tasks na abertura em repositórios Azure DevOps nos estados New, Active e Closed. Use para iniciar pesquisa, abrir o próximo incremento, adicionar ou atualizar pendências, fechar itens, registrar progresso ou retomar uma pesquisa; aceita referências como IC 3 e incremento 003. Não executa discovery, planejamento ou implementação, nem gerencia listas fora de docs/research/.
license: CC-BY-4.0
metadata:
  author: flaviostudart@gmail.com
  version: 1.9.0
---

# Increment Flow

Keeps a heavy piece of work small: one research folder, a `pending.md` that tracks the status of each increment and lists everything still to do, a `progress.md` that summarizes what each increment has done so far, and numbered increment folders that each answer one small, verifiable question or delivery.

## Always, before anything else

1. **Resolve the active research.** It is the `docs/research/<topic>/` folder this conversation is working in. "The pending.md", "add an item", "item 4" always mean that folder's `pending.md`. If the conversation, memory or context points at more than one research folder or `pending.md` and nothing in the current request settles which, stop and ask. Never pick one, and never write to a `pending.md` you found by searching.
2. **Read the research's `AGENTS.md`** unless it is already in context. Claude Code skips a subfolder's `AGENTS.md` when the repository has a `CLAUDE.md` above it, so do not count on it having loaded.
3. **Read the active `pending.md` before editing it.** Edit it in place and keep everything you do not change byte-identical. If it has no increments table, create it before anything else (see The increments table). If its items table holds `Done` or `Rejected` items, move them to the Done table right then, creating the table when missing (see Move to the Done table).
4. **Read `progress.md` when resuming or entering an increment you did not start**, to learn what was decided and done so far. A research that has none yet is not an error: see Log progress.
5. **Validate after every edit to `pending.md` or `progress.md`:** `python3 <this skill>/scripts/pending.py check <pending.md>`, which checks both files. Fix every reported line before replying. Use `pending.py next <pending.md>` for the next item number and the next increment number; never count by eye.

## Layout

```text
docs/research/<topic>/
├── AGENTS.md          rules and map for agents (from assets/AGENTS.<lang>.md)
├── pending.md         increments table + items table + Done table + one section per item (from assets/pending.<lang>.md)
├── progress.md        short summary per increment of what was decided and done (from assets/progress.<lang>.md; the file is always named progress.md)
├── 001-<slug>/        the initial research
└── 002-<slug>/ …      one folder per increment, in the order they open; on Azure DevOps repos each holds a wit.md
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

The items table holds every item that is not `Done` or `Rejected`. Columns `# | Item | Status | Depends on | Increment | Details` (pt-BR: `# | Item | Estado | Depende de | Incremento | Detalhe`). Each cell holds only what its column defines, and `pending.py check` enforces it:

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

## The Done table

Sits right below the items table, under `## Done Items` (pt-BR `## Itens Feitos`), with the same columns as the items table. It holds every `Done` and `Rejected` item and nothing else; the items table holds none. `Declined` items stay in the items table. A row keeps its `#` and every other cell as it was: moving it is a cut and paste, never a renumbering, and Depends on and sections keep citing the same numbers.

`pending.py check` fails on a `Done` or `Rejected` row in the items table, on any other row in the Done table, and on a number that appears in both tables.

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
8. Crie a Task do `001` no Azure DevOps agora, antes de iniciar discovery ou plano (veja Azure DevOps).
9. Run `pending.py check`. Then offer to start the discovery with `tlc-discover`.

`{{VERSIONED}}` values:
- Pushed: en-US `yes — committed with the repository.`; pt-BR `sim — vai para o repositório com o resto do código.`
- Local: en-US ``no — excluded from git. Files outside this folder never cite `docs/research/`, its paths or its item numbers: the link dies for every other reader. The reasoning goes into an ADR or the project docs.``; pt-BR ``não — fora do git. Arquivo fora desta pasta nunca cita `docs/research/`, os caminhos dela nem os números de item: o link morre para qualquer outro leitor. O porquê vai para um ADR ou para a documentação do projeto.``

### Add an item

1. **Check for a duplicate first.** Compare each item the user asks to add against every item in `pending.md`, in both tables, reading its row and its section. Same goal and scope is a duplicate even when worded differently.
   - **Already present:** add no row and no section. Append what the request brings that the section does not already say, as a dated paragraph (`YYYY-MM-DD: …`) in that item's section; if it brings nothing new, change nothing. Tell the user it is already item N and what you added. Shorten the Details cell only as in Update an item, then run `check`.
   - **Present but closed** (Done, Declined, Rejected): tell the user and ask whether to reopen it; never reopen it or register a new item on your own. Reopening a `Done` or `Rejected` item also moves its row back to the items table, at its numeric place, and drops the status suffix.
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

The first time an item of an increment leaves `Open`, set that increment to `In Progress` in the increments table. It also becomes `In Progress` the moment anything else is done in it, such as a discovery, a plan or any work without an item. Each time it becomes `In Progress`, sync its Azure DevOps Task to `Active` (see Azure DevOps).

Any new fact (a decision, a blocker, a note from the user) goes into the item's section as a dated paragraph; when it changes what the increment's Azure DevOps Task says, keep the card true (see Azure DevOps). Only shorten the Details cell when it would otherwise stop describing what is left. Run `check`.

### Close an item

1. Set the status: `Done` when delivered and proven, `Declined` when decided not to do, `Rejected` when out of the current scope.
2. Add the suffix to the section title: `(done)`, `(declined)` or `(rejected)`.
3. Right under the title, add one line pointing to what was delivered or why it closed: increment folder, commit, date.
4. A `Done` item from an increment with independent verification closes only with no open gap: each gap is fixed in the same increment, or goes to the user and enters `pending.md` as a new item only with their acceptance recorded in its section.
5. A `Done` or `Rejected` item is not closed until its row is in the Done table (see Move to the Done table).
6. Run `check`.

### Move to the Done table

Trigger: closing an item as `Done` or `Rejected`, or finding such rows in the items table.

1. If `pending.md` has no Done table, create it right below the items table: heading `## Done Items` (pt-BR `## Itens Feitos`) and the same header row as the items table.
2. Cut each `Done` and `Rejected` row from the items table and paste it into the Done table in ascending `#` order, unchanged.
3. Run `check`.

Say in the reply which items moved.

### Remove an item

Only for an item registered by mistake: no work started, not cited elsewhere. Delete its row and its section. Anything else is closed as `Declined`, never removed, because "item N" may be cited in sections or increment documents. Run `check`.

### Open an increment

1. Read the initial research (`001-*/`) and `pending.md`. Decisions closed in the initial research are input; reopening one needs a named reason.
2. Prefer one increment at a time. If another increment is `In Progress`, say so and open the new one only if the user confirms.
3. `pending.py next` gives the increment number; create `NNN-<slug>/` and append its row to the increments table: Title, Status `Open` (`Aberto`).
4. Set the Increment column to `NNN` on every item the increment works, and move their status as the work starts.
5. Append the section `## Increment NNN — <slug>` (pt-BR `## Incremento NNN — <slug>`) at the end of `progress.md`, with the same slug as the folder; create the file first if the research has none (see Log progress).
6. Crie a Task do incremento no Azure DevOps nesta abertura, antes de iniciar discovery ou plano (veja Azure DevOps).
7. When the increment runs RPI, its documents go in `NNN-<slug>/`.
8. Ao concluir o primeiro design ou plano, complete a descrição da mesma Task com `wit.py update`; não crie outra Task.

### Close an increment

1. **Check the work is committed.** `git status --short` must show nothing the increment changed or produced: code, tests, docs outside the research and, when the research is versioned, its folder and files. Anything uncommitted: stop, tell the user what is pending, and leave the increment `In Progress` until it is committed. A research kept out of git is exempt for its own folder; the changes outside it still count.
2. Close its items (see Close an item) and set the increment to `Done` (`Feito`) in the increments table, then sync its Azure DevOps Task to `Closed` (see Azure DevOps).
3. Reread its `progress.md` section against what the increment actually did and add any decision, change, customization or addition that is missing.
4. Feed the learning back: update the affected decision, item or evidence in the initial research (`001-*/`) and point to the increment folder.
5. If the research is local (not versioned), check that nothing the increment changed outside `docs/research/` cites the research, its paths or its item numbers.

### Azure DevOps

Em repositórios Azure DevOps, crie a Task no momento em que o incremento é aberto. O título basta para a abertura; não espere discovery, design, plano ou confirmação de uma User Story já conhecida. A Task acompanha o estado do incremento.

**Gate.** `python3 <this skill>/scripts/wit.py ado` exits 0 only when a git remote is Azure DevOps. Any other exit: skip every Azure DevOps step in this skill, silently. No question, no `wit.md`. A GitHub repository never sees any of it.

**`NNN-<slug>/wit.md`** guarda organização, projeto, User Story, Task, estado e data. Somente `wit.py` o lê e escreve. `User Story | none` com uma Task indica criação sem pai; ambos como `none` registram a decisão explícita de não rastrear no ADO. A ausência de `wit.md` indica criação pendente, não uma pergunta obrigatória ao usuário.

**Criar na abertura.** Reutilize a User Story já definida para a pesquisa; na ausência dela, reutilize a do `wit.md` do incremento anterior e informe o vínculo adotado. Só pergunte quando houver ambiguidade real ou o usuário tiver indicado outro destino. Se não houver User Story conhecida, crie a Task sem pai no projeto do repositório; a definição do pai pode vir depois. A ausência de descrição ou de User Story não adia a criação. Um pedido explícito para não rastrear no ADO continua sendo respeitado com `wit.py none`.

- Com User Story: `wit.py create <NNN-slug/> --us <ref> --title …`.
- Sem User Story: `wit.py create <NNN-slug/> --project <projeto> --title …`.
- Se o design ou plano já estiver pronto, forneça também `--description …` com o texto completo.
- A Task herda a área da User Story quando disponível; usa Activity `30-Desenvolvimento` e estimativa original `8`, conforme o processo já verificado.
- A Task nasce `New`; se o incremento já estiver `In Progress`, sincronize para `Active` nesta mesma abertura.
- Confirme a criação por leitura posterior e registre o vínculo em `wit.md` antes de anunciar a tarefa como criada. Se houver falha de rede ou autenticação, registre a pendência e continue o trabalho local; não trate a Task como criada.

**Completar após design ou plano.** Quando o primeiro dos dois estiver pronto, atualize a descrição da Task existente com `wit.py update <NNN-slug/> --description …`; não espere o segundo documento nem a implementação. Se o outro documento trouxer mudança relevante depois, atualize a mesma Task. O comando relê o ADO, confirma a descrição e preserva o vínculo. Um incremento retomado com documento pronto e descrição pendente recebe a atualização na retomada.

**Keep the card true.** Whenever something changes what the Task says (scope added, removed or narrowed; the reason or justification; the goals; the validation method; the approach; or what the title promises), whether it comes from the user, a decision, a finding, a design or plan change or a blocker, update the Task in the same turn you record the change in `pending.md` or `progress.md`:
- Rewrite the whole description so it states the current truth in the four labelled parts, never an appended diff, and run `wit.py update <NNN-slug/> --description …`. Add `--title …` when the title no longer says what is delivered. Texto do cartão applies in full: no references to this flow.
- Skip it for changes that leave the card's content as it is: status moves, progress notes, commits, wording of the research. No `wit.md`, or `none`: skip silently.
- Say in the reply that Task #N was updated and what changed, in one line. If `az` fails, say so and redo the update at the next sync or when the increment is resumed.

**Texto do cartão.** Título e descrição são em pt-BR e descrevem o trabalho de forma autossuficiente: sem números de IC, nomes de pastas da pesquisa, itens do pending, arquivos `.md` ou caminhos desse fluxo. O título diz o que será entregue, sem depender do contexto da conversa. A descrição pode ficar ausente somente na abertura anterior ao primeiro design ou plano; quando preenchida, deve ser completa e ter quatro partes, cada uma iniciada pelo rótulo: `O que será feito:`, `Por quê:`, `Objetivos:` e `Como validar:`. Preserve o escopo e os critérios definidos no documento disponível. A exceção de descrição ausente vale para a Task inicial, não para Features ou User Stories.

**Incremento retomado sem Task.** Crie a Task assim que detectar a lacuna, usando a User Story conhecida e a descrição completa se o primeiro design ou plano já existir. A pergunta antiga sobre vínculo não é motivo para continuar adiando a criação.

**Keep the Task in step.** After the increments table changes, run `wit.py state <NNN-slug/> <state>`. It does nothing when `wit.md` says `none` and when the Task is already there:

| Increment | Task state |
|---|---|
| `Open` | `New` (what `create` leaves it in) |
| `In Progress` | `Active` |
| `Done`, after the commit check | `Closed` |

If Azure DevOps rejects a state (the process names it differently), report the error and ask; never pick another state. Any other `az` failure (login, network, permission): say so, leave the table and the work as they are, and retry on the next sync; a Task out of step blocks nothing. `az login` is the user's step.

**Create a Feature.** When the user asks for a Feature instead of giving a User Story, this is a conversation first, in this order, short and one decision at a time:
1. The **Feature**: title and goal.
2. Its **User Stories**: title, intent and acceptance criteria each.
3. The **Tasks** planned under each User Story (one per increment by default).

Propose a full draft of the three levels from what the user said, adjust it with them, and show the final tree. **Create nothing in Azure DevOps before the user approves that tree.** Then, in pt-BR:
1. `wit.py item --type Feature --title … --description … --project <project>`. The project defaults to the one in the Azure DevOps remote URL; say which.
2. For each User Story: `wit.py item --type "User Story" --parent <feature id> --title … --description …`. Its description is complete (veja Texto do cartão) and lists the planned Tasks, so they are findable in Azure DevOps. The Feature's description is complete too.
3. Log one `addition` line in `progress.md` with the Feature and User Story ids.
4. Link the current increment to the User Story it serves with `create`. The other planned Tasks are created as their increments open, reutilizando essa User Story sem nova confirmação, salvo ambiguidade ou instrução contrária.

If Azure DevOps rejects a type name (`Feature`, `User Story`, `Task` are the Agile process's; Scrum uses Product Backlog Item), report it and ask for the right one.

### Log progress

Trigger: inside an increment, a decision is made, a task finishes, something changes, is customized or is added, and a later reader would need it to understand where the work stands.

1. Append one line at the end of that increment's section in `progress.md`: `- YYYY-MM-DD · <type> · <text>`. Types, en-US / pt-BR: `decision` / `decisão`, `done` / `feito`, `change` / `mudança`, `customization` / `customização`, `addition` / `adição`.
2. The text is one sentence of up to 200 characters. Say what was decided or done and, when useful, point to the file or item (`item 4`) instead of repeating it. Not a transcript: no attempts, no reasoning, nothing already clear from a commit or the item's section.
3. A `decision` or `change` that alters what the increment's Azure DevOps Task says also updates the Task (see Azure DevOps, Keep the card true).
4. Entries go in the order they happen and are never rewritten; a later decision that reverses an earlier one is a new `decision` line.
5. Run `check`.

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

**Close.** User: "item 3 is done, commit a1b2c3d". Actions: Status `Done`; title `## 3 — <title> (done)`; under it `Done in increment 004 (a1b2c3d, 2026-10-14).`; move row 3 to the Done table, creating `## Done Items` below the items table if the file has none; `check`.

**Azure DevOps.** Usuário: "abra o próximo incremento". O remoto é Azure DevOps e o incremento anterior usa a User Story #50. Abra a pasta e crie imediatamente a Task com `wit.py create 004-… --us 50 --title "Validar a instalação independente dos agentes"`; não espere o plano. Ao começar o trabalho, sincronize para `Active`. Quando o primeiro design ou plano estiver pronto, preencha as quatro partes da descrição com `wit.py update`. Se não houver pai conhecido, crie com `--project` e deixe o pai para depois. Em outros remotos, pule os passos do ADO conforme o gate.


## Troubleshooting

- `wit.py state` sai 3: falta `wit.md`; crie a Task imediatamente usando o vínculo conhecido e repita a sincronização.
- `--project is required when the item has no parent`: a Feature has no parent to take the project from; pass `--project`.

- `no increments table`: the research predates the table, or the header was renamed. Create it as described in The increments table.
- `increment NNN has a folder but no row in the increments table`: add the row. `no folder … next to pending.md`: create the folder or fix the number.
- `is Open but item #N is …` / `is Done but item #N is …`: the increment status and its items disagree. Set `In Progress`, or close the item or move it to the increment that works it.
- `Item '…' differs from section title '…'`: the row and the section drifted. Make them identical; the section title wins unless the user renamed the item.
- `Increment NNN has no folder`: create the folder, or fix the number; never point at an increment that does not exist.
- `progress.md line N: …`: an entry or section heading in `progress.md` breaks the format. Entries are `- YYYY-MM-DD · <type> · <text>` with a type from the file's language; headings are `## Increment NNN — <slug>` with the slug of an existing folder.
- `Status is Done; move the row to the Done table …` (or `Rejected`): such a row is still in the items table. Move it (see Move to the Done table).
- `only Done and Rejected items belong in the Done table`: a row in the Done table has another status. Move it back to the items table, or fix its status.
- `expected one items table and at most one Done table …`: the header row differs from the template (renamed column, extra column), or a third table has it. Restore the template's header for the file's language.
- `section N has no row in the table`: an item was half-removed. Restore the row, or finish the removal (see Remove an item).
