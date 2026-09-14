# Fix Stage

Stage 3: acting on the findings that remain after the checkpoint. It runs in one fresh fix worker dispatched by the root conversation — after a review, directly from the fix-existing-findings entry, or once for every PR of a batch sweep. Loaded by that worker, and by the root to write its dispatch prompt.

---

## Findings Source

| Target | Findings are | Delivered as |
|---|---|---|
| GitHub PR | Every published, unresolved review thread fetched fresh at step 1 — from this skill's review, a human reviewer, or both | Commits pushed to the PR branch, then replies and resolves via `deliver` |
| Local changes (no PR) | The findings the root passes in the dispatch prompt — the report minus whatever the user dropped at the checkpoint, or the IDs the user named ("fix Q1, H2") | Working-tree edits or local commits (see Local Mode) — never pushed |

**Only what remains is a finding.** A thread a human deleted, or a finding dropped at the checkpoint, does not exist for this stage.

## Guardrails

### Source of truth

- **On a PR, GitHub is the only source of truth, fetched fresh at step 1 of every run.** Never act on, reconcile against, or trust any earlier analysis, summary, or report in the conversation — including this skill's own review report — as evidence of what findings exist or what state they're in. State changes between when something was observed and when this stage acts; a manual comment may have been added or a thread edited. A finding mentioned only in the conversation and never published is out of scope in PR mode.
- **Never act on a review that is still `PENDING`.** If the only review is pending, stop and report it — the checkpoint's `submit` should have published it.
- Read every comment on a thread in order to decide what it currently asks — a later comment can revise or replace the first; don't grab only the last line either.
- Use the PR's title, body, and diff to understand what a finding is asking for, not the comment text in isolation.

### Judgment

- **Never fix a finding just because it exists.** A comment or finding is a claim to check against the current code. The check happens once, at fix time, by the context already reading the target file to make the edit (step 5) — never as a separate pass. An item that doesn't hold (stale, a misread of the diff, already addressed, or wrong) is **rejected** with reasoning, no edit. Silence from other reviewers is not evidence a finding is correct.
- **"Is this true?" is not "is this wanted?"** Before applying an item that changes a default, a threshold, a configuration value, or documented behavior, check it against the requirement that put the behavior there — the active feature's spec under `.specs/features/<feature>/`, this project's `CLAUDE.md`/`AGENTS.md`, and the PR's title/body. An item that contradicts a stated requirement is **rejected**, citing that requirement; changing a requirement is the user's call. A real run confirmed "`LOG_LEVEL` defaults to debug" against the code, switched it to `info`, and rewrote the tests asserting the spec'd value — reversing a requirement in that project's `CLAUDE.md`, which its caller then reverted across four files.
- **One clear remedy per item.** An item whose fix is still an open design choice — several approaches with no decision rule, a dependency swap, a change to a shared component beyond the PR's diff — is **blocked** with the options named. An item running far past ~10–20 tool calls without converging is itself that signal: stop and mark it blocked with what was found.
- Not confident what an item asks, even after reading it fully → **unclear**, reported unfixed with the reason. Never guess.
- A thread whose current comment addresses a specific person by name or handle ("@alice, can you weigh in?") is a live person-to-person exchange: **routed to a person** — no fix, no reply, no resolve; note it in the report.
- Never resolve a thread that still carries a live, unanswered question — reply with the answer instead.
- If file state no longer matches what step 4 assumed when you reach an item, mark it **blocked** — never force-apply.
- No explanatory comments on a fix unless the code is genuinely non-obvious.

### Execution

