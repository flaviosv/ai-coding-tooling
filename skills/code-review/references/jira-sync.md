# Jira Ticket Sync

Optional progress updates on a PR's linked Jira ticket during the fix stage. Loaded only when the user's request explicitly asks for it ("and update the Jira ticket", "move the ticket to in progress", "comment on the ticket when done") — never on a plain review or fix request, since not every repo or PR has a linked ticket.

---

Applies per PR — once inside a single fix worker, or once per PR inside each fix-sweep worker. PRs are never batched together, and each gets exactly one starting comment and one completion comment, never one per finding.

1. Resolve the Atlassian `cloudId` via `mcp__atlassian__getAccessibleAtlassianResources` — once per run, not once per PR.
2. Resolve the ticket key from the PR's title or description, keying off whatever ticket-key pattern appears (e.g. `OIQ-123`) — the project prefix varies by repo; never hardcode one. No key found → skip this PR's sync and note it in the report; never block or fail the fix run over it.
3. **Before fixing begins** (fix-stage step 5): post one comment via `mcp__atlassian__addCommentToJiraIssue` saying code review found issues on this PR (link it), listing each finding concisely (severity + one-line summary), and that fixes are starting.
4. Resolve the active-work transition by name via `mcp__atlassian__getTransitionsForJiraIssue` — never guess or hardcode a transition id; they are workflow-specific. If one matching an active-work status (commonly "In Progress") is available from the current status, apply it via `mcp__atlassian__transitionJiraIssue`; otherwise skip it and note that in the report.
5. Run the fix stage as normal, unaffected by the sync.
6. **After fixing completes** — whether every item was fixed or some were rejected, blocked, or unclear — post one comment on the same ticket summarizing what was fixed, what was left unfixed and why, and that the PR is ready for a new review round.
