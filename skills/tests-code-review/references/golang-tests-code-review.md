# Go Reference — tests-code-review

Supplements `test-review-checklist.md` for Go projects.
For Gin-specific handler test review, also load `gin-tests-code-review.md` if present.

---

## General Go Test Review Patterns

Universal test quality expectations that apply across all supported Go versions (1.23+).

### Test Structure

#### Black-Box Testing by Default

```go
// Bad — same package without justification; tests unexported state
package mypackage

func TestInternalCounter(t *testing.T) {
    obj := &myObject{}
    assert.Equal(t, 0, obj.internalCounter) // testing private state
}

// Good — black-box by default; test via the public API
package mypackage_test

func TestItemValidation(t *testing.T) {
    item := Item{Name: "Test"}
    assert.NoError(t, item.Validate())
}
```

Use `package foo` (without `_test`) only when testing private functions is genuinely necessary. Require a justification comment.

#### Test Names

```go
// Bad — name tells you nothing about the scenario or expected outcome
func TestItem(t *testing.T) {}
func TestCase1(t *testing.T) {}

// Good — top-level name identifies component + method; subtests describe scenario
func TestItemHandlerList(t *testing.T) {
    t.Run("returns 200 and items on success", func(t *testing.T) { ... })
    t.Run("returns 500 when use case fails", func(t *testing.T) { ... })
    t.Run("returns empty list when no items found", func(t *testing.T) { ... })
}

// Also acceptable — verbose single-function naming
func TestItem_Validate_EmptyName_ReturnsError(t *testing.T) {}
```

---

## Table-Driven Tests

### Copy-Pasted Test Cases

```go
// Bad — repeated structure, brittle, hard to extend
func TestPagination(t *testing.T) {
    _, err1 := NewPagination(50, 0)
    assert.NoError(t, err1)

    _, err2 := NewPagination(200, 0)
    assert.Error(t, err2)

    _, err3 := NewPagination(50, -1)
    assert.Error(t, err3)
}

// Good — table-driven with descriptive case names and error message assertions
func TestPagination_Validation(t *testing.T) {
    tests := []struct {
        name    string
        limit   int
        offset  int
        wantErr bool
        errMsg  string
    }{
        {name: "valid", limit: 50, offset: 0, wantErr: false},
        {name: "limit too high", limit: 200, offset: 0, wantErr: true, errMsg: "exceeds maximum"},
        {name: "negative offset", limit: 50, offset: -1, wantErr: true, errMsg: "cannot be negative"},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            _, err := NewPagination(tt.limit, tt.offset)
            if tt.wantErr {
                require.Error(t, err)
                assert.Contains(t, err.Error(), tt.errMsg)
            } else {
                assert.NoError(t, err)
            }
        })
    }
}
```

Use table-driven tests for: 3+ similar cases, multiple status codes, multiple validation rules, or edge cases (nil, empty, zero, boundary values).

For complex scenarios with varying mock behaviour, use function fields in the table struct.

---

## Arrange-Act-Assert

```go
// Good — clear phases; no interleaving of setup with assertions
func TestUseCaseList(t *testing.T) {
    // Arrange
    mockRepo := &MockItemRepository{
        ListFunc: func(ctx context.Context) ([]Item, error) {
            return []Item{{Name: "Test"}}, nil
        },
    }
    useCase := NewUseCase(mockRepo)

    // Act
    items, err := useCase.List(context.Background())

    // Assert
    require.NoError(t, err)
    assert.Len(t, items, 1)
    assert.Equal(t, "Test", items[0].Name)
}
```

---

## Mocking

### Over-Complex Mocks

```go
// Bad — tracking every call adds noise; rarely asserted on
type MockRepository struct {
    ListCallCount   int
    ListCallHistory []context.Context
}

// Good — simple and focused; only add fields you actually assert on
type MockItemRepository struct {
    ListFunc func(ctx context.Context) ([]Item, error)
}
func (m *MockItemRepository) List(ctx context.Context) ([]Item, error) {
    if m.ListFunc != nil {
        return m.ListFunc(ctx)
    }
    return nil, nil
}
```

### Real Dependencies in Unit Tests

```go
// Bad — hits a real DB in a unit test
func TestUseCaseList(t *testing.T) {
    repo := NewRepository(setupRealDatabase())
    useCase := NewUseCase(repo)
    // ...
}

// Good — mock the interface for unit tests; real DB only in integration tests
func TestUseCaseList(t *testing.T) {
    mockRepo := &MockItemRepository{...}
    useCase := NewUseCase(mockRepo)
    // ...
}
```

