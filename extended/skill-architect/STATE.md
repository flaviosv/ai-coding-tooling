# STATE

## Decisions

### AD-001
- **Decision**: Removed `templates/version-stratification-guide.md` and its two touchpoints in this overlay (the Phase 2.4 link, and the Phase 3 "Version sections" compression rule that depended on the concept it defined).
- **Reason**: No reference file in the repo (`skills/*/references/`, `extended/*/references/`) ever exercised the version-stratified structure — the guide was unused template weight, and the leftover "Version sections" compression rule referenced a concept with no definition once the guide was gone.
- **Trade-off**: If a future skill needs multi-version reference docs (e.g. a PHP skill spanning 8.1–8.4 with real per-version differences), the stratification pattern has to be re-authored — it's recoverable from git history (deleted in the same change that added this entry) but not currently in the template set.
- **Date**: 2026-09-13
- **Status**: active

### AD-002
- **Decision**: Removed `templates/reference-file-naming-convention.md` and inlined its content directly into this overlay's Phase 2.4 (naming pattern, kebab-case slug rule, examples, generic-baseline exemption).
- **Reason**: This overlay was the template's only real caller (a bare link) — extracting a two-paragraph rule used by a single reader added an indirection with no reuse benefit.
- **Trade-off**: If a second skill later needs this same naming rule, it will be duplicated rather than shared until re-extracted into `templates/`.
- **Date**: 2026-09-13
- **Status**: active

### AD-003
- **Decision**: Replace the two `templates/agent-wait-protocol.md` links in Extension 4 (the Phase 2.5 dispatch-check instruction and the Phase 3 wait-instruction wording) with references to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch`'s own SKILL.md body (see `skills/subagent-dispatch/STATE.md` AD-002) rather than remaining a standalone template.
- **Trade-off**: Extension 4's wording now assumes `subagent-dispatch` stays installed; removing that skill without updating this overlay would leave a stale pointer.
- **Date**: 2026-09-13
- **Status**: superseded by AD-007

### AD-004
- **Decision**: Phase 2.4's `<technology>-<skill-name>.md` rule gains an exception: a skill whose references split by scope declares `<technology>.<variant>.md` naming in its own `SKILL.md` (e.g. `code-review`'s `fastapi.code.md`, `fastapi.tests.md`), and the declaration wins. Examples no longer name the removed `tests-code-review`.
- **Reason**: `code-review` absorbed `tests-code-review` and `complete-review` and now names checklists by scope suffix; an overlay still mandating `<tech>-<skill-name>.md` would steer new skills and `tech-reference-add` toward files that skill never loads.
- **Trade-off**: Two naming patterns exist repo-wide instead of one; the default still applies to every skill that doesn't declare otherwise.
- **Date**: 2026-09-13
- **Status**: superseded by AD-012

### AD-005
- **Decision**: Phase 2.4's "Linking a shared template" guidance is replaced by "Keep links inside the skill": a skill links only files in its own directory, since the repo's `templates/` folder no longer exists.
- **Reason**: Its last file, `reply-review-filter.md`, moved into `code-review` once that skill became its only consumer (`skills/code-review/STATE.md` AD-010), and `fs-harness` no longer creates the `~/.claude/templates` link; guidance to link `../../templates/` would now produce broken links.
- **Trade-off**: Content two skills genuinely share would have to be duplicated or re-extracted into a new shared mechanism; accepted, since every template this repo ever had ended up with a single consumer.
- **Date**: 2026-09-13
- **Status**: superseded by AD-008

### AD-006
- **Decision**: Replaced Phase 2.5's `[docs/cli.md](../../docs/cli.md)` link with an instruction to run `fs-harness help` and read the `override` entry.
- **Reason**: A new `doctor` check (`docs/cli.md` "Notes & gotchas") resolves a skill/overlay file's relative `.md` links against its *installed* `~/.claude/` symlink location, not just its repo location — this file installs as `~/.claude/skills/skill-architect/SKILL.extended.md`, one directory shallower than `extended/skill-architect/` is in the repo, so `../../docs/cli.md` resolved to a nonexistent `~/.claude/docs/cli.md` once installed. Confirmed with a direct `readlink`/`ls` check, not just the new check's own report. A live command reference can't drift the same way a linked doc path can.
- **Trade-off**: None identified — `fs-harness help` is already documented as the CLI's own source of truth for syntax (`docs/cli.md`), so this loses no information the doc link had.
- **Date**: 2026-09-13
- **Status**: superseded by AD-011

### AD-007
- **Decision**: Deleted Extension 4 (Subagent Dispatch — Wait Protocol) entirely — its Phase 2 dispatch check, Phase 3 wait-instruction wording, and Phase 4 wait check — and the overlay no longer mentions `subagent-dispatch`, wait protocols, or dispatch at all.
- **Reason**: User decision: skill-architect must not define rules for triggering or waiting on subagents. That belongs to `subagent-dispatch`, which loads on its own whenever a subagent is dispatched; the overlay's pointer only covered waiting (harness-evaluation #20) and restated that skill's rules and 15-minute default in drift-prone copies (#21).
- **Trade-off**: A skill designed through skill-architect gets no design-time prompt about dispatch; correctness relies on `subagent-dispatch` triggering at authoring or run time.
- **Date**: 2026-09-14
- **Status**: active

### AD-008
- **Decision**: Restated "Keep links inside the skill" (in 2.2b Reference File Design) as a self-contained rule: a skill links only files within its own directory (its `references/`, `scripts/`, or `../SKILL.md` from a reference file) and never links or loads anything outside it — not `CLAUDE.md`, `CLAUDE.global.md`, the repo's `references/`, `docs/`, or another skill's files.
- **Reason**: User decision overriding harness-evaluation #18's fix, which pointed at a `CLAUDE.global.md` section that has since been deleted; the rule stays, but no longer depends on (or explains) repo-level folders.
- **Trade-off**: None beyond AD-005's: content two skills share is duplicated rather than linked.
- **Date**: 2026-09-14
- **Status**: superseded by AD-013

### AD-009
- **Decision**: Guardrail and step-structure fixes: injected steps use `Na` labels anchored to real base steps (1.2a Guardrail Discovery, 2.2a Design the Guardrail Set, 2.2b Reference File Design) instead of reusing base numbers; the `## Guardrails` template is placed before the workflow steps; risk categories point at the guardrail menu's When to propose column instead of fixed per-tier lists (the Low-risk "Scope only is sufficient" line went with them); Phase 4 guardrail testing is one simulation line.
- **Reason**: Harness-evaluation #22 (base 1.3/2.3/2.4 collided with injected steps), #23 (repo skills and the base put gates at the top), #29 (tier lists and menu gave different guardrail sets for the same skill — the menu is now the single source), #24 (base 4.3/4.4 already cover the rest).
- **Trade-off**: Earlier entries' "Phase 2.4"/"Phase 2.5" names now refer to 2.2b and Extension 2's step 4; tier alone no longer yields a quick default guardrail list.
- **Date**: 2026-09-14
- **Status**: active

