# Go Reference — tests-code-review

Supplements `test-review-checklist.md` for Go projects.
For Gin-specific handler test review, also load `gin-tests-code-review.md` if present.

---

## General Go Test Review Patterns

### Test Structure

#### Black-Box Testing by Default

```go
// Bad — same package; tests unexported state
package mypackage
func TestInternalCounter(t *testing.T) {
    assert.Equal(t, 0, (&myObject{}).internalCounter)
}

// Good — black-box by default; test via public API
package mypackage_test
func TestItemValidation(t *testing.T) {
    item := Item{Name: "Test"}
    assert.NoError(t, item.Validate())
}
```

Use `package foo` (without `_test`) only when testing private functions is genuinely necessary. Require a justification comment.

#### Test Names

```go
// Bad
func TestItem(t *testing.T) {}
func TestCase1(t *testing.T) {}

// Good — top-level identifies component + method; subtests describe scenario
func TestItemHandlerList(t *testing.T) {
    t.Run("returns 200 and items on success", func(t *testing.T) { ... })
    t.Run("returns 500 when use case fails", func(t *testing.T) { ... })
    t.Run("returns empty list when no items found", func(t *testing.T) { ... })
}
// Also acceptable — verbose single-function naming
func TestItem_Validate_EmptyName_ReturnsError(t *testing.T) {}
```

## Table-Driven Tests

```go
// Bad — repeated structure, brittle, hard to extend
func TestPagination(t *testing.T) {
    _, err1 := NewPagination(50, 0)
    assert.NoError(t, err1)
    _, err2 := NewPagination(200, 0)
    assert.Error(t, err2)
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

Use table-driven tests for: 3+ similar cases, multiple status codes, multiple validation rules, or edge cases (nil, empty, zero, boundary values). For complex scenarios with varying mock behaviour, use function fields in the table struct.

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

## Mocking

### Over-Complex Mocks

```go
// Bad — tracking every call; rarely asserted on
type MockRepository struct {
    ListCallCount   int
    ListCallHistory []context.Context
}

// Good — only add fields you actually assert on
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
repo := NewRepository(setupRealDatabase())

// Good — mock the interface; real DB only in integration tests
mockRepo := &MockItemRepository{...}
useCase := NewUseCase(mockRepo)
```

## Database Tests

```go
// Bad — no isolation, leaves data, may hit wrong DB
func TestRepository(t *testing.T) {
    db := getProductionDB()
    NewRepository(db).Create(&Item{Name: "Test"})
}

// Good — isolated, skippable, cleaned up
func TestItemRepository_Integration(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test")
    }
    db := setupTestDB(t) // uses testcontainers or TEST_DB_URL
    // t.Cleanup registered inside setupTestDB
}
```

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

// Bad — nil context causes panic in most implementations
items, err := useCase.List(nil)
```

## Test Helpers

```go
// Bad — duplicated literal across tests
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

Always call `t.Helper()` in helper functions so failures point to the calling test:

```go
func assertItemValid(t *testing.T, item Item) {
    t.Helper()
    assert.NoError(t, item.Validate())
    assert.NotEmpty(t, item.ID)
}
```

## Common Anti-Patterns

### `time.Sleep` for Synchronisation

```go
// Bad — slow and non-deterministic
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
// Bad — file never closed or removed
f, _ := os.Create("test.txt")

// Good — register cleanup immediately after creation
f, err := os.Create("test.txt")
require.NoError(t, err)
t.Cleanup(func() { f.Close(); os.Remove("test.txt") })
```

## Checklist for Go Tests

### Structure
- [ ] Black-box `_test` package used by default
- [ ] Test names identify component + method; subtests name scenario and outcome
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
- [ ] Not using `reflect.DeepEqual` — use `slices.Equal`, `maps.Equal`, or `assert.Equal`
- [ ] No error values silently ignored (`_ = err`) — use `require.NoError` or `assert.NoError`
- [ ] Test variables use `got`/`want` naming convention

## Go 1.23 Test Review Points

### Range-Over-Function Iterators Must Test Early Termination

Iterators using `iter.Seq` / `iter.Seq2` must call `return` when `yield` returns `false`. Reviews must confirm both full traversal and early-break are tested.

```go
// Bad — only tests full traversal; misses early-stop contract
func TestActiveItems(t *testing.T) {
    items := []Item{{Name: "A", IsActive: true}, {Name: "B", IsActive: true}}
    var got []Item
    for item := range ActiveItems(items) { got = append(got, item) }
    assert.Len(t, got, 2)
}

