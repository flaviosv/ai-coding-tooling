# progress.md Schema

Read this when Step 0 needs to resume a run, or whenever a step is about to write its own section of `progress.md`. Lives at `<worktree_path>/.specs/features/<task_id>-<slug>/progress.md`, lowercase, one file per feature, never committed; Step 0 finds it by enumerating `git worktree list` and matching `.specs/features/<task_id>-*/progress.md`. Only the orchestrator ever writes it — see the SKILL.md Guardrails' State Ownership section.

## Structure

```markdown
# Progress: <task_id> — <description>

## Run State

- status: in-progress | complete
- last_completed_step: <step number/name>
- worktree_path: <absolute path to .claude/worktrees/<task_id>-<slug>>
- branch: feature/<task_id>_<desc-kebab>
- base_branch: <value>
- target_branch: <value>
- human_review: yes | no
- human_review_exclude: <comma list, if any>
- context_docs_copied_from: <main working tree path> (only when Step 1 copied an untracked/ignored `docs/codebase/` in; absent when the path is tracked or the project has none — Step 11's sync-out reads this to know whether to write back, and where)
- pr_number: <N> (once Step 7 has run)
- design_sync: pending-user-action | skipped (once Step 12 has run)
- merge_check: clean | resolved | inconclusive | conflicting (once Step 13 has run)

## Checkpoints

- spec: pending | approved | n/a
- design: pending | approved | skipped (auto-sizing) | n/a
- code_review: pending | approved | n/a

## Step Log

One line per completed step, appended as it finishes:

- Step 1 (worktree/branch): done — <worktree_path>, <branch>; context docs: tracked | copied from <path> | none in repo
- Step 2 (push): done
- Step 3 (grilling, live in this conversation): done — <N rounds, or "no questions — frontier empty on round 1">
- Step 4 (grilling notes): done — .specs/features/<task_id>-<slug>/grilling-session.md
- Step 5a (specify): done — spec.md
- Step 5b (design): done — design.md | skipped (Small/Medium scope)
- Step 6 (tasks): done — tasks.md | skipped (Small/Medium scope)
- Step 7 (commit spec artifacts, open draft PR): done — <commit sha>, PR #<N>
- Step 8 (execute): done — Verifier: PASS
- Step 9 (push + PR description): done
- Step 10 (code-review, via Skill in this conversation): done — <N> findings posted; checkpoint approved (user edited on GitHub and replied) | no pause (human_review=no or excluded); <N> fixed, <N> answered, <N> rejected, <N> blocked; <N> commits pushed
- Step 11 (architecture-evaluate): done — <N> files, committed | left uncommitted (all new) | synced back to <path> | not synced back (source changed mid-run); <N> questions for the final report
- Step 12 (design-sync handoff): done — pending-user-action — handed off in the final report | skipped — no .design-sync/config.json
- Step 13 (merge check + mark ready): done — merge_check: clean | resolved (<N> files, <merge commit sha>) | inconclusive (mergeable UNKNOWN) | conflicting (unresolved: <files>) ; ready: done | not marked (conflicts unresolved)
```

## Resume Logic

1. Read `status`. `complete` → route per SKILL.md Step 0's completed-run branches (merged/closed → the cleanup sweep, or open-PR re-entry through `code-review`'s fix-existing-findings entry). `in-progress` → continue below.
2. **Checked before step 3:** if `Checkpoints` shows `pending` for `spec`/`design`/`code_review`, the run is paused at that checkpoint, even though the step that paused is already logged in `last_completed_step`. Resume by re-showing that exact artifact and waiting again — do not auto-approve because time has passed since the pause began. `code_review: pending` differs in mechanism, not in waiting: the review is already posted on GitHub, so show its PR URL (from `pr_number`) and wait for the user's reply, then invoke `code-review`'s continue-after-checkpoint entry instead of re-running the review, passing `pr_number`, `worktree_path`, and the feature folder (the directory this file lives in) (SKILL.md Step 10).
3. Otherwise read `last_completed_step` and resume at the next step in SKILL.md's sequence — never re-run a step already logged as done.
4. Pull `worktree_path`, `branch`, and `pr_number` directly from `Run State` — never re-derive them from scratch on a resume; re-deriving risks landing on a different worktree or PR than the one this run already committed to.
5. If `Run State` is missing a field a resumed step needs (a partially-written file from a crash mid-step), treat that step as not-yet-done regardless of what `last_completed_step` claims, and re-run it from its own start — a step is only "done" once its full result, not just a partial one, is logged.
