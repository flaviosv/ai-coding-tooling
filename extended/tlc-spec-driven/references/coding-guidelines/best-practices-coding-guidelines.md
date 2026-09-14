# Software Design Principles — Coding Guidelines

Proactive rules for writing sustainable code. Treat violations as design defects, not style suggestions.

---

## SOLID

Apply dependency injection, extension points, and polymorphism only where a second implementation, a test seam, or an existing project pattern needs them; otherwise the parent skill's "No abstractions for single-use code" rule wins.

- Entry points (controllers, handlers) stay thin — no business logic; cross-cutting concerns (logging, auth) go in middleware/decorators
- Replace `switch`/`if-elif` chains that grow per new type with polymorphism or strategy
- No no-op overrides or `raise NotImplementedError` in subtypes
- If `isinstance` checks precede a call, the abstraction is broken — fix it
- Define interfaces at the point of consumption, not production
- Inject volatile deps (DB, HTTP, queues, filesystem); no `new ConcreteType()` inside domain/business logic
- Assemble the dependency graph in one composition root; externalize volatile config

---

## Separation of Concerns
- Each layer owns its role: controller → HTTP I/O; service → business rules; repository → persistence; job → async processing; client → external calls

## Law of Demeter
- Avoid long method chains traversing internal structure: `a.b().c().d()` is a smell

## Fail Fast
- Validate inputs and assert invariants as early as possible; fail with a clear, explicit error

## Convention over Configuration
- Document deviations explicitly when overriding defaults

---

## Pre-Completion Checklist

Before marking any implementation done:

1. Each class describable in one sentence without "and"? (SRP)
2. Where a second implementation, test seam, or existing extension point needs it, can the next variant be added without editing stable code? (OCP)
3. Subclass honors full parent contract? (LSP)
4. Caller depends only on methods it uses? (ISP)
5. Where a second implementation, test seam, or existing DI pattern needs it, are volatile deps injected rather than instantiated inline? (DIP)
6. Layer boundaries respected? (SoC)
