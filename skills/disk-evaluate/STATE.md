# STATE

## Decisions

### AD-001
- **Decision**: `disable-model-invocation: true` in frontmatter — the skill is reachable only via explicit `/disk-evaluate`, never auto-triggered by description matching or loaded as a dependency by another skill.
- **Reason**: user explicitly asked for the grill-me/grilling pattern — a disk audit should never fire passively off phrases like "check my disk" or "clean up space".
- **Trade-off**: lower discoverability; the description field's trigger phrases are informational only, not functional.
- **Date**: 2026-09-09
- **Status**: active

### AD-002
- **Decision**: Built as a repo-owned local skill (`skills/disk-evaluate`, registered via `fs-harness add --source local`) rather than an untracked folder directly under `~/.claude/skills/`.
- **Reason**: user chose repo-tracked + `fs-harness`-managed over a bare global install, despite the skill's content being machine-personal (macOS disk hygiene) rather than project-specific.
- **Trade-off**: a personal utility now lives inside a repo whose stated purpose is this project's own tooling; accepted knowingly by the user over the global-only alternative.
- **Date**: 2026-09-09
- **Status**: active

### AD-003
- **Decision**: The skill executes the read-only diagnostic commands itself (`df`, `docker ps -a`, `docker system df -v`, `kubectl get-contexts`/`get pods`, `brew cleanup --dry-run`, `find -size`) rather than only ever printing them for the user to run and paste back.
- **Reason**: mirrors the source playbook's own "re-evaluation prompt" workflow, which already asked Claude to gather live state itself; cross-referencing stale pasted output would be unreliable.
- **Trade-off**: the skill needs Bash access, so the read-only/no-write boundary is enforced entirely by the Guardrails section's command discipline, not by withholding tool access outright.
- **Date**: 2026-09-09
- **Status**: active

### AD-004
- **Decision**: Dropped the source doc's manual "Re-evaluation prompt" section (a copy-paste block instructing a future Claude session how to re-run the workflow) from `references/playbook.md`.
- **Reason**: that prompt existed only because the workflow had no skill to invoke; `/disk-evaluate` now is that re-invocation mechanism, so the prompt text is dead weight.
- **Trade-off**: none — pure removal of now-redundant content, everything substantive from that section (report sectioning, cross-reference rules, flag-non-cache-items) is already covered by `SKILL.md`'s Instructions.
- **Date**: 2026-09-09
- **Status**: active

### AD-005
- **Decision**: Deleted the opening body line under `# Disk Evaluate` ("Reports reclaimable disk space on this Mac, sectioned by category, with the exact command for each finding.") and the bare `User: /disk-evaluate` line in Example 1.
- **Reason**: 2026-09-12 harness-eval run (`docs/harness-evaluation.md` rows #13-#14) flagged the opening line as duplicating the frontmatter `description` field with no added nuance, and the bare example line as adding nothing beyond the skill's own name — Example 1's `Result:` line already demonstrates usage.
- **Trade-off**: none — pure removal of redundant content; Example 1 still reads correctly as a heading followed directly by its `Result:` line.
- **Date**: 2026-09-12
- **Status**: active

### AD-006
- **Decision**: Stale local-registry builds cached inside k3d nodes (old Tilt tags) are evaluated by a bundled read-only script, `scripts/k3d_stale_images.sh`, and suggested for removal by exact image ID; `crictl rmi --prune` is never suggested.
- **Reason**: a 2026-10-01 run found ~42.6GB (54GiB actually freed) of old Tilt tags across three k3d nodes, invisible to `docker system df`; computing the set by hand (per-node container refs × workload-spec refs × registry prefix) is mechanical and went wrong twice in-session, so it moved to a script. The blanket prune was ruled out because on k3s the pause image is unpinned and unreferenced by containers, so it would be deleted along with system images and scaled-to-0 workload images.
- **Trade-off**: the script assumes k3d's container labels (`k3d.cluster`, `k3d.role`) and its `<registry-container>:5000/` image prefix, so kind/minikube clusters are not covered; it needs `jq` on the host.
- **Date**: 2026-10-01
- **Status**: active

### AD-007
- **Decision**: The playbook and Steps 2–4 now cover the user temp directory (`$TMPDIR`), agent worktrees (`.claude/worktrees`, `.worktrees`), and a contents-free `~/Projects` size scan; `rm -rf` targets are suggested as literal paths, never `$(...)`.
- **Reason**: the 2026-10-24 run found 172GB of leaked test fixtures (`step-tree-*`, `step-work-*`) under `/private/var/folders/.../T` that `du ~` never sees, 14GB of agent worktrees, and 31GB of test-run output; the first Homebrew `rm -rf "$(brew --cache)"` was blocked by Claude Code's safety check, and a whole-directory `du` over the temp dir took over 5 minutes, so sampling by name pattern replaced it.
- **Trade-off**: the temp-dir scan relies on name-pattern grouping and sampled averages, so sizes are estimates; correlating fixtures to a producer uses metadata and process arguments only, so it is a correlation, not proof of the producing code.
- **Date**: 2026-10-26
- **Status**: active
