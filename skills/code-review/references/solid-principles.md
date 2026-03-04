# SOLID Principles Review Checklist

Checklist for evaluating SOLID design principles during code review. Use alongside `clean-code-checklist.md` — this file focuses specifically on object-oriented design correctness and long-term maintainability.

---

## S — Single Responsibility Principle

> A class (or module, function) should have one, and only one, reason to change.

- [ ] Each class/module has a single, clearly stated purpose — if you need "and" to describe it, it violates SRP
- [ ] Business logic is not mixed with persistence, serialization, or transport concerns in the same class
- [ ] Validation logic is not embedded inside domain models or controllers — it lives in a dedicated layer
- [ ] Classes don't accumulate unrelated utility methods over time (the "catch-all" class smell)
- [ ] A change to one concern (e.g. logging format) does not require touching unrelated code
- [ ] Large classes are flagged — size is a proxy for multiple responsibilities

**Common violations to flag:**
- `UserService` that also handles email delivery, file uploads, and audit logging
- A model class that contains SQL queries or HTTP calls
- A controller action that performs data access, business logic, and response formatting inline

---

## O — Open/Closed Principle

> Software entities should be open for extension, but closed for modification.

- [ ] Adding new behavior does not require modifying existing, stable code
- [ ] Conditionals that dispatch on type or enum values are not scattered — use polymorphism or a strategy pattern instead
- [ ] New variants can be added by implementing an interface or extending a base class, not by editing switch/if chains
- [ ] Core domain logic is not frequently modified to accommodate new features — it is extended
- [ ] Plugin, strategy, or decorator patterns are used where behavior needs to vary

**Common violations to flag:**
- A `switch(type)` or `if/elif` chain that must grow every time a new type is added
- Adding a new feature by editing a core utility function shared across many callers
- Hard-coded conditionals like `if env == "production"` scattered through business logic

---

## L — Liskov Substitution Principle

> Subtypes must be substitutable for their base types without altering correctness.

- [ ] Subclasses do not override methods in ways that break the contract defined by the parent
- [ ] A subclass does not narrow preconditions (require more) or weaken postconditions (guarantee less) compared to the parent
- [ ] Subclasses do not throw exceptions for operations the parent declares as valid
- [ ] Inheriting and then doing nothing (no-op overrides or `raise NotImplementedError`) is a red flag — prefer composition
- [ ] Callers can use the base type without knowing which concrete subtype they have

**Common violations to flag:**
- A `ReadOnlyList` that extends `List` but throws on `add()` — callers expecting `List` break
- An override that silently ignores input the parent processed
- Checking `instanceof` before calling a method — code doesn't trust the substitution

---

## I — Interface Segregation Principle

> Clients should not be forced to depend on interfaces they do not use.

- [ ] Interfaces are focused — no "fat interfaces" that bundle unrelated capabilities
- [ ] A class that implements an interface is not forced to leave methods empty or raise `NotImplementedError`
- [ ] Consumers depend only on the slice of behavior they actually use
- [ ] Large interfaces are split by role (e.g. `Readable`, `Writable` instead of one `FileHandler`)
- [ ] A change to one part of a fat interface does not force recompilation or changes in unrelated consumers

**Common violations to flag:**
- A single `IRepository` interface with `findById`, `save`, `delete`, `bulkImport`, `generateReport` — consumers only using read operations still depend on write operations
- An interface implemented by a class that leaves 3 of 7 methods as `pass` or `throw new NotImplementedException()`
- Injecting a full service into a component that only uses one method from it

---

## D — Dependency Inversion Principle

> High-level modules should not depend on low-level modules. Both should depend on abstractions. Abstractions should not depend on details.

- [ ] High-level business logic depends on interfaces/abstractions, not concrete implementations
- [ ] Concrete classes (database adapters, HTTP clients, file system wrappers) are injected, not instantiated inline
- [ ] `new ConcreteService()` inside a business logic class is a violation — use dependency injection
- [ ] Unit tests are possible without mocking internals — if you can't inject a fake, the dependency is inverted wrong
- [ ] The direction of dependency matches the direction of abstraction: volatile (infrastructure) depends on stable (domain), not the reverse
- [ ] No static calls to concrete utility classes inside domain logic

**Common violations to flag:**
- `OrderService` directly instantiating `MySQLOrderRepository` or `StripePaymentGateway`
- Business logic importing and using a specific logger implementation instead of a logging interface
- Infrastructure code (e.g. a database adapter) pulling in domain objects directly

---

## Cross-Cutting SOLID Smells

Flag any of the following — they often indicate multiple SOLID violations at once:

- **God Class**: one class that orchestrates everything — violates SRP, OCP, and DIP
- **Anemic Domain Model**: domain objects with no behavior, all logic in services — often violates SRP and OCP
- **Feature Envy**: a method that uses data from another class more than its own — violates SRP
- **Shotgun Surgery**: a single change requires edits across many unrelated files — violates SRP and OCP
- **Refused Bequest**: a subclass ignores or breaks parent behavior — violates LSP
- **Parallel Inheritance Hierarchies**: adding a subclass in one hierarchy always requires adding one in another — violates OCP and DIP
