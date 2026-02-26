# Go Testing Guide

Applies to: Go projects using the standard `testing` package, optionally with `testify`.
For Gin-specific handler testing, also load `gin-tests.md`.

---

## Basics

### Test File Structure

```go
// Black-box testing — tests the public API only (preferred default)
package mypackage_test

import (
    "testing"
    "github.com/stretchr/testify/assert"
)

func TestItemValidation(t *testing.T) {
    // ...
}
```

Use `package mypackage` (without `_test`) only when you need to test unexported internals.

### Basic Test Function

```go
func TestAdd(t *testing.T) {
    result := Add(2, 3)
    if result != 5 {
        t.Errorf("Add(2, 3) = %d; want %d", result, 5)
    }
}
```

### Using testify/assert

```go
func TestItem(t *testing.T) {
    item := Item{Name: "Test"}
    assert.NotNil(t, item)
    assert.Equal(t, "Test", item.Name)
}
```

---

## Table-Driven Tests

The idiomatic Go approach for covering multiple scenarios without code duplication.

```go
func TestPagination(t *testing.T) {
    tests := []struct {
        name    string
        limit   int
        offset  int
        wantErr bool
    }{
        {name: "valid", limit: 50, offset: 0, wantErr: false},
        {name: "limit too high", limit: 200, offset: 0, wantErr: true},
        {name: "negative offset", limit: 50, offset: -1, wantErr: true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            _, err := NewPagination(tt.limit, tt.offset)
            if tt.wantErr {
                assert.Error(t, err)
            } else {
                assert.NoError(t, err)
            }
        })
    }
}
```

### Parallel Table-Driven Tests

```go
for _, tt := range tests {
    tt := tt // capture range variable (required before Go 1.22)
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        assert.Equal(t, tt.want, Double(tt.input))
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

// Hand-rolled test mock
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
    assert.NoError(t, err)
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

    assert.NoError(t, err)
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
    assert.NoError(t, err)
    assert.Len(t, items, 2)
    assert.NoError(t, mock.ExpectationsWereMet())
}
```

### Integration Tests with a Real Test Database

```go
func TestItemRepository_Integration(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test in short mode")
    }
    db := setupTestDB(t)
    defer cleanupTestDB(t, db)

    _ = db.Create(&Item{Name: "Test", ID: "id-1"}).Error
    items, err := NewRepository(db).List(context.Background())
    assert.NoError(t, err)
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
    return db
}

func cleanupTestDB(t *testing.T, db *gorm.DB) {
    t.Helper()
    db.Exec("TRUNCATE TABLE items CASCADE")
}
```

---

## Test Helpers & Fixtures

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

// Usage
item := newTestItem()
custom := newTestItem(withName("Custom"))
```

Always call `t.Helper()` in helper functions so failures point to the calling test.

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
    for i := 0; i < 10; i++ {
        wg.Add(1)
        go func() { defer wg.Done(); atomic.AddInt32(&counter, 1) }()
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
    for i := 0; i < b.N; i++ {
        Process(data)
    }
}
```

Run with: `go test -bench=. -benchmem`

---

## testify Assertions Reference

```go
assert.Equal(t, expected, actual)
assert.NotNil(t, obj)
assert.NoError(t, err)
assert.Error(t, err)
assert.ErrorIs(t, err, target)
assert.Len(t, collection, n)
assert.Contains(t, collection, element)
assert.ElementsMatch(t, expected, actual) // same elements, any order
```

### require vs assert — When to Use Each

This is a critical distinction:

- **`assert`** — records the failure but continues executing the test. Use for independent assertions where later assertions still make sense even if earlier ones fail.
- **`require`** — stops the test immediately on failure. Use for setup steps and preconditions where continuing would cause panics or misleading failures.

```go
func TestItemRepository_Get(t *testing.T) {
    // Setup — use require: if the DB or insert fails, all assertions below are meaningless
    db := setupTestDB(t)
    require.NoError(t, db.Create(&Item{ID: "id-1", Name: "Test"}).Error)

    item, err := NewRepository(db).GetByID(context.Background(), "id-1")
    require.NoError(t, err)  // require: if this fails, item is nil and the next line panics

    // Multiple assertions on the returned value — assert is fine here
    assert.Equal(t, "id-1", item.ID)
    assert.Equal(t, "Test", item.Name)
    assert.True(t, item.IsActive)
}
```

Rule of thumb: **`require` for preconditions and setup; `assert` for validating properties of the result.**

---

## Fuzzing (Go 1.18+)

Go has built-in fuzzing support. Use it to discover edge cases that structured tests miss:

```go
// FuzzXxx functions are run by: go test -fuzz=FuzzParseDate
func FuzzParseDate(f *testing.F) {
    // Seed corpus — known good inputs the fuzzer starts from
    f.Add("2024-01-15")
    f.Add("2000-12-31")
    f.Add("")  // edge case seed

    f.Fuzz(func(t *testing.T, input string) {
        // The fuzz function must not panic on any input
        // and must be deterministic (no global state)
        result, err := ParseDate(input)
        if err == nil {
            // If parsing succeeded, the result must be valid
            if result.Year() < 1000 || result.Year() > 9999 {
                t.Errorf("ParseDate(%q) produced out-of-range year %d", input, result.Year())
            }
        }
        // err != nil is acceptable — ParseDate may reject invalid input
    })
}
```

Run with: `go test -fuzz=FuzzParseDate -fuzztime=30s`