---

## Database Tests

### No Isolation and No Cleanup

```go
// Bad — no isolation, leaves data, may hit the wrong DB
func TestRepository(t *testing.T) {
    db := getProductionDB() // wrong
    NewRepository(db).Create(&Item{Name: "Test"})
    // depends on previous test state
}

// Good — isolated, skippable, cleaned up
func TestItemRepository_Integration(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test")
    }
    db := setupTestDB(t) // uses testcontainers or TEST_DB_URL
    // t.Cleanup registered inside setupTestDB
    // ...
}
```

---

## Context Usage

```go
// Good — always pass a real context
items, err := useCase.List(context.Background())

// Good — test cancellation explicitly
func TestOperationRespectsTimeout(t *testing.T) {
    ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
    defer cancel()
    err := SlowOperation(ctx)
    assert.ErrorIs(t, err, context.DeadlineExceeded)
}

// Bad — nil context or abusing context.TODO()
items, err := useCase.List(nil) // nil context causes a panic in most implementations
```

---

## Test Helpers

### Copy-Pasted Setup

```go
// Bad — duplicated literal across tests; change in one place breaks another
func TestA(t *testing.T) { item := Item{Name: "Test Item", ID: "id-1"} }
func TestB(t *testing.T) { item := Item{Name: "Test Item", ID: "id-1"} }

// Good — functional options builder
func newTestItem(opts ...func(*Item)) Item {
    item := Item{Name: "Test Item", ID: "id-1", IsActive: true}
    for _, opt := range opts {
        opt(&item)
    }
    return item
}
```

Always call `t.Helper()` in helper functions so failures point to the calling test, not the helper:

```go
func assertItemValid(t *testing.T, item Item) {
    t.Helper()
    assert.NoError(t, item.Validate())
    assert.NotEmpty(t, item.ID)
}
```

---

## Common Anti-Patterns

### `time.Sleep` for Synchronisation

```go
// Bad — slow and non-deterministic; test may fail on a slow CI machine
go doWork()
time.Sleep(1 * time.Second)
assert.True(t, workDone)

// Good — wait on a channel or WaitGroup with a timeout
done := make(chan struct{})
go func() { doWork(); close(done) }()
select {
case <-done:
    assert.True(t, workDone)
case <-time.After(5 * time.Second):
    t.Fatal("timeout waiting for doWork")
}
```

### Race Conditions in Tests

```go
// Bad — unsynchronised access; -race will catch this
counter := 0
for range 10 {
    go func() { counter++ }()
}

// Good — atomic or mutex-protected
var counter int32
var wg sync.WaitGroup
for range 10 {
    wg.Add(1)
    go func() {
        defer wg.Done()
        atomic.AddInt32(&counter, 1)
    }()
}
wg.Wait()
assert.Equal(t, int32(10), counter)
```

Always run: `go test -race ./...`

### Not Cleaning Up Resources

```go
// Bad — file never closed or removed; leaks in the test runner
f, _ := os.Create("test.txt")

// Good — register cleanup immediately after creation
f, err := os.Create("test.txt")
require.NoError(t, err)
t.Cleanup(func() {
    f.Close()
    os.Remove("test.txt")
})
```

---

## Checklist for Go Tests

### Structure
- [ ] Black-box `_test` package used by default
- [ ] Test names identify component + method; subtests name the scenario and outcome
- [ ] Table-driven tests used for 3+ similar cases
- [ ] Arrange-Act-Assert sections clearly separated
- [ ] `t.Helper()` called in all helper functions

### Coverage
- [ ] Happy path tested
- [ ] Error paths tested — error message validated, not just existence (`assert.Contains` or `assert.ErrorIs`)
- [ ] Edge cases covered (nil, empty, zero, boundary values)
- [ ] Context cancellation and timeout tested where relevant

### Mocking and Dependencies
- [ ] External dependencies mocked in unit tests
- [ ] Mocks are minimal — no unnecessary call tracking
- [ ] Integration tests use a real test database (testcontainers or `TEST_DB_URL`)
- [ ] Integration tests skippable with `testing.Short()`

