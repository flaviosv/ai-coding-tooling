# STAR Method Reference

The gold-standard structure for behavioral/experience interview answers at senior+ levels (Meta, Amazon, Google, Stripe, Figma-style loops), also usable to structure a system-design decision defense.

---

## Structure

- **S — Situation**: the context/problem, concrete enough that a stranger could picture it.
- **T — Task**: the candidate's specific responsibility or goal within that context.
- **A — Action**: what the candidate actually did — decisions made, trade-offs weighed, people influenced.
- **R — Result**: the measurable outcome (time saved, cost reduced, reliability gained, adoption achieved).

A strong answer does not need four rigid, separately-labeled paragraphs — S/T often blend into one framing sentence. What matters is that all four elements are recoverable from the answer, in some order, with the Result quantified wherever possible.

## What a strong STAR answer demonstrates

- **Clarity** — the problem is stated before the solution.
- **Ownership** — the candidate is the owner of the result, not just of code written.
- **Impact** — outcomes are quantified, not just described.
- **Leadership** — influence on technical decisions across people/teams shows up, even without a formal title.

## Example

Scenario: migrating 290 monolithic JSON config files to a normalized schema.

// Bad — describes the work, proves nothing
"I migrated the config to a database and added validation."

// Good — proves impact, systems thinking, and influence
"We had 200+ partners across 400 environments who couldn't update configs safely — any change risked leaking data across tenants or breaking dependent systems. I led the migration to a normalized schema with per-tenant validation; config change time dropped from months to minutes, and we haven't had a cross-tenant leak since."

## Common gaps to flag when scoring

- **No Situation** — jumps straight to actions with no context, forcing the listener to guess the stakes.
- **No Task** — unclear what the candidate's specific role/responsibility was versus the team's.
- **Action described as "we" throughout** — ownership is unclear; the evaluator should distinguish individual contribution from team credit, without penalizing legitimate collaborative framing.
- **No Result, or an unquantified Result** — "it went well" instead of a number or concrete before/after.
- **Technical narrative only** — describes what was built but never why it mattered or who it affected.
