# Go Test Code Review Guide

Supplements `test-review-checklist.md` for Go projects.
For Gin-specific handler test review, also load `gin-test-review-guide.md`.

---

## Test Structure

### ❌ White-box Testing Without Justification

```go
// Bad — same package without reason; testing unexported state
package mypackage

func TestInternalCounter(t *testing.T) {
    obj := &myObject{}
    assert.Equal(t, 0, obj.internalCounter)
}

// Good — black-box by default; test via public API
package mypackage_test

func TestItemValidation(t *testing.T) {
    item := Item{Name: "Test"}
    assert.NoError(t, item.Validate())
}
```

Use `package foo` (without `_test`) only when testing private functions is genuinely necessary.

### ❌ Vague Test Names

```go
// Bad
func TestItem(t *testing.T) {}
func TestCase1(t *testing.T) {}

// Good — top-level names component + method; subtests describe the scenario
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

### ❌ Copy-Pasted Test Cases

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

// Good — table-driven with descriptive case names
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
                assert.Error(t, err)
                assert.Contains(t, err.Error(), tt.errMsg)
            } else {
                assert.NoError(t, err)
            }
        })
    }
}
```

Use table-driven tests for: 3+ similar cases, multiple status codes, multiple validation rules, or edge cases (nil, empty, zero, boundary values).

For complex scenarios with varying mock behaviour, use function fields in the table:

```go
tests := []struct {
    name      string
    setupMock func(m *MockRepository)
    check     func(t *testing.T, result []Item)
}{ ... }
```

---

## Arrange-Act-Assert

```go
// Good — clear phases
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
    assert.NoError(t, err)
    assert.Len(t, items, 1)
    assert.Equal(t, "Test", items[0].Name)
}
```

---

## Mocking

### ❌ Over-Complex Mocks

```go
// Bad — tracking every call adds noise
type MockRepository struct {
    ListCallCount   int
    ListCallHistory []context.Context
}

// Good — simple, focused; only add fields you assert on
type MockItemRepository struct {
    ListFunc func(ctx context.Context) ([]Item, error)
}
func (m *MockItemRepository) List(ctx context.Context) ([]Item, error) {
    if m.ListFunc != nil { return m.ListFunc(ctx) }
    return nil, nil
}
```

### ❌ Using Real Dependencies in Unit Tests

```go
// Bad — hits real DB in a unit test
func TestUseCaseList(t *testing.T) {
    repo := NewRepository(setupRealDatabase())
    useCase := NewUseCase(repo)
    // ...
}

// Good — mock the interface for unit tests; real DB only in integration tests
```

---

## Database Tests

### ❌ No Isolation and No Cleanup

```go
// Bad — no isolation, leaves data, may hit production
func TestRepository(t *testing.T) {
    db := getProductionDB()
    NewRepository(db).Create(&Item{Name: "Test"})
    // Depends on previous state
}

// Good
func TestItemRepository_Integration(t *testing.T) {
    if testing.Short() { t.Skip("Skipping integration test") }
    db := setupTestDB(t)
    defer cleanupTestDB(t, db)
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

// Bad — nil context or abusing context.TODO
items, err := useCase.List(nil)
```

---

## Test Helpers

### ❌ Copy-Pasted Setup

```go
// Bad — duplicated literal in every test
func TestA(t *testing.T) { item := Item{Name: "Test Item", ID: "id-1"} }
func TestB(t *testing.T) { item := Item{Name: "Test Item", ID: "id-1"} }

// Good — functional options builder
func newTestItem(opts ...func(*Item)) Item {
    item := Item{Name: "Test Item", ID: "id-1", IsActive: true}
    for _, opt := range opts { opt(&item) }
    return item
}
```

Always call `t.Helper()` in helper functions so failures point to the calling test:

```go
func assertItemValid(t *testing.T, item Item) {
    t.Helper()
    assert.NoError(t, item.Validate())
}
```

---

## Common Anti-Patterns

### ❌ `time.Sleep` for Synchronisation

```go
// Bad
go doWork()
time.Sleep(1 * time.Second)
assert.True(t, workDone)

// Good
done := make(chan struct{})
go func() { doWork(); close(done) }()
select {
case <-done:
    assert.True(t, workDone)
case <-time.After(5 * time.Second):
    t.Fatal("timeout")
}
```

### ❌ Race Conditions in Tests

```go
// Bad
counter := 0
for i := 0; i < 10; i++ { go func() { counter++ }() }

// Good
var counter int32
var wg sync.WaitGroup
for i := 0; i < 10; i++ {
    wg.Add(1)
    go func() { defer wg.Done(); atomic.AddInt32(&counter, 1) }()
}
wg.Wait()
```

Always run: `go test -race ./...`

### ❌ Not Cleaning Up Resources

