# PHP Coding Style Guide

## Naming Conventions

- **Classes, interfaces, traits, enums**: PascalCase (`UserService`, `PaymentGatewayInterface`)
- **Methods and functions**: camelCase (`getUserById`, `processPayment`)
- **Properties**: camelCase (`$firstName`, `$isActive`)
- **Constants**: `UPPER_SNAKE_CASE` (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Variables**: camelCase (`$userList`, `$orderTotal`)
- **Interfaces**: suffix with `Interface` (`RepositoryInterface`, `EventDispatcherInterface`) to make the contract explicit at call sites. If your codebase follows the Symfony convention of naming the interface as the noun and suffixing implementations (e.g., interface `UserRepository`, implementation `DoctrineUserRepository`), apply that consistently — do not mix conventions.
- **Abstract classes**: prefix with `Abstract` (`AbstractEntity`, `AbstractCommand`)
- **Traits**: suffix with `Trait` (`TimestampableTrait`, `SoftDeletableTrait`)
- **Exceptions**: suffix with `Exception` (`UserNotFoundException`, `PaymentException`)

## File Organization

- One class per file; file name matches the class name exactly
- Follow PSR-4 autoloading: namespace mirrors the directory path from the autoload root
- Namespace declaration at the top, followed by `use` statements grouped and sorted alphabetically
- Order within a file: namespace → use statements → class declaration → constants → properties → constructor → public methods → protected methods → private methods

## PSR Standards Compliance

- **PSR-1**: basic coding standard — UTF-8, Unix LF, no BOM, PHP 5.3+ namespaces
- **PSR-4**: autoloading — one class per file, namespace matches directory structure
- **PSR-12**: extended coding style — 4-space indent, 120-char soft line limit, brace placement rules
- **PSR-3**: use `Psr\Log\LoggerInterface` for all logging — never `error_log()` or `var_dump()`
- **PSR-6 / PSR-16**: use cache interfaces (`CacheItemPoolInterface` / `CacheInterface`) — not custom cache wrappers
- **PSR-7**: use HTTP message interfaces for request/response handling in framework-agnostic code
- **PSR-11**: use `ContainerInterface` for dependency injection — avoid `new` inside services
- **PSR-14**: use `EventDispatcherInterface` for event dispatching
- **PSR-15**: use `MiddlewareInterface` and `RequestHandlerInterface` for HTTP middleware

## Type Safety

- Declare `declare(strict_types=1)` at the top of every PHP file. Note: strict type checking applies only to function calls made *from* that file — it does not enforce strict types on calls made *into* functions defined in that file from other files without `strict_types=1`. For full enforcement, all calling files must also declare strict types.
- Annotate all method signatures: typed parameters, return types, and `void` where applicable
- Use named arguments for clarity when calling functions with many optional parameters
- Use union types (`int|string`), intersection types (`Countable&Iterator`), and DNF types (`(Countable&Iterator)|null`) as needed
- Avoid `mixed` — narrow to the actual type wherever possible
- Use `readonly` properties for value objects and DTOs

## OOP and Design Patterns

- Program to interfaces — inject `XxxInterface`, not concrete classes
- Prefer constructor injection; avoid setter injection and property injection
- Keep classes small and focused — apply single responsibility
- Use value objects for domain concepts that have no identity (`Money`, `Email`, `DateRange`)
- Use DTOs to transfer data between layers — not raw arrays
- Prefer immutability: `readonly` properties and pure methods that return new instances. Use constructor property promotion for DTOs and value objects:
  ```php
  final readonly class Money {
      public function __construct(
          public int $amount,
          public string $currency,
      ) {}
  }
  ```
- Use `final` on concrete classes unless designed for extension
- Use backed enums (`enum Status: string`) for values that need serialization (stored in DB, sent over API). Use pure enums for sets of named constants that are purely internal. Prefer enums over class constants for closed sets of values.
- Use PHP 8.0+ attributes (`#[Attribute]`) for declarative metadata — route definitions, validation constraints, serialization hints, and DI configuration. Prefer attributes over docblock annotations in new code.

## Error Handling

- Use typed, domain-specific exceptions — not generic `\Exception` or `\RuntimeException`
- Catch only exceptions you can handle; let others propagate
- Never silence errors with `@` operator
- Use `try/catch/finally` only for genuinely exceptional conditions — not for flow control
- Log exceptions with full context at the boundary where they are caught

## Modern PHP Features (apply when the project's PHP version supports them)

- **PHP 8.1+**: use Fibers for cooperative concurrency in event-loop contexts (ReactPHP/Revolt). Do not use Fibers as a general threading mechanism — PHP remains single-threaded per request in traditional FPM environments.
- **PHP 8.2+**: use `readonly` classes for immutable value objects; use `true`, `false`, `null` standalone types; use DNF intersection types
- **PHP 8.3+**: use `#[Override]` attribute on overriding methods; use `json_validate()` before `json_decode()`; use typed class constants; use `mb_str_split()` and `str_*` functions with encoding awareness
- **PHP 8.4+**: use property hooks for computed or validated properties; use asymmetric visibility (`public readonly`, `protected set`); use `array_find()` and `array_find_key()` instead of manual loops
- **PHP 8.5+**: use `array_first()` / `array_last()` for first/last element access instead of `reset()`/`end()`; use the pipe operator (`|>`) for fluent left-to-right data transformation chains; use `clone($obj, ['prop' => $value])` syntax for immutable updates on `readonly` classes; use the `Uri\Rfc3986\Uri` class for URL parsing and manipulation instead of `parse_url()`; use `#[\NoDiscard]` on methods whose return value must not be ignored

## Anti-Patterns to Avoid

- Do not use `var_dump`, `print_r`, or `error_log` in production code
- Do not use `static` methods or properties for mutable shared state — this creates hidden global state and makes testing impossible. Stateless utility methods and named constructors are legitimate uses of `static`. Never store mutable state in static properties.
- Do not use `global` variables
- Do not use `array` as a catch-all data structure — prefer typed DTOs or value objects
- Do not call `new ClassName()` inside services — use dependency injection
- Do not use magic methods (`__get`, `__set`) in place of explicit properties and methods
- Do not suppress errors with `@` — fix the root cause or handle the exception properly
