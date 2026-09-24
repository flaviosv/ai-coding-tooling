# Azure DevOps Writes

Every read and write this skill makes on an Azure DevOps PR — PR metadata, posting findings, fetching threads, replying and changing thread status — goes through `scripts/ado_review.py`. This file covers what you compose, how to invoke the script, and what its output means. Loaded by the review worker and the fix worker on an Azure DevOps PR. Azure DevOps Services (`dev.azure.com`) only.

---

## Rules

- **Never hand-roll an Azure DevOps call.** No `az repos`, `az devops invoke`, `curl`, or REST call of your own. If the script is missing or exits `2`, the run is **blocked** — report its raw JSON.
- **The script's JSON is the result.** Every count you report is quoted from its stdout, never from what you intended to send. Exit `0` confirmed, `1` partial (report exactly which items), `2` fatal (nothing confirmed).
- **There is no pending review.** A thread is public, and notifies the PR's people, the moment `post` creates it. So `post` runs only when the findings are final: straight after the review with `human_review: false`, or after the checkpoint page with `true` ([ADO Checkpoint](ado-checkpoint.md)). A review worker with `human_review: true` never runs `post`.
- **Never create work items.** Every finding is a file thread.
- **Never delete** a thread or comment, and never vote on the PR. Duplicates `post` or `deliver` report are reported for a human to remove.
- **Never post placeholder, test, or probe content to a real PR.** Use `--dry-run` to check a run before any write.
- **Throttling** is handled by the script: it honors `Retry-After` at most twice per run, then fails the request. Never work around a slow run with a bulk call.
- **Credentials:** `az login` (the script asks `az` for a token), else a PAT in `AZURE_DEVOPS_EXT_PAT`. Neither → exit `2` naming both; tell the user to run `az login`. Never print a token.
- Write every input file with the `Write` tool — never a shell heredoc.

## Script Location

`~/.claude/skills/code-review/scripts/ado_review.py`; if and only if that path does not exist, `.claude/skills/code-review/scripts/ado_review.py`. Never `find` for it. `<org> <project> <repo>` come from `detect_remote.py`'s JSON in the same directory ([SKILL.md — Step 1](../SKILL.md#step-1-entry-detection)); quote a project name that contains spaces.

## PR and Diff

`python3 <script> pr <org> <project> <repo> <N>` returns `title`, `description`, `source_branch`, `target_branch`, `source_commit`, `target_commit`, `iteration`, `pr_url`, and `files` (path and change type). A non-zero exit on a PR that doesn't exist → stop and report, never guess another number.

The diff comes from git: `git fetch origin <source_branch> <target_branch>`, then `git diff origin/<target_branch>...origin/<source_branch> -- $EXCLUDE` (three dots: against the merge base, as the PR shows it). If `git rev-parse origin/<source_branch>` is not `source_commit`, fetch again once; still different → say the PR moved while reviewing and use the fetched head.

## Comment Shape

Identical to GitHub's. Each finding becomes one comment: `path` (repo-relative), `line`, `body`, `anchor`, and in `findings.json` also `id`, `severity`, `title`.

```
**[<Zone/Dimension> — <Finding ID>, <Severity>]** <explanation>

**Recommendation:** <concrete, actionable fix>
```

- Zone and Finding ID are carried verbatim from the report — never renumbered.
- The `Recommendation` line is mandatory.
- **`line`** is the line in the file at the PR's source commit, never a diff offset; **`anchor`** is that line's exact text, one line, trimmed. A finding whose line can't be resolved returns `line: null` with `anchor` populated. **Never `Read` whole source files to check line numbers** — `post` checks every anchor itself.

## Review Stage

Both files live in `<tmp>/code-review/<org>-<project>-<repo>-pr<N>/`, where `<tmp>` is the system temp directory (`python3 -c "import tempfile; print(tempfile.gettempdir())"`) and spaces in the name become `-`. Save the PR diff there as `pr.diff` (the whole `git diff` above, before splitting by scope). Zero findings → write nothing and return zero counts.

**`human_review: true` → `findings.json`, never `post`.** Every finding left after Step 8's duplicate collapse, unfiltered:

