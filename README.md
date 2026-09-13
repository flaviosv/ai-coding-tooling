# ai-coding-tooling

Shared agent configuration and skills for Claude Code.

## Installation

Everything is managed by the **`fs-harness`** command (`scripts/bin/fs-harness.mjs`) — a single-file Node CLI with no dependencies. It replaces the former `agent-setup`/`skill-manager` skills and the `Makefile`.

> The command is **repo-local for now** — it requires this cloned repository. Making it available on any computer (publishing to npm) is a deferred follow-up (see scope in [docs/codebase/PROJECT.md](docs/codebase/PROJECT.md)).

### Prerequisites

- **Node.js ≥ 18** (oldest maintained LTS) and `npx` — bundled with Node. Developed and tested on Node 26.
- Unix-like shell (macOS/Linux)

Check your version with `node --version`. The CLI has zero runtime dependencies, so Node + `npx` is all you need.

### 1. Clone the repository

```bash
git clone <repo-url>
cd ai-coding-tooling
```

### 2. Make the `fs-harness` command available

```bash
npm link
```

This exposes `fs-harness` from any directory on this machine. (Or skip it and run `node scripts/bin/fs-harness.mjs …` from the repo.)

> **`fs-harness: command not found` right after `npm link`?**
> Your shell cached the old "not found" result. Run `rehash` (zsh) / `hash -r` (bash) in the current shell, or open a new terminal, then `which fs-harness` should resolve.
>
> **Using nvm?** `npm link` installs the symlink under the **active** Node's global prefix, and `fs-harness` runs on whatever `node` is active in the current directory (its shebang is `#!/usr/bin/env node`). Run `npm link` on the Node version you intend to use, and confirm with `node --version` before a real `setup`. If you add a `.nvmrc` that pins an old version, the CLI will execute on it.

### 3. Run setup

```bash
fs-harness setup
```

One command bootstraps everything:

- **Global:** symlinks `CLAUDE.global.md` to Claude Code's global config, installs every skill by source (project skills via symlink; Tech Leads Club / Matt Pocock via `npx`), applies all `extended/` overrides, installs any `personal/` skills, and syncs `config/hooks.json` into `settings.json` (`scripts/hooks/` — see `docs/cli.md`).
- **Project-local:** this repo's own instructions (`CLAUDE.md`) are tracked directly in the repo — no setup step needed to see them.

It refuses to overwrite an existing global config. To reverse everything `setup` did (remove the global config symlink, uninstall the skills it installed), run `fs-harness destroy`.

### 4. Install the status line script

```bash
fs-harness statusline          # skip if file already exists
fs-harness statusline --force  # overwrite with the version from this repo
```

Installs the Claude Code status line to `~/.claude/statusline-command.sh` (copied from `scripts/bin/misc/statusline.sh`). It shows the active model, effort level, directory, git branch, context-window usage, and the 5-hour rate-limit usage:

```
[Opus 4.8 (1M context) (high) - 📁 ai-coding-tooling (main)] ctx:6% 5h:3%
```

<img src="assets/images/statusline.png" alt="Status line sample" width="600">

Colors (rendered in the terminal):

| Element | Color |
|---------|-------|
| 🟦 Model (`Opus 4.8`) | bold cyan |
| 🟪 Effort (`high`) | bold magenta |
| 🟩 Directory (`my-project`) | green |
| 🟨 Branch (`main`) | yellow |
| ⬜ Labels (`ctx:`, `5h:`) | white |
| 🟩🟨🟥 Percentages | green < 50%, yellow < 80%, red ≥ 80% |

To customize without losing changes on the next `--force` run, edit `~/.claude/statusline-command.sh` directly and omit `--force`.

## Managing skills

| Command | Action |
|---|---|
| `fs-harness add <skill> --source <local\|tech-leads-club\|matt-pocock>` | Install one skill and register it in `config/skills.json` |
| `fs-harness delete <skill>` | Remove one skill: uninstall + deregister from `config/skills.json`; keeps `skills/<skill>` source and `extended/<skill>/` |
| `fs-harness list` | Show each skill's source and install state |
| `fs-harness override <skill>` | Scaffold `extended/<skill>/` and apply the overlay onto a vendor skill |
| `fs-harness update [skills...]` | Update Tech Leads Club / Matt Pocock skills |

Add `--dry-run` to any command to print the actions without changing anything. See [docs/cli.md](docs/cli.md) for the full command reference.

## Skills

Skills are reusable agent instructions that extend AI coding tools with specialized workflows. They are grouped below by source.

### Source: This Project (`ai-coding-tooling`)

Maintained here and installed globally via `fs-harness setup` / `fs-harness add`. These are the only skills you should modify:

