# PHP Code Review Checklist (8.2+)

Supplements the generic `review-checklist.md` for PHP 8.2+ projects. Covers PHP language best practices — framework-specific concerns live in separate checklists.

---

## Type Safety

- [ ] `declare(strict_types=1)` declared at the top of all PHP files — absence leads to silent type coercion bugs
- [ ] Return types declared on all methods — no missing `void`, `string`, `int`, `array`, etc.
- [ ] Parameter types declared on all function signatures
- [ ] `mixed` used only when type is genuinely unknown — not as a lazy default
- [ ] Nullable types (`?string`) used instead of `string|null` for simple nullable params
- [ ] Union types (`int|string`) preferred over `mixed` when types are known
- [ ] Intersection types (`Iterator&Countable`) used correctly (PHP 8.1+, DNF in 8.2+)
- [ ] DNF types (`(A&B)|null`) used when mixing intersection and union (PHP 8.2+)
- [ ] `never` return type applied to methods that always throw or exit

---

## Modern PHP Features (8.2+)

- [ ] `readonly` classes used for pure value/DTO objects — not just readonly properties (PHP 8.2+)
- [ ] `#[Override]` attribute applied to methods intentionally overriding a parent (PHP 8.3+)
- [ ] `json_validate()` used for JSON format validation instead of `json_decode` + error check (PHP 8.3+)
- [ ] Typed class constants declared with explicit types (PHP 8.3+)
- [ ] Property hooks (`get`/`set`) used instead of trivial getter/setter boilerplate (PHP 8.4+)
- [ ] Asymmetric visibility (`public private(set)`) used for write-restricted properties (PHP 8.4+)
- [ ] `#[\Deprecated]` attribute used on deprecated methods, constants, and traits (PHP 8.4+, extended in 8.5)
- [ ] `array_find()` / `array_find_key()` preferred over manual `foreach` searches (PHP 8.4+)
- [ ] `new` in initializers used where appropriate (`public function __construct(private Logger $log = new NullLogger())`) (PHP 8.1+)
- [ ] `array_first()` / `array_last()` used instead of `reset()` / `end()` for first/last element access (PHP 8.5+)
- [ ] Pipe operator `|>` used for readable left-to-right transformation chains (PHP 8.5+)
- [ ] `clone($obj, ['prop' => $val])` used to derive modified copies of readonly objects (PHP 8.5+)
- [ ] `#[\NoDiscard]` attribute applied to methods whose return values must not be silently ignored (PHP 8.5+)
- [ ] `Uri\Rfc3986\Uri` / `Uri\WhatWg\Url` used for URL parsing — not `parse_url()` (PHP 8.5+)
- [ ] Backtick operator not used — deprecated in PHP 8.5; use `shell_exec()` explicitly
- [ ] Non-canonical casts `(boolean)`, `(integer)`, `(double)` not used — deprecated in PHP 8.5
- [ ] `__sleep()` / `__wakeup()` replaced with `__serialize()` / `__unserialize()` — soft-deprecated in PHP 8.5

---

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
- [ ] `sprintf()` or string interpolation used for multi-part strings over concatenation

---

## PSR Standards Compliance

- [ ] **PSR-1**: Class names in `PascalCase`, methods in `camelCase`, constants in `UPPER_CASE`
- [ ] **PSR-4**: Autoloading follows `VendorName\Namespace\ClassName` → `src/Namespace/ClassName.php` mapping
- [ ] **PSR-12 / PER Coding Style**: Code style enforced — indentation (4 spaces), braces on same line for methods, blank lines between methods. Note: [PER Coding Style](https://www.php-fig.org/per/coding-style/) is the current evolving standard that supersedes PSR-12 for PHP 8.x features
- [ ] **PSR-3**: Logger uses `Psr\Log\LoggerInterface` — not a concrete logger class directly
- [ ] **PSR-6 / PSR-16**: Cache uses `Psr\Cache\CacheItemPoolInterface` or `Psr\SimpleCache\CacheInterface` — not proprietary cache APIs
- [ ] **PSR-7**: HTTP messages (`Request`/`Response`) use `Psr\Http\Message\*` interfaces when building middleware/HTTP clients
- [ ] **PSR-11**: Service container uses `Psr\Container\ContainerInterface` — not vendor-specific container directly
- [ ] **PSR-14**: Event dispatcher uses `Psr\EventDispatcher\EventDispatcherInterface` when applicable
- [ ] **PSR-15**: HTTP middleware implements `Psr\Http\Server\MiddlewareInterface`

---

## OOP & Design

- [ ] Interfaces type-hinted in constructor parameters — not concrete classes
- [ ] Composition preferred over inheritance for code reuse
- [ ] `final` applied to classes not designed for extension
- [ ] `abstract` methods used only when a base class truly enforces a contract
- [ ] No `static` state in business logic classes (hard to test, causes side effects)
- [ ] Value objects immutable — use `readonly` classes or no setters

---

## Security

- [ ] No `eval()` or dynamic code execution
- [ ] User input never passed directly to `shell_exec`, `exec`, `system`, `passthru`
- [ ] File paths constructed from user input validated and sanitized against path traversal
- [ ] `unserialize()` not called with user-supplied data — if necessary, `allowed_classes` option is set to a strict allowlist
- [ ] Cryptography uses `random_bytes()` / `sodium_*` — not `rand()`, `mt_rand()`, `md5()`
- [ ] `hash_equals()` used for timing-safe comparison of secrets/tokens — not `===`
- [ ] `session_regenerate_id(true)` called after successful login to prevent session fixation
- [ ] `composer audit` runs in CI — no known vulnerabilities in dependencies; `composer.lock` is committed

---

## Testing

- [ ] Code is written to be testable: dependencies injected, no hidden global state
- [ ] Pure functions / value objects have no side effects — easy to unit test
- [ ] Classes using `static` methods or globals are isolated behind interfaces for testability

---

## Documentation

- [ ] Public methods and interfaces have PHPDoc blocks with `@param` and `@return`
- [ ] Complex algorithms have inline comments explaining the "why"
- [ ] `@throws` documented for methods that propagate exceptions

---

## Resources

- [PHP 8.2 Release Notes](https://www.php.net/releases/8.2/en.php)
- [PHP 8.3 Release Notes](https://www.php.net/releases/8.3/en.php)
- [PHP 8.4 Release Notes](https://www.php.net/releases/8.4/en.php)
- [PHP 8.5 Release Notes](https://www.php.net/releases/8.5/en.php)
- [PHP The Right Way](https://phptherightway.com/)
- [PSR-1 Basic Coding Standard](https://www.php-fig.org/psr/psr-1/)
- [PSR-4 Autoloading Standard](https://www.php-fig.org/psr/psr-4/)
- [PSR-12 Extended Coding Style](https://www.php-fig.org/psr/psr-12/)
- [PSR-3 Logger Interface](https://www.php-fig.org/psr/psr-3/)
- [PSR-6 Cache Interface](https://www.php-fig.org/psr/psr-6/)
- [PSR-7 HTTP Message Interface](https://www.php-fig.org/psr/psr-7/)
- [PSR-11 Container Interface](https://www.php-fig.org/psr/psr-11/)
- [PSR-14 Event Dispatcher](https://www.php-fig.org/psr/psr-14/)
- [PSR-15 HTTP Handlers](https://www.php-fig.org/psr/psr-15/)
- [Magento 2 Coding Standards](https://developer.adobe.com/commerce/php/coding-standards/) *(for Adobe Commerce projects)*
