# PHP Performance Review Reference (PHP 8.2–8.5)

Applies to: PHP 8.2–8.5 projects. Covers PHP language-level performance patterns — framework-specific optimizations live in separate guides.

---

## General PHP Performance Patterns

### OPcache

OPcache eliminates repeated compilation overhead. In production:

```ini
opcache.enable=1
opcache.validate_timestamps=0   ; never stat files in production
opcache.memory_consumption=256
opcache.max_accelerated_files=20000
```

Never disable OPcache during deployment — use `opcache_reset()` via CLI or atomic deploys.

#### JIT

JIT benefits CPU-bound code (math, image processing, parsers). For I/O-bound web request/response cycles, gain is modest — profile before enabling.

```ini
; Tracing JIT — highest performance for CPU-bound workloads
opcache.jit=tracing
opcache.jit_buffer_size=64M
; Function JIT — lower overhead; good default for I/O-bound web apps
; opcache.jit=function
; opcache.jit_buffer_size=32M
; Disable JIT — valid for pure I/O-bound apps where profiling shows no gain
; opcache.jit=off
```

#### Preloading (PHP 8.0+)

Compiles frequently-used files into shared memory at FPM startup, eliminating per-request parsing. Changes require FPM restart.

```ini
opcache.preload=/var/www/app/preload.php
opcache.preload_user=www-data
```

```php
// preload.php
$files = glob('/var/www/app/src/**/*.php', GLOB_BRACE);
foreach ($files as $file) {
    opcache_compile_file($file);
}
```

### Avoid Repeated Expensive Calls

Cache results of expensive computations within the same request:

```php
// Good
class Validator
{
    private const DATE_PATTERN = '/^\d{4}-\d{2}-\d{2}$/';
    public function isValid(string $input): bool
    {
        return (bool) preg_match(self::DATE_PATTERN, $input);
    }
}
```

### String Operations

```php
// Good — str_contains / str_starts_with / str_ends_with (PHP 8.0+)
if (str_contains($haystack, $needle)) { ... }

// Bad
if (strpos($haystack, $needle) !== false) { ... }

// Good — implode() for building strings in loops; single allocation
$parts = [];
foreach ($items as $item) {
    $parts[] = $item->getName();
}
$result = implode(', ', $parts);

// Bad — repeated allocations
$result = '';
foreach ($items as $item) {
    $result .= $item->getName() . ', ';
}
```

### Arrays

```php
// Good — array_column() extracts a column efficiently
$ids = array_column($items, 'id');
$indexedByKey = array_column($records, null, 'id');

// Good — array_map with arrow function
$names = array_map(fn(Item $i) => $i->getName(), $items);

// Good — array_find() (PHP 8.4+): short-circuits on first match
$match = array_find($items, fn(Item $i) => $i->getId() === $targetId);

// Bad — manual foreach+break
$match = null;
foreach ($items as $item) {
    if ($item->getId() === $targetId) {
        $match = $item;
        break;
    }
}

// Good — isset() for O(1) key existence
if (isset($map[$key])) { ... }

// Bad — O(n)
if (in_array($key, array_keys($map))) { ... }
```

### Memory Management

```php
// Good — generators for large datasets; avoids loading everything into memory
function readLines(string $file): \Generator
{
    $handle = fopen($file, 'r');
    while (($line = fgets($handle)) !== false) {
        yield $line;
    }
    fclose($handle);
}
foreach (readLines('large.csv') as $line) {
    process($line);
}

// Bad — loads entire file into memory
$lines = file('large.csv');
foreach ($lines as $line) {
    process($line);
}
```

#### WeakMap for Object-Keyed Caches

Use `WeakMap` when caching data keyed by objects — entries are automatically removed when the key is GC'd, unlike `SplObjectStorage` or `spl_object_id()` arrays.

```php
// Good — no strong reference to key
$cache = new \WeakMap();
function computeExpensive(object $obj, \WeakMap $cache): Result
{
    return $cache[$obj] ??= runExpensiveComputation($obj);
}

// Bad — prevents GC; requires manual cleanup
$cache = [];
$cache[spl_object_id($obj)] = runExpensiveComputation($obj);
```

