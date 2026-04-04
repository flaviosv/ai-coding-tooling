# PHP Code Review Reference (PHP 8.2–8.5)

Supplements the generic `review-checklist.md` for PHP 8.2–8.5 projects. Covers PHP language best practices — framework-specific concerns live in separate checklists.

---

## General PHP Patterns

- `declare(strict_types=1)` at the top of every PHP file — prevents silent type coercion
- PSR-1 naming (`PascalCase` classes, `camelCase` methods, `UPPER_CASE` constants) and PSR-4 autoloading
- All parameters and return types declared — avoid `mixed` unless genuinely unknown
- Depend on interfaces (`Psr\Log\LoggerInterface`, `Psr\Container\ContainerInterface`), not concrete classes
- Domain-specific exception types — never broad `\Exception` or silent catch-and-ignore
- Backed enums (`enum Status: string`) for closed value sets — not class constants
- PHP 8.0+ attributes (`#[Attribute]`) for metadata — not docblock annotations in new code
- `random_bytes()` / `sodium_*` for cryptography — never `rand()`, `md5()`, or `sha1()`
- `hash_equals()` for timing-safe comparison of secrets and tokens
- All dependencies injected via constructor — never `new ClassName()` inside service methods

## Type Safety

- [ ] `declare(strict_types=1)` declared at the top of all PHP files — absence leads to silent type coercion bugs
- [ ] Return types declared on all methods — no missing `void`, `string`, `int`, `array`, etc.
- [ ] Parameter types declared on all function signatures
- [ ] `mixed` used only when type is genuinely unknown — not as a lazy default
- [ ] Nullable types (`?string`) used instead of `string|null` for simple nullable params
- [ ] Union types (`int|string`) preferred over `mixed` when types are known
- [ ] Intersection types (`Iterator&Countable`) used correctly (PHP 8.1+, DNF in 8.2+)
- [ ] DNF types (`(A&B)|null`) used when combining intersection and union (PHP 8.2+)
- [ ] `never` return type applied to methods that always throw or exit

## PHP 8.2 Features

- [ ] `readonly` classes used for pure value/DTO objects — all properties implicitly immutable, no need to declare each one individually (PHP 8.2+)
- [ ] `true`, `false`, and `null` standalone return types used where value is always one of those literals
- [ ] DNF types (`(Countable&Iterator)|null`) used when combining intersection and union types
- [ ] No reliance on implicit dynamic properties on non-`stdClass` objects — requires `#[AllowDynamicProperties]`; flag any class that sets undefined properties without it

## PHP 8.3 Features

- [ ] `#[Override]` attribute applied to methods intentionally overriding a parent — catches rename mismatches at static-analysis time (PHP 8.3+)
- [ ] `json_validate()` used for JSON format validation instead of `json_decode` + error check — avoids allocating the decoded structure just to validate (PHP 8.3+)
- [ ] Typed class constants declared with explicit types (`const int MAX = 100`) — avoids implicit coercion and enables static-analysis validation (PHP 8.3+)
- [ ] `mb_str_split()` and `mb_*` functions used when processing multibyte character strings

## PHP 8.4 Features

- [ ] Property hooks (`get`/`set`) used instead of trivial getter/setter boilerplate — keeps properties as the public interface (PHP 8.4+)
- [ ] Virtual (get-only) properties used for computed values — no backing field needed (PHP 8.4+)
- [ ] Asymmetric visibility (`public private(set)`) used for write-restricted properties — lighter alternative to full `readonly` when mutation within the class is needed (PHP 8.4+)
- [ ] `array_find()` / `array_find_key()` preferred over manual `foreach` searches (PHP 8.4+)
- [ ] `#[\Deprecated]` attribute used on deprecated methods, constants, and traits — triggers native deprecation notices without requiring docblock `@deprecated` (PHP 8.4+)
- [ ] `Dom\HTMLDocument` used for HTML5-compliant DOM parsing — not legacy `DOMDocument` which does not handle modern HTML5 documents correctly (PHP 8.4+)
- [ ] `Dom\XMLDocument` used for modern XML parsing when strong type guarantees are needed (PHP 8.4+)
- [ ] Hand-rolled null-check lazy-initialization patterns replaced with native lazy objects via `ReflectionClass::newLazyGhost()` or `newLazyProxy()` (PHP 8.4+)