// Good — also tests iterator stops when consumer breaks
func TestActiveItems_StopsOnBreak(t *testing.T) {
    items := []Item{{Name: "A", IsActive: true}, {Name: "B", IsActive: true}}
    var got []Item
    for item := range ActiveItems(items) {
        got = append(got, item)
        break
    }
    assert.Len(t, got, 1)
}
```

### `reflect.DeepEqual` on Slices/Maps

```go
// Bad — slow, poor error output, false results with unexported fields
if !reflect.DeepEqual(got, want) { t.Errorf("got %v, want %v", got, want) }

// Good — type-safe comparisons (Go 1.21+)
if !slices.Equal(got, want) { t.Errorf("got %v, want %v", got, want) }
if !maps.Equal(gotMap, wantMap) { t.Errorf("got %v, want %v", gotMap, wantMap) }
```

## Go 1.24 Test Review Points

### `b.Loop()` in Benchmarks (Go 1.24+)

```go
// Bad — old style
for i := 0; i < b.N; i++ { _ = Process(data) }

// Good (Go 1.24+)
for b.Loop() { _ = Process(data) }
```

**Benchmark checklist:**
- [ ] `b.ResetTimer()` called after expensive setup
- [ ] `b.ReportAllocs()` called when tracking memory efficiency
- [ ] `b.Loop()` used instead of `i < b.N` (Go 1.24+)
- [ ] Benchmark result assigned to `_` — prevents compiler elimination
- [ ] Sub-benchmarks test scaling behaviour across input sizes

### `t.Cleanup` with `os.Root` (Go 1.24+)

```go
// Bad — os.Root handle not closed
root, _ := os.OpenRoot(t.TempDir())

// Good — always register cleanup
root, err := os.OpenRoot(t.TempDir())
require.NoError(t, err)
t.Cleanup(func() { root.Close() })
```

### Unnecessary Loop Variable Capture (Go 1.22+)

```go
// Bad — tt := tt is a pre-1.22 workaround; unnecessary in Go 1.22+
for _, tt := range tests {
    tt := tt // remove this
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

## Go 1.25 Test Review Points (upcoming)

> `testing/synctest` not yet stable (current: Go 1.24, March 2026). Apply only on pre-release builds.

### `time.Sleep` in Timing-Sensitive Tests

```go
// Bad — real sleep makes tests slow and flaky
func TestCacheExpiry(t *testing.T) {
    cache := NewCache(1 * time.Second)
    cache.Set("key", "value")
    time.Sleep(2 * time.Second)
    assert.Nil(t, cache.Get("key"))
}

// Good — testing/synctest with fake clock (Go 1.25+)
func TestCacheExpiry(t *testing.T) {
    synctest.Run(func() {
        cache := NewCache(1 * time.Second)
        cache.Set("key", "value")
        time.Sleep(2 * time.Second) // fake — advances instantly
        assert.Nil(t, cache.Get("key"))
    })
}
```

Same pattern applies to `context.WithTimeout` tests — wrap in `synctest.Run` so `time.Sleep` uses the fake clock.

**Checklist for Go 1.25+:**
- [ ] `testing/synctest` used for time-dependent concurrent tests — not `time.Sleep`

## Go 1.26 Test Review Points (upcoming)

> Go 1.26 not yet stable (current: Go 1.24, March 2026).

### `go fix -fix=modernize` Before Review

Go 1.26 ships a modernizer that auto-updates outdated patterns. Reviews should confirm this ran before submission.

```bash
go fix -fix=modernize ./...
```

Patterns it fixes: `reflect.DeepEqual` -> `slices.Equal`, `tt := tt` captures removed, `sort.Slice` -> `slices.SortFunc`.

### `new(T, value)` in Test Fixtures (Go 1.26+)

```go
// Bad — two-step allocation
config := new(ServerConfig)
*config = ServerConfig{Host: "localhost", Port: 8080}

// Good (Go 1.26+)
config := new(ServerConfig, ServerConfig{Host: "localhost", Port: 8080})
```

**Checklist for Go 1.26+:**
- [ ] `go fix -fix=modernize ./...` run before review — outdated test patterns auto-fixed

## Fuzzing Review

```go
// Good — seed corpus covers edge cases; fuzz asserts invariants only
func FuzzParseInput(f *testing.F) {
    f.Add("")
    f.Add("valid input")
    f.Add("null\x00byte")
    f.Add(strings.Repeat("a", 10000))
    f.Fuzz(func(t *testing.T, input string) {
        result, err := ParseInput(input)
        if err == nil { _ = result }
    })
}
```

**Fuzzing checklist:**
- [ ] Seed corpus (`f.Add()`) includes empty input, boundary values, and known-tricky inputs
- [ ] Fuzz function asserts invariants only — not exact output values
- [ ] Corpus files under `testdata/fuzz/FuzzXxx/` committed to source control
- [ ] Run with `-fuzz` flag in CI: `go test -fuzz=FuzzParseInput -fuzztime=30s`
