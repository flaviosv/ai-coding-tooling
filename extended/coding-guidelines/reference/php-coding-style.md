# PHP Coding Style Guide

## Naming Conventions

- **Classes, interfaces, traits, enums**: PascalCase (`UserService`, `PaymentGatewayInterface`)
- **Methods and functions**: camelCase (`getUserById`, `processPayment`)
- **Properties**: camelCase (`$firstName`, `$isActive`)
- **Constants**: `UPPER_SNAKE_CASE` (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Variables**: camelCase (`$userList`, `$orderTotal`)
- **Interfaces**: suffix with `Interface` (`RepositoryInterface`, `EventDispatcherInterface`)
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

- Declare `strict_types=1` in every file
- Annotate all method signatures: typed parameters, return types, and `void` where applicable
- Use named arguments for clarity when calling functions with many optional parameters
- Use union types (`int|string`), intersection types (`Countable&Iterator`), and DNF types (`(Countable&Iterator)|null`) as needed
- Avoid `mixed` — narrow to the actual type wherever possible
- Use `readonly` properties for value objects and DTOs

## Modern PHP Features (apply when the project's PHP version supports them)

- **PHP 8.2+**: use `readonly` classes for immutable value objects; use `true`, `false`, `null` standalone types; use DNF intersection types
- **PHP 8.3+**: use `#[Override]` attribute on overriding methods; use `json_validate()` before `json_decode()`; use typed class constants; use `mb_str_split()` and `str_*` functions with encoding awareness
- **PHP 8.4+**: use property hooks for computed or validated properties; use asymmetric visibility (`public readonly`, `protected set`); use `array_find()` and `array_find_key()` instead of manual loops
- **PHP 8.5+**: use `array_first()` / `array_last()` for first/last element access; use the pipe operator (`|>`) for fluent data transformation chains; use `clone` with property modification syntax (`clone $obj with { prop: value }`); use `Uri` class for URL parsing and manipulation

## OOP and Design Patterns

- Program to interfaces — inject `XxxInterface`, not concrete classes
- Prefer constructor injection; avoid setter injection and property injection
- Keep classes small and focused — apply single responsibility
- Use value objects for domain concepts that have no identity (`Money`, `Email`, `DateRange`)
- Use DTOs to transfer data between layers — not raw arrays
- Prefer immutability: `readonly` properties and pure methods that return new instances
- Use `final` on concrete classes unless designed for extension

## Error Handling

- Use typed, domain-specific exceptions — not generic `\Exception` or `\RuntimeException`
- Catch only exceptions you can handle; let others propagate
- Never silence errors with `@` operator
- Use `try/catch/finally` only for genuinely exceptional conditions — not for flow control
- Log exceptions with full context at the boundary where they are caught

## Anti-Patterns to Avoid

- Do not use `var_dump`, `print_r`, or `error_log` in production code
- Do not use `static` methods or properties for mutable shared state
- Do not use `global` variables
- Do not use `array` as a catch-all data structure — prefer typed DTOs or value objects
- Do not call `new ClassName()` inside services — use dependency injection
- Do not use magic methods (`__get`, `__set`) in place of explicit properties and methods
- Do not suppress errors with `@` — fix the root cause or handle the exception properly