```
{"org": "<org>", "project": "<project>", "repo": "<repo>", "pr": <N>,
 "pr_url": "<pr_url from `pr`>", "pr_title": "<title>",
 "comments": [{"id": "S1", "severity": "High", "title": "<finding title>",
               "path": "src/a.py", "line": 18, "body": "**[Security — S1, High]** ...", "anchor": "..."}]}
```

Return `findings_json_path` and `pr_diff_path`; the root runs the checkpoint page from them.

**`human_review: false` → `post`.** Write the same file as `post.json` (the extra fields are ignored), then:

`python3 <script> post <post_json_path>`

What it does: resolves the identity and the PR's latest iteration; lists the files it changed; checks each `anchor` against the file at the source commit — correcting `line` when the text sits elsewhere, posting at the given `line` as **`anchor_unverified`** when the text is found nowhere (only a comment with no `line` becomes **unpostable**); marks a comment on a file the PR didn't change, or deleted, **unpostable**; skips comments whose path, line, and body are already a thread this identity opened; creates one thread per comment, 1 s apart; re-fetches the threads and retries once only comments whose request failed; reconciles.

| Output field | Meaning |
|---|---|
| `already_present` | Already a thread from this identity — not posted again |
| `anchor_corrected` | Line changed to where the anchor text actually is |
| `anchor_unverified` | Posted at the given line, but the anchor text wasn't found — carry into the report so the line can be checked |
| `duplicates_found` | Same comment on the PR more than once — report, never delete |
| `errors` | Per-request failures; a `request_failed` entry's comment was retried once |
| `missing` | Intended but not on the PR after the retry |
| `posted_confirmed` | Threads confirmed by the final fetch |
| `unpostable` | Not posted (file not changed or deleted by the PR, no `line` and anchor not found) — carry every one into the report by `path:line` |

`--dry-run` runs everything up to the first write and reports `would_post`. Exit `2`, or a non-empty `missing`, is a posting failure: the root re-runs `post` once from the same file (SKILL.md Stage 2). Nothing on Azure DevOps is re-anchored: it accepts a thread on any line of a changed file.

## Fix Stage: Fetch Threads

`python3 <script> threads <org> <project> <repo> <N>` returns `identity` (`id`, `name`) and every in-scope thread: a text thread (not a system message) whose status is `active` or `pending`, with `id`, `status`, `path`, `line`, and every comment in order (`id`, `author_id`, `author`, `body`). Read every comment of a thread. A thread a human deleted or already closed is not in the list, which is what makes "only what remains is a finding" hold.

## Fix Stage: `deliver`

1. Write `delivery.json`:
   ```
   {"org": "<org>", "project": "<project>", "repo": "<repo>", "pr": <N>,
    "threads": {"17": {"body": "<reply text>", "resolve": "fixed"}},
    "skipped": {"18": "routed to Alice — awaiting her answer"}}
   ```
   Keys are thread ids as strings. `resolve` is the status to set once the reply is confirmed: **`fixed`** for a fixed finding, **`wontFix`** for a rejected one, `false` to leave the thread active. **`threads` and `skipped` together must account for every in-scope thread.**
2. `python3 <script> deliver <delivery.json> --dry-run` — checks coverage before any write.
3. The same command without `--dry-run`.

What it does: fetches a baseline; replies to each thread under its first comment, 1 s apart, each reply ending in a hidden marker (`<!-- code-review:deliver -->`); fetches again and confirms each reply landed exactly once; sets the status only on threads whose reply is confirmed; fetches again to confirm the status. Re-running after a partial failure is safe — it skips threads that already carry a marked reply from this identity.

| Output field | Meaning |
|---|---|
| `duplicates_found` | A thread carries more than one marked reply from this run |
| `in_scope` | Active or pending text threads on the PR |
| `replied_confirmed` / `resolved_confirmed` | Confirmed by re-fetch |
| `reply_missing` / `resolve_not_confirmed` | Intended but not on Azure DevOps |
| `unaccounted` | In-scope threads in neither map — go back and classify them; never report around them |
| `unknown_threads` | Ids in `threads` that don't exist on the PR |
