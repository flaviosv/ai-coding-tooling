# Go Reference — tests

Applies to Go projects using the standard `testing` package, optionally with `testify`.
For Gin-specific handler testing, also load `gin-tests.md` if present.

---

## General Go Testing Patterns

Universal testing conventions that apply across all supported Go versions (1.23+).

### Test File Structure

```go
// Black-box testing — tests the public API only (preferred default)
package mypackage_test

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestItemValidation(t *testing.T) {
    // ...
}
```

Use `package mypackage` (without `_test`) only when you need to test unexported internals.

### Basic Test Function

Name test variables `got` (actual result) and `want` (expected result) — this is the convention used throughout the Go standard library. Error messages follow `"got %v, want %v"` format.

```go
func TestAdd(t *testing.T) {
    got := Add(2, 3)
    want := 5
    if got != want {
        t.Errorf("Add(2, 3) = %d; want %d", got, want)
    }
}
```

Never ignore errors with `_ = err` in test code — use `require.NoError` or `assert.NoError`. Silent error discard masks test failures.

```go
// Bad — error discarded; test may silently pass on failure
result, _ := Parse(input)

// Good — use require to stop the test on error
result, err := Parse(input)
require.NoError(t, err)
```

### Using testify/assert

```go
func TestItem(t *testing.T) {
    item := Item{Name: "Test"}
    assert.NotNil(t, item)
    assert.Equal(t, "Test", item.Name)
}
```

### `require` vs `assert` — Critical Distinction

- `assert` — records the failure but continues executing the test. Use for independent assertions.
- `require` — stops the test immediately on failure. Use for setup steps and preconditions.

```go
func TestItemRepository_Get(t *testing.T) {
    // Setup — use require: if DB or insert fails, all later assertions are meaningless
    db := setupTestDB(t)
    require.NoError(t, db.Create(&Item{ID: "id-1", Name: "Test"}).Error)

    item, err := NewRepository(db).GetByID(context.Background(), "id-1")
    require.NoError(t, err) // require: if this fails, item is nil and next line panics

    // Multiple assertions on the returned value — assert is fine
    assert.Equal(t, "id-1", item.ID)
    assert.Equal(t, "Test", item.Name)
    assert.True(t, item.IsActive)
}
```

Rule of thumb: **`require` for preconditions and setup; `assert` for properties of the result.**

---

## Table-Driven Tests

The idiomatic Go pattern for multiple scenarios without code duplication.

```go
func TestPagination(t *testing.T) {
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

For complex scenarios with varying mock behaviour, use function fields:

```go
tests := []struct {
    name      string
    setupMock func(m *MockRepository)
    check     func(t *testing.T, result []Item, err error)
}{
    {
        name: "returns items on success",
        setupMock: func(m *MockRepository) {
            m.ListFunc = func(ctx context.Context) ([]Item, error) {
                return []Item{{Name: "A"}}, nil
            }
        },
        check: func(t *testing.T, result []Item, err error) {
            require.NoError(t, err)
            assert.Len(t, result, 1)
        },
    },
}
```

### Parallel Table-Driven Tests (Go 1.22+)

```go
// Good (Go 1.22+) — no tt := tt needed; loop variables are per-iteration
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        assert.Equal(t, tt.want, process(tt.input))
    })
}

// Pre-1.22 — required tt := tt capture; remove in Go 1.22+ projects
for _, tt := range tests {
    tt := tt // remove this in Go 1.22+ projects
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        assert.Equal(t, tt.want, process(tt.input))
    })
}
```

---

## Subtests

```go
func TestItem(t *testing.T) {
    t.Run("valid item passes validation", func(t *testing.T) {
        item := Item{Name: "Test", ID: "id-1"}
        assert.NoError(t, item.Validate())
    })

    t.Run("empty name fails validation", func(t *testing.T) {
        item := Item{ID: "id-1"}
        assert.Error(t, item.Validate())
    })
}
```

---

## Mocking

### Interface-Based Mocking (preferred)

```go
// Production interface
type ItemRepository interface {
    List(ctx context.Context) ([]Item, error)
    GetByID(ctx context.Context, id string) (*Item, error)
}

// Hand-rolled test mock — simple and transparent
type MockItemRepository struct {
    ListFunc    func(ctx context.Context) ([]Item, error)
    GetByIDFunc func(ctx context.Context, id string) (*Item, error)
}

func (m *MockItemRepository) List(ctx context.Context) ([]Item, error) {
    if m.ListFunc != nil {
        return m.ListFunc(ctx)
    }
    return nil, nil
}

