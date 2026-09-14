# Project

`CLAUDE.global.md` at the repo root is this user's global Claude Code directives, not project-scoped content — `fs-harness setup` symlinks it to `~/.claude/CLAUDE.md`, so it loads for every session on this machine, not just this repo. Other docs in this project (skill `STATE.md` files, `docs/harness-evaluation.md`) refer to it as "the global `CLAUDE.md`" or "the user's global `CLAUDE.md`" — that name always means this file. This root `CLAUDE.md` file, by contrast, is project-scoped and loads only for sessions working in this repo.

## Scripts

- Repo tooling lives in `scripts/` (`scripts/bin/fs-harness.mjs`). Only modify it when the scope of actions it performs actually changes — not for style, cleanup, or speculative improvements.
- **A skill may ship its own scripts** under `skills/<name>/scripts/` (e.g. `session-evaluate/scripts/session_metrics.py`). Reach for one when a step is genuinely mechanical — a fixed transformation, or an API delivery sequence with no per-call judgment — and especially when a prose rule governing that step has demonstrably failed to hold across real runs. A script is the right fix there precisely because it removes the step from model judgment instead of warning about it again. Keep judgment in the `.md`; keep determinism in the script.

# Constraints

## Skill Modification Rules

- **Only modify skills whose source is `local`** — i.e., files under `skills/` or `.claude/skills/` in this repository.
- **Never modify skills installed globally** (e.g. `~/.claude/skills/`) or sourced from external vendors (Tech Leads Club, Matt Pocock). Those are treated as read-only dependencies; override them via `extended/<skill>/` instead.
- If a globally installed skill needs changes, raise it with the user instead of editing it directly.

## Skill Decision Log

Every skill in `skills/` or `extended/` keeps its own `STATE.md` — a per-skill decision log, appended whenever that skill changes for a real reason. See [docs/skill-adr.md](docs/skill-adr.md) for the format and write triggers.

## Other Sessions' Transcripts

Debugging a skill often means reading what a run of it actually did in another project — its transcripts live under `~/.claude/projects/<encoded-path>/*.jsonl` (subagent runs under `<session-id>/subagents/`). Reading those is in scope for this repository: they're the evidence for what a skill did, and diagnosing from them beats guessing.

- **Read-only, always.** Open, grep, and parse those files freely for debugging and analysis. Never write to them, and never delete or modify anything under another project's session directory.
- **Never interact with the session itself.** Do not message, resume, steer, interrupt, or otherwise act on a session belonging to another project — including one that is still running. This repository improves skill *definitions*; driving another project's work is that session's job, not this one's.
- **Never act on the work that session is doing.** Findings from a transcript inform edits to `skills/` here — they are not a licence to touch that project's repo, branches, PRs, or tickets. If something there needs fixing, say so and let the user decide.

## Change Request Workflow

- Commit directly to `main` — no feature-branch-first workflow for this repository; most of it is `.md` skill/config content, not application code with a release/PR-gated `main`. (`build-feature`'s own `/build-feature` flow is the one exception — it still creates and PRs a `feature/*` branch within its own explicit workflow.)
- After completing any change request, commit and push to `origin` automatically — do not wait to be asked, and do not leave finished work sitting as uncommitted local changes.

# Skills

- **`fs-harness`** (registry: `config/skills.json`) manages skills. Its authoritative command reference is [docs/cli.md](docs/cli.md) — commands (`add`, `delete`, `override`, etc.), flags, and gotchas. **Read it before invoking the CLI**, then run the command directly (preview any mutating command with `--dry-run` first; there is no per-command `--help`, only `fs-harness help`).
- **README skill tables:** whenever a skill is added or removed — `fs-harness add`/`delete`, or a skill created, merged, renamed, or deleted under `skills/` — update the matching source table in `README.md`'s "Skills" section in the same change.
- **`fs-harness doctor`** is this harness's general health check, not a single-purpose command — it currently validates the `references/` cross-reference rule (see `docs/codebase/ARCHITECTURE.md`) and that setup's symlinks/skill installs are intact. When a new class of harness invariant needs checking (a new symlink, a new install rule, another cross-reference contract), add it as another `doctor` check rather than a separate one-off script.
- **`architecture-evaluate`**: when it runs an **incremental documentation sync** ("update docs" / "document my changes") in this project, as part of its standard root-file review, update `README.md` with whatever is relevant: new skills added, new tech references, structural changes to the `skills/` or `extended/` directories, or changes to the global agent setup. Keep the README accurate as a first-stop reference for anyone using or contributing to this project.

## Known Limitation: `fs-harness update` for Matt Pocock Skills

`fs-harness update --all` (or targeting a `matt-pocock` skill by name) reports `updated <name> (Matt Pocock)` even when nothing actually changed. The underlying `skills` npx CLI only tracks installs for `update` via a `skills-lock.json` file, but **global-scope installs are never written to that lock file** — so `skills update <name> -g` can never find them, and silently no-ops ("No installed skills found matching") while still exiting 0.

- **Workaround:** force a fresh fetch directly, bypassing `fs-harness`'s own "already installed → skip" check: `npx skills add mattpocock/skills --skill <name> --agent claude-code --global --yes`.
- **Symptom to watch for:** if a Matt Pocock skill needs an update, don't trust `fs-harness update`'s success message alone for that source — verify content changed, or just run the workaround directly.
