# Go Reference — coding-guidelines

Authoritative style and idiom guide for Go projects. Deviations from these rules are findings.
Sourced from Effective Go, the Go Code Review Comments wiki, and official release notes.

---

## General Go Coding Style

Universal conventions that apply across all supported Go versions (1.23+).

### Naming Conventions

- **Packages**: lowercase, single word, no underscores — `http`, `strconv`, `userauth`
- **Exported identifiers**: PascalCase — `UserService`, `ParseConfig`
- **Unexported identifiers**: camelCase — `userService`, `parseConfig`
- **Interfaces**: use `-er` suffix for single-method interfaces — `Reader`, `Stringer`, `Handler`
- **Constants**: PascalCase if exported, camelCase if unexported; avoid `ALL_CAPS`
- **Acronyms**: keep consistent casing — `HTTPClient`, `URLParser`, `userID`, `parseHTML`
- **Error variables**: prefix with `Err` — `ErrNotFound`, `ErrTimeout`
- **Error strings**: lowercase, no trailing punctuation or newline — `errors.New("connection refused")` not `errors.New("Connection refused.")`
- **Receiver names**: short (1–2 chars), consistent across all methods of the same type, derived from the type name — `s` for `Server`, `r` for `Request`, `u` for `User`. Never `self` or `this`.
- **Constructors**: exported constructor functions use `NewXxx(...)` — `NewServer(...)`, `NewClient(...)`
- **Test files**: suffix `_test.go`; test functions `TestXxx(t *testing.T)`
- **Enumeration types**: implement `String() string` via `stringer` or manually so values are human-readable in logs

### File Organization

- One package per directory; package name matches directory name
- Group related types, functions, and methods in the same file
- Keep `main.go` thin — delegate logic to packages
- File names: lowercase with underscores for multi-word names — `user_service.go`
- Order within a file: package declaration → imports → constants → vars → types → functions
- Group imports: stdlib first, then external, then internal (blank line between groups)
- Import aliases used only for genuine name collisions — not as stylistic preference or abbreviation

```go
import (
    "context"
    "fmt"
    "os"

    "github.com/gin-gonic/gin"
    "golang.org/x/sync/errgroup"

    "github.com/myorg/myapp/internal/domain"
)

// Good — alias required because two packages share the name "v1"
import (
    corev1 "k8s.io/api/core/v1"
    appsv1 "k8s.io/api/apps/v1"
)

// Bad — alias used as abbreviation with no collision
import (
    ctx "context"  // wrong: no collision
    str "strings"  // wrong: same reason
)
```

### Code Structure

- Keep functions short and focused on a single responsibility
- Return early to reduce nesting — guard clauses over deeply nested conditionals
- Prefer explicit over implicit; avoid `init()` unless necessary
- Always use named fields in composite literals for exported types — `Config{Host: "localhost", Port: 5432}` not `Config{"localhost", 5432}`; positional literals break silently when fields are reordered
- Declare empty slices as `var s []int` when nil is acceptable — `nil` slices are valid for `range`, `append`, and `len`; prefer `make([]T, 0, n)` only when capacity pre-allocation matters
- Do not use dot-imports (`import . "pkg"`) — they pollute the local namespace and make identifier origins unclear; acceptable only in `_test.go` files for DSL-style testing packages
- Use `context.Context` as the first parameter for functions that perform I/O or long work
- Accept interfaces, return concrete types by default; return an interface only when the caller genuinely depends on behaviour rather than structure
- Avoid naked returns in functions longer than a few lines
- Design types to be useful at their zero value where possible — `sync.Mutex`, `bytes.Buffer`, `http.Client` are ready to use at zero value

```go
// Good — guard clause; minimal nesting
func processOrder(ctx context.Context, order Order) error {
    if order.ID == "" {
        return ErrMissingOrderID
    }
    if !order.IsValid() {
        return fmt.Errorf("invalid order %s: %w", order.ID, ErrValidation)
    }
    return submitOrder(ctx, order)
}

// Bad — nested conditionals
func processOrder(ctx context.Context, order Order) error {
    if order.ID != "" {
        if order.IsValid() {
            return submitOrder(ctx, order)
        }
        return ErrValidation
    }
    return ErrMissingOrderID
}
```

### Error Handling

- Always handle errors — never assign to `_` unless intentionally discarding with a comment
- Wrap errors with context: `fmt.Errorf("parsing user %d: %w", id, err)`
- Use `errors.Is` / `errors.As` for error type checks — not string comparison
- Define sentinel errors with `var ErrFoo = errors.New("...")` at package level
- Define custom error types with `type FooError struct {}` when extra context is needed
- Log errors at the boundary where they are handled, not at every level

```go
// Good
var ErrNotFound = errors.New("not found")

func (r *UserRepository) Get(ctx context.Context, id string) (*User, error) {
    user, err := r.db.FindByID(ctx, id)
    if errors.Is(err, sql.ErrNoRows) {
        return nil, fmt.Errorf("user %s: %w", id, ErrNotFound)
    }
    if err != nil {
        return nil, fmt.Errorf("querying user %s: %w", id, err)
    }
    return user, nil
}

// Bad — error string comparison breaks wrapping
if err.Error() == "not found" { ... }
```