func (m *MockItemRepository) GetByID(ctx context.Context, id string) (*Item, error) {
    if m.GetByIDFunc != nil {
        return m.GetByIDFunc(ctx, id)
    }
    return nil, nil
}

func TestUseCaseList(t *testing.T) {
    mockRepo := &MockItemRepository{
        ListFunc: func(ctx context.Context) ([]Item, error) {
            return []Item{{Name: "Test"}}, nil
        },
    }
    items, err := NewUseCase(mockRepo).List(context.Background())
    require.NoError(t, err)
    assert.Len(t, items, 1)
}
```

### testify/mock

```go
type MockRepository struct{ mock.Mock }

func (m *MockRepository) List(ctx context.Context) ([]Item, error) {
    args := m.Called(ctx)
    return args.Get(0).([]Item), args.Error(1)
}

func TestWithMock(t *testing.T) {
    mockRepo := new(MockRepository)
    mockRepo.On("List", mock.Anything).Return([]Item{{Name: "Test"}}, nil)

    items, err := NewUseCase(mockRepo).List(context.Background())

    require.NoError(t, err)
    assert.Len(t, items, 1)
    mockRepo.AssertExpectations(t)
}
```

---

## Database Testing

### Unit Tests with sqlmock (GORM)

```go
func TestItemRepository_List(t *testing.T) {
    mockDB, mock, err := sqlmock.New()
    require.NoError(t, err)
    defer mockDB.Close()

    db, err := gorm.Open(postgres.New(postgres.Config{
        Conn: mockDB, DriverName: "postgres",
    }), &gorm.Config{})
    require.NoError(t, err)

    rows := sqlmock.NewRows([]string{"id", "name"}).
        AddRow("id-1", "Item1").
        AddRow("id-2", "Item2")
    mock.ExpectQuery(`SELECT \* FROM "items"`).WillReturnRows(rows)

    items, err := NewRepository(db).List(context.Background())
    require.NoError(t, err)
    assert.Len(t, items, 2)
    assert.NoError(t, mock.ExpectationsWereMet())
}
```

### Integration Tests with testcontainers-go (preferred)

`testcontainers-go` spins up real Docker containers — more portable than requiring a pre-configured environment variable.

```go
import (
    "github.com/testcontainers/testcontainers-go/modules/postgres"
)

func setupTestDB(t *testing.T) *gorm.DB {
    t.Helper()

    ctx := context.Background()
    container, err := postgres.RunContainer(ctx,
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
    )
    require.NoError(t, err)
    t.Cleanup(func() { container.Terminate(ctx) })

    dsn, err := container.ConnectionString(ctx, "sslmode=disable")
    require.NoError(t, err)

    db, err := gorm.Open(gormpostgres.Open(dsn), &gorm.Config{})
    require.NoError(t, err)
    require.NoError(t, db.AutoMigrate(&Item{}))
    return db
}
```

### Integration Tests with `TEST_DB_URL` (fallback)

```go
func TestItemRepository_Integration(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test in short mode")
    }
    db := setupTestDB(t)

    require.NoError(t, db.Create(&Item{Name: "Test", ID: "id-1"}).Error)
    items, err := NewRepository(db).List(context.Background())
    require.NoError(t, err)
    assert.Len(t, items, 1)
}

func setupTestDB(t *testing.T) *gorm.DB {
    t.Helper()
    dsn := os.Getenv("TEST_DB_URL")
    if dsn == "" {
        t.Skip("TEST_DB_URL not set")
    }
    db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
    require.NoError(t, err)
    require.NoError(t, db.AutoMigrate(&Item{}))
    t.Cleanup(func() { db.Exec("TRUNCATE TABLE items CASCADE") })
    return db
}
```

---

## Test Helpers and Fixtures

### Functional Options Pattern

```go
func newTestItem(opts ...func(*Item)) Item {
    item := Item{Name: "Test Item", ID: "test-id", IsActive: true}
    for _, opt := range opts {
        opt(&item)
    }
    return item
}

func withName(name string) func(*Item) { return func(i *Item) { i.Name = name } }
func withInactive() func(*Item)        { return func(i *Item) { i.IsActive = false } }

