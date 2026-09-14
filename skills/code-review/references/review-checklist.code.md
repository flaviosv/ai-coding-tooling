# Code Review Checklist

Generic checklist for reviewing code changes across any technology stack.
Use this as a baseline — technology-specific checklists extend this file.

---

## Architecture & Design

- [ ] Changes follow the architectural layers defined in `ARCHITECTURE.md`
- [ ] Layer responsibilities are respected — no logic in the wrong layer
- [ ] No new patterns introduced that contradict existing conventions
- [ ] Separation of concerns is maintained
- [ ] Reusable abstractions used — no reimplementing functionality that already exists
- [ ] API design is consistent (naming, response shape, status codes, error format)
- [ ] Breaking changes are intentional and documented
- [ ] Dependencies are injected — business logic does not construct concrete services or infrastructure objects inline
- [ ] Middleware and interceptor responsibilities are narrow — each handles one cross-cutting concern and does not leak into adjacent layers

## Scope & Simplicity

- [ ] Changes do not include unrequested features, refactors, or speculative additions
- [ ] No abstractions or helpers created for a single use — YAGNI applies
- [ ] No unnecessary configurability or "flexibility" that was not asked for
- [ ] Adjacent code outside the task's scope has not been modified or reformatted
- [ ] Dead code **introduced or orphaned by these changes** is removed — pre-existing dead code is noted but NOT expected to be removed unless explicitly requested
- [ ] Code volume is proportional to the problem — if a simpler solution exists, flag it
- [ ] Every changed line traces to a stated requirement — flag anything that doesn't

## Code Quality

- [ ] Code is readable — intent is clear without needing comments to explain what it does
- [ ] Naming follows conventions from the loaded coding style references (variables, functions, classes, files)
- [ ] No dead code introduced or orphaned by these changes — unused imports, variables, functions created by this diff are removed
- [ ] No unnecessary duplication — shared logic is extracted appropriately
- [ ] Error handling is present and meaningful — failures are caught and communicated correctly
- [ ] No debug artifacts left behind (`print`, `console.log`, `TODO: remove`, etc.)

## Documentation

- [ ] Public API documentation present where the language/framework standard requires it (see `clean-code-checklist.code.md` Comments)
- [ ] Parameter types and return values described where not obvious from types
- [ ] Inline comments explain *why*, not just *what*
- [ ] `README` or usage docs updated if behaviour, configuration, or setup changed
- [ ] Exceptions or errors that callers must handle are documented in the function signature or docstring