```php
// Good — PHP 8.4 lazy ghost: same class, initialized on first property access
$lazy = (new \ReflectionClass(HeavyService::class))
    ->newLazyGhost(function (HeavyService $service): void {
        $service->__construct(/* real dependencies */);
    });
// HeavyService constructor is not called until $lazy->someProperty is first accessed

// Bad — hand-rolled lazy pattern; works but bypasses native optimization
class Container
{
    private ?HeavyService $service = null;
    public function getService(): HeavyService
    {
        return $this->service ??= new HeavyService($this->dep);
    }
}
```

## PHP 8.5 Features

- [ ] `array_first()` / `array_last()` used instead of `reset()` / `end()` — they do not mutate the internal array pointer (PHP 8.5+)
- [ ] Pipe operator `|>` used for readable left-to-right transformation chains (PHP 8.5+)
- [ ] `clone($obj, ['prop' => $val])` used to derive modified copies of readonly objects — no custom `with*()` clone methods needed (PHP 8.5+)
- [ ] `#[\NoDiscard]` attribute applied to methods whose return values must not be silently ignored (PHP 8.5+)
- [ ] Callers of `#[\NoDiscard]`-annotated methods capture the return value — silently discarding it emits a notice at runtime
- [ ] `Uri\Rfc3986\Uri` / `Uri\WhatWg\Url` used for URL parsing — not `parse_url()` which returns an untyped array (PHP 8.5+)
- [ ] Backtick operator not used — deprecated in PHP 8.5; use `shell_exec()` explicitly
- [ ] Non-canonical casts `(boolean)`, `(integer)`, `(double)` not used — deprecated in PHP 8.5
- [ ] `__sleep()` / `__wakeup()` replaced with `__serialize()` / `__unserialize()` — soft-deprecated in PHP 8.5

## Code Quality

- [ ] Constructor promotion used for simple dependency injection — avoids boilerplate property declarations
- [ ] `match` expressions preferred over `switch` for exhaustive value mapping
- [ ] `match` expressions without `default` — verify this is intentional exhaustiveness (throws `UnhandledMatchError` on unmatched value) or a missing case
- [ ] Named arguments used to clarify intent on calls with multiple same-type params
- [ ] Null coalescing `??` and nullsafe `?->` used where appropriate
- [ ] No `isset()` / `empty()` overuse — typed properties and strict null checks preferred
- [ ] No broad `catch (\Exception $e)` — specific exception types caught and handled
- [ ] No `@` error suppression operator — handle errors explicitly
- [ ] No dead code, unused `use` statements, or debug artifacts (`var_dump`, `print_r`, `die`)
- [ ] `sprintf()` or string interpolation used for multi-part strings over concatenation chains

## PSR Standards Compliance