// Usage
item := newTestItem()
custom := newTestItem(withName("Custom"), withInactive())
```

Always call `t.Helper()` in helper functions so failures point to the calling test:

```go
func assertItemValid(t *testing.T, item Item) {
    t.Helper()
    assert.NoError(t, item.Validate())
    assert.NotEmpty(t, item.ID)
}
```

### Global Setup / Teardown

```go
func TestMain(m *testing.M) {
    setup()
    code := m.Run()
    teardown()
    os.Exit(code)
}
```

---

## Testing Concurrency

```go
func TestConcurrentAccess(t *testing.T) {
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
}
```

Always run tests with `-race` to catch data races:

```bash
go test -race ./...
```

---

## Testing Timeouts and Context Cancellation

```go
func TestOperationRespectsTimeout(t *testing.T) {
    ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
    defer cancel()
    err := SlowOperation(ctx)
    assert.ErrorIs(t, err, context.DeadlineExceeded)
}
```

---

## Benchmarks

```go
func BenchmarkProcess(b *testing.B) {
    data := setupTestData()
    b.ResetTimer()
    b.ReportAllocs()
    for b.Loop() { // Go 1.24+: b.Loop() preferred over i < b.N
        _ = Process(data)
    }
}

// Sub-benchmarks for scaling behaviour
func BenchmarkProcess_Sizes(b *testing.B) {
    for _, size := range []int{10, 100, 1000, 10000} {
        b.Run(fmt.Sprintf("size=%d", size), func(b *testing.B) {
            data := generateData(size)
            b.ResetTimer()
            for b.Loop() {
                _ = Process(data)
            }
        })
    }
}
```

Run with: `go test -bench=. -benchmem`

---

## testify Assertions Reference

```go
assert.Equal(t, expected, actual)
assert.NotEqual(t, unexpected, actual)
assert.NotNil(t, obj)
assert.Nil(t, obj)
assert.NoError(t, err)
assert.Error(t, err)
assert.ErrorIs(t, err, target)
assert.ErrorAs(t, err, &target)
assert.Len(t, collection, n)
assert.Empty(t, collection)
assert.Contains(t, collection, element)
assert.ElementsMatch(t, expected, actual) // same elements, any order
assert.True(t, condition)
assert.False(t, condition)
```

---

## Fuzzing (Go 1.18+)

Built-in fuzzing to discover edge cases that structured tests miss.

```go
// FuzzXxx functions run with: go test -fuzz=FuzzParseDate -fuzztime=30s
func FuzzParseDate(f *testing.F) {
    // Seed corpus — known inputs the fuzzer starts from
    f.Add("2024-01-15")
    f.Add("2000-12-31")
    f.Add("")        // edge case: empty input
    f.Add("not-a-date")

    f.Fuzz(func(t *testing.T, input string) {
        // Must not panic on any input
        result, err := ParseDate(input)
        if err == nil {
            // If parsing succeeded, assert invariants on the result
            if result.Year() < 1000 || result.Year() > 9999 {
                t.Errorf("ParseDate(%q) produced out-of-range year %d", input, result.Year())
            }
        }
        // err != nil is acceptable — parsing may reject invalid input
    })
}
```

Failing inputs are saved to `testdata/fuzz/FuzzParseDate/` and become permanent regression tests.

---

## Go 1.23 Testing Patterns

### Testing Range-Over-Function Iterators

Iterators must respect early termination. Test both full traversal and break.

```go
func TestActiveItemsIterator_FullTraversal(t *testing.T) {
    items := []Item{
        {Name: "A", IsActive: true},
        {Name: "B", IsActive: false},
        {Name: "C", IsActive: true},
    }
    var got []Item
    for item := range ActiveItems(items) {
        got = append(got, item)
    }
    assert.Len(t, got, 2)
    assert.Equal(t, "A", got[0].Name)
    assert.Equal(t, "C", got[1].Name)
}

func TestActiveItemsIterator_StopsOnBreak(t *testing.T) {
    items := []Item{
        {Name: "A", IsActive: true},
        {Name: "B", IsActive: true},
    }
    var got []Item
    for item := range ActiveItems(items) {
        got = append(got, item)
        break // consumer stops after first item
    }
    assert.Len(t, got, 1) // B was never yielded
}
```

### `slices` and `maps` for Assertions

```go
// Good — type-safe slice comparison (Go 1.21+)
import "slices"

func TestGetNames(t *testing.T) {
    got := getNames(items)
    want := []string{"Alpha", "Beta", "Gamma"}
    if !slices.Equal(got, want) {
        t.Errorf("got %v, want %v", got, want)
    }
}

// Good — map comparison (Go 1.21+)
import "maps"

func TestBuildIndex(t *testing.T) {
    got := buildIndex(items)
    want := map[string]int{"alpha": 1, "beta": 2}
    if !maps.Equal(got, want) {
        t.Errorf("got %v, want %v", got, want)
    }
}

