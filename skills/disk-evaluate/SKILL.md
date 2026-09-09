---
name: disk-evaluate
description: Evaluates disk usage on this Mac — Docker/local Kubernetes, Homebrew, dev/language caches, system caches, node_modules, and large individual files — by running read-only diagnostic commands and cross-referencing live state, then reports reclaimable space per category with the exact command to free it. Never runs any command that deletes, prunes, moves, or otherwise modifies anything; only invoked explicitly via /disk-evaluate, not model-invocable or auto-triggered by phrases like "check my disk" or "clean up disk space". Do NOT use for actually freeing space, running cleanup commands, or reviewing code/tests — it only reports suggestions for the user to run themselves.
disable-model-invocation: true
license: CC-BY-4.0
metadata:
  author: flaviostudart@gmail.com
  version: 1.0.0
---

# Disk Evaluate

Reports reclaimable disk space on this Mac, sectioned by category, with the exact command for each finding.

## Role

Adopt this persona for the entire skill: *"I'm a sysadmin doing a read-only disk audit. I report what the data proves is reclaimable, and I never touch anything myself."* Every command actually executed must be read-only; every command that would free space is printed as a suggestion, never run.

## Guardrails

### Scope
- Do NOT run any command that deletes, prunes, moves, or otherwise modifies a file, volume, container, image, or cache — every command this skill executes must be read-only (`df`, `docker ps`, `docker system df`, `kubectl get`, `brew cleanup --dry-run`, `du`, `find`, registry catalog reads).
- Do NOT run `docker system prune` in any form, even with `--dry-run` — see [references/playbook.md](references/playbook.md) for why a blanket prune is unsafe even as a preview on a machine like this one.
- Do NOT treat anything in the report as pre-approved. Listing a command is not running it — the user decides, in a separate turn, which commands (if any) to run themselves.

## Instructions

### Step 1: Load the playbook

Read [references/playbook.md](references/playbook.md) — it has the category breakdown, the read-only verification commands, the per-category safe-to-suggest commands, and the environment gotchas (nested container runtimes, Homebrew cache defaults, macOS cache paths) that Step 2's data-gathering depends on getting right.

### Step 2: Gather live state

Run every read-only command from the playbook's verification section: `df -h`, `docker ps -a`, `docker system df -v`, `kubectl config get-contexts` + `get pods -A` for any local cluster found, a local registry catalog check if one is running on `localhost`, `brew cleanup --dry-run`, and the large-file scan (`find ... -size +500M`). Skip a tool cleanly if it isn't installed or isn't running (no `kubectl` context, Docker daemon not running, no `brew`) — say so in the report, don't fail the whole evaluation over one missing tool.

### Step 3: Cross-reference before calling anything reclaimable

Zero host containers referencing a Docker image does not mean the image is dead — check it against deployed pod images (if a local cluster exists) and any local registry catalog before counting its size as reclaimable. A stopped compose project is not automatically orphaned — check whether its project directory still exists before treating its containers/volumes as removable.

### Step 4: Build the report

One section per category: Docker/local Kubernetes, Homebrew, dev/language caches, system/app update caches, node_modules, large individual files. For each finding, give the reclaimable size (or file path + size), the exact command to free it, and the one-line reason it's safe. Put anything that is not a pure cache — model weights, DB dumps, personal media, named volumes with a live reference — in its own flagged subsection, never folded into a blanket removal command.

### Step 5: Stop after reporting

End the turn with the report. Do not run, offer to run, or ask whether to run any of the listed commands.

## Examples

### Example 1: Normal run
User: `/disk-evaluate`
Result: a sectioned report — e.g. "**Docker** — 4.2GB via `docker image prune -a -f` (0 containers, 0 kubectl pods, not in the local registry catalog) · **Homebrew** — 1.8GB via `rm -rf $(brew --cache)` · **node_modules** — 620MB across 3 idle projects, review list attached."

### Example 2: No local cluster present
User: `/disk-evaluate` on a machine with no `kubectl` configured.
Result: the Docker section still reports reclaimable image/volume/build-cache space from `docker system df -v` alone, with a note that no local Kubernetes context was found so the pod cross-reference was skipped — not an error.

## Troubleshooting

### Docker daemon not running
`docker ps` / `docker system df` fail with a connection error. Skip the Docker/local Kubernetes section entirely and say so in the report — don't guess at sizes from a previous run.

### `brew` not installed
Skip the Homebrew section entirely rather than reporting zero.
