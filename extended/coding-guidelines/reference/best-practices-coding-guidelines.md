# Software Design Principles — Coding Guidelines

Proactive rules for writing sustainable code. Treat violations as design defects, not style suggestions.

---

## SOLID

### S — Single Responsibility
- One reason to change; describe each class in one sentence without "and"
- Separate: domain logic, persistence, validation, transport, presentation
- Entry points (controllers, handlers) stay thin — no business logic; cross-cutting concerns (logging, auth) go in middleware/decorators

### O — Open/Closed
- New behavior via extension (new implementations), not modification of stable code
- Replace `switch`/`if-elif` chains that grow per new type with polymorphism or strategy
- Use composition hooks (plugins, interceptors, middleware) before subclassing

### L — Liskov Substitution
- Subtypes usable anywhere the base type is used, without breaking behavior
- Never narrow preconditions or weaken postconditions; no no-op overrides or `raise NotImplementedError`
- If `isinstance` checks precede a call, the abstraction is broken — fix it

### I — Interface Segregation
- Interfaces serve one role; callers see only methods they invoke
- A class forced to leave interface methods empty → split the interface
- Define interfaces at the point of consumption, not production

### D — Dependency Inversion
- Depend on abstractions; inject all volatile deps (DB, HTTP, queues, filesystem)
- No `new ConcreteType()` inside domain/business logic
- Assemble the full dependency graph in one composition root; externalize volatile config

---

## DRY — Don't Repeat Yourself
- Centralize knowledge/rules, not just code — duplicated behavior creates inconsistency
- Extract when the same rule appears in multiple call sites; don't extract just because code looks similar
- Balance: premature abstraction is worse than controlled duplication

## KISS — Keep It Simple, Stupid
- Default to the simplest solution that solves the problem; add complexity only when the problem demands it
- An `if`, a small class, or an explicit rule beats unnecessary abstraction
- System complexity grows naturally; never add accidental complexity

## YAGNI — You Aren't Gonna Need It
- Don't build for hypothetical future requirements — speculative code needs maintenance too
- Validate the actual problem before building a framework around it
- Every premature generalization has a cost; solve now, extend when needed

## Separation of Concerns
- Each layer owns its role: controller → HTTP I/O; service → business rules; repository → persistence; job → async processing; client → external calls
- Blurring layer boundaries causes cascading coupling; a change in one place should not ripple everywhere

## Low Coupling / High Cohesion
- Each class is focused on one clear purpose (cohesion); components depend minimally on each other (low coupling)
- High coupling = any change risks a chain reaction; low cohesion = classes become "boxes of everything"
- Prefer dependency injection and interfaces to reduce coupling

## Composition over Inheritance
- Compose behaviors via services and small abstractions instead of deep inheritance hierarchies
- Use inheritance only for genuine behavioral specialization (IS-A), not code reuse
- If an inheritance tree is growing, ask: is this really specialization?

## Law of Demeter
- An object calls methods only on: itself, its own fields, injected dependencies, objects it directly created
- Avoid long method chains traversing internal structure: `a.b().c().d()` is a smell
- Encapsulate responsibilities so external code doesn't need to navigate your internals

## Fail Fast
- Validate inputs and assert invariants as early as possible; fail with a clear, explicit error
- Never let the system continue in an inconsistent state — silent failures compound
- Early failure = smaller blast radius and faster diagnosis

## Convention over Configuration
- Follow framework and language conventions unless there is a concrete reason to deviate
- Conventions reduce noise and make the project readable to new team members
- Document deviations explicitly when overriding defaults

## Readability over Cleverness
- Code is read far more times than it is written — optimize for the reader
- Clear names, simple flow, and explicit logic beat "smart" one-liners
- Ask before committing clever code: would a peer understand this in six months without context?

## Boy Scout Rule
- Leave every file you touch slightly better than you found it
- Small improvements compound: rename a confusing variable, extract a responsibility, remove obvious duplication
- Don't rewrite — improve incrementally and continuously

---

## Pre-Completion Checklist

Before marking any implementation done:

1. Each class describable in one sentence without "and"? (SRP)
2. Adding the next variant requires editing stable code? (OCP)
3. Subclass honors full parent contract? (LSP)
4. Caller depends only on methods it uses? (ISP)
5. All volatile deps injected, none instantiated inline? (DIP)
6. Any rule duplicated across multiple call sites? (DRY)
7. Simplest solution used? (KISS)
8. Any speculative/unrequested feature added? (YAGNI)
9. Layer boundaries respected? (SoC)
10. Left the code better than found? (Boy Scout)

---

## Comments

1. Add a comment only when:
   (a) the language/framework requires it as an industry standard (e.g. Go `godoc` on exported identifiers), or
   (b) the name/signature alone does not convey intent — explain *why* or *what constraint* applies, never *what the code does*
