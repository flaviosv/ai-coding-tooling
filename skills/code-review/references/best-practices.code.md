# Software Design Principles — Review Checklist

Checklist for evaluating core design principles during code review. Use alongside `clean-code-checklist.code.md`.

---

## SOLID

### O — Open/Closed
- [ ] New behavior added via new implementations, not by modifying stable existing code
- [ ] No `switch`/`if-elif` chains that grow per new type — polymorphism or strategy used instead
- [ ] Core logic is extended, not frequently modified to support new features

### L — Liskov Substitution
- [ ] Subclasses don't narrow preconditions or weaken postconditions vs parent
- [ ] No no-op overrides or `raise NotImplementedError` — if present, composition is the fix
- [ ] No `instanceof`/`isinstance` checks needed before calling a method on the base type

### D — Dependency Inversion
- [ ] Business logic depends on abstractions, not concretions
- [ ] No `new ConcreteService()` inside domain/business code; all volatile deps injected
- [ ] Unit tests possible without a real database or external service

---

## KISS
- [ ] Simplest solution used; no unnecessary abstraction layers or indirection
- [ ] No over-engineered patterns for a problem a few lines would solve
- [ ] Added complexity is justified by actual requirements

## YAGNI
- [ ] No speculative features, configurations, or abstractions not requested
- [ ] No "just in case" code paths; no framework built before the problem is validated

## Separation of Concerns
- [ ] Layer roles respected as defined in `ARCHITECTURE.md` (e.g. transport vs business rules vs persistence)
- [ ] Business logic not leaking into controllers, models, jobs, or repositories
- [ ] Cross-cutting concerns (logging, auth, rate-limiting) in dedicated layers only

## Low Coupling / High Cohesion
- [ ] Classes are focused; no "catch-all" modules accumulating unrelated logic
- [ ] A single change doesn't require edits across many unrelated files (shotgun surgery)
- [ ] Dependencies flow through abstractions/interfaces, not direct concretions

## Composition over Inheritance
- [ ] Inheritance used only for genuine behavioral specialization (IS-A), not code reuse
- [ ] No deep or growing inheritance hierarchies where composition would work
- [ ] Shared behavior flows via services or collaborators, not parent classes

## Fail Fast
- [ ] Input validation and invariant checks happen as early as possible
- [ ] No silent error swallowing; no system continuing in inconsistent state
- [ ] Errors are explicit with enough context to diagnose quickly

## Convention over Configuration
- [ ] Framework and language conventions followed; deviations are explicit and documented
- [ ] No unnecessary custom config for something the framework handles by default

## Boy Scout Rule
- [ ] Code left in at least as good a state as found; no new tech debt introduced

---

## Cross-Cutting Smells (flag any)

- **God Class** — one class orchestrating everything (SRP + OCP + DIP)
- **Shotgun Surgery** — one change requires edits across many unrelated files (SRP + OCP)
- **Feature Envy** — method uses another class's data more than its own (SRP)
- **Refused Bequest** — subclass ignores/breaks parent behavior (LSP)
- **Anemic Domain Model** — domain objects with no behavior, all logic in services (SRP + OCP)
- **Data Clumps** — recurring groups of data never encapsulated in a type (SRP)
