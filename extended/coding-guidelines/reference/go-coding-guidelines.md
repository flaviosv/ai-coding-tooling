# Go Coding Style Guide

## Naming Conventions

- **Packages**: lowercase, single word, no underscores (`http`, `strconv`, `userauth`)
- **Exported identifiers**: PascalCase (`UserService`, `ParseConfig`)
- **Unexported identifiers**: camelCase (`userService`, `parseConfig`)
- **Interfaces**: use `-er` suffix for single-method interfaces (`Reader`, `Stringer`, `Handler`)
- **Constants**: PascalCase if exported, camelCase if unexported; avoid `ALL_CAPS`
- **Acronyms**: keep consistent casing — `HTTPClient`, `URLParser`, `userID`, `parseHTML`
- **Error variables**: prefix with `Err` (`ErrNotFound`, `ErrTimeout`)
- **Test files**: suffix `_test.go`, test functions `TestXxx(t *testing.T)`

## File Organization

- One package per directory; package name matches directory name
- Group related types, functions, and methods in the same file
- Keep `main.go` thin — delegate logic to packages
- File names: lowercase with underscores for multi-word names (`user_service.go`)
- Order within a file: package declaration → imports → constants → vars → types → functions
- Group imports: stdlib first, then external, then internal (blank line between groups)

## Code Structure

- Keep functions short and focused on a single responsibility
- Return early to reduce nesting — guard clauses over deeply nested conditionals
- Prefer explicit over implicit; avoid `init()` unless necessary
- Use `context.Context` as the first parameter for functions that perform I/O or long work
- Accept interfaces, return concrete types as a default. Return an interface when the caller genuinely needs to depend on behavior rather than structure — e.g., `io.Reader`, repository interfaces, or public API boundaries. Do not return interfaces solely to defer the type decision.
- Avoid naked returns in functions longer than a few lines
- Design types to be useful at their zero value where possible — a zero-value `sync.Mutex`, `bytes.Buffer`, or `http.Client` is ready to use without initialization. Document explicitly when a zero value is not safe to use.

## Error Handling

- Always handle errors — never assign to `_` unless intentionally discarding
- Wrap errors with context: `fmt.Errorf("parsing user %d: %w", id, err)`
- Use `errors.Is` / `errors.As` for checking error types, not string comparison
- Define sentinel errors with `var ErrFoo = errors.New("...")` at package level
- Define custom error types with `type FooError struct {}` when extra context is needed
- Log errors at the boundary where they are handled, not at every level

## Idioms and Patterns

- Use table-driven tests for exhaustive coverage
- Use `defer` for cleanup (closing files, unlocking mutexes)
- Prefer `for range` over index loops when the index is unused
- Use `make([]T, 0, n)` when the final length is known to avoid reallocations
- Use `sync.Once` for one-time initialization, `sync.RWMutex` for read-heavy shared state
- Use channels for signalling, mutexes for protecting shared state — don't mix roles
- Prefer `select` with a `default` case to avoid blocking channel operations
- Always know who owns a goroutine's lifetime. The goroutine's creator is responsible for ensuring it terminates — pass a `context.Context` for cancellation and use `sync.WaitGroup` or `errgroup.Group` to wait for completion. Never start a goroutine without a clear shutdown path.
- Use `errgroup.Group` (from `golang.org/x/sync/errgroup`) for concurrent work that can fail — it collects the first error and cancels a derived context, replacing error-prone `sync.WaitGroup` + channel patterns
- For enumeration types using `iota`, always implement `String() string` (manually or via `go generate` with `stringer`) so that values are human-readable in logs and error messages. Avoid exposing raw integer values across package boundaries.

## Tooling

- Run `gofmt` (or `goimports`) on every file — formatting is non-negotiable in Go
- Use `golangci-lint` with at minimum `errcheck`, `staticcheck`, `gosimple`, and `govet` enabled
- `goimports` handles import grouping automatically — use it instead of `gofmt` where available

## Modern Go Features (apply when the project's Go version supports them)

- **Go 1.21+**: use `slices` and `maps` stdlib packages instead of manual loops for common operations; use `log/slog` for structured logging
- **Go 1.22+**: use `for i := range n` instead of `for i := 0; i < n; i++`; use enhanced `net/http` route patterns with method and path matching
- **Go 1.23+**: use range-over-function iterators for custom collection types; use `crypto/hpke` for hybrid public key encryption
- **Go 1.24+**: use `os.Root` for scoped filesystem access; use generic type aliases; use `testing/synctest` (experimental) for deterministic concurrency tests; run `go tool modernize` to auto-apply idiomatic fixes

## Anti-Patterns to Avoid

- Do not use `panic` for normal error flow — only for unrecoverable programmer errors
- Do not store `context.Context` in structs — pass it as a function parameter
- Do not use global mutable state without synchronization
- Do not shadow `err` across sequential `:=` assignments in the same scope — each new `:=` that includes `err` introduces a new variable, masking the previous one. Use `=` for subsequent assignments to the same `err` variable, or break the chain into separate scopes.
- Do not use `interface{}` / `any` when a concrete type or typed interface can express intent
- Do not copy a `sync.Mutex` — always use a pointer receiver or embed by value in a struct
- Do not ignore the second return value of map lookups when the zero value is ambiguous
