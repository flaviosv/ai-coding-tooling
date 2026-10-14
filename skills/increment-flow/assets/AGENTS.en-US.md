# AGENTS.md — Research: {{TOPIC}}

This folder holds one research, worked in small numbered increments. Load the `increment-flow` skill before changing `pending.md` or any increment folder: it holds the procedures, and its `scripts/pending.py check` must pass after every edit to `pending.md`.

## Map

| Path | What it is | Read it when |
|---|---|---|
| `001-*/` | The initial research: verdict and decisions for the whole topic | Before opening any increment |
| `NNN-<slug>/` | One increment and everything it produces | Working on that increment |
| `pending.md` | Every item of this research, its status and the increment that works it | Before choosing what to do next |

## Rules

- **Decisions already closed in the initial research are input, not agenda.** Reopening one needs a named reason.
- **Keep `pending.md` current.** Update an item's status the moment it moves, not when the increment closes.
- **An increment never closes with an open gap.** Each gap from the independent verification becomes a fix in the same increment, or goes to the user and enters `pending.md` only with their acceptance recorded.
- **On closing an increment, feed the learning back** into the initial research (the decision, item or evidence it changed), pointing to the increment folder.
- **Versioned:** {{VERSIONED}}
