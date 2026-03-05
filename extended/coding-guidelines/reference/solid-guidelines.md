# SOLID Design Principles — Coding Guidelines

Guidelines for applying SOLID principles when writing or modifying code. These are proactive rules — apply them while writing, not just during review.

---

## S — Single Responsibility Principle

**One reason to change. One job per unit.**

- Each class, module, or function must have a single, clearly stated purpose
- If you need "and" to describe what something does, split it
- Separate concerns into distinct layers: domain logic, persistence, validation, transport, presentation
- When a class grows large, ask: is it accumulating responsibilities? Extract before it becomes a god object
- Corollary: a function that takes a boolean flag to change its behavior is doing two things — split it

---

## O — Open/Closed Principle

**Extend behavior by adding code, not by changing existing code.**

- Design core logic so new behavior can be added without touching it
- Replace `if/elif` or `switch` chains that grow with every new type — use polymorphism or strategy patterns
- Stable, shared code should rarely need modification; if it does, the abstraction is wrong
- Use interfaces, abstract classes, or composition points to allow extension without patching

---

## L — Liskov Substitution Principle

**Subtypes must honor the contract of their base type.**

- A subclass must be usable anywhere its parent is used without breaking behavior
- Never narrow preconditions (require more from callers) or weaken postconditions (guarantee less)
- Never override a method with a no-op or `raise NotImplementedError` — that is a sign inheritance is the wrong tool; use composition instead
- If you find yourself checking `isinstance` before calling a method, the abstraction is broken — fix it

---

## I — Interface Segregation Principle

**Keep interfaces small and focused. Don't force clients to depend on what they don't use.**

- Split large interfaces by role — callers should only see the methods they actually invoke
- If implementing an interface forces a class to leave methods empty or throw, the interface is too fat — split it
- Inject the narrowest interface sufficient for the use case, not the full concrete type
- A class that depends on 10 methods but uses 2 is a coupling liability

---

## D — Dependency Inversion Principle

**Depend on abstractions, not on concretions. Inject dependencies, don't instantiate them.**

- Business logic must never `new` up infrastructure: no `new MySQLRepository()`, no `new StripeClient()` inside domain code
- All volatile dependencies (databases, HTTP clients, queues, file system) must be injected via constructor, parameter, or DI container
- Domain code must import interfaces, not concrete implementations
- If a unit can't be tested without a real database or external service, DIP is being violated
- Dependency direction: infrastructure depends on domain, never the reverse

---

## Application Rules

When writing new code:
1. Before creating a class, state its single responsibility in one sentence — if you can't, redesign it
2. Before adding a method to an existing class, check whether it belongs there or should live elsewhere
3. Before using `new ConcreteType()` inside a class, ask whether it should be injected instead
4. Before adding a case to a switch/if chain, ask whether the design should be extended rather than modified
5. Before subclassing, confirm LSP is preserved — if in doubt, compose instead of inherit

When refactoring:
- Extract classes/modules when a single unit has grown to handle multiple concerns
- Replace type-dispatching conditionals with polymorphism
- Replace constructor-instantiated dependencies with injected ones
- Split fat interfaces when callers only use a subset of methods
