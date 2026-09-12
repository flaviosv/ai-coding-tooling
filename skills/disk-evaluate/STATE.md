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
- **Reason**: 2026-09-12 harness-eval run (`docs/HARNESS-EVALUATION.md` rows #13-#14) flagged the opening line as duplicating the frontmatter `description` field with no added nuance, and the bare example line as adding nothing beyond the skill's own name — Example 1's `Result:` line already demonstrates usage.
- **Trade-off**: none — pure removal of redundant content; Example 1 still reads correctly as a heading followed directly by its `Result:` line.
- **Date**: 2026-09-12
- **Status**: active