- **This worker fixes every item itself, inline, one at a time, and never calls the `Agent` tool.** It chooses the sequence — across PRs in a batch sweep, and across items within a PR. The test is mechanical: you are a dispatched worker, so you are already the isolated context. Do not reason about whether some other context "already isolated" you. (Two real runs had a dispatched worker decide it was the exception, nest a second and third agent, and drop the reply/resolve steps between them — commits pushed, zero threads answered.)
- File clusters organize the reading, not the dispatch: items whose fixes touch the same file are grouped so the file is read once, then processed one item at a time, each PR's items committing to that PR's checkout.
- When committing, stage each item's own files by path (`git add <path> …`) — never `git add -A`, which sweeps in unrelated working-tree changes. When not committing (an uncommitted workspace), stage nothing: the user's index is theirs.
- **Test impact per item:** add a test when the change isn't covered (follow `docs/codebase/TESTING.md` when present, else the conventions of neighbouring tests); update a test whose assertions the fix invalidates; remove a test only when it asserted the very behavior the fix corrects, replacing it with a test of the corrected behavior whenever there is anything left to cover. Coverage moves only as a stated consequence of a fix; a removal with nothing added back needs a one-line reason in the report. Run only the tests covering the files that item's fix touched.
- **Never clean up a dirty tree you didn't create.** Never `git stash`, `git restore`, `git checkout --`, or `git clean` anything this run didn't make, and never target a path outside the checkout you are working in. `progress.md` belongs to whoever invoked this skill and is being written while you run — leave it as found. (A real run's first two actions were `git stash` in the parent repo and `git restore` of its caller's live `progress.md`.) If uncommitted changes block a commit, name the files and stop.
- **In a worktree, resolve every path from the worktree root** (`pwd`). The main checkout holds the same relative paths on a different branch, so a read there can return plausible pre-feature content and silently invalidate the judgment at step 5 — one real run read the wrong branch's file this way.
- If the dispatch prompt names an active tlc-spec-driven feature folder, write the classified plan to `.specs/features/<feature>/fix-code-review.md`. Otherwise keep it in this worker's context only — never create anything under `.specs/`.
- Cite commit SHAs exactly as a command printed them — the short form from `git log --oneline` or the full form from `git rev-parse`. Never expand a short SHA or write one no tool output contains; a real run reported three invented 40-character SHAs.

## Dispatch (root conversation)

One `Agent` call, `subagent_type: general-purpose`, `model: sonnet`: **one fix worker for every finding in the run** — a single PR's, a local target's, or every PR of a batch sweep. Never one worker per PR. Where it works:

- **The caller supplied a worktree or checkout path** (as an orchestrator does) → the prompt names that absolute path; the worker works there.
- **Otherwise** the worker gets onto each PR's head branch however it judges safest ([PR Mode](#pr-mode) step 0), and never switches branches in a checkout that has uncommitted changes. Local targets work in the current checkout ([Local Mode](#local-mode)).

**The branch that receives local fix commits** is resolved by the root before dispatch: a named branch as named; for a commits target, the current branch when every reviewed commit is on it (`git merge-base --is-ancestor <commit> HEAD`), otherwise ask the user which branch — never guess.

Prompt:

- Prefix `[code-review][fix:PR-<N>]`, `[code-review][batch-fix]`, or `[code-review][fix:local]`.
- The target — for each PR: number, owner/repo, head branch, and the checkout path when the caller supplied one — or, for local, the target kind (uncommitted workspace, named branch, or commits), the branch that receives commits, and every remaining finding verbatim (ID, severity, `file:line`, anchor, explanation, recommendation).
- The active tlc-spec-driven feature folder (`.specs/features/<feature>/`) when the caller named one — `build-feature` always does; without it the worker writes no plan file.
- The files to load, by absolute path — never a skill-relative name, which one real worker spent ~1.2M tokens searching for: "Read `~/.claude/skills/code-review/references/fix-stage.md` and follow it; you are the fix worker — never call `Agent`." For a PR, also `~/.claude/skills/code-review/references/github-writes.md`; with Jira sync requested, `~/.claude/skills/code-review/references/jira-sync.md`. If `~/.claude/skills/code-review` does not exist, the skill is installed project-locally: give the same files under `.claude/skills/code-review/`, resolved to an absolute path.
- **Retry note**, whenever this dispatch comes from the continue-after-checkpoint entry (including a caller's resume and a user's "continue") or recovers a worker that failed outright — harmless when nothing was pushed: "This may be a retry. <What the failed worker already reported — PRs delivered, items done — when it reported anything; continue from there.> The PR branch may already hold commits an earlier fix worker pushed<, SHAs: …>. A thread whose fix is already on the branch is **fixed — its reply is still needed**; never reject it as already addressed. `deliver` skips any thread that already carries a delivered reply."
- Completion condition: every in-scope thread (or local finding) of every PR has a fixed / rejected / answered / blocked / unclear / routed outcome, and on a PR `deliver` has confirmed it.
- Return shape: the Report below — never finding bodies or diffs.
- Delegation depth: none.