### AD-010
- **Decision**: Token-efficiency trims: dropped the reference-file `// Good` / `// Bad` example-marker rule with no replacement, replaced the Phase 4 token-efficiency checklist with a one-line re-check against the Phase 3.2 output rules, and removed the repeated "Inject the following steps…" intro lines.
- **Reason**: User decision on harness-evaluation #27 (the marker was C-family-only and its trim clause ambiguous); #19 (checklist duplicated the rules ~20 lines above); #28 (every sub-heading already names its injection point).
- **Trade-off**: Generated reference files no longer get a uniform Good/Bad labeling convention.
- **Date**: 2026-09-14
- **Status**: active

### AD-011
- **Decision**: Deleted Extension 2 (The `extended/` Pattern for Global Skills) entirely: its Important Boundaries inject, manual steps, when-to-use bullets, frontmatter template, and 200-line / `reference/` overflow rule. The one tooling fact worth keeping (an overlay's `references/` installs as `references.extended/` when the parent already ships `references/`) moved to `docs/cli.md` Gotchas.
- **Reason**: User decision closing harness-evaluation #12-#16, #25, #26: skill-architect is for creating skills only (the base's Important Boundaries says so), and maintaining vendor skills is already covered by root `CLAUDE.md` Skill Modification Rules, `fs-harness override`/`unoverride`, and `CLAUDE.global.md` Skill Extensions. The extension contradicted the base redirect, pointed at a nonexistent `AGENTS.md`, a `reference/` folder fs-harness never links, and duplicated the `override` scaffold.
- **Trade-off**: A skill-architect run gets no in-skill guidance on overlaying a vendor skill; that relies on the repo-level docs and CLI. The overlay's frontmatter description and intro blockquote still mention the `extended/` pattern until #31 is decided, and the remaining extension keeps its "Extension 3" number.
- **Date**: 2026-09-14
- **Status**: active

### AD-012
- **Decision**: 2.2b's naming examples now use real files: `<technology>` slugs `php`, `go-gin`, `ruby-on-rails`; `<skill-name>` is the reference folder the skill scans (e.g. `coding-guidelines` in `extended/tlc-spec-driven/references/coding-guidelines/php-coding-guidelines.md`); the scoped-variant exception is `<name>.<scope>.md` (e.g. `code-review`: `php.code.md`, `review-checklist.tests.md`); baseline files are exempt from the `<technology>` prefix (e.g. `review-checklist.code.md`).
- **Reason**: Harness-evaluation #17: the old examples (`tests`/`coding-guidelines` as skill names, `fastapi.*` files, `review-checklist.md`, `testing-patterns.md`) did not exist and taught the wrong layout; `code-review` applies the scope suffix to topic checklists too, not only to technologies.
- **Trade-off**: None beyond AD-004's two coexisting naming patterns.
- **Date**: 2026-09-14
- **Status**: active

### AD-013
- **Decision**: "Keep links inside the skill" now says a skill never links, loads, or defers its instructions to anything outside its directory, that naming an outside file as the source of a rule counts (state the rule inline instead), and that files a skill works on as its subject (a target project's `CLAUDE.md`, `docs/codebase/`, a PR) are not dependencies.
- **Reason**: User decision on harness-evaluation #18's scope: pointer-style mentions ("follow the global CLAUDE.md rule") are dependencies just like links; the subject clause keeps the rule from being over-applied to skills whose job is reading or writing those files. Existing violations in `tlc-spec-driven`, `session-evaluate`, and `architecture-evaluate` were fixed in the same change.
- **Trade-off**: A rule a skill shares with a repo-level file is duplicated and can drift.
- **Date**: 2026-09-14
- **Status**: active
