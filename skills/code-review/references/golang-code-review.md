# Go Reference — code-review

Supplements `review-checklist.md`, `clean-code-checklist.md`, and `solid-principles.md` for Go projects.
For Gin-specific handler review, also load `gin-code-review.md` if present.

---

## General Go Patterns

Universal conventions that apply across all supported Go versions (1.23+).

### Error Handling

- [ ] Errors returned, not swallowed — `_ = err` only with explicit justification comment
- [ ] Errors wrapped with context: `fmt.Errorf("doing X: %w", err)`
- [ ] Sentinel errors defined with `errors.New` or `fmt.Errorf` at package level; prefixed `Err`
- [ ] `errors.Is` / `errors.As` used for error type/value checks — not string comparison
- [ ] Panics avoided in library code; only acceptable in `main` for truly unrecoverable states

```go
// Good — wraps with context so stack trace is meaningful
func loadConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("loading config from %s: %w", path, err)
    }
    // ...
}

// Bad — caller has no idea where the error originated
return nil, err
```

```go
// Good — errors.Is for sentinel comparison
if errors.Is(err, ErrNotFound) { ... }

// Bad — string comparison breaks wrapping
if err.Error() == "not found" { ... }
```

### Code Quality

- [ ] Exported functions, types, and methods have doc comments
- [ ] Unexported helpers are small and single-purpose
- [ ] Function signatures accept interfaces, not concrete types where it adds flexibility
- [ ] No unused imports, variables, or exported symbols
- [ ] No `init()` with side-effecting operations (DB connections, HTTP calls, global registrations)
- [ ] `sync.Once` used for safe lazy initialisation of singletons — not manual double-checked locking
- [ ] No `interface{}` / `any` where a concrete type or typed interface expresses intent
- [ ] `context.Context` is the first parameter of functions that need it — never stored in structs

```go
// Good — context first, interface dependency injected
func (s *OrderService) Create(ctx context.Context, repo OrderRepository, order Order) error { ... }

// Bad — context stored in struct, concrete type dependency
type OrderService struct {
    ctx  context.Context // wrong
    repo *PostgresRepo   // wrong: concrete type
}
```

### Go Idioms

- [ ] `if err != nil` checks immediately follow the call that may produce the error
- [ ] Named return values used only when they genuinely improve readability
- [ ] `defer` used for resource cleanup (file close, mutex unlock, connection release)
- [ ] Struct embedding used judiciously — not as a shortcut to avoid composition
- [ ] Zero values are useful — structs work correctly without explicit initialisation where feasible
- [ ] `iota` used for enumerated constants with a `String()` method via `stringer` or manually

```go
// Good — defer for cleanup
f, err := os.Open(path)
if err != nil {
    return fmt.Errorf("opening %s: %w", path, err)
}
defer f.Close()

// Bad — no defer; cleanup may be skipped on early return
f, err := os.Open(path)
if err != nil { return err }
// ... long function body with multiple return paths ...
f.Close()
```

### Architecture & Design

- [ ] Dependencies injected via interfaces — not constructed inside functions
- [ ] Packages organised by domain/feature, not by layer (avoid `models/`, `utils/` dumping grounds)
- [ ] Package names are lowercase, single words, and describe what they provide
- [ ] Circular dependencies absent
- [ ] Public API surface is minimal — only export what callers need

### Security

- [ ] No hardcoded secrets, tokens, or credentials
- [ ] User input validated and sanitised before use
- [ ] SQL queries use parameterised statements — no string interpolation into queries
- [ ] Sensitive values (passwords, tokens) not logged or exposed in error messages
- [ ] Context deadlines set on outbound HTTP calls and DB queries
- [ ] HTML rendered with `html/template` — not `text/template` (prevents XSS)
- [ ] `unsafe` package usage is justified with an explanatory comment
- [ ] `govulncheck` runs in CI to detect known vulnerabilities in dependencies

```go
// Good — parameterised query
db.QueryContext(ctx, "SELECT * FROM users WHERE id = $1", userID)

// Bad — string interpolation opens SQL injection
db.QueryContext(ctx, fmt.Sprintf("SELECT * FROM users WHERE id = %s", userID))
```

### Testing