```go
// Bad — file never closed or removed
f, _ := os.Create("test.txt")

// Good
f, err := os.Create("test.txt")
require.NoError(t, err)
t.Cleanup(func() { f.Close(); os.Remove("test.txt") })
```

---

## Checklist for Go Tests

### Structure
- [ ] Black-box `_test` package used by default
- [ ] Test names identify component + method; subtests name the scenario
- [ ] Table-driven tests used for 3+ similar cases
- [ ] Arrange-Act-Assert sections clearly separated
- [ ] `t.Helper()` called in all helper functions
- [ ] `tt := tt` loop variable capture removed — unnecessary in Go 1.22+ projects (Go 1.22+)
- [ ] `go fix -fix=modernize ./...` run before review — outdated patterns auto-fixed (Go 1.26+)

### Coverage
- [ ] Happy path tested
- [ ] Error paths tested — error message validated, not just existence
- [ ] Edge cases covered (nil, empty, zero, boundary values)
- [ ] Context cancellation and timeout tested where relevant
- [ ] Range-over-function iterators tested for both full traversal and early-break (Go 1.23+)
- [ ] `testing/synctest` used for time-dependent concurrent tests — not `time.Sleep` (Go 1.25+)

### Mocking and Dependencies
- [ ] External dependencies mocked in unit tests
- [ ] Mocks are simple — no unnecessary call tracking
- [ ] Integration tests use real test database, not mocks
- [ ] Integration tests skippable with `testing.Short()`

### Concurrency and Determinism
- [ ] No `time.Sleep` for synchronisation
- [ ] No shared mutable state between tests
- [ ] No race conditions (`go test -race ./...` passes)
- [ ] Tests are deterministic

### Resource Management
- [ ] Resources cleaned up with `defer` or `t.Cleanup`
- [ ] Test DB cleaned after integration tests
- [ ] No goroutine leaks
- [ ] `os.Root` handles closed with `t.Cleanup` when used in tests (Go 1.24+)

### Assertions
- [ ] `assert` for non-critical checks; `require` for setup steps
- [ ] Error messages checked with `assert.Contains` or `assert.ErrorIs`

### CI Integration
- [ ] Integration tests skippable with `-short`
- [ ] No hard-coded environment values — use `os.Getenv` with skip fallback

---

## Fuzzing Review

Fuzz tests require specific review points beyond regular unit tests:

```go
// Good — seed corpus covers known edge cases; f.Fuzz exercises the space
func FuzzParseInput(f *testing.F) {
    // Seed corpus: explicit known inputs including edge cases
    f.Add("")
    f.Add("valid input")
    f.Add("null\x00byte")
    f.Add(strings.Repeat("a", 10000)) // large input

    f.Fuzz(func(t *testing.T, input string) {
        // Should not panic, and if it errors, the error should be typed
        result, err := ParseInput(input)
        if err == nil {
            // If parsing succeeds, round-trip should be stable
            _ = result
        }
    })
}
```

**Fuzzing checklist items:**
- [ ] Seed corpus (`f.Add()`) includes empty input, boundary values, and known-tricky inputs
- [ ] Fuzz function does not assert exact output values — only invariants (no panic, type safety, round-trip stability)
- [ ] Corpus files under `testdata/fuzz/FuzzXxx/` are committed to source control
- [ ] Run with `-fuzz` flag in CI for a bounded duration: `go test -fuzz=FuzzParseInput -fuzztime=30s`

---

## Benchmark Review

```go
// Good — ResetTimer excludes setup from measurement; ReportAllocs for allocation tracking
func BenchmarkProcessItems(b *testing.B) {
    items := generateTestItems(1000) // setup
    b.ResetTimer()                   // start timing after setup
    b.ReportAllocs()                 // report allocations per op

    for b.Loop() {                   // Go 1.24+: b.Loop() preferred over i < b.N
        _ = ProcessItems(items)
    }
}

// Good — sub-benchmarks for size scaling
func BenchmarkProcessItems_Sizes(b *testing.B) {
    for _, size := range []int{10, 100, 1000, 10000} {
        b.Run(fmt.Sprintf("size=%d", size), func(b *testing.B) {
            items := generateTestItems(size)
            b.ResetTimer()
            for b.Loop() {
                _ = ProcessItems(items)
            }
        })
    }
}
```

**Benchmark checklist items:**
- [ ] `b.ResetTimer()` called after expensive setup
- [ ] `b.ReportAllocs()` called when tracking memory efficiency
- [ ] `b.Loop()` used instead of `i < b.N` (Go 1.24+)
- [ ] Benchmark result is used (assign to `_`) — prevents compiler elimination
- [ ] Sub-benchmarks test scaling behaviour across input sizes

---

## Go Version-Specific Test Review Points

