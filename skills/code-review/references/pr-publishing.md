# PR Publishing

How a PR review reaches GitHub: the publishing worker for `post: true`, holding findings with `findings_path`, publishing a user's selection after a local report, and Publish Mode. Loaded only when a run will write to GitHub or to `findings_path`. The write itself is always [Posting Mechanics](posting-mechanics.md).

---

## Who Does the Work

A PR run with `post: true` or `findings_path` executes Steps 2–9 in an isolated worker, so the diff, dimension findings, and comments arrays never enter a caller's context — only the compact result (below) does.

**The test for whether to dispatch is mechanical, never a judgment about who dispatched you or why: if you are executing this skill as a subagent at all — started via the `Agent` tool for any reason, including `build-feature`'s Step 11 wrapper or a Batch Mode per-PR agent — do the work inline and dispatch no worker.** Being a subagent *is* the isolation; do not reason about whether some other context "already isolated" you. Only a root context that is not itself a subagent — a user's own live conversation — dispatches the worker. A wrapper holding nothing but this one dispatch has no context to protect, and the extra hop cost 715k–820k tokens and 20–24 minutes of idle relay on every measured `build-feature` run. (Same mechanical form as `fix-review`'s AD-006, adopted after a self-classifying version was misread one level deeper than it was tested.)

A plain `post: false` PR run with no `findings_path` runs in the current context, like a local review — its report is meant for the user to read.

### Dispatching the worker

One `Agent` call: `subagent_type: general-purpose`, `model: sonnet`. The prompt follows the `subagent-dispatch` contract — completion condition: the PR's pending review posted with every finding from every active scope (or findings written to `findings_path` when held); return shape: the compact result below, never the findings report; delegation depth: the worker dispatches Step 6's dimension agents, nothing deeper. It tells the worker to invoke `code-review` via the `Skill` tool with PR #N, the run's `scope`, and `post: true` (or the `findings_path`) — as a subagent it runs everything inline. The prompt must also **carry** two things rather than name them:

1. **The absolute path of `posting-mechanics.md`**, with an instruction to read that whole file before posting. A worker told to "post via Posting Mechanics" without the path went hunting — ~1.2M tokens and 8 round-trips of `find` probes plus a full re-read of the skill file. Never `find` for it: the installed skill directory is a symlink and the search surfaces confusing near-matches.
2. **The `subagent-dispatch` wait protocol instruction**, restated — the worker fans out dimension agents of its own, and waiting on them is where this skill's largest avoidable cost was measured: one run spent 31 consecutive turns on `echo "waiting"` (4.36M tokens, 15.8% of its budget) for zero output. When waiting on a dispatched agent, end the turn with one line of plain text and no tool call. Never `sleep`, `echo`, or `ToolSearch` for a waiting tool; `Monitor` waits on a clock, never on an agent.

**The worker itself fails outright** (PR not found, auth failure, skill-invocation error) → retry once with a fresh worker. A second failure → stop and report it; never fabricate a finding count or claim a review was posted.

Track the worker's name against its PR number for the rest of the conversation — a later "new commit landed on PR #N" routes to it via `SendMessage` (see [Batch Mode — New Commits or Comments](batch-mode.md#new-commits-or-comments-after-dispatch); the same routing applies to a single-PR worker). Every `Agent` dispatch is asynchronous, so this worker is as long-lived and routable as a Batch Mode one.

## Publishing Flow

After Step 8 consolidation (duplicates already collapsed):

1. **Full failure** — every dimension agent in every active scope failed even after its retry: post nothing, write nothing. Return every failure reason and stop; never proceed as if a review was posted. A partial failure publishes what succeeded, with the failed dimensions named in the result.
2. **Holding (`post: false` with `findings_path`):** write the comments array (Comment Shape in Posting Mechanics, `anchor` included) and the complexity banner to `findings_path`. Don't check for or touch any pending review. Return `awaiting_approval: true`, the counts, the banner, and the path used. A `findings_path` is never invented — if a caller asks to hold findings without one, stop and ask.
3. **Publishing (`post: true`):** post via [Posting Mechanics](posting-mechanics.md) — every finding, unfiltered. Never filter by severity, never ask per finding, never stop to ask how to handle an existing pending review of this identity (appending to it is always right), and never append an empty array.

### Compact result (the worker's entire return)

- PR URL; pending-review posted yes/no (or `awaiting_approval: true` + `findings_path`).
- The complexity banner verbatim. A Complex-tier caveat is relayed with its **actual wording** ("findings are best-effort and may be non-exhaustive — consider splitting this PR"), never a label saying a caveat exists; it is a standard part of every Complex banner, not a run-specific warning. The banner is informational — nothing here changes how a scope routes its own execution.
- Finding counts per scope, with a per-severity breakdown, and the single most important finding in one line.
- **Three counts that must survive every relay hop** — report `0` for each when none, since a run that doesn't say is indistinguishable from one that never looked: same-root-cause clusters **collapsed** (Step 8), findings **re-anchored** (Posting Mechanics 3a), findings **unpostable** (3a). A downstream consumer (`fix-review`, or a human) cannot trust a comment's `file:line` without them. The contract is otherwise closed, and a relay obeying it literally drops anything not named — which is exactly how one real run's 8 re-anchored findings, including a Critical, disappeared between the worker and the user.
- Whether an existing pending review was appended to, and how many comments carried over; any batch retried or posted out of sequence.
- Any dimension marked not executed, with its reason.

### Report to the user

"PR #N — code: Complex (32 files, 1,840 lines) · Parallel, 4 agents · 7 findings; tests: Medium (9 test files, 420 lines) · Single agent · 2 findings. 9 findings published as one pending review — submit manually on GitHub when ready." Add "3 comments carried over from an already-pending review, plus 9 new — 12 total" when appending, and the three counts. On a full failure, report the PR URL and every failure reason — never claim findings were published.

## Publishing After a Local Report

A `post: false` PR report ends by offering to publish. When the user answers — "post all", "post all P0", "post all Critical", "post 1, 3, 5", or "post A1, V2" — post exactly that selection via Posting Mechanics from the report already in this conversation. Never re-analyze the PR to do it.

## Publish Mode

Entered on an explicit request to publish findings held by an earlier `findings_path` run (e.g. "publish code-review findings for PR #N from `<findings_path>`"). Never re-runs the review.

1. `gh auth status` must succeed, or GitHub MCP tools must be available — neither → stop: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server." Then read `findings_path` — given explicitly, never inferred. Missing or unreadable → stop and report; never fabricate a findings set or fall back to re-analyzing.
2. Post the held comments array via Posting Mechanics — unfiltered, exactly as held, regardless of how long ago it was assembled.
3. Report in the same form as above, using the banner read from the file.

The caller owns the `findings_path` file's lifecycle; this skill reads it once and never cleans it up.
