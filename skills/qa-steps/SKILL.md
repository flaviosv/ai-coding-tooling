---
name: qa-steps
description: Generates a detailed, step-by-step Manual QA test plan for a Jira ticket, optionally enriched with a linked GitHub PR's diff and description. Fetches the ticket's description, comments, and attachments via Jira MCP, and the PR's diff via gh CLI when provided, then produces a structured plan (Setup, numbered Steps, optional technical spot-checks, Notes), shows it inline in chat, and — only after the user confirms — posts it as a comment on the Jira ticket — never on the PR. Use when the user says "give me the QA steps for", "what's the QA test plan for", "manual QA process for this ticket/PR", "how do I test this", or invokes /qa-steps. Do NOT use for writing automated tests or general code review (use code-review).
license: CC-BY-4.0
metadata:
  author: flaviostudart@gmail.com
  version: 2.1.1
---

# QA Steps

Turns a Jira ticket — optionally cross-referenced with a GitHub PR — into a precise, executable Manual QA test plan, and posts it as a comment on the ticket.

## Role

Adopt this persona for the entire skill: *"I'm a QA Engineer and I need to run manual validation on the informed PR / Jira ticket."* Write every scenario and step the way that QA Engineer would actually perform it by hand — concrete, hands-on actions on the real surface a user or caller touches — never an abstract test-case description a QA engineer would have to re-interpret before executing.

Every plan targets the team's **staging environment**, never the engineer's local machine. Never write a step, URL, host, or spot-check that assumes local infrastructure (`localhost`, a local dev server, `docker-compose`, a local `.env`, a locally-run DB) — a QA engineer executing this plan has no access to the reporter's machine and no reason to run one up. When a concrete host/URL is needed (an API call, a spot-check), use the project's staging domain/URL if it's known from `docs/codebase/` or the PR; otherwise use a clearly-labeled placeholder like `<staging-url>` rather than defaulting to a local one.

## Instructions

### Step 1: Resolve the ticket and (optional) PR

- Ticket key/URL is **required**. Take it from an explicit `/qa-steps <TICKET-KEY> [PR-number-or-URL]` argument, or from a ticket already referenced earlier in the conversation.
- If no ticket key/URL can be identified, stop and ask for it before doing anything else — never guess a ticket.
- PR is optional. If given, it only enriches the plan with real code-change detail; the ticket is still the source of truth for scope.

### Step 2: Fetch the Jira ticket

Use the Jira/Atlassian MCP tools (same integration `jira-assistant` uses) to fetch the ticket's summary, full description, all comments, and its attachment list (including inline images where the MCP exposes them).

- If the MCP is not connected/authenticated or the ticket isn't found, stop and tell the user — do not fabricate ticket content from the key alone.
- Read every comment, not just the description — acceptance criteria, edge cases, and repro steps are often clarified there rather than in the original description.

### Step 3: Fetch the PR (only if one was given)

```bash
gh pr view <number> --json title,body,url,files
gh pr diff <number>
```

Read the actual diff, not just the description — map QA steps to the real changed files, endpoints, and field names instead of guessing from the ticket text alone.

If `gh` fails (PR not found, not authenticated), proceed with a ticket-only plan and note in the output that PR-derived detail was skipped. For environments with more than one `gh` account logged in, see [gh Account Resolution](../../templates/gh-account-resolution.md) for scoping this call to the correct account — not applied here by default; adopt it only if this skill starts running somewhere that actually hits the multi-account problem.

### Step 4: Load project technical context (optional)