### Lazy Objects (PHP 8.4+)

Native lazy objects defer initialization until first property access. Prefer over hand-rolled null-check patterns.

```php
// Good — lazy ghost
$lazy = (new \ReflectionClass(HeavyService::class))
    ->newLazyGhost(function (HeavyService $service): void {
        $service->__construct($realDependency);
    });

// Good — lazy proxy
$lazy = (new \ReflectionClass(HeavyService::class))
    ->newLazyProxy(fn(HeavyService $ghost) => new HeavyService($realDependency));

// Bad — hand-rolled lazy pattern
class Container
{
    private ?HeavyService $service = null;
    public function getService(): HeavyService
    {
        return $this->service ??= new HeavyService($this->dep);
    }
}
```

DI containers (Symfony 6.4+, Laravel 11+) use lazy objects internally — prefer native lazy objects over custom proxy solutions.

### Readonly and Immutability

`readonly` classes (8.2+) allow runtime optimizations and signal clear intent. Immutable objects can be shared safely without defensive copying.

```php
readonly class Money
{
    public function __construct(
        public int $amount,
        public string $currency,
    ) {}
    public function add(Money $other): self
    {
        return new self($this->amount + $other->amount, $this->currency);
    }
}
```

### Avoid Dynamic Features in Hot Paths

```php
// Bad — defeats OPcache, static analysis, IDE support
$method = 'get' . ucfirst($field);
$value  = $object->$method();

// Good — explicit dispatch; OPcache-friendly
$value = match ($field) {
    'name'  => $object->getName(),
    'email' => $object->getEmail(),
    default => throw new \InvalidArgumentException("Unknown field: $field"),
};
```

### Fibers (PHP 8.1+)

Fibers enable cooperative concurrency in I/O-bound code. Not threads — cooperative only. Use when integrating with event-loop libraries (ReactPHP, Revolt). No benefit in traditional FPM request/response cycles.

```php
$fiber = new \Fiber(function (): void {
    $value = \Fiber::suspend('first suspension');
    echo "Resumed with: $value\n";
});
$first = $fiber->start();
$fiber->resume('hello');
```

### Session Performance

PHP-FPM holds a file lock on the session file for the entire request. Concurrent requests from the same user are serialized.

```php
// Good — release session lock early
session_start();
$userData = $_SESSION['user'];
session_write_close();

// Bad — lock held through slow operations
session_start();
// ... slow DB queries/API calls block all concurrent requests from this user
```

### Database Performance

Most common PHP performance bottleneck:

- Use **prepared statements** to avoid repeated query parsing and prevent SQL injection
- Use **PDO persistent connections** (`PDO::ATTR_PERSISTENT => true`) to reuse connections across FPM requests
- **Never run queries in loops** — batch with `IN (...)` or build in-memory index with `array_column()`
- Measure slow queries with `EXPLAIN ANALYZE` — do not optimize without evidence

### Profiling Before Optimizing

MUST measure before changing code for performance:

- **Xdebug** (`xdebug.mode=profile`) — cachegrind files for KCacheGrind / Webgrind
- **Blackfire** — low-overhead, suitable for staging
- **Tideways** — continuous profiling for production
- **SPX** — lightweight open-source for local dev

## PHP 8.5 Performance Features

### Pipe Operator

```php
// Good — left-to-right, no temp variables, same performance as nested calls
$result = $rawInput
    |> trim(...)
    |> strtolower(...)
    |> htmlspecialchars(...);

// Bad
$result = htmlspecialchars(strtolower(trim($rawInput)));
```

### array_first() / array_last()

```php
// Good — no side-effects on array pointer
$first = array_first($items);
$last  = array_last($items);

// Bad — mutates internal array pointer
$first = reset($items);
$last  = end($items);
```

### Persistent cURL Share Handles

```php
// Good — share handle persists across requests (reuses DNS/TLS state)
$share = curl_share_init_persistent(['dns', 'ssl_session']);
$ch = curl_init($url);
curl_setopt($ch, CURLOPT_SHARE, $share);
curl_exec($ch);

// Bad — new share handle per request; no cross-request reuse
$share = curl_share_init();
```