### Concurrency and Determinism
- [ ] No `time.Sleep` for synchronisation
- [ ] No shared mutable state between tests
- [ ] No race conditions (`go test -race ./...` passes)
- [ ] Tests are deterministic — no random values, no wall-clock assertions

### Resource Management
- [ ] Resources cleaned up with `defer` or `t.Cleanup`
- [ ] Test DB state cleaned after integration tests
- [ ] No goroutine leaks

### Assertions
- [ ] `assert` for non-critical checks; `require` for setup preconditions
- [ ] Not using `reflect.DeepEqual` — use `slices.Equal`, `maps.Equal`, or `assert.Equal` instead
- [ ] No error values silently ignored (`_ = err`) in test code — use `require.NoError` or `assert.NoError`
- [ ] Test variables use `got`/`want` naming convention for actual vs expected values

---

## Go 1.23 Test Review Points

### Range-Over-Function Iterators Must Test Early Termination

Iterators using `iter.Seq` / `iter.Seq2` must call `return` when `yield` returns `false`. Reviews must confirm both full traversal and early-break are tested.

```go
// Bad — only tests full traversal; misses the early-stop contract
func TestActiveItems(t *testing.T) {
    items := []Item{{Name: "A", IsActive: true}, {Name: "B", IsActive: true}}
    var got []Item
    for item := range ActiveItems(items) {
        got = append(got, item)
    }
    assert.Len(t, got, 2)
}

// Good — also test that the iterator stops when consumer breaks
func TestActiveItems_StopsOnBreak(t *testing.T) {
    items := []Item{{Name: "A", IsActive: true}, {Name: "B", IsActive: true}}
    var got []Item
    for item := range ActiveItems(items) {
        got = append(got, item)
        break
    }
    assert.Len(t, got, 1) // only first item; B was never yielded
}
```

### `reflect.DeepEqual` on Slices/Maps

```go
// Bad — reflect.DeepEqual is slow, gives poor error output, and can produce
// false results for types with unexported fields
if !reflect.DeepEqual(got, want) {
    t.Errorf("got %v, want %v", got, want)
}

// Good — type-safe comparisons (Go 1.21+)
import "slices"
if !slices.Equal(got, want) {
    t.Errorf("got %v, want %v", got, want)
}

import "maps"
if !maps.Equal(gotMap, wantMap) {
    t.Errorf("got %v, want %v", gotMap, wantMap)
}
```

---

## Go 1.24 Test Review Points

### `b.Loop()` in Benchmarks

```go
// Bad — old style; b.Loop() is preferred in Go 1.24+
for i := 0; i < b.N; i++ {
    _ = Process(data)
}

// Good (Go 1.24+)
for b.Loop() {
    _ = Process(data)
}
```

**Benchmark checklist items:**
- [ ] `b.ResetTimer()` called after expensive setup
- [ ] `b.ReportAllocs()` called when tracking memory efficiency
- [ ] `b.Loop()` used instead of `i < b.N` (Go 1.24+)
- [ ] Benchmark result is used (assign to `_`) — prevents compiler elimination
- [ ] Sub-benchmarks test scaling behaviour across input sizes

### `t.Cleanup` with `os.Root`

```go
// Bad — os.Root handle not closed; OS-level file descriptor leak
func TestFileAccess(t *testing.T) {
    root, _ := os.OpenRoot(t.TempDir())
    // ... test body ... root.Close() forgotten
}

// Good — always register cleanup
func TestFileAccess(t *testing.T) {
    root, err := os.OpenRoot(t.TempDir())
    require.NoError(t, err)
    t.Cleanup(func() { root.Close() })
    // ... test body ...
}
```

### Unnecessary Loop Variable Capture (Go 1.22+)

```go
// Bad — tt := tt is a pre-1.22 workaround; unnecessary and misleading in Go 1.22+ projects
for _, tt := range tests {
    tt := tt // remove this in Go 1.22+ projects
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        assert.Equal(t, tt.want, process(tt.input))
    })
}

// Good (Go 1.22+)
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        assert.Equal(t, tt.want, process(tt.input))
    })
}
```

---

## Go 1.25 Test Review Points (upcoming)

> `testing/synctest` is not yet in a stable release (current stable: Go 1.24, March 2026). Apply only on pre-release builds.

### `time.Sleep` in Timing-Sensitive Tests