- [ ] New public behaviour has tests
- [ ] Table-driven tests used for multiple similar cases
- [ ] Integration tests marked with `testing.Short()` guard
- [ ] Tests run clean under `go test -race ./...`
- [ ] No `time.Sleep` for synchronisation in tests
- [ ] `t.Cleanup` used for test resource teardown — preferred over `defer` in test helpers

### Module Hygiene

- [ ] `go mod tidy` has been run — no unused or missing dependencies
- [ ] `go.sum` is committed and consistent with `go.mod`
- [ ] `govulncheck ./...` passes — no known vulnerabilities

---

## Go 1.23

Patterns and features available as of Go 1.23 (the older of the two currently supported releases).

### Concurrency

- [ ] Goroutines respect context cancellation — `select` on `ctx.Done()`
- [ ] No goroutine leaks — every goroutine has a clear exit condition
- [ ] Shared mutable state protected with `sync.Mutex`, `sync.RWMutex`, or atomics
- [ ] Channels closed by the sender, never the receiver
- [ ] Worker pool or bounded concurrency used instead of unbounded goroutine spawning
- [ ] `errgroup.Group` used for concurrent work that can fail — replaces `WaitGroup + channel` error handling

```go
// Good — context cancellation honoured
func worker(ctx context.Context, jobs <-chan Job) {
    for {
        select {
        case job, ok := <-jobs:
            if !ok {
                return
            }
            process(job)
        case <-ctx.Done():
            return
        }
    }
}

// Bad — goroutine has no exit path
func leakyWorker(jobs <-chan Job) {
    for job := range jobs {
        process(job)
    }
    // leaks if jobs is never closed
}
```

```go
// Good — errgroup for concurrent fan-out with error collection
g, ctx := errgroup.WithContext(context.Background())
for _, item := range items {
    item := item
    g.Go(func() error {
        return process(ctx, item)
    })
}
if err := g.Wait(); err != nil {
    return fmt.Errorf("processing items: %w", err)
}
```

### Iterators (Go 1.23+)

- [ ] Range-over-function iterators (`iter.Seq`, `iter.Seq2`) used for custom collection traversal instead of ad-hoc callback APIs
- [ ] Iterators call `return` when `yield` returns `false` (early-break contract)

```go
// Good — iter.Seq for lazy, allocation-free traversal
import "iter"

func ActiveItems(items []Item) iter.Seq[Item] {
    return func(yield func(Item) bool) {
        for _, item := range items {
            if item.IsActive {
                if !yield(item) {
                    return // consumer broke early
                }
            }
        }
    }
}

// Bad — allocates full intermediate slice even if caller only needs first match
func ActiveItems(items []Item) []Item {
    var result []Item
    for _, item := range items {
        if item.IsActive {
            result = append(result, item)
        }
    }
    return result
}
```

### Standard Library

- [ ] `slices.Contains()`, `slices.SortFunc()`, `slices.Equal()` used — not manual loops
- [ ] `maps.Keys()`, `maps.Values()`, `maps.Equal()` used — not manual loops
- [ ] `log/slog` structured logger used — not `log.Printf`
- [ ] `min()` / `max()` built-in functions used instead of manual comparisons
- [ ] `cmp.Compare` / `cmp.Or` used for ordered comparisons and defaults

```go
// Good — slices.SortFunc with cmp.Compare
import ("cmp"; "slices")
slices.SortFunc(items, func(a, b Item) int {
    return cmp.Compare(a.Name, b.Name)
})

// Bad — reflect overhead and type-unsafe sort.Slice
sort.Slice(items, func(i, j int) bool {
    return items[i].Name < items[j].Name
})
```

```go
// Good — structured logging with log/slog
slog.Info("request completed",
    "method", r.Method,
    "path", r.URL.Path,
    "status", statusCode,
    "duration_ms", elapsed.Milliseconds(),
)

// Bad — unstructured format string
log.Printf("request completed: %s %s %d %dms", r.Method, r.URL.Path, statusCode, elapsed.Milliseconds())
```

---

## Go 1.24

Only what is new in Go 1.24 compared to Go 1.23.

### Filesystem Sandboxing

- [ ] `os.Root` used for sandboxed filesystem access when path traversal must be restricted

