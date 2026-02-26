# Go Code Review Checklist (1.21+)

Supplements the generic `review-checklist.md` for projects using Go.

---

## Security

- [ ] No hardcoded secrets, tokens, or credentials
- [ ] User input validated and sanitised before use
- [ ] SQL queries use parameterised statements — no string interpolation into queries
- [ ] Sensitive values (passwords, tokens) not logged or exposed in error messages
- [ ] Context deadlines set on outbound HTTP calls and DB queries
- [ ] HTML rendered with `html/template` — not `text/template` (prevents XSS)
- [ ] `unsafe` package usage is justified with an explanatory comment
- [ ] `govulncheck` runs in CI to detect known vulnerabilities in dependencies

---

## Error Handling

- [ ] Errors returned, not swallowed (`_ = err` only with explicit justification)
- [ ] Errors wrapped with context: `fmt.Errorf("doing X: %w", err)`
- [ ] Sentinel errors defined with `errors.New` or `fmt.Errorf` at package level
- [ ] `errors.Is` / `errors.As` used for error type checks — not string comparison
- [ ] Panics avoided in library code; only acceptable in `main` for truly unrecoverable states

---

## Performance

- [ ] Slices pre-allocated with `make([]T, 0, n)` when size is known
- [ ] `strings.Builder` used for multi-step string construction
- [ ] Maps used for O(1) membership testing instead of linear slice scans
- [ ] HTTP client reused across requests — not created per call
- [ ] Database queries paginated — no unbounded `SELECT *`
- [ ] `Preload` / `Joins` used in GORM to avoid N+1 queries
- [ ] `defer` not used inside loops (see common pitfalls)

---

## Concurrency

- [ ] Goroutines respect context cancellation — select on `ctx.Done()`
- [ ] No goroutine leaks — every goroutine has a clear exit condition
- [ ] Shared mutable state protected with `sync.Mutex`, `sync.RWMutex`, or atomics
- [ ] Channels closed by the sender, never the receiver
- [ ] Worker pool or bounded concurrency used instead of unbounded goroutine spawning

---

## Code Quality

- [ ] Exported functions and types have doc comments
- [ ] Unexported helpers are small and single-purpose
- [ ] Function signatures accept interfaces, not concrete types (where it adds flexibility)
- [ ] No unused imports, variables, or exported symbols
- [ ] No `init()` functions with side effects that are hard to trace — specifically: no database connections, HTTP calls, or global registrations in `init()`
- [ ] `sync.Once` used for safe lazy initialisation of singletons — not manual double-checked locking
- [ ] No `interface{}` / `any` where a concrete type works — reduces clarity and type safety
- [ ] `context.Context` is the first parameter of functions that need it — not stored in structs

---

## Go Idioms

- [ ] `if err != nil` checks immediately follow the call that may produce the error
- [ ] Named return values used only when they genuinely improve readability
- [ ] `defer` used for resource cleanup (file close, unlock, etc.)
- [ ] Struct embedding used judiciously — not as a shortcut to avoid composition
- [ ] Zero values are useful — structs work correctly without explicit initialisation where feasible
- [ ] `iota` used for enumerated constants

---

## Architecture & Design

- [ ] Dependencies injected via interfaces — not constructed inside functions
- [ ] Packages organised by domain/feature, not by layer (no `models/`, `utils/` dumping grounds)
- [ ] Package names are lowercase, single words, and describe what they provide
- [ ] Circular dependencies absent
- [ ] Public API surface is minimal — only export what callers need

---

## Testing

- [ ] New public behaviour has tests
- [ ] Table-driven tests used for multiple similar cases
- [ ] Integration tests marked with `testing.Short()` guard
- [ ] Tests run clean under `go test -race ./...`
- [ ] No `time.Sleep` for synchronisation in tests
- [ ] `t.Cleanup` used for test resource teardown — preferred over `defer` in test helpers

---

## Module Hygiene

- [ ] `go mod tidy` has been run — no unused or missing dependencies
- [ ] `go.sum` is committed and consistent with `go.mod`
- [ ] `govulncheck ./...` passes — no known vulnerabilities in the dependency tree

---

## Modern Go Features by Version

- [ ] `slices.Contains()`, `slices.SortFunc()`, `maps.Keys()`, `maps.Values()` used instead of manual loops (Go 1.21+)
- [ ] `log/slog` structured logger used — not `log.Printf` (Go 1.21+)
- [ ] `min()` / `max()` built-in functions used instead of manual comparisons (Go 1.21+)
- [ ] `for i := range n` used for integer ranges — not `for i := 0; i < n; i++` (Go 1.22+)
- [ ] Loop variable capture (`tt := tt`) removed from parallel table tests — unnecessary in Go 1.22+ (Go 1.22+)
- [ ] `net/http` route method+path patterns used (`"GET /items/{id}"`) — not manual method checks in handler (Go 1.22+)
- [ ] Range-over-function iterators (`iter.Seq`, `iter.Seq2`) used for custom iteration — not ad-hoc callback APIs (Go 1.23+)
- [ ] `unique.Make()` used for interning comparable values when identity/deduplication matters (Go 1.23+)
- [ ] Generic type aliases used for type-safe wrappers where appropriate (Go 1.24+)
- [ ] `os.Root` used for sandboxed filesystem access when path traversal must be restricted (Go 1.24+)
- [ ] `testing/synctest` used for testing time-dependent concurrent code — not `time.Sleep` (Go 1.25+ — upcoming, not yet in stable release)
- [ ] `encoding/json/v2` used for new projects requiring custom marshal/unmarshal logic (Go 1.25+ — upcoming)
- [ ] `new(T, value)` used to allocate and initialise a pointer in one expression (Go 1.26+ — upcoming)
- [ ] `crypto/hpke` used for hybrid public key encryption instead of manual ECIES implementations (Go 1.26+ — upcoming)
- [ ] `go fix -fix=modernize ./...` run periodically to auto-apply modern Go idioms (Go 1.26+ — upcoming)

> ⚠️ **Note:** Items marked Go 1.25+ or Go 1.26+ are upcoming features not yet in a stable release. Current stable Go version is Go 1.24 (as of Feb 2026). Apply these items only to projects already on the relevant pre-release builds.

---

## Resources

- [Effective Go](https://go.dev/doc/effective_go)
- [Go 1.21 Release Notes](https://go.dev/doc/go1.21)
- [Go 1.22 Release Notes](https://go.dev/doc/go1.22)
- [Go 1.23 Release Notes](https://go.dev/doc/go1.23)
- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)
- [Go 1.25 Release Notes](https://go.dev/doc/go1.25)
- [Go 1.26 Release Notes](https://go.dev/doc/go1.26)
