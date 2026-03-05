# PHP Performance Review Reference (PHP 8.2–8.5)

Applies to: PHP 8.2–8.5 projects. Covers PHP language-level performance patterns — framework-specific optimizations live in separate guides.

---

## General PHP Performance Patterns

Patterns that apply across all PHP 8.2–8.5 projects regardless of version.

### OPcache

OPcache eliminates repeated compilation overhead. In production:

```ini
; php.ini
opcache.enable=1
opcache.validate_timestamps=0   ; never stat files in production — eliminates file-stat syscalls per request
opcache.memory_consumption=256
opcache.max_accelerated_files=20000
```

Never disable OPcache during deployment — use `opcache_reset()` via a CLI script or atomic deploys.

#### JIT

PHP 8.0+ includes a JIT compiler. JIT provides the most benefit for CPU-bound code (mathematical operations, image processing, parsers). For typical web request/response cycles dominated by I/O, the gain is modest — always profile before enabling in production.

```ini
; Tracing JIT — highest performance for CPU-bound workloads (queues, workers, batch jobs)
opcache.jit=tracing
opcache.jit_buffer_size=64M

; Function JIT — lower overhead; good default for I/O-bound web apps
; opcache.jit=function
; opcache.jit_buffer_size=32M

; Disable JIT — valid choice for pure I/O-bound web apps where profiling shows no gain
; opcache.jit=off
```

#### Preloading (PHP 8.0+)

Preloading compiles frequently-used files into shared memory at FPM startup, eliminating per-request parsing:

```ini
; php.ini
opcache.preload=/var/www/app/preload.php
opcache.preload_user=www-data
```

```php
// preload.php — compile core files into OPcache shared memory at startup
$files = glob('/var/www/app/src/**/*.php', GLOB_BRACE);
foreach ($files as $file) {
    opcache_compile_file($file);
}
```

Preloading is most effective for framework core files and frequently-used service classes. Changes to preloaded files require an FPM restart.

---

### Avoid Repeated Expensive Calls

Cache results of expensive computations within the same request:

```php
// PHP's PCRE extension caches compiled regex patterns internally — no recompilation per call.
// A constant buys readability and prevents accidental pattern drift across call sites.
class Validator
{
    private const DATE_PATTERN = '/^\d{4}-\d{2}-\d{2}$/';

    public function isValid(string $input): bool
    {
        return (bool) preg_match(self::DATE_PATTERN, $input);
    }
}
```

---

### String Operations

```php
// Good — str_contains / str_starts_with / str_ends_with (PHP 8.0+): cleaner and marginally faster than strpos tricks
if (str_contains($haystack, $needle)) { ... }

// Bad — less readable
if (strpos($haystack, $needle) !== false) { ... }

// Good — implode() for building strings in loops; single allocation
$parts = [];
foreach ($items as $item) {
    $parts[] = $item->getName();
}
$result = implode(', ', $parts);

// Bad — string concatenation in a loop causes repeated allocations
$result = '';
foreach ($items as $item) {
    $result .= $item->getName() . ', ';
}
```

---

### Arrays

```php
// Good — array_column() extracts a column efficiently; faster than a manual foreach
$ids = array_column($items, 'id');
$indexedByKey = array_column($records, null, 'id'); // index by 'id' field

// Good — array_map with arrow function; avoids closure allocation overhead
$names = array_map(fn(Item $i) => $i->getName(), $items);

// Good — array_find() (PHP 8.4+): short-circuits on first match
$match = array_find($items, fn(Item $i) => $i->getId() === $targetId);

// Bad — manual foreach+break for a simple predicate search
$match = null;
foreach ($items as $item) {
    if ($item->getId() === $targetId) {
        $match = $item;
        break;
    }
}

// Good — isset() for O(1) key existence checks on large arrays
if (isset($map[$key])) { ... }

// Bad — in_array on array_keys is O(n)
if (in_array($key, array_keys($map))) { ... }
```

---

### Memory Management

```php
// Good — generators for large datasets; avoids loading everything into memory at once
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

// Bad — loads the entire file into memory before processing
$lines = file('large.csv');
foreach ($lines as $line) {
    process($line);
}
```

#### WeakMap for Object-Keyed Caches

Use `WeakMap` when caching data keyed by objects. Unlike `SplObjectStorage` or plain arrays keyed by `spl_object_id()`, `WeakMap` does not prevent garbage collection of the key object — entries are automatically removed when the key is GC'd.

```php
// Good — WeakMap: cache per-object results without holding a strong reference to the key
$cache = new \WeakMap();

function computeExpensive(object $obj, \WeakMap $cache): Result
{
    return $cache[$obj] ??= runExpensiveComputation($obj);
}

// Bad — array keyed by spl_object_id: prevents GC of the object; requires manual cleanup
$cache = [];
$cache[spl_object_id($obj)] = runExpensiveComputation($obj);
// $obj cannot be GC'd while the cache holds the entry
```

---

### Lazy Objects (PHP 8.4+)

PHP 8.4 native lazy objects defer initialization until the first property is accessed. Prefer over hand-rolled null-check patterns.

