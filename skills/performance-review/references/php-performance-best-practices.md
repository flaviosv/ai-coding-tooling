# PHP Performance Best Practices (8.2+)

Applies to: PHP 8.2+ projects. Covers PHP language-level performance patterns — framework-specific optimizations live in separate guides.

---

## OPcache

OPcache eliminates repeated compilation overhead. In production:

```ini
; php.ini
opcache.enable=1
opcache.validate_timestamps=0   ; never stat files in production
opcache.memory_consumption=256
opcache.max_accelerated_files=20000
opcache.jit=tracing             ; PHP 8.0+ JIT — significant gains for CPU-bound code
opcache.jit_buffer_size=64M
```

Never disable OPcache during deployment — use `opcache_reset()` via a CLI script or use atomic deploys.

### Preloading (PHP 8.0+)

Preloading compiles and loads frequently-used files into shared memory at server startup, eliminating per-request file parsing:

```ini
; php.ini — point to a preload script run once at FPM startup
opcache.preload=/var/www/app/preload.php
opcache.preload_user=www-data
```

```php
// preload.php — list files to preload
$files = glob('/var/www/app/src/**/*.php', GLOB_BRACE);
foreach ($files as $file) {
    opcache_compile_file($file);
}
```

Preloading is most effective for framework core files and frequently-used service classes. Changes to preloaded files require an FPM restart.

---

## Avoid Repeated Expensive Calls

Cache the result of expensive computations within the same request:

```php
// Note: PHP's PCRE extension caches compiled regex patterns internally,
// so there is no recompilation overhead on repeated calls with the same pattern.
// The primary benefit of a constant is readability and preventing accidental
// pattern drift across multiple call sites — not performance.
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

## String Operations

```php
// Good — str_contains / str_starts_with / str_ends_with (PHP 8.0+) are faster than strpos tricks
if (str_contains($haystack, $needle)) { ... }

// Bad — less readable, marginally slower
if (strpos($haystack, $needle) !== false) { ... }

// Good — implode for building strings in loops
$parts = [];
foreach ($items as $item) {
    $parts[] = $item->getName();
}
$result = implode(', ', $parts);

// Bad — string concatenation in loop causes repeated allocation
$result = '';
foreach ($items as $item) {
    $result .= $item->getName() . ', ';
}
```

---

## Arrays

```php
// Good — array_column extracts a column from a multi-dimensional array efficiently
// PHP's internal implementation is faster than a manual foreach loop
$ids = array_column($items, 'id');
$indexedByKey = array_column($records, null, 'id'); // index by 'id' field

// Good — array_map with a named function or arrow fn avoids closure overhead
$names = array_map(fn(Item $i) => $i->getName(), $items);

// Good — array_find (PHP 8.4+) short-circuits on first match
$match = array_find($items, fn(Item $i) => $i->getId() === $targetId);

// Bad — manual loop with break for a simple find
$match = null;
foreach ($items as $item) {
    if ($item->getId() === $targetId) {
        $match = $item;
        break;
    }
}

// Good — isset() for O(1) key existence checks on large arrays
if (isset($map[$key])) { ... }

// Bad — in_array on large arrays is O(n)
if (in_array($key, array_keys($map))) { ... }
```

---

## Memory Management

```php
// Good — generators for large datasets avoid loading everything into memory
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

---

## Readonly and Immutability

`readonly` properties (8.1+) and `readonly` classes (8.2+) allow the runtime to make internal optimizations and signal intent clearly:

```php
// Good — readonly class: all properties immutable, no clone guard needed
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

## Avoid Dynamic Features in Hot Paths

```php
// Bad — variable variables and dynamic method calls defeat OPcache & static analysis
$method = 'get' . ucfirst($field);
$value = $object->$method();

// Good — explicit dispatch
$value = match ($field) {
    'name'  => $object->getName(),
    'email' => $object->getEmail(),
    default => throw new \InvalidArgumentException("Unknown field: $field"),
};
```

---

## Fibers (PHP 8.1+)

Use Fibers for cooperative concurrency in I/O-bound code without external async frameworks:

```php
$fiber = new \Fiber(function (): void {
    $value = \Fiber::suspend('first suspension');
    echo "Resumed with: $value\n";
});

$first = $fiber->start();          // runs until first suspend
$fiber->resume('hello');           // resumes the fiber
```

Fibers are not threads — they are cooperative. Use them when integrating with event-loop-based libraries.

---

## Session Performance

PHP-FPM holds a file lock for the session file for the entire duration of each request. Concurrent requests from the same user are serialized:

```php
// Good — release the session lock as early as possible
session_start();
$userData = $_SESSION['user'];  // read what you need
session_write_close();           // release the lock — subsequent requests can proceed concurrently

// Bad — session lock held for entire request including slow operations
session_start();
// ... slow DB queries, API calls — all block concurrent requests from this user
```

For read-only access to session data, call `session_write_close()` immediately after reading.

---

## Database Performance

The most common PHP performance bottleneck is database access:

- Use **prepared statements** to avoid repeated query parsing and SQL injection: `$stmt = $pdo->prepare('SELECT * FROM users WHERE id = ?')`
- Use **PDO persistent connections** (`PDO::ATTR_PERSISTENT => true`) to reuse connections across requests in long-running contexts
- **Never run queries in loops** — batch with `IN (...)` or use `array_column()` to build an in-memory index
- Measure slow queries with `EXPLAIN ANALYZE` — don't optimize blind

---

## Profiling Before Optimizing

Always measure before changing code for performance:

- **Xdebug** (`xdebug.mode=profile`) — generates cachegrind files for KCacheGrind / Webgrind
- **Blackfire** — low-overhead profiler suitable for staging environments
- **Tideways** — continuous profiling for production PHP applications
- **SPX** — lightweight open-source profiler for local development

Do not optimize code paths that are not in the hot path — measure first.

---

## PHP 8.5 Performance Features

### Pipe Operator for Readable Transformation Chains

```php
// Good — pipe operator (PHP 8.5+): left-to-right, no temp variables
$result = $rawInput
    |> trim(...)
    |> strtolower(...)
    |> htmlspecialchars(...);

// Equivalent old approach — harder to read, same performance
$result = htmlspecialchars(strtolower(trim($rawInput)));
```

### array_first() / array_last()

```php
// Good — PHP 8.5+: dedicated functions, no side-effects on array pointer
$first = array_first($items);
$last  = array_last($items);

// Bad — reset()/end() mutate the internal array pointer
$first = reset($items);
$last  = end($items);
```

### Persistent cURL Share Handles

```php
// Good — PHP 8.5+: share handle persists across requests (reuses DNS/TLS)
$share = curl_share_init_persistent(['dns', 'ssl_session']);
$ch = curl_init($url);
curl_setopt($ch, CURLOPT_SHARE, $share);
curl_exec($ch);

// Old approach — new share per request, no cross-request reuse
$share = curl_share_init();
```

---

## Resources

- [PHP 8.2 Performance Improvements](https://www.php.net/releases/8.2/en.php)
- [PHP 8.4 Property Hooks](https://www.php.net/releases/8.4/en.php)
- [PHP 8.5 Release Notes](https://www.php.net/releases/8.5/en.php)
- [PHP OPcache Configuration](https://www.php.net/manual/en/opcache.configuration.php)
- [PHP Fibers RFC](https://wiki.php.net/rfc/fibers)
- [Generators in PHP](https://www.php.net/manual/en/language.generators.overview.php)
- [Blackfire Profiler](https://blackfire.io/)