### Idioms and Patterns

- Use `defer` for cleanup — closing files, unlocking mutexes, releasing connections
- Prefer `for range` over index loops when the index is unused
- Use `make([]T, 0, n)` when the final length is known to avoid reallocations
- Use `sync.Once` for one-time initialisation; `sync.RWMutex` for read-heavy shared state
- Use channels for signalling, mutexes for protecting shared state — do not mix roles
- Goroutines must have a clear shutdown path — pass `context.Context` for cancellation; use `sync.WaitGroup` or `errgroup.Group` to wait for completion
- Use `errgroup.Group` for concurrent work that can fail — collects the first error and cancels a derived context

```go
// Good — errgroup for concurrent fan-out
g, ctx := errgroup.WithContext(context.Background())
for _, item := range items {
    item := item
    g.Go(func() error {
        return process(ctx, item)
    })
}
if err := g.Wait(); err != nil {
    return fmt.Errorf("processing batch: %w", err)
}
```

```go
// Good — defer for cleanup
f, err := os.Open(path)
if err != nil {
    return fmt.Errorf("opening %s: %w", path, err)
}
defer f.Close()
```

### Anti-Patterns to Avoid

- Do not use `panic` for normal error flow — only for unrecoverable programmer errors
- Do not store `context.Context` in structs — pass it as a function parameter
- Do not use global mutable state without synchronisation
- Do not shadow `err` across sequential `:=` assignments — use `=` for subsequent assignments to the same `err` variable
- Do not use `interface{}` / `any` when a concrete type or typed interface expresses intent
- Do not copy a `sync.Mutex` — always use a pointer receiver or embed by value in a struct
- Do not ignore the second return value of map lookups when the zero value is ambiguous
- Methods that require the caller to already hold a lock use a `Locked` suffix — `processLocked()`, `validateLocked()`. The public method acquires the lock; the internal one assumes it is already held. This makes lock discipline explicit at the call site.

```go
// Good — lock discipline is visible in naming
func (s *Server) Shutdown() {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.shutdownLocked()
}

func (s *Server) shutdownLocked() {
    // called with s.mu held
    s.state = stateStopped
}

// Bad — unclear whether caller must hold the lock
func (s *Server) shutdown() {
    s.state = stateStopped
}
```

```go
// Bad — err shadowing across sequential :=
data, err := fetchData(ctx)
result, err := processData(data) // use = here

// Good
data, err := fetchData(ctx)
if err != nil {
    return fmt.Errorf("fetching: %w", err)
}
result, err := processData(data)
if err != nil {
    return fmt.Errorf("processing: %w", err)
}
```

```go
// Bad — map lookup without ok check; zero value is ambiguous
count := counters["key"]

// Good — check the presence explicitly
count, ok := counters["key"]
if !ok {
    // key is absent; handle appropriately
}
```

### Tooling

- Run `gofmt` (or `goimports`) on every file — formatting is non-negotiable in Go
- Use `golangci-lint` with at minimum `errcheck`, `staticcheck`, `gosimple`, and `govet` enabled
- `goimports` handles import grouping automatically — prefer it over `gofmt` where available

---

## Go 1.23

Patterns and features available as of Go 1.23 (the older of the two currently supported releases).

### Iterators

Use range-over-function iterators (`iter.Seq`, `iter.Seq2`) for custom collection traversal instead of ad-hoc callback APIs or allocating intermediate slices.

```go
// Good — lazy iterator; no allocation for the filtered sequence
func ActiveItems(items []Item) iter.Seq[Item] {
    return func(yield func(Item) bool) {
        for _, item := range items {
            if item.IsActive {
                if !yield(item) {
                    return // respect early termination
                }
            }
        }
    }
}

// Caller — clean for-range syntax, stops early if needed
for item := range ActiveItems(allItems) {
    fmt.Println(item.Name)
}

// Bad — ad-hoc callback; unnatural API
func ForEachActive(items []Item, fn func(Item)) {
    for _, item := range items {
        if item.IsActive {
            fn(item)
        }
    }
}
```

### `slices` and `maps` Packages

Use `slices` and `maps` stdlib packages instead of manual loops for common operations.

```go
// Good — type-safe sort with cmp.Compare
slices.SortFunc(items, func(a, b Item) int {
    return cmp.Compare(a.Name, b.Name)
})

// Bad — sort.Slice uses interface boxing
sort.Slice(items, func(i, j int) bool {
    return items[i].Name < items[j].Name
})

// Good — idiomatic membership test
if slices.Contains(tags, "admin") { ... }

// Good — delete map entry inside iteration (Go 1.23: maps.DeleteFunc)
maps.DeleteFunc(scores, func(k string, v int) bool {
    return v < threshold
})
```

### Structured Logging with `log/slog`

Use `log/slog` for structured logging. Discard `log.Printf` in new code.