### Go 1.21+ Review

#### ❌ Using `reflect.DeepEqual` for Slice/Map Comparison

```go
// Bad — reflect.DeepEqual is slow, gives poor error output, and can produce false results
// for types with unexported fields
if !reflect.DeepEqual(got, want) {
    t.Errorf("got %v, want %v", got, want)
}

// Good — type-safe slice comparison (Go 1.21+)
import "slices"

if !slices.Equal(got, want) {
    t.Errorf("got %v, want %v", got, want)
}

// Good — map comparison (Go 1.21+)
import "maps"

if !maps.Equal(gotMap, wantMap) {
    t.Errorf("got %v, want %v", gotMap, wantMap)
}
```

### Go 1.22+ Review

#### ❌ Unnecessary Loop Variable Capture in Parallel Table Tests

```go
// Bad — tt := tt is a pre-1.22 workaround; unnecessary and misleading in Go 1.22+ projects
for _, tt := range tests {
    tt := tt  // remove this — loop variables are per-iteration in Go 1.22+
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

#### ❌ Manual Method Checks Instead of `net/http` Route Patterns

```go
// Bad — manual method check inside the handler
mux.HandleFunc("/items/", func(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        w.WriteHeader(http.StatusMethodNotAllowed)
        return
    }
    // handle GET
})

// Good — method+path pattern in the mux (Go 1.22+)
mux.HandleFunc("GET /items/{id}", handler.GetItem)
```

### Go 1.23+ Review

#### ❌ Not Testing Iterator Early Termination

Range-over-function iterators must call `return` when `yield` returns `false`. Tests must verify this.

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
    assert.Len(t, got, 1)  // only first item; B was never yielded
}
```

### Go 1.24+ Review

#### ❌ Not Using `t.Cleanup` with `os.Root`

```go
// Bad — root handle not closed; resource leak
func TestFileAccess(t *testing.T) {
    root, _ := os.OpenRoot(t.TempDir())
    // ... test body ... root.Close() forgotten
}

// Good — always register cleanup (Go 1.24+)
func TestFileAccess(t *testing.T) {
    root, err := os.OpenRoot(t.TempDir())
    require.NoError(t, err)
    t.Cleanup(func() { root.Close() })
    // ... test body ...
}
```

### Go 1.25+ Review

#### ❌ Using `time.Sleep` for Timing-Sensitive Tests Instead of `testing/synctest`

```go
// Bad — real sleep makes tests slow and timing-dependent
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

#### ❌ Not Using `testing/synctest` for Context Timeout Tests

```go
// Bad — real timeout delay in test
func TestRequestTimesOut(t *testing.T) {
    ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
    defer cancel()
    time.Sleep(200 * time.Millisecond) // real wait
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

### Go 1.26+ Review

#### ❌ Not Running `go fix -fix=modernize` Before Review

Go 1.26 ships a `go fix` modernizer that automatically updates outdated patterns. Test code reviews should confirm this has been run.

```bash
# Run before submitting for review — catches outdated patterns automatically
go fix -fix=modernize ./...
```

Common test code patterns it fixes:
- `reflect.DeepEqual(sliceA, sliceB)` → `slices.Equal(sliceA, sliceB)`
- `tt := tt` loop captures → removed (already idiomatic in Go 1.22+, now auto-fixed)
- `sort.Slice` in test helpers → `slices.SortFunc`

#### ❌ Using Two-Step Allocation in Test Fixtures When `new(T, value)` Is Cleaner

```go
// Bad — two-step allocation in test setup
config := new(ServerConfig)
*config = ServerConfig{Host: "localhost", Port: 8080}

// Good (Go 1.26+) — allocate and initialise in one expression
config := new(ServerConfig, ServerConfig{Host: "localhost", Port: 8080})
```

---

## Resources

- [Go Testing Package](https://pkg.go.dev/testing)
- [Testify](https://github.com/stretchr/testify)
- [Table-Driven Tests](https://go.dev/wiki/TableDrivenTests)
- [Go Subtests](https://go.dev/blog/subtests)
- [go-sqlmock](https://github.com/DATA-DOG/go-sqlmock)
- [Go 1.21 Release Notes](https://go.dev/doc/go1.21)
- [Go 1.22 Release Notes](https://go.dev/doc/go1.22)
- [Go 1.23 Range Over Functions](https://go.dev/blog/range-functions)
- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)
- [Go 1.25 Release Notes](https://go.dev/doc/go1.25)
- [testing/synctest package](https://pkg.go.dev/testing/synctest)
- [Go 1.26 Release Notes](https://go.dev/doc/go1.26)
- [go fix modernizer](https://go.dev/blog/go1.26)
- [slices package](https://pkg.go.dev/slices)
- [maps package](https://pkg.go.dev/maps)