- [ ] **PSR-1**: Class names in `PascalCase`, methods in `camelCase`, constants in `UPPER_CASE`
- [ ] **PSR-4**: Autoloading follows `VendorName\Namespace\ClassName` → `src/Namespace/ClassName.php` mapping
- [ ] **PSR-12 / PER Coding Style**: Code style enforced — 4-space indent, braces on same line for methods, blank lines between methods. [PER Coding Style](https://www.php-fig.org/per/coding-style/) is the current evolving standard that supersedes PSR-12 for PHP 8.x features
- [ ] **PSR-3**: Logger uses `Psr\Log\LoggerInterface` — not a concrete logger class directly
- [ ] **PSR-6 / PSR-16**: Cache uses `Psr\Cache\CacheItemPoolInterface` or `Psr\SimpleCache\CacheInterface` — not proprietary cache APIs
- [ ] **PSR-7**: HTTP messages (`Request`/`Response`) use `Psr\Http\Message\*` interfaces when building middleware or HTTP clients
- [ ] **PSR-11**: Service container uses `Psr\Container\ContainerInterface` — not vendor-specific container directly
- [ ] **PSR-14**: Event dispatcher uses `Psr\EventDispatcher\EventDispatcherInterface` when applicable
- [ ] **PSR-15**: HTTP middleware implements `Psr\Http\Server\MiddlewareInterface`

## OOP & Design

- [ ] Interfaces type-hinted in constructor parameters — not concrete classes
- [ ] Composition preferred over inheritance for code reuse
- [ ] `final` applied to classes not designed for extension
- [ ] `abstract` methods used only when a base class truly enforces a contract
- [ ] No `static` state in business logic classes — hard to test, causes hidden side effects
- [ ] Value objects immutable — use `readonly` classes (PHP 8.2+) or no setters
- [ ] Backed enums (`enum Status: string`) used for closed sets of values — not class constants
- [ ] PHP 8.0+ attributes (`#[Attribute]`) used for metadata — not docblock annotations in new code

## Error Handling

- [ ] Domain-specific exception types used — not generic `\Exception` or `\RuntimeException`
- [ ] Exceptions caught only at the boundary where they can be meaningfully handled
- [ ] No silent catch-and-ignore (`catch (\Exception $e) {}`) — log or rethrow
- [ ] `try/catch/finally` not used for flow control — only for genuine exceptional conditions
- [ ] `@throws` documented for exceptions that callers must handle

## Security

- [ ] No `eval()` or dynamic code execution
- [ ] User input never passed directly to `shell_exec`, `exec`, `system`, `passthru`
- [ ] File paths constructed from user input validated and sanitized against path traversal
- [ ] `unserialize()` not called with user-supplied data — if necessary, `allowed_classes` option set to a strict allowlist
- [ ] Cryptography uses `random_bytes()` / `sodium_*` — not `rand()`, `mt_rand()`, `md5()`
- [ ] `hash_equals()` used for timing-safe comparison of secrets/tokens — not `===`
- [ ] `session_regenerate_id(true)` called after successful login to prevent session fixation
- [ ] `composer audit` runs in CI — no known vulnerabilities in dependencies; `composer.lock` committed

## Testing Readiness

- [ ] Code is written to be testable: dependencies injected, no hidden global state
- [ ] Pure functions and value objects have no side effects — straightforward to unit test
- [ ] Classes using `static` methods or globals are isolated behind interfaces for testability

## Documentation

- [ ] Public methods and interfaces have PHPDoc blocks with `@param` and `@return`
- [ ] Complex algorithms have inline comments explaining the "why" — not the "what"
- [ ] `@throws` documented for methods that propagate exceptions callers must handle

## Anti-Patterns

```php
// Bad — hand-rolled lazy init; prefer PHP 8.4 lazy objects in new code
private ?HeavyService $svc = null;
public function getSvc(): HeavyService { return $this->svc ??= new HeavyService(); }

// Bad — dynamic method call defeats static analysis and OPcache
$method = 'get' . ucfirst($field);
$value  = $object->$method();

// Bad — non-canonical cast (deprecated PHP 8.5)
$n = (integer) $value;

// Bad — string class reference bypasses refactoring tools
$container->get('App\Service\UserService');
// Good
$container->get(UserService::class);
```

- [ ] No `var_dump`, `print_r`, or `error_log` in production code paths
- [ ] No `global` variables — use dependency injection
- [ ] No raw `array` as a catch-all data structure in method signatures — prefer typed DTOs or value objects
- [ ] No `new ClassName()` inside service methods — inject via constructor
- [ ] No magic methods (`__get`, `__set`) in place of explicit typed properties
- [ ] No string class references (`'App\Service\Foo'`) where `Foo::class` can be used
- [ ] `isset()` and `array_key_exists()` not used interchangeably — `isset()` returns `false` for keys with `null` value; `array_key_exists()` returns `true`
- [ ] No dynamic variable variables (`$$var`) in application code — defeats static analysis
- [ ] No `intval()`, `strval()`, `floatval()` — use type casting `(int)`, `(string)`, `(float)` or typed parameters