Failing corpus inputs are saved to `testdata/fuzz/FuzzParseDate/` and become permanent regression tests.

---

## testcontainers-go for Integration Tests

`testcontainers-go` spins up real Docker containers for integration tests — more portable than requiring a pre-configured `TEST_DB_URL`:

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

This replaces the `t.Skip("TEST_DB_URL not set")` pattern — every CI run gets a fresh, isolated database.

---

## Go Version-Specific Testing Patterns

### Go 1.21+ Testing

```go
// Good — slices.Equal for slice comparison; no reflect.DeepEqual needed
import "slices"

func TestGetNames(t *testing.T) {
    got := getNames(items)
    want := []string{"Alpha", "Beta", "Gamma"}
    if !slices.Equal(got, want) {
        t.Errorf("got %v, want %v", got, want)
    }
}

// Good — maps.Equal for map comparison
import "maps"

func TestBuildIndex(t *testing.T) {
    got := buildIndex(items)
    want := map[string]int{"alpha": 1, "beta": 2}
    if !maps.Equal(got, want) {
        t.Errorf("got %v, want %v", got, want)
    }
}
```

### Go 1.22+ Testing

```go
// No more tt := tt needed in parallel table tests (Go 1.22+)
// Loop variables are captured per-iteration automatically.

// Old (pre-1.22) — required to avoid all subtests sharing the last tt
for _, tt := range tests {
    tt := tt  // remove this in Go 1.22+ projects
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

```go
// Good — test net/http mux with method+path routing (Go 1.22+)
func TestGetItemHandler(t *testing.T) {
    mux := http.NewServeMux()
    mux.HandleFunc("GET /items/{id}", handler.GetItem)

    req := httptest.NewRequest(http.MethodGet, "/items/123", nil)
    w := httptest.NewRecorder()
    mux.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
}
```

### Go 1.23+ Testing

```go
// Good — test range-over-function iterators for both full traversal and early break

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
        break  // consumer stops after first item
    }
    assert.Len(t, got, 1)
}
```

### Go 1.24+ Testing

```go
// Good — os.Root in tests to verify no path traversal escapes the sandbox
func TestFileWriter_StaysInSandbox(t *testing.T) {
    root, err := os.OpenRoot(t.TempDir())
    require.NoError(t, err)
    t.Cleanup(func() { root.Close() })

    err = writer.WriteFile(root, "output.txt", []byte("data"))
    assert.NoError(t, err)

    // Verify that escaping the sandbox is rejected
    err = writer.WriteFile(root, "../etc/passwd", []byte("malicious"))
    assert.Error(t, err)
}
```

### Go 1.25+ Testing

> ⚠️ `testing/synctest` is not yet in a stable release (current stable: Go 1.24 as of Feb 2026). Apply only if running a pre-release build.

```go
// Good — testing/synctest for deterministic concurrent tests (Go 1.25+)
// Runs the test body in a "bubble" with a fake clock; time only advances when
// all goroutines are blocked.
import "testing/synctest"

func TestCacheExpiry(t *testing.T) {
    synctest.Run(func() {
        cache := NewCache(5 * time.Second)
        cache.Set("key", "value")

        time.Sleep(6 * time.Second) // fake sleep — instant, no real delay
        assert.Nil(t, cache.Get("key"), "entry should have expired")
    })
}
```

```go
// Good — testing/synctest for testing timeout behaviour without real waits
func TestOperationTimesOut(t *testing.T) {
    synctest.Run(func() {
        ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
        defer cancel()

        time.Sleep(200 * time.Millisecond) // fake — advances fake clock instantly

        err := SlowOperation(ctx)
        assert.ErrorIs(t, err, context.DeadlineExceeded)
    })
}
```

### Go 1.26+ Testing

```go
// Good — new(T, value) for cleaner test fixture allocation (Go 1.26+)
item := new(Item, Item{Name: "Test", IsActive: true})
assert.Equal(t, "Test", item.Name)

// Old approach
item := &Item{Name: "Test", IsActive: true}
```

```go
// Good — run go fix modernizer in CI to catch outdated test patterns (Go 1.26+)
// go fix -fix=modernize ./...
//
// Automatically updates test code:
// - Removes unnecessary tt := tt loop captures
// - Replaces reflect.DeepEqual(sliceA, sliceB) → slices.Equal(sliceA, sliceB)
// - Replaces sort.Slice in test helpers → slices.SortFunc
```

---

## Resources

- [Go Testing Package](https://pkg.go.dev/testing)
- [Testify](https://github.com/stretchr/testify)
- [go-sqlmock](https://github.com/DATA-DOG/go-sqlmock)
- [Table-Driven Tests](https://go.dev/wiki/TableDrivenTests)
- [Go Subtests and Sub-benchmarks](https://go.dev/blog/subtests)
- [Go Testing Best Practices](https://go.dev/doc/tutorial/add-a-test)
- [Go 1.22 Release Notes](https://go.dev/doc/go1.22)
- [Go 1.23 Range Over Functions](https://go.dev/blog/range-functions)
- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)
- [Go 1.25 Release Notes](https://go.dev/doc/go1.25)
- [testing/synctest package](https://pkg.go.dev/testing/synctest)
- [Go 1.26 Release Notes](https://go.dev/doc/go1.26)
- [slices package](https://pkg.go.dev/slices)
- [maps package](https://pkg.go.dev/maps)
