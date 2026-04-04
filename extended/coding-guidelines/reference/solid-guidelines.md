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
- Keep entry points (request handlers, view functions, resolvers, graph nodes) thin: parse input, call a service, return a response — no business logic inside them
- Keep entity/model classes as data containers: field definitions, constraints, and identity. Push orchestration, calculation, and side-effect logic into service classes
- Cross-cutting concerns (logging, authentication, rate limiting, tracing) must live in dedicated layers (middleware, decorators, interceptors) — never embedded in domain or service code

## O — Open/Closed Principle

**Extend behavior by adding code, not by changing existing code.**

- Design core logic so new behavior can be added without touching it
- Replace `if/elif` or `switch` chains that grow with every new type — use polymorphism or strategy patterns
- Stable, shared code should rarely need modification; if it does, the abstraction is wrong
- Use interfaces, abstract classes, or composition points to allow extension without patching
- Prefer adding a new implementation (plugin, strategy, handler, observer) over modifying an existing one to support a new case
- When the framework provides a composition mechanism (plugins, interceptors, middleware, decorators), use it instead of subclassing or modifying core classes — composition hooks are explicit OCP enforcement

## L — Liskov Substitution Principle

**Subtypes must honor the contract of their base type.**

- A subclass must be usable anywhere its parent is used without breaking behavior
- Never narrow preconditions (require more from callers) or weaken postconditions (guarantee less)
- Never override a method with a no-op or `raise NotImplementedError` — that is a sign inheritance is the wrong tool; use composition instead
- If you find yourself checking `isinstance` before calling a method, the abstraction is broken — fix it
- Prefer composition over inheritance by default; only inherit when the subtype genuinely is a behavioral specialization of the parent, not merely a code reuse opportunity
- Use explicit override markers (annotations, decorators, or attributes) on every method that overrides a parent method — they catch contract drift at the point of change before it reaches runtime

## I — Interface Segregation Principle

**Keep interfaces small and focused. Don't force clients to depend on what they don't use.**

- Split large interfaces by role — callers should only see the methods they actually invoke
- If implementing an interface forces a class to leave methods empty or throw, the interface is too fat — split it
- Inject the narrowest interface sufficient for the use case, not the full concrete type
- A class that depends on 10 methods but uses 2 is a coupling liability
- Define interfaces at the point of consumption (the caller's package/module), not at the point of production (the implementation's package) — this keeps interfaces minimal and caller-driven, and avoids forcing producers to implement more than any single caller needs
- Single-method or small-method-count interfaces are a design signal of correctness, not a sign of over-engineering

## D — Dependency Inversion Principle

**Depend on abstractions, not on concretions. Inject dependencies, don't instantiate them.**

- Business logic must never `new` up infrastructure: no `new MySQLRepository()`, no `new StripeClient()` inside domain code
- All volatile dependencies (databases, HTTP clients, queues, file system) must be injected via constructor, parameter, or DI container
- Domain code must import interfaces, not concrete implementations
- If a unit can't be tested without a real database or external service, DIP is being violated
- Dependency direction: infrastructure depends on domain, never the reverse
- Use factory functions or factory classes for creating instances of DI-managed objects — factories are the correct DIP mechanism when object construction requires runtime parameters that cannot be injected upfront
- Assemble the full dependency graph in a single composition root (main function, application bootstrap, DI container configuration) — never scatter wiring logic across service classes
- Volatile configuration (external service URLs, model names, timeouts, feature flags) must be externalized and injected, not hardcoded inside modules

## Application Rules

When writing new code:
1. Before creating a class, state its single responsibility in one sentence — if you can't, redesign it
2. Before adding a method to an existing class, check whether it belongs there or should live elsewhere
3. Before using `new ConcreteType()` inside a class, ask whether it should be injected instead — if you need runtime parameters, use a factory
4. Before adding a case to a switch/if chain, ask whether the design should be extended rather than modified
5. Before subclassing, confirm LSP is preserved — if in doubt, compose instead of inherit
6. Before placing logic in an entry point (handler, view, resolver, controller), confirm it belongs in a service — entry points must remain thin
7. Before writing a new interface, ask who the consumer is and define the interface only with the methods that consumer actually calls

When refactoring:
- Extract classes/modules when a single unit has grown to handle multiple concerns
- Replace type-dispatching conditionals with polymorphism
- Replace constructor-instantiated dependencies with injected ones
- Split fat interfaces when callers only use a subset of methods
- Move business logic out of entry points (handlers, views, resolvers) into service classes
- Extract cross-cutting concerns (logging, authentication, validation, rate limiting) into dedicated middleware, decorators, or interceptors
- Move scattered dependency wiring into a single composition root
