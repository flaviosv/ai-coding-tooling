# Code Review Checklist

Generic checklist for reviewing code changes across any technology stack.
Use this as a baseline — technology-specific checklists extend this file.

---

## Security

- [ ] No hardcoded secrets, credentials, or API keys
- [ ] All user-supplied input is validated and sanitized at system boundaries
- [ ] Authentication is enforced on all protected endpoints or operations
- [ ] Authorization checks are in place — users can only access what they are permitted to
- [ ] Sensitive data is not exposed in error messages, logs, or API responses
- [ ] Injection risks are mitigated (SQL, command, template, path traversal, etc.)
- [ ] Dependencies used securely — no known-vulnerable patterns
- [ ] Insecure defaults avoided (e.g. debug mode off, CORS not wildcard in production)

---

## Performance

- [ ] No unbounded data fetches (pagination or limits applied)
- [ ] No N+1 patterns — related data fetched efficiently in bulk
- [ ] No unnecessary blocking operations on hot paths
- [ ] No redundant computations inside loops
- [ ] Caching applied where data is expensive to compute and changes infrequently
- [ ] Resource leaks avoided — connections, file handles, and streams are properly closed
- [ ] Heavy or long-running operations deferred (async, queue, background job) where appropriate

---

## Architecture & Design

- [ ] Changes follow the architectural layers defined in `ARCHITECTURE.md`
- [ ] Layer responsibilities are respected — no logic in the wrong layer
- [ ] No new patterns introduced that contradict existing conventions
- [ ] Separation of concerns is maintained
- [ ] Reusable abstractions used — no reimplementing functionality that already exists
- [ ] API design is consistent (naming, response shape, status codes, error format)
- [ ] Breaking changes are intentional and documented

---

## Code Quality

- [ ] Code is readable — intent is clear without needing comments to explain what it does
- [ ] Naming follows conventions from `CODING_STYLE.md` (variables, functions, classes, files)
- [ ] No dead code — unused imports, variables, functions, or branches removed
- [ ] No unnecessary duplication — shared logic is extracted appropriately
- [ ] Error handling is present and meaningful — failures are caught and communicated correctly
- [ ] No debug artifacts left behind (`print`, `console.log`, `TODO: remove`, etc.)
- [ ] Complex or non-obvious logic has an explanatory comment

---

## Documentation

- [ ] Public functions, methods, and classes have documentation (docstring, JSDoc, etc.)
- [ ] Parameter types and return values described where not obvious from types
- [ ] Inline comments explain *why*, not just *what*
- [ ] `README` or usage docs updated if behaviour, configuration, or setup changed

---

## Tests

- [ ] New behaviour has corresponding tests
- [ ] Tests cover the happy path, error paths, and relevant edge cases
- [ ] Test names are descriptive — they communicate intent without reading the body
- [ ] Tests are independent — no shared mutable state between test cases
- [ ] External dependencies are mocked appropriately in unit tests
- [ ] No flaky test patterns (sleeps, random values, time-dependent assertions)
- [ ] Test setup and teardown is clean — no leaked state between runs
- [ ] Tests run fast — slow tests are marked or isolated