```go
// Bad — real sleep makes tests slow and timing-dependent; flaky on CI
func TestCacheExpiry(t *testing.T) {
    cache := NewCache(1 * time.Second)
    cache.Set("key", "value")
    time.Sleep(2 * time.Second) // slow and flaky
    assert.Nil(t, cache.Get("key"))
}

// Good — testing/synctest with fake clock (Go 1.25+)
import "testing/synctest"

func TestCacheExpiry(t *testing.T) {
    synctest.Run(func() {
        cache := NewCache(1 * time.Second)
        cache.Set("key", "value")
        time.Sleep(2 * time.Second) // fake — advances instantly
        assert.Nil(t, cache.Get("key"))
    })
}
```

```go
// Bad — real timeout delay in test
func TestRequestTimesOut(t *testing.T) {
    ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
    defer cancel()
    time.Sleep(200 * time.Millisecond) // real wait; test takes 200ms+
    err := doRequest(ctx)
    assert.ErrorIs(t, err, context.DeadlineExceeded)
}

// Good — fake clock, instant execution (Go 1.25+)
func TestRequestTimesOut(t *testing.T) {
    synctest.Run(func() {
        ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
        defer cancel()
        time.Sleep(200 * time.Millisecond) // fake — no real delay
        err := doRequest(ctx)
        assert.ErrorIs(t, err, context.DeadlineExceeded)
    })
}
```

**Checklist additions for Go 1.25+ projects:**
- [ ] `testing/synctest` used for time-dependent concurrent tests — not `time.Sleep`

---

## Go 1.26 Test Review Points (upcoming)

> Go 1.26 is not yet in a stable release (current stable: Go 1.24, March 2026).

### `go fix -fix=modernize` Before Review

Go 1.26 ships a `go fix` modernizer that auto-updates outdated patterns. Test code reviews should confirm this has been run before submission.

```bash
# Run before submitting for review
go fix -fix=modernize ./...
```

Patterns it fixes in test code automatically:
- `reflect.DeepEqual(sliceA, sliceB)` → `slices.Equal(sliceA, sliceB)`
- `tt := tt` loop captures → removed
- `sort.Slice` in test helpers → `slices.SortFunc`

### `new(T, value)` in Test Fixtures

```go
// Bad — two-step allocation in test setup
config := new(ServerConfig)
*config = ServerConfig{Host: "localhost", Port: 8080}

// Good (Go 1.26+) — allocate and initialise in one expression
config := new(ServerConfig, ServerConfig{Host: "localhost", Port: 8080})
```

**Checklist additions for Go 1.26+ projects:**
- [ ] `go fix -fix=modernize ./...` run before review — outdated test patterns auto-fixed

---

## Fuzzing Review

```go
// Good — seed corpus covers known edge cases; fuzz function asserts invariants only
func FuzzParseInput(f *testing.F) {
    // Seed corpus: include empty, boundary, and tricky inputs
    f.Add("")
    f.Add("valid input")
    f.Add("null\x00byte")
    f.Add(strings.Repeat("a", 10000)) // large input

    f.Fuzz(func(t *testing.T, input string) {
        // Must not panic on any input
        result, err := ParseInput(input)
        if err == nil {
            // Assert invariants — not exact output values
            _ = result
        }
    })
}
```

**Fuzzing checklist items:**
- [ ] Seed corpus (`f.Add()`) includes empty input, boundary values, and known-tricky inputs
- [ ] Fuzz function asserts invariants only — not exact output values
- [ ] Corpus files under `testdata/fuzz/FuzzXxx/` are committed to source control
- [ ] Run with `-fuzz` flag in CI for a bounded duration: `go test -fuzz=FuzzParseInput -fuzztime=30s`

---

## Resources

- [Go Testing Package](https://pkg.go.dev/testing)
- [Testify](https://github.com/stretchr/testify)
- [Table-Driven Tests](https://go.dev/wiki/TableDrivenTests)
- [Go Subtests](https://go.dev/blog/subtests)
- [Go Fuzzing](https://go.dev/doc/fuzz)
- [go-sqlmock](https://github.com/DATA-DOG/go-sqlmock)
- [testing/synctest package](https://pkg.go.dev/testing/synctest)
- [slices package](https://pkg.go.dev/slices)
- [maps package](https://pkg.go.dev/maps)
- [Go 1.23 Release Notes](https://go.dev/doc/go1.23)
- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)
- [Go 1.25 Release Notes](https://go.dev/doc/go1.25)
- [Go 1.26 Release Notes](https://go.dev/doc/go1.26)
