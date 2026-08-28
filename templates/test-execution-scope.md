---
name: test-execution-scope
description: Shared decision procedure for how much to verify after a change — which tier of tests to run, when to stop, and how to state that scope in a subagent prompt — for any skill that ends a change with verification.
type: template
---

## Why this exists

Verification has an asymmetric felt cost. "Did I verify enough?" hurts visibly when the answer is no — a bug ships. "Did I verify too much?" costs nothing anyone in the turn can feel: suite minutes and tokens are invisible from the inside. Left to judgment, that asymmetry ratchets one way, every time.

Measured across seven real merge-conflict sessions:

| What happened | Result |
|---|---|
| `build-feature` Step 16 dispatched a subagent told to *"run the project's gate checks"* for a merge whose only conflict was `docs/codebase/STRUCTURE.md` | `go build/vet/test ./...` + `npm run typecheck` + `npm run lint` |
| A session ran the three integration tests actually covering its change — **44 passed** — then continued: *"Now let's run the full unit + integration suite to be thorough"* | `npm run test:unit` (**1740 tests**) + `npm run test:integration` |
| A session said *"let's run the relevant test suites"* and resolved "relevant" to the whole directory | `npx vitest run tests/unit` |
| A `.md`/`README`-scoped conflict resolution | `go build/vet/test ./...`, `npm run typecheck/lint/test/build` |

Two of those escalations happened **after a targeted run had already passed**. None of them caught anything.

The contrast is the finding: when the intended scope was stated in the prompt, compliance was **2 of 2** — one session ran two named test files, one ran nothing at all. When it was left to a general preference, **3 of 5** escalated to a full-tier suite. Scope holds when it is stated where the work is dispatched, and drifts when it is only implied.

## Tiers

Pick by what the change can actually affect, not by how important it feels.

| Tier | When | Run |
|---|---|---|
| **Docs-only** | The change touches only `.md`, `docs/`, `.specs/`, comments, or config with no runtime effect | **No tests.** Verify the content is correct, no conflict markers remain, tree is clean |
| **Punctual** | Confined to a specific function, module, or handful of files | Only the test file(s) or targeted pattern covering exactly that code |
| **Cross-cutting** | Shared modules, contracts between components, or several subsystems at once | Build/typecheck/lint, plus the suites covering each affected area. Full suite only when the touched surface genuinely spans it |

When a change sits between two tiers, take the narrower one and widen only if the blast radius turns out to be broader than it looked.

## The stop rule

**Once the run for the chosen tier passes, verification is done. Do not widen.**

Widening after a green run requires naming the specific risk the wider run would catch and why the narrower one could not. If that risk cannot be named, the wider run is not warranted. *"To be thorough"*, *"to be safe"*, and *"while I'm here"* are not risks — they are the failure this rule exists to stop.

This cuts both ways, and so does the quality bar behind it: a staff engineer rejects over-verification as readily as under-verification. Re-running a suite that just passed, or running a suite the change provably cannot affect, is waste they would flag in review — not diligence.

## Merges and conflict resolution

Scope by what the merge **brings in**, never by the size of the conflict and never by the commit count. Those are two separate questions:

- *What did I resolve by hand?* — drives how carefully the resolution is reviewed.
- *What does the merged range change?* — drives the tier.

A merge whose entire merged range is documentation is **docs-only**, however many commits it spans. A merge that brings in code is at minimum **build/typecheck/lint**, even when every conflict was in a `.md` file — because auto-merge produces semantic breakage that carries no conflict markers at all.

That case is real, not hypothetical: one merge reported exactly one conflict (`docs/codebase/STRUCTURE.md`) while the cleanly auto-merged Go files did not compile — `application.StatusLabel`/`AllStatuses` and `jobwebsite.AllWebsiteTypes` undefined, plus a `WebsiteType` vs `*WebsiteType` mismatch introduced by parallel work on the target branch. "No conflict markers" proves lines did not overlap, not that the result builds.

Note what actually caught it: the **compile and typecheck**, which are cheap and bounded. The full test suite that ran alongside them added nothing. Reach for build/typecheck/lint on any code-bearing merge; reach for the suites only per the tiers above.

## Stating scope when delegating

A subagent resolves an unqualified verification instruction to the **widest tier available to it**. That is exactly how *"run the project's gate checks"* became `go test ./...` plus a frontend typecheck and lint for a one-file documentation conflict.

So, in every subagent prompt that ends in verification:

- Never write *"run the gate checks"*, *"run the tests"*, or *"verify it works"* unqualified.
- Name the tier and what it covers — *"run only the tests covering `internal/orders`"*, *"docs-only change: run no tests, confirm no conflict markers remain"*.
- Say the stop rule applies, whenever the subagent has a suite it could reach for.
- Require the tier it actually ran to come back in its report, so an escalation is visible instead of silent.

## Out of scope

This template governs **ad-hoc verification**: merges, conflict resolution, review fixes, one-off changes, and anything else not already covered by a skill that defines its own gates.

It does **not** override skills that own their gate tiers. `tlc-spec-driven` is the one that matters here, and its gates stand exactly as written:

- `references/implement.md` — the per-task gate check, mandatory at the task's own quick/full/build tier
- `references/tasks.md` — the Build tier at phase completion (`build + lint + all tests`)
- `references/validate.md` — the build-level gate and the discrimination sensor that follows it

Those are a spec-verification cycle with its own contract. Do not narrow them by citing this template, and do not restate them here.