| Skill | Description |
|---|---|
| **architecture-evaluate** | Creates and incrementally syncs the project context docs in `docs/codebase/` (PROJECT, STACK, STRUCTURE, ARCHITECTURE, CONVENTIONS, INTEGRATIONS, TESTING, CONCERNS, PIPELINE) that agents load at session start. Full mode maps the whole codebase; Incremental mode syncs only what changed (and root files like this README); Package mode documents a single module. |
| **build-feature** | Delivers a brand-new feature end-to-end: creates a worktree, branch, and draft PR, optionally grills you on scope, runs `tlc-spec-driven`'s Specify → Design → Tasks → Execute cycle, runs `code-review`, syncs architecture docs, and confirms the PR merges before marking it ready. Resumable from any interrupted step via `progress.md`. |
| **code-review** | Reviews code and tests (or either alone, via `scope`) and fixes what the review finds, as one run — architecture, code quality, performance, regression, security, and requirements; test coverage, gaps, isolation, clarity, and maintainability. Works on local changes, commits, or a GitHub PR, where it posts the review, optionally pauses for your edits (`human_review`), then fixes, pushes, and replies to and resolves every thread through a verifying script. Also fixes existing review comments, and batch-sweeps PRs awaiting your review or where you requested changes. |
| **disk-evaluate** | Reports reclaimable disk space on this Mac (Docker/local Kubernetes, Homebrew, dev and system caches, `node_modules`, large files) with the exact command to free each one. Read-only — never deletes anything — and only runs when invoked explicitly via `/disk-evaluate`. |
| **not-your-babysitter** | Autonomous senior-operator mode: resolves tasks end to end, verifies every claim against real evidence, and interrupts only for destructive actions, evidence dead-ends, or outcome-changing ambiguity. |
| **qa-steps** | Generates a step-by-step manual QA test plan for a Jira ticket, optionally enriched with a linked GitHub PR's diff, and posts it to the ticket only after you confirm. |
| **session-evaluate** | Analyzes a completed agent session transcript for token waste, slow turns, missed parallelism, subagent misuse, self-corrected mistakes, and oversized test runs — whole session or scoped to named skills — then applies the approved fixes to the responsible skill or context file. |
| **subagent-dispatch** | Reference for dispatching and waiting on subagents via the `Agent` tool: model aliases, the dispatch-prompt contract, the no-polling wait protocol, and this project's model-tier matrix for pipeline sites. |
| **tech-reference-add** ⭐ | Adds technology-specific reference files across all skills and extends qualifying global skills. Run this when adding a new framework or language to a project's stack. |

> Skill installation/update is handled by the `fs-harness` command (`scripts/bin/fs-harness.mjs`), not by a skill. See [Managing skills](#managing-skills).

> ⭐ **Highlighted skills:**
>
> - **`tech-reference-add`** — The recommended way to extend the tooling for a new technology. It propagates tech-specific reference files into all relevant skills (code review, coding guidelines, tests, etc.) in one step.

### Personal Skills (`personal/`)

You can add private, local-only skills that are never committed to git. Create a `personal/` directory at the project root and add skill subdirectories inside it — each must contain a `SKILL.md` file following the same structure as `skills/`.

```
personal/
  my-private-skill/
    SKILL.md
```

`fs-harness setup` auto-discovers and installs everything in `personal/` via symlink. These skills are never listed in `config/skills.json` and are discovered dynamically at setup time.

The `personal/` directory is gitignored — nothing inside it is tracked or committed.

## Recommended MCP Servers

| MCP Server | Purpose | Used by |
|---|---|---|
| **[Context7](https://context7.com)** | Fetches up-to-date documentation and code examples for any library. Provides authoritative raw material when generating technology-specific reference files. | `tech-reference-add` (Step 7) |

Context7 is optional but strongly recommended. When available, `tech-reference-add` queries it for official documentation to ground reference files in current best practices rather than relying solely on LLM training data. If unavailable, the skill falls back to the agent's own knowledge.

### Source: [Tech Leads Club](https://techlead.club)

Installed globally by `fs-harness setup`. Treated as read-only — do not edit these directly:

| Skill | Description |
|---|---|
| **docs-writer** | Writing, reviewing, and editing documentation and `.md` files. |
| **harness-eval** | Audits a repo's agent harness (AGENTS.md, rules, skills, skill references) for broken paths/commands, redundant instructions, and usefulness, using a dual-judge protocol with planted traps. |
| **jira-assistant** | Manages Jira issues via the Atlassian MCP — search, create, update, transition status, and handle sprint tasks. |
| **mermaid-studio** | Mermaid diagram creation, validation, and rendering (SVG/PNG/ASCII) across 20+ diagram types, with code-to-diagram analysis and theming. |
| **security-best-practices** | Language and framework specific security reviews (Python, JavaScript/TypeScript, Go). |
| **skill-architect** | Expert guide for designing and building high-quality skills from scratch through structured conversation. Covers standalone skills and MCP-enhanced workflows. |
| **subagent-creator** | Guide for creating AI subagents with isolated context for complex multi-step workflows. |
| **technical-design-doc-creator** | Creates comprehensive Technical Design Documents (TDD) following industry standards. |
| **tlc-spec-driven** ⭐ | Spec-driven planning (Specify → Design → Tasks → Execute) with complexity auto-sizing, atomic tasks, requirement traceability, and persistent memory. **Extended in this project** (`extended/tlc-spec-driven/`): augments `coding-principles` with software-design/observability/stack-style references and routes security to `security-best-practices`. |

### Source: [Matt Pocock](https://github.com/mattpocock/skills)

Installed globally by `fs-harness setup` via the `npx skills` CLI. Treated as read-only — override via `extended/<skill>/` rather than editing directly:

| Skill | Description |
|---|---|
| **grill-me** | A relentless interview to sharpen a plan or design; user-invoked only (`/grill-me`), delegates to `grilling`. |
| **grilling** | Grills you relentlessly about a plan, decision, or idea to stress-test your thinking. |

Adopt another one with:

```bash
fs-harness add <skill> --source matt-pocock
```
