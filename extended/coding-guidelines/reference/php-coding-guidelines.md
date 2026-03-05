# PHP Coding Style Guide

<!-- General section covers conventions that apply across ALL currently supported versions (PHP 8.2+) -->
## General PHP Patterns

### Naming Conventions

- **Classes, interfaces, traits, enums**: PascalCase (`UserService`, `PaymentGatewayInterface`)
- **Methods and functions**: camelCase (`getUserById`, `processPayment`)
- **Properties**: camelCase (`$firstName`, `$isActive`)
- **Constants**: `UPPER_SNAKE_CASE` (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Variables**: camelCase (`$userList`, `$orderTotal`)
- **Interfaces**: suffix with `Interface` (`RepositoryInterface`, `EventDispatcherInterface`). If your codebase follows the Symfony convention of naming the interface as the noun and suffixing implementations (e.g., interface `UserRepository`, implementation `DoctrineUserRepository`), apply that consistently — do not mix conventions.
- **Abstract classes**: prefix with `Abstract` (`AbstractEntity`, `AbstractCommand`)
- **Traits**: suffix with `Trait` (`TimestampableTrait`, `SoftDeletableTrait`)
- **Exceptions**: suffix with `Exception` (`UserNotFoundException`, `PaymentException`)

### File Organization

- One class per file; file name matches the class name exactly
- Follow PSR-4 autoloading: namespace mirrors the directory path from the autoload root
- Namespace declaration at the top, followed by `use` statements grouped and sorted alphabetically
- Order within a file: namespace → use statements → class declaration → constants → properties → constructor → public methods → protected methods → private methods

### PSR Standards Compliance

- **PSR-1**: basic coding standard — UTF-8, Unix LF, no BOM, namespaces required
- **PSR-4**: autoloading — one class per file, namespace matches directory structure
- **PSR-12**: extended coding style — 4-space indent, 120-char soft line limit, brace placement
- **PSR-3**: use `Psr\Log\LoggerInterface` for logging (see Logging section)
- **PSR-6 / PSR-16**: use `CacheItemPoolInterface` / `CacheInterface` — not custom cache wrappers
- **PSR-11**: use `ContainerInterface` for dependency injection — avoid `new` inside services
- **PSR-14**: use `EventDispatcherInterface` for event dispatching
- **PSR-15**: use `MiddlewareInterface` and `RequestHandlerInterface` for HTTP middleware

Use `php-cs-fixer` or `phpcs` to enforce PSR-1 and PSR-12 automatically — do not rely on manual formatting.

### Type Safety

- Declare `declare(strict_types=1)` at the top of every PHP file. Strict type checking applies only to calls *from* that file — all calling files must also declare strict types for full enforcement.
- Annotate all method signatures: typed parameters, return types, and `void` where applicable
- Use named arguments for clarity when calling functions with many optional parameters
- Use union types (`int|string`), intersection types (`Countable&Iterator`), and DNF types (`(Countable&Iterator)|null`) as needed
- Avoid `mixed` — narrow to the actual type wherever possible
- Use `readonly` properties for value objects and DTOs

```php
// Prefer typed, readonly value objects
final readonly class Money {
    public function __construct(
        public int $amount,
        public string $currency,
    ) {}
}
```

### OOP and Design Patterns

- Program to interfaces — inject `XxxInterface`, not concrete classes
- Prefer constructor injection; avoid setter injection and property injection
- Keep classes small and focused — apply single responsibility
- Use value objects for domain concepts with no identity (`Money`, `Email`, `DateRange`)
- Use DTOs to transfer data between layers — not raw arrays
- Prefer immutability: `readonly` properties and pure methods that return new instances
- Use `final` on concrete classes unless designed for extension
- Use backed enums (`enum Status: string`) for values that need serialization (DB, API). Use pure enums for internal named constant sets. Prefer enums over class constants for closed sets of values.
- Use PHP 8.0+ attributes (`#[Attribute]`) for declarative metadata — route definitions, validation constraints, serialization hints, DI configuration. Prefer attributes over docblock annotations in new code.

### Error Handling

- Use typed, domain-specific exceptions — not generic `\Exception` or `\RuntimeException`
- Catch only exceptions you can handle; let others propagate
- Never silence errors with the `@` operator
- Use `try/catch/finally` only for genuinely exceptional conditions — not for flow control
- Log exceptions with full context at the boundary where they are caught

```php
// Typed exception hierarchy
class UserNotFoundException extends DomainException {
    public function __construct(int $userId) {
        parent::__construct("User {$userId} not found");
    }
}
```

### Idioms and Patterns

- Use the nullsafe operator (`?->`) for chained calls on nullable objects instead of nested null checks
- Use null coalescing assignment (`??=`) for lazy initialization of nullable properties
- Use `match` instead of `switch` — it is strict (no type coercion), exhaustive (throws `UnhandledMatchError`), and expression-based:
  ```php
  $label = match($status) {
      Status::Active => 'Active',
      Status::Inactive => 'Inactive',
      Status::Pending => 'Pending',
  };
  ```
- Use named arguments when calling functions with many optional or ambiguous parameters:
  ```php
  array_slice(array: $items, offset: 0, length: 10, preserve_keys: true);
  ```
- Use first-class callables (`strlen(...)`) instead of `Closure::fromCallable('strlen')` or `['obj', 'method']` string arrays
- Use the spread operator (`...$args`) to pass variadic arguments from arrays

### Logging

- Inject `Psr\Log\LoggerInterface` via constructor — never use `error_log()`, `var_dump()`, or framework-specific loggers directly in domain code
- Use structured log context arrays, not string interpolation, to preserve machine-readability:
  ```php
  $this->logger->error('Payment failed', [
      'order_id' => $order->getId(),
      'amount'   => $order->getTotal(),
      'error'    => $e->getMessage(),
  ]);
  ```
- Log at the right level: `debug` for trace info, `info` for normal events, `warning` for recoverable issues, `error`/`critical` for failures
- Never log sensitive data — mask PII, tokens, and credentials before logging

### Dependency Management

- Use Composer for all dependencies — never vendor packages manually
- Pin exact versions in `composer.lock` and commit it to version control
- Use semver constraints in `composer.json`: `^1.2` (compatible with 1.x, ≥1.2) or `~1.2.3` (≥1.2.3, <1.3.0)
- Separate `require` (runtime) from `require-dev` (dev tools: PHPStan, PHPUnit, PHP CS Fixer)
- Use private Composer repositories (Satis, Private Packagist) for internal packages — never commit proprietary code to public registries

### Tooling

- **PHP CS Fixer** or **PHP_CodeSniffer**: enforce PSR-12 automatically in CI — not optional
- **PHPStan** or **Psalm**: run at level 6+ minimum; aim for max level in new projects. Treat type errors as build failures.
- **Rector**: automate upgrade migrations (e.g., PHP 8.1 → 8.4 syntax) and enforce coding rules programmatically
- Run all tools in CI on every pull request — local pre-commit hooks alone are insufficient

### Anti-Patterns to Avoid

- Do not use `var_dump`, `print_r`, or `error_log` in production code
- Do not use `static` methods or properties for mutable shared state — this creates hidden global state and makes testing impossible. Stateless utility methods and named constructors are legitimate uses of `static`.
- Do not use `global` variables
- Do not use raw `array` as a catch-all data structure — prefer typed DTOs or value objects
- Do not call `new ClassName()` inside services — use dependency injection
- Do not use magic methods (`__get`, `__set`) in place of explicit properties and methods
- Do not suppress errors with `@` — fix the root cause or handle the exception properly
- Do not use string class references (`'App\Service\UserService'`) where `UserService::class` can be used — string references bypass static analysis and refactoring tools
- Do not use `isset()` and `array_key_exists()` interchangeably — `isset()` returns `false` for keys that exist with a `null` value; use `array_key_exists()` when `null` is a valid value

---

## PHP 8.2

> Floor for new projects — PHP 8.1 reached end of life December 2025.
> Includes features introduced since PHP 8.1 that all supported projects can use.

- Use `readonly` classes for fully immutable value objects — all properties are implicitly `readonly`, no need to declare each one individually:
  ```php
  final readonly class Coordinate {
      public function __construct(
          public float $latitude,
          public float $longitude,
      ) {}
  }
  ```
- Use `true`, `false`, and `null` as standalone return types where the value is always one of those literals
- Use DNF (Disjunctive Normal Form) intersection types: `(Countable&Iterator)|null`
- Use Fibers for cooperative concurrency in event-loop contexts (ReactPHP/Revolt). Do not use Fibers as a general threading mechanism — PHP remains single-threaded per request in traditional FPM environments.
- Backed enums (`enum Status: string`) and pure enums are available — prefer them over class constants for closed sets

---

## PHP 8.3

- Use `#[Override]` attribute on overriding methods to make the intent explicit and catch rename mismatches at static analysis time:
  ```php
  class ConcreteRepository extends AbstractRepository {
      #[Override]
      public function findById(int $id): ?Entity { ... }
  }
  ```
- Use typed class constants (`const int MAX = 100`) — avoids implicit coercion and enables static analysis validation
- Use `json_validate()` to check JSON validity before calling `json_decode()` — avoids allocating the decoded structure just to check validity
- Use `mb_str_split()` and other `mb_*` functions when processing multibyte strings

---

## PHP 8.4

- Use **property hooks** for computed or validated properties — replaces explicit getters/setters while keeping properties as the public interface:
  ```php
  class User {
      public string $email {
          set(string $value) {
              if (!filter_var($value, FILTER_VALIDATE_EMAIL)) {
                  throw new InvalidArgumentException("Invalid email: {$value}");
              }
              $this->email = strtolower($value);
          }
      }
  }
  ```
- Use **asymmetric visibility** (`public protected(set)`) to make a property publicly readable but write-restricted to the class or subclass — a lighter alternative to full `readonly` when mutation within the class is needed:
  ```php
  class Order {
      public protected(set) string $status = 'pending';
  }
  ```
- Use `array_find()` and `array_find_key()` instead of manual `foreach` loops for searching arrays by predicate
- Use the `#[\Deprecated]` attribute to mark deprecated functions/methods — it triggers native deprecation notices without requiring docblock `@deprecated` annotations
- Use `Dom\HTMLDocument` for HTML5-compliant DOM parsing — the new parser correctly handles modern HTML5 documents unlike the legacy `DOMDocument`

---

## PHP 8.5

- Use `array_first()` and `array_last()` for first/last element access instead of `reset()` / `end()` — they do not move the internal array pointer
- Use the **pipe operator** (`|>`) for left-to-right function composition chains — passes the left-hand value as the argument to the right-hand callable:
  ```php
  $result = "  Hello World  " |> trim(...) |> strtolower(...) |> strlen(...);
  ```
- Use `clone($obj, ['prop' => $value])` syntax for immutable updates on `readonly` classes — creates a clone with specified property overrides without requiring manual clone methods
- Use `Uri\Rfc3986\Uri` for URL parsing and manipulation instead of `parse_url()` — returns a typed, structured URI object rather than an untyped array
- Use `#[\NoDiscard]` on methods whose return value must not be silently ignored — causes a notice when the return value is discarded at call sites