```go
// Good — structured, queryable in log aggregators
slog.Info("request completed",
    "method", r.Method,
    "path", r.URL.Path,
    "status", statusCode,
    "duration_ms", elapsed.Milliseconds(),
)
slog.Error("database query failed", "query", queryName, "err", err)

// Bad — unstructured; cannot be parsed by log aggregators
log.Printf("request: %s %s %d %dms", r.Method, r.URL.Path, statusCode, elapsed.Milliseconds())
```

### `min()` / `max()` Built-ins

```go
// Good — built-in; no helper needed
largest := max(a, b, c)
smallest := min(x, y)

// Bad — manual comparison chain
largest := a
if b > largest { largest = b }
if c > largest { largest = c }
```

### `cmp` Package

```go
// Good — cmp.Or for default values (returns first non-zero value)
name := cmp.Or(userProvidedName, "default")

// Good — cmp.Compare for ordered comparisons in sort functions
slices.SortFunc(items, func(a, b Item) int {
    return cmp.Compare(a.Priority, b.Priority)
})
```

---

## Go 1.24

Only what is new in Go 1.24 compared to Go 1.23.

### `os.Root` for Sandboxed Filesystem Access

When accepting user-provided paths, use `os.Root` to scope all filesystem access to a specific directory. This enforces the sandbox at the OS level — path traversal sequences (`../`) are rejected by the OS, not by application code.

```go
// Good — os.Root enforces containment
root, err := os.OpenRoot("/var/data/uploads")
if err != nil {
    return fmt.Errorf("opening upload root: %w", err)
}
defer root.Close()
f, err := root.Open(userFilename) // traversal rejected by OS

// Bad — filepath.Join does NOT prevent traversal; ../../../etc/passwd passes through
f, err := os.Open(filepath.Join("/var/data/uploads", userFilename))
```

### Generic Type Aliases

Use generic type aliases for type-safe wrappers that avoid runtime overhead.

```go
// Good — generic alias; no wrapper struct needed
type Set[K comparable] = map[K]bool

var tags Set[string]
tags = Set[string]{"admin": true, "user": true}
if tags["admin"] { ... }
```

### Weak Pointers

Use `weak.Pointer` for caches where GC reclamation under memory pressure is desirable.

```go
// Good — cache that does not prevent GC from reclaiming values
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

// Bad — sync.Map-based cache grows unboundedly; values are never GC'd
```

### `for i := range n` (Go 1.22+)

```go
// Good — idiomatic integer range (Go 1.22+)
for i := range 10 {
    process(i)
}

// Old style — verbose and error-prone
for i := 0; i < 10; i++ {
    process(i)
}
```

### Enhanced HTTP Routing (Go 1.22+)

```go
// Good — method+path pattern in the mux (Go 1.22+)
mux := http.NewServeMux()
mux.HandleFunc("GET /items/{id}", handler.GetItem)
mux.HandleFunc("POST /items", handler.CreateItem)
mux.HandleFunc("DELETE /items/{id}", handler.DeleteItem)

// Bad — single handler with manual method dispatch
mux.HandleFunc("/items/", func(w http.ResponseWriter, r *http.Request) {
    switch r.Method {
    case http.MethodGet:
        handler.GetItem(w, r)
    case http.MethodDelete:
        handler.DeleteItem(w, r)
    default:
        w.WriteHeader(http.StatusMethodNotAllowed)
    }
})
```

---

## Go 1.25 (upcoming — not yet in stable release)

> Items in this section require Go 1.25+. Current stable is Go 1.24 (as of March 2026). Apply only to projects on pre-release builds.

- GOMAXPROCS auto-detects cgroup CPU limits in containers — no code change needed; remove any `automaxprocs` library usage if upgrading
- `runtime.SetDefaultGOMAXPROCS()` available to restore auto-detection if it was overridden

---

## Go 1.26 (upcoming — not yet in stable release)

> Items in this section require Go 1.26+. Current stable is Go 1.24 (as of March 2026). Apply only to projects on pre-release builds.

### `go fix -fix=modernize`

Run periodically to auto-apply modern idioms. Integrate into CI as a hygiene step.

```bash
go fix -fix=modernize ./...
```

Examples of what it fixes automatically:
- `sort.Slice` → `slices.SortFunc`
- `strings.Index(...) >= 0` → `strings.Contains(...)`
- `reflect.DeepEqual` on slices → `slices.Equal`
- Unnecessary `tt := tt` loop captures → removed

### `new(T, value)`

```go
// Good (Go 1.26+) — allocate and initialise in one expression
p := new(Config, Config{Host: "localhost", Port: 5432})

// Old approach — still valid
p := &Config{Host: "localhost", Port: 5432}

// Old two-step approach — no longer needed
p := new(Config)
*p = Config{Host: "localhost", Port: 5432}
```

### `crypto/hpke` for Hybrid Encryption

```go
// Good (Go 1.26+) — use crypto/hpke for hybrid public key encryption
// instead of manual ECIES or custom KEM+DEM implementations
import "crypto/hpke"
```
