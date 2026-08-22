# progress.md Schema

Read this when Step 0 needs to resume a run, or whenever a step is about to write its own section of `progress.md`. Lives at `.specs/features/<task_id>-<slug>/progress.md`, lowercase, one file per feature. Only the orchestrator ever writes it — see the SKILL.md Guardrails' State Ownership section.

## Structure

```markdown
# Progress: <task_id> — <description>

## Run State

- status: in-progress | complete
- last_completed_step: <step number/name>
- worktree_path: .claude/worktrees/<task_id>-<slug>
- branch: feature/<task_id>_<description>
- base_branch: <value>
- target_branch: <value>
- pr_number: <N> (once Step 3 has run)
- gh_login: <resolved account login — never a token>
- human_review: yes | no
- human_review_exclude: <comma list, if any>

## Checkpoints

- spec: pending | approved | n/a
- design: pending | approved | skipped (auto-sizing) | n/a
- complete_review: pending | approved | n/a

## Step Log

One line per completed step, appended as it finishes:

- Step 1 (worktree/branch): done — <worktree_path>, <branch>
- Step 2 (push): done
- Step 3 (draft PR): done — PR #<N>
- Step 4 (quick gate + grilling): done — gate: <triggered|skipped>; grilling: <N rounds, or "no questions">
- Step 6 (feature folder): done — .specs/features/<task_id>-<slug>/
- Step 7a (specify): done — spec.md
- Step 7b (design): done — design.md | skipped (Small/Medium scope)
- Step 8 (tasks): done — tasks.md
- Step 9 (commit spec artifacts): done — <commit sha>
- Step 10 (execute): done — Verifier: PASS
- Step 11 (PR description): done
- Step 12 (complete-review): done — <N> findings published | held pending approval
- Step 13 (fix-review): done — <N> fixed, <N> blocked
- Step 14 (architecture-evaluate): done — <N> files, committed | left uncommitted (all new)
- Step 15 (design-sync): done | skipped (no .design-sync/config.json)
- Step 16 (mark ready): done
```

## Resume Logic

1. Read `status`. `complete` → route per SKILL.md Step 0's two completed-run branches (merged/closed cleanup, or open-PR fix-review re-entry). `in-progress` → continue below.
2. Read `last_completed_step`. Resume at the next step in SKILL.md's sequence — never re-run a step already logged as done.
3. If the last logged step is a checkpoint pause (`Checkpoints` shows `pending` for `spec`/`design`/`complete_review`), resume by re-showing that exact artifact and waiting again — do not auto-approve because time has passed since the pause began.
4. Pull `worktree_path`, `branch`, `pr_number`, and `gh_login` directly from `Run State` — never re-derive them from scratch on a resume; re-deriving risks landing on a different worktree or PR than the one this run already committed to.
5. If `Run State` is missing a field a resumed step needs (a partially-written file from a crash mid-step), treat that step as not-yet-done regardless of what `last_completed_step` claims, and re-run it from its own start — a step is only "done" once its full result, not just a partial one, is logged.