Check whether `docs/codebase/STACK.md` and `docs/codebase/ARCHITECTURE.md` exist in the current repo. If they do, use them to write one optional, clearly-labeled higher-confidence technical spot-check (e.g. a DB query in the project's actual DB technology, a `curl` against a real endpoint, a log grep) — against staging, never a local DB/server — never invent stack details that aren't backed by these files or the PR diff.

If these files don't exist, skip this step entirely; the plan stays behavioral-only. Never ask the user to run `architecture-evaluate` as a prerequisite — this step is opportunistic, not required.

### Step 5: Identify every distinct test scenario and its testing surface

From the ticket's description, comments, and (if present) the PR diff, enumerate every distinct testable scenario: the main fix/feature, edge cases called out in comments, and any regression explicitly mentioned. For tickets covering more than one scenario, give each its own numbered **Steps** block rather than collapsing them into a single flow — a plan that silently skips a scenario is worse than a longer plan.

For each scenario, decide its primary testing surface using this priority order — apply it per scenario, since one ticket can mix surfaces:

1. **UI interaction (default)** — if the scenario is reachable through a screen, page, component, or form, the primary Steps walk through the UI end-to-end. This is the default whenever a UI surface exists, even when the underlying fix is backend — QA validates through what a user actually sees and clicks.
2. **API calling (fallback)** — only when the scenario has no reachable UI (a backend-only ticket, an internal API, a webhook, a service-to-service change), the primary Steps become direct calls against the real staging endpoint (`curl`/Postman-style: method, URL, headers, payload, expected status code and response body) — never a `localhost`/local-dev URL.
3. **DB (secondary only)** — a DB check is never the primary way to test a scenario. It stays what Step 4 already produces: an optional, clearly-labeled spot-check that confirms the UI/API action actually changed persisted state.
4. **Manual test suite run / other CLI commands (conditional)** — include running the test suite or another CLI command as Steps only when the ticket/PR's own change is focused on that surface (e.g. a fix to a flaky test, a new CLI subcommand, a build/tooling script, a lint rule). If the CLI/test suite is incidental to a UI or API feature, leave it out entirely — never add a generic "run `npm test`" step as boilerplate.

### Step 6: Write the plan

Write each scenario's **Steps** block on the surface Step 5 assigned it — UI walkthrough by default, direct API calls only as the fallback, CLI/test-suite commands only when that's the scenario's own surface. Follow this exact structure (mirrors a proven format — do not compress it):

```markdown
# Manual QA test plan — <TICKET-KEY>[ (PR #<number>)]

<One sentence: what this verifies, in terms of the actual bug/feature — not "tests the changes in PROJ-217".>

## Setup
- <Accounts, browser/session setup, staging URL/environment, feature flags — whatever a tester needs before starting on staging.>

## Steps
1. **<Action-oriented step name>**
   - <Concrete sub-step: exact screen, field, value. Use realistic throwaway values (e.g. a `+qa` email alias), not vague placeholders.>
   - <...>
2. **<Next step>**
   - ...
   - Call out the **core assertion** and its **fail condition** explicitly on whichever step actually exercises the ticket's bug/feature — this is the step a QA reviewer must not skim past.

<n>. (Optional, higher-confidence) <Technical spot-check title>
   \`\`\`<language>
   <query/command from Step 4's project context>
   \`\`\`
   <What result to expect, and what a failure would mean.>

## Notes
- <Map specific steps back to the ticket's acceptance criteria / reproduction steps.>
- <Explicitly flag which step's failure should be treated as a blocker.>
```

Write every step so a QA engineer unfamiliar with the ticket could execute it without opening Jira or the PR — spell out exact UI paths, field values, and expected results; a vague step like "verify it works" is a failure of this skill, not an acceptable output.

Show the full plan inline in the chat response as plain markdown (not just a summary) — this is the primary deliverable of this step, before anything is posted anywhere.

### Step 7: Ask permission, then post to Jira

After showing the plan, ask the user whether to post it as a comment on the ticket. Do not post automatically and do not skip the question. Never offer to post it to the PR.

- If the user confirms, post the full plan as a comment on the ticket via the Jira MCP. Confirm to the user that it was posted and include the comment link if the MCP returns one.
- If the user declines, or asks for changes first, stop there — the plan already shown in chat stands as the deliverable; revise and re-show it if they ask for edits, then ask again before posting.
- If posting fails after the user confirms (permissions, MCP error), tell the user explicitly that it was **not** posted, with the reason, so they can post it manually if needed.

## Examples

### Example 1: Ticket + PR

User says: `/qa-steps PROJ-217 175`

Actions: Fetch PROJ-217 via Jira MCP (description, comments, attachments) → fetch PR 175 via `gh pr view`/`gh pr diff` → load `docs/codebase/STACK.md` if present → identify scenarios (main fix + any edge cases from comments) and assign each its surface (UI walkthrough by default, API-only fallback if the diff shows no UI surface) → write the plan, including an optional DB spot-check if project context supports it → show the plan in chat → ask whether to post it to PROJ-217 → on confirmation, post it and share the comment link.

### Example 2: Ticket only, natural language

User says: "What's the QA test plan for PROJ-88?"

Actions: Fetch PROJ-88 via Jira MCP → no PR given, so skip Step 3 and any diff-derived detail → write a behavioral-only or context-only plan depending on whether `docs/codebase/` exists → show it in chat → ask whether to post it to PROJ-88 → on confirmation, post it.

### Example 3: No ticket identifiable

User says: "Give me the step-by-step QA process for this."

Actions: No ticket key/URL in the argument or recent conversation → ask for the ticket key or URL before doing anything else. Do not proceed on a guess.

## Troubleshooting

### Jira MCP not connected or ticket not found

Stop immediately and tell the user. Do not write a plan from the ticket key alone — a plan built on a guessed description is actively misleading.

### `gh` not installed, not authenticated, or PR not found

Proceed with a ticket-only plan. State plainly in the chat response (not just buried in the plan) that PR-derived detail was skipped and why.

### Ticket has no clear acceptance criteria

Ask the user to clarify scope rather than inventing acceptance criteria. If the title alone is enough to infer a reasonable scope, you may proceed, but say explicitly in the plan's summary line that scope was inferred from the title.

### Posting to Jira fails

Tell the user clearly that it was not posted, with the error reason, so they can post it manually if needed. The plan is already shown in chat from Step 6, regardless of posting outcome.