// Bad — reflect.DeepEqual is slow and gives poor error output
if !reflect.DeepEqual(got, want) { ... }
```

---

## Go 1.24 Testing Patterns

### `os.Root` for Sandbox Tests

```go
// Good — verify that no path traversal escapes the sandbox
func TestFileWriter_StaysInSandbox(t *testing.T) {
    root, err := os.OpenRoot(t.TempDir())
    require.NoError(t, err)
    t.Cleanup(func() { root.Close() })

    err = writer.WriteFile(root, "output.txt", []byte("data"))
    assert.NoError(t, err)

    // Escaping the sandbox must be rejected
    err = writer.WriteFile(root, "../etc/passwd", []byte("malicious"))
    assert.Error(t, err)
}
```

### `b.Loop()` in Benchmarks

```go
// Good — b.Loop() preferred over i < b.N in Go 1.24+
func BenchmarkProcessItems(b *testing.B) {
    items := generateTestItems(1000)
    b.ResetTimer()
    b.ReportAllocs()
    for b.Loop() {
        _ = ProcessItems(items)
    }
}
```

### Testing `net/http` Route Patterns (Go 1.22+)

```go
func TestGetItemHandler(t *testing.T) {
    mux := http.NewServeMux()
    mux.HandleFunc("GET /items/{id}", handler.GetItem)

    req := httptest.NewRequest(http.MethodGet, "/items/123", nil)
    w := httptest.NewRecorder()
    mux.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
}
```

---

## Go 1.25 Testing Patterns (upcoming)

> `testing/synctest` is not yet in a stable release (current stable: Go 1.24, March 2026). Apply only on pre-release builds.

### `testing/synctest` for Deterministic Concurrent Tests

Runs the test body in a synthetic "bubble" with a fake clock. Time only advances when all goroutines are blocked. Eliminates real `time.Sleep` calls from timing-sensitive tests.

```go
import "testing/synctest"

// Good — fake clock; executes instantly without real delay
func TestCacheExpiry(t *testing.T) {
    synctest.Run(func() {
        cache := NewCache(5 * time.Second)
        cache.Set("key", "value")

        time.Sleep(6 * time.Second) // fake — advances fake clock instantly
        assert.Nil(t, cache.Get("key"), "entry should have expired")
    })
}
```

```go
// Good — test timeout behaviour without real waits
func TestOperationTimesOut(t *testing.T) {
    synctest.Run(func() {
        ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
        defer cancel()

        time.Sleep(200 * time.Millisecond) // fake — no real delay

        err := SlowOperation(ctx)
        assert.ErrorIs(t, err, context.DeadlineExceeded)
    })
}
```

---

## Go 1.26 Testing Patterns (upcoming)

> Go 1.26 is not yet in a stable release (current stable: Go 1.24, March 2026).

### `new(T, value)` for Cleaner Test Fixtures

```go
// Good (Go 1.26+) — allocate and initialise in one expression
item := new(Item, Item{Name: "Test", IsActive: true})
assert.Equal(t, "Test", item.Name)

// Old approach — still works
item := &Item{Name: "Test", IsActive: true}
```

### `go fix -fix=modernize` in CI

```bash
# Run before submitting for review — catches outdated test patterns automatically
go fix -fix=modernize ./...

# Automatically updates test code:
# - Removes tt := tt loop captures (unnecessary in Go 1.22+)
# - reflect.DeepEqual(sliceA, sliceB) → slices.Equal(sliceA, sliceB)
# - sort.Slice in test helpers → slices.SortFunc
```

---

## Resources

- [Go Testing Package](https://pkg.go.dev/testing)
- [Testify](https://github.com/stretchr/testify)
- [Table-Driven Tests](https://go.dev/wiki/TableDrivenTests)
- [Go Subtests and Sub-benchmarks](https://go.dev/blog/subtests)
- [go-sqlmock](https://github.com/DATA-DOG/go-sqlmock)
- [testcontainers-go](https://golang.testcontainers.org)
- [Go Fuzzing](https://go.dev/doc/fuzz)
- [testing/synctest package](https://pkg.go.dev/testing/synctest)
- [slices package](https://pkg.go.dev/slices)
- [maps package](https://pkg.go.dev/maps)
- [Go 1.23 Release Notes](https://go.dev/doc/go1.23)
- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)
- [Go 1.25 Release Notes](https://go.dev/doc/go1.25)
- [Go 1.26 Release Notes](https://go.dev/doc/go1.26)
