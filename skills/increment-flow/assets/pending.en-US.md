# Pending — {{TOPIC}}

Items to keep track of in this research. An increments table (progress of each increment) and an items table; every item has a section below with the same number, where the full text lives.

- `#` is the section number. It never changes and is never reused: "item N" and "§N" always mean section N.
- A new item goes at the end of the table with the next free number.
- A finished item (`Done`, `Declined`, `Rejected`) stays in the table, and its section title gets the status in parentheses.

Item columns. Each cell holds only what its column says:

- **Item:** short title, identical to the section title.
- **Status:** one value from the table below, nothing else.
- **Depends on:** item numbers only (`3` or `3, 5`); `—` when none. Anything else that blocks the item goes in its section.
- **Increment:** the increment number only (`002`); `—` when none.
- **Details:** a short summary of what needs to be done, up to 200 characters; the rest goes in the section.

| Status | When to use |
|---|---|
| Open | registered, no work started |
| Researching | discovery (`tlc-discover`) in progress, no verdict yet |
| Researched | discovery finished with a verdict; the plan is missing |
| Planning | plan (`tlc-plan`) in progress |
| Planned | plan finished; implementation is missing |
| Implementing | implementation (`tlc-implement`) in progress |
| Done | delivered and proven |
| Declined | decided not to do |
| Rejected | out of the current scope, left for another time |

Increment status:

| Status | When to use |
|---|---|
| Open | folder opened, nothing done yet |
| In Progress | anything done in it: a discovery, a plan, any work |
| Done | closed, all its items closed |

## Increments

| Increment Number | Title | Status |
|---|---|---|
| 001 | Initial research: {{TOPIC}} | Open |

## Items

| # | Item | Status | Depends on | Increment | Details |
|---|---|---|---|---|---|
| 1 | Initial research: {{TOPIC}} | Open | — | 001 | {{SUMMARY}} |

## 1 — Initial research: {{TOPIC}}

Registered on {{DATE}}. {{QUESTION}}