A worker that fails outright is retried per [SKILL.md — Guardrails](../SKILL.md#guardrails), with the retry note above. Items that come back blocked are not a failure: no retry, and the rest of the run continues.

## PR Mode

With several PRs, run steps 0–10 for one PR at a time, in the order you judge best.

0. **Before starting:** `gh auth status` must succeed — otherwise stop: "No way to reach GitHub — install/authenticate `gh`." Then get onto the PR's head branch (`gh pr view <N> --json headRefName --jq .headRefName`):
   - **The prompt names a checkout path:** work there; it already has the branch.
   - **Otherwise:** check the branch out however you judge safest — `git worktree list` shows whether a checkout already has it (git refuses to check one branch out twice); a temporary `git worktree add` you create is removed once that PR is done, unless a blocker left state worth inspecting — say so instead. **Never switch branches in a checkout that has uncommitted changes.** In a checkout you set up, install dependencies once (the command in `docs/codebase/STACK.md`/`TESTING.md`, else the package manager's standard install).
1. **Fetch** threads with the query in [GitHub Writes](github-writes.md#fix-stage-fetch-threads). Skip resolved threads and threads on a pending review. At 100 threads, note that more may exist.
2. **Classify** each remaining thread from its full exchange:

   | Class | When | Action |
   |---|---|---|
   | answer-only | The current ask is a question | Reply with the answer; fix only if the answer implies a change; leave unresolved |
   | apply-as-directed | The current direction suggests an approach | Fix as directed, after the step-5 check |
   | auto-fix | No human reply on the thread | Fix, after the step-5 check |
   | routed to a person | Addressed to someone by name or handle | Nothing; record for the report |
   | unclear | Still unsure what it asks | Nothing, or a clarifying reply if you have a specific question; record for the report |

   A standalone comment not tied to a finding gets whichever class it resembles. A thread whose last comment is an earlier reply from this identity answering it, with nothing newer from anyone, is already answered: list it in `skipped` ("answered, awaiting reviewer") — replies from before `deliver`'s marker carry no marker, so `deliver` alone would reply again.
3. **Plan:** group auto-fix and apply-as-directed items into file clusters, in the order you will work them; write `fix-code-review.md` when a feature is active (`## Cluster: <file path>` per cluster, each item with thread id, class, `path:line`, one-line direction). Zero threads → report and stop.
4. **Re-fetch** the same query immediately — no approval gate — and silently drop any item no longer present, resolved, or changed. Drop a cluster that empties.
5. **Fix, item by item:** read the target file(s), judge whether the finding or direction still holds (Judgment above), then either edit + test-impact + targeted tests + one Conventional Commits commit, or reject / block with reasoning. Compose the answer-only and unclear replies now.
6. **Validation gate** — if any file was edited, committed or not: this project's build/typecheck command plus the tests covering every file this run touched (from `docs/codebase/STACK.md`/`TESTING.md`), and `git grep -nE '^(<{7}|={7}|>{7})( |$)' -- <touched files>`. This checks the composite state, which step 5's per-item runs never saw. It means those files' own tests, named explicitly — not `./...`, not an unfiltered suite. A failure is fixed here — with its own commit, or as a further uncommitted edit in an uncommitted workspace; one that can't be fixed stops the run as blocked.
7. **Push** to the existing PR branch if any commits survived the gate — before any reply claims a fix landed. Never open a new PR.
8. **Deliver:** compose every reply, then run `deliver` per [GitHub Writes](github-writes.md#fix-stage-deliver).

   | Outcome | Reply | Resolve |
   |---|---|---|
   | answer-only | The answer | No — the user resolves it |
   | blocked | Only a specific clarifying question, else skipped with reason | No |
   | fixed | What changed, why, and test impact | Yes |
   | rejected | The reasoning, and the approach taken instead if any | Yes |
   | routed to a person | None — skipped with reason | No |
   | unclear | A specific clarifying question, else skipped with reason | No |

9. **Read the script's JSON.** Non-zero exit → the run is blocked; carry the raw JSON into the report. Non-empty `unaccounted` → return to step 2 for those threads.
10. **Report** (below), taking every reply/resolve count from step 9's JSON.

## Local Mode

No threads, no replies, nothing pushed.

1. The findings are exactly those in the dispatch prompt.
2. **Uncommitted workspace:** apply fixes to the working tree, **commit nothing, and stage nothing** — a commit would sweep in the user's unfinished edits to the same files. **Named branch or commits:** `git status --porcelain` must be clean before anything else, whether or not a checkout is needed — dirty → stop and report the exact output, never stash; then check out the branch the prompt names if it isn't current, and make one Conventional Commits commit per fix.
3. Same Judgment, test impact, targeted tests, and validation gate as PR Mode steps 5–6 — the gate runs whenever a file was edited, committed or not.
4. Never push. Report what is ready to commit or push.

## Jira Ticket Sync

Opt-in only — when the user explicitly asks ("and update the Jira ticket"). Follow [jira-sync.md](jira-sync.md) around steps 5–9.

## Report

One section per PR when the run covered several.

- Outcomes by class: fixed, rejected (with reasons), answered, blocked (with options or reason), unclear, routed to a person (who).
- On a PR: the `deliver` JSON counts verbatim, and a note if 100+ threads were fetched.
- Commits (SHAs verbatim) and whether they were pushed; for an uncommitted workspace, the files edited.
- The validation gate's command and outcome.
- Test additions, updates, and removals, with a reason for each removal.
- With Jira sync requested: the ticket key synced (or that none could be resolved), and whether the start comment, the transition, and the completion comment landed.

## Examples

| Situation | Outcome |
|---|---|
| PR #128, the caller supplied the worktree that has the branch | Fix worker works in that worktree; 6 threads → 3 fixed, 2 rejected (one already handled on the branch, one unsound suggested approach), 1 answered and left open; gate passes on the four touched files' tests; 3 commits pushed; `deliver` exits 0 with `replied_confirmed: 6, resolved_confirmed: 5` |
| "fix the review comments on PR #201", checkout on `main` with uncommitted changes | Worker adds a temporary worktree for the PR branch and removes it after `deliver`; the user's `main` checkout never touched |
| Batch fix sweep over PRs #12, #9, #15 | One worker; it picks the order, finishes each PR through `deliver` before starting the next, and reports one section per PR |
| "fix Q1, H2" after a local review of uncommitted changes | Fix worker gets exactly Q1 and H2; edits left uncommitted; report lists the edited files |
| Thread "@bob, is this timeout still right?" | Routed to a person — skipped with reason in `delivery.json`, noted in the report |
| A finding asks to change a value the spec requires | Rejected, citing the spec line in the reply |
| Conversation holds an unposted report for PR #305, GitHub holds a submitted review with 2 comments | Only the 2 GitHub threads are in scope |
| PR #219 "OIQ-88: add retry backoff", user asks to update Jira | Jira start comment + "In Progress" before step 5, completion comment after step 9; 2 fixed, 1 rejected |
