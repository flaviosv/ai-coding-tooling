---
name: gh-account-resolution
description: Shared gh CLI account resolution — identify and scope every gh/git remote call to the correct authenticated account when more than one is logged in, without relying on gh's mutable global active-account state.
type: template
---

## Why this exists

`gh auth status` can have more than one account logged in at once, with exactly one marked active. `gh auth switch` changes that active account globally, for every process on the machine — a parallel session (another Claude Code session, a script, a human terminal) can flip it between two of your own `gh` calls. A skill that assumes "the active account" stays put across a multi-step run can silently act as the wrong identity partway through.

## Resolution

Run this once per skill invocation, not once per `gh` call — cache the result for the rest of the run.

1. **List logged-in accounts**: `gh auth status` (parse the account logins it reports; ignore which one is marked active — that flag is exactly the state this resolves around, not evidence of which one to use).
2. **Match by email** against a configured owner email (the caller supplies this — e.g. from project config or the user's known email; there is no universal default). For each candidate account: `GH_TOKEN=$(gh auth token --user <login>) gh api user --jq .email`. An account with no public email returns nothing — that's a non-match, not an error.
3. **Exactly one match** → that's the resolved account. Cache its **login** for the rest of the run.
4. **Zero or more than one match** → stop and report the ambiguity. Do not guess which account to act as — this is exactly the kind of outcome-changing ambiguity that warrants a human's input rather than a silent pick.

## Using the resolved account

Scope every `gh` call for the rest of the run with `GH_TOKEN=$(gh auth token --user <resolved-login>) gh ...` (or export it once for the run's shell scope) — never `gh auth switch`, which would mutate the same global state this resolution exists to route around, and would affect other processes on the machine too.

For `git` operations against a remote (`push`, `fetch`) that need the same identity, the account's token doubles as the `git` credential when the remote uses HTTPS; if the remote is configured over SSH, this resolution only covers `gh`/GitHub-API calls — SSH identity is a separate, key-based concern outside this template's scope.

## What never gets persisted

The resolved **login** (e.g. `flaviosv`) may be written to any state file that needs to survive across invocations (a resumable run's progress file, for instance). The **token** itself — from `gh auth token` — is never written to disk, logged, or printed. Re-derive it fresh via `gh auth token --user <login>` whenever it's needed; treat it as a value that exists only for the duration of the command it scopes.