```php
// Good — lazy ghost: same class, initialized on first property access
$lazy = (new \ReflectionClass(HeavyService::class))
    ->newLazyGhost(function (HeavyService $service): void {
        // Called once, on first property access
        $service->__construct($realDependency);
    });
// HeavyService constructor is not called until $lazy->someProperty is first accessed

// Good — lazy proxy: virtual proxy wrapping the real object
$lazy = (new \ReflectionClass(HeavyService::class))
    ->newLazyProxy(fn(HeavyService $ghost) => new HeavyService($realDependency));

// Bad — hand-rolled lazy pattern with a null-check guard
class Container
{
    private ?HeavyService $service = null;

    public function getService(): HeavyService
    {
        return $this->service ??= new HeavyService($this->dep);
    }
}
```

DI containers (Symfony 6.4+, Laravel 11+) use lazy objects internally for service proxies — prefer native lazy objects over custom proxy solutions in application code.

---

### Readonly and Immutability

`readonly` classes (8.2+) allow the runtime to make internal optimizations and signal clear intent. Immutable objects can be shared safely across contexts without defensive copying.

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

---

### Avoid Dynamic Features in Hot Paths

```php
// Bad — dynamic method calls defeat OPcache, static analysis, and IDE support
$method = 'get' . ucfirst($field);
$value  = $object->$method();

// Good — explicit dispatch; OPcache-friendly, statically analysable
$value = match ($field) {
    'name'  => $object->getName(),
    'email' => $object->getEmail(),
    default => throw new \InvalidArgumentException("Unknown field: $field"),
};
```

---

### Fibers (PHP 8.1+)

Use Fibers for cooperative concurrency in I/O-bound code without external async frameworks:

```php
$fiber = new \Fiber(function (): void {
    $value = \Fiber::suspend('first suspension');
    echo "Resumed with: $value\n";
});

$first = $fiber->start();   // runs until Fiber::suspend()
$fiber->resume('hello');    // resumes the fiber
```

Fibers are not threads — they are cooperative. Use them when integrating with event-loop-based libraries (ReactPHP, Revolt). For traditional FPM request/response cycles, fibers provide no performance benefit.

---

### Session Performance

PHP-FPM holds a file lock for the session file for the entire request duration. Concurrent requests from the same user are serialized:

```php
// Good — release the session lock as early as possible
session_start();
$userData = $_SESSION['user']; // read what you need
session_write_close();          // release the lock — subsequent requests from this user can proceed

// Bad — session lock held through slow DB queries and API calls
session_start();
// ... slow operations here — all concurrent requests from this user are blocked
```

For read-only session access, call `session_write_close()` immediately after reading.

---

### Database Performance

The most common PHP performance bottleneck is database access:

- Use **prepared statements** to avoid repeated query parsing and prevent SQL injection: `$stmt = $pdo->prepare('SELECT * FROM users WHERE id = ?')`
- Use **PDO persistent connections** (`PDO::ATTR_PERSISTENT => true`) to reuse connections across requests in long-running FPM contexts
- **Never run queries in loops** — batch with `IN (...)` clauses or build an in-memory index with `array_column()`
- Measure slow queries with `EXPLAIN ANALYZE` — do not optimize without evidence

---

### Profiling Before Optimizing

Always measure before changing code for performance reasons:

- **Xdebug** (`xdebug.mode=profile`) — generates cachegrind files for KCacheGrind / Webgrind
- **Blackfire** — low-overhead profiler suitable for staging environments
- **Tideways** — continuous profiling for production PHP applications
- **SPX** — lightweight open-source profiler for local development

Do not optimize code paths that are not in the hot path — measure first.

---

## PHP 8.5 Performance Features

### Pipe Operator for Readable Transformation Chains

```php
// Good — pipe operator (PHP 8.5+): left-to-right, no temp variables, same performance as nested calls
$result = $rawInput
    |> trim(...)
    |> strtolower(...)
    |> htmlspecialchars(...);

// Equivalent — harder to read
$result = htmlspecialchars(strtolower(trim($rawInput)));
```

### array_first() / array_last()

```php
// Good — PHP 8.5+: no side-effects on array pointer
$first = array_first($items);
$last  = array_last($items);

// Bad — reset()/end() mutate the internal array pointer; can cause subtle bugs in iteration
$first = reset($items);
$last  = end($items);
```

### Persistent cURL Share Handles

```php
// Good — PHP 8.5+: share handle persists across requests (reuses DNS resolution and TLS session state)
$share = curl_share_init_persistent(['dns', 'ssl_session']);
$ch = curl_init($url);
curl_setopt($ch, CURLOPT_SHARE, $share);
curl_exec($ch);

// Old approach — new share handle per request; no cross-request DNS/TLS reuse
$share = curl_share_init();
```

---

## Resources

- [PHP 8.4 Release Notes](https://www.php.net/releases/8.4/en.php)
- [PHP 8.4 Lazy Objects RFC](https://wiki.php.net/rfc/lazy-objects)
- [PHP 8.5 Release Notes](https://www.php.net/releases/8.5/en.php)
- [PHP OPcache Configuration](https://www.php.net/manual/en/opcache.configuration.php)
- [PHP JIT Compiler](https://www.php.net/manual/en/opcache.configuration.php#ini.opcache.jit)
- [PHP Fibers RFC](https://wiki.php.net/rfc/fibers)
- [Generators in PHP](https://www.php.net/manual/en/language.generators.overview.php)
- [WeakMap documentation](https://www.php.net/manual/en/class.weakmap.php)
- [Blackfire Profiler](https://blackfire.io/)