```go
// Good — os.Root enforces filesystem sandbox at the OS level
root, err := os.OpenRoot("/var/data/uploads")
if err != nil {
    return fmt.Errorf("opening upload root: %w", err)
}
defer root.Close()

// All operations are scoped to /var/data/uploads; path traversal is rejected
f, err := root.Open(userProvidedFilename)
if err != nil {
    return fmt.Errorf("opening user file: %w", err)
}

// Bad — path.Join is not sufficient to prevent traversal
f, err := os.Open(filepath.Join("/var/data/uploads", userProvidedFilename))
```

### Benchmarking

- [ ] `b.Loop()` used in benchmarks instead of `for i := 0; i < b.N; i++` (Go 1.24+)

```go
// Good — b.Loop() is preferred in Go 1.24+
func BenchmarkProcess(b *testing.B) {
    data := setupData()
    b.ResetTimer()
    for b.Loop() {
        _ = Process(data)
    }
}

// Old style — still works but b.Loop() is now idiomatic
for i := 0; i < b.N; i++ {
    _ = Process(data)
}
```

### Generic Type Aliases

- [ ] Generic type aliases used for type-safe wrappers where appropriate

```go
// Good — generic alias for a type-safe set
type Set[K comparable] = map[K]bool

// Usage: Set[string], Set[int] — no wrapper type needed
```

### Weak Pointers

- [ ] `weak.Pointer` used for memory-pressure-aware caches instead of unbounded `sync.Map`

```go
import "weak"

type Cache[K comparable, V any] struct {
    mu      sync.Mutex
    entries map[K]weak.Pointer[V]
}

func (c *Cache[K, V]) Get(key K, compute func() *V) *V {
    c.mu.Lock()
    defer c.mu.Unlock()
    if ptr, ok := c.entries[key]; ok {
        if v := ptr.Value(); v != nil {
            return v
        }
    }
    v := compute()
    c.entries[key] = weak.Make(v)
    return v
}
```

---

## Go 1.25 (upcoming — not yet in stable release)

> Items in this section require Go 1.25+. Current stable is Go 1.24 (as of March 2026). Apply only to projects on pre-release builds.

- [ ] `testing/synctest` used for timing-sensitive concurrent tests — not `time.Sleep`
- [ ] `runtime.SetDefaultGOMAXPROCS()` called if cgroup CPU limit auto-detection needs overriding (1.25+ auto-detects)
- [ ] `runtime/trace.FlightRecorder` used for low-overhead in-production trace capture

```go
// Good — testing/synctest for deterministic concurrent test (Go 1.25+)
import "testing/synctest"

func TestCacheExpiry(t *testing.T) {
    synctest.Run(func() {
        cache := NewCache(5 * time.Second)
        cache.Set("key", "value")
        time.Sleep(6 * time.Second) // fake — advances instantly
        assert.Nil(t, cache.Get("key"), "entry should have expired")
    })
}
```

---

## Go 1.26 (upcoming — not yet in stable release)

> Items in this section require Go 1.26+. Current stable is Go 1.24 (as of March 2026). Apply only to projects on pre-release builds.

- [ ] `go fix -fix=modernize ./...` run periodically to auto-apply modern Go idioms
- [ ] `new(T, value)` used to allocate and initialise a pointer in one expression
- [ ] `crypto/hpke` used for hybrid public key encryption instead of manual ECIES implementations
- [ ] Green Tea GC (enabled by default in 1.26) — no code change required; verify no GOGC overrides are set unnecessarily

```go
// Good (Go 1.26+) — allocate and initialise in one expression
p := new(Config, Config{Host: "localhost", Port: 5432})

// Old approach
p := new(Config)
*p = Config{Host: "localhost", Port: 5432}
```

```bash
# Good — run before merging to auto-fix outdated patterns
go fix -fix=modernize ./...
```

---

## Resources

- [Effective Go](https://go.dev/doc/effective_go)
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)
- [Go 1.23 Release Notes](https://go.dev/doc/go1.23)
- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)
- [Go 1.25 Release Notes](https://go.dev/doc/go1.25)
- [Go 1.26 Release Notes](https://go.dev/doc/go1.26)
- [slices package](https://pkg.go.dev/slices)
- [maps package](https://pkg.go.dev/maps)
- [iter package](https://pkg.go.dev/iter)
- [weak package](https://pkg.go.dev/weak)
- [log/slog package](https://pkg.go.dev/log/slog)
- [govulncheck](https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck)
