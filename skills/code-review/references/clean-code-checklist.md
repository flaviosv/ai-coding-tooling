# Clean Code Review Checklist

Focused checklist for evaluating clean code principles. Use alongside `review-checklist.md` — this file goes deeper on readability, naming, structure, and maintainability.

---

## Naming

- [ ] Names are intention-revealing — you can understand purpose without reading the implementation
- [ ] No single-letter variables except conventional loop counters (`i`, `j`) or math formulas
- [ ] No misleading names — the name accurately reflects what the thing does or holds
- [ ] No noise words that add no meaning (`data`, `info`, `manager`, `processor`, `handler` without context)
- [ ] Boolean names read as predicates (`isActive`, `hasPermission`, `canEdit`)
- [ ] Functions named as verbs or verb phrases (`fetchUser`, `calculateTotal`, `validateInput`)
- [ ] Classes and types named as nouns (`UserRepository`, `OrderSummary`, not `ProcessOrders`)
- [ ] No abbreviations unless universally understood in the domain (`url`, `id`, `api`)
- [ ] No encoding type into names unless required by the language (`strName`, `arrItems`)

---

## Functions

- [ ] Functions do one thing — if you can describe it with "and", it does too much
- [ ] Functions are short — a function that requires scrolling is a candidate for extraction
- [ ] Functions operate at a single level of abstraction — no mixing high-level logic with low-level detail
- [ ] No flag arguments (`processOrder(order, true)`) — split into separate functions instead
- [ ] No output arguments — functions return values rather than mutating arguments
- [ ] Functions with side effects make them explicit in the name or contract
- [ ] No more than 3 parameters where avoidable — consider a parameter object for more
- [ ] Early returns used to avoid deeply nested conditionals (guard clauses)
- [ ] Cyclomatic complexity is low — flag functions with many `if`/`else`/`switch` branches (aim for ≤ 10); consider extracting into smaller functions

---

## Classes & Modules

- [ ] Single Responsibility — each class or module has one reason to change
- [ ] Classes are small — large classes are a sign of multiple responsibilities
- [ ] Instance variables are minimal and meaningful — no unused or redundant state
- [ ] Methods that don't use instance state are candidates for static methods or standalone functions
- [ ] No "god objects" that know too much or do too much
- [ ] Dependencies are explicit — no hidden globals or service locators
- [ ] Interface segregation — no forcing callers to depend on methods they don't use
- [ ] Law of Demeter respected — avoid deep method chains through unrelated objects (e.g. `obj.getA().getB().doThing()`). Each unit should have limited knowledge of other units

---

## Comments

- [ ] No comments that restate what the code already says
- [ ] No commented-out code left in the codebase
- [ ] No misleading or outdated comments — comments that contradict the code are worse than none
- [ ] Comments explain *why*, not *what* — the code explains what, comments explain the intent or constraint
- [ ] TODO/FIXME comments reference a ticket or issue — not open-ended

---

## Control Flow

- [ ] No deeply nested conditionals (more than 2–3 levels) — flatten with early returns or extraction
- [ ] Complex boolean expressions extracted into named variables or functions
- [ ] Switch/match statements are not spread across the codebase for the same type — centralize dispatch
- [ ] No magic numbers — numeric literals that carry meaning are named constants
- [ ] No magic strings — string literals used as flags or identifiers are constants or enums

---

## Side Effects & State

- [ ] Functions with side effects are clearly separated from pure computation
- [ ] Mutable state is minimized — prefer immutable data where practical
- [ ] Global or shared mutable state is avoided or explicitly justified
- [ ] Operations that look like queries do not have hidden mutations

---

## Boundaries & Abstractions

- [ ] No leaking internal implementation details through public interfaces
- [ ] Abstractions represent domain concepts, not just technical layers
- [ ] No inappropriate intimacy — classes don't reach into each other's internals
- [ ] Dependency direction flows toward stability — volatile code depends on stable code, not the reverse

---

## Error Handling

- [ ] Errors are not silently swallowed — all caught exceptions are handled or re-raised with context
- [ ] Error types are specific — avoid catching broad exceptions unless explicitly justified
- [ ] No returning `null`/`nil`/`undefined` to signal absence when a typed result or exception is clearer
- [ ] Error messages are actionable — they tell the caller what went wrong and ideally how to fix it

---

## DRY & Duplication

- [ ] No copy-pasted logic — duplicated code is extracted into a shared function or module
- [ ] Shared logic is not duplicated across layers (e.g. same validation in controller and service)
- [ ] Duplication of structure (not logic) is acceptable — don't abstract prematurely

---

## Formatting & Consistency

- [ ] Code style is consistent with the rest of the file and project conventions
- [ ] Blank lines used to group logically related statements, not randomly
- [ ] Related code is close together — the newspaper rule: code reads top-to-bottom like a newspaper article. High-level abstractions and callers appear at the top; low-level details and callees appear below
- [ ] No inconsistent levels of indentation or formatting that makes structure hard to scan
