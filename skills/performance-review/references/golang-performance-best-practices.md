# Go Performance Best Practices

Applies to: Go 1.21+ projects.

---

## Profiling

Always measure before optimising.

### pprof (HTTP endpoint)

```go
import _ "net/http/pprof"

// Register in main or init
go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()
```

Access profiles at:
- `http://localhost:6060/debug/pprof/`
- CPU: `go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30`
- Heap: `go tool pprof http://localhost:6060/debug/pprof/heap`

### Benchmarks

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

## Memory Optimisation

### Pre-allocate Slices

```go
// Good — single allocation with known capacity
items := make([]Item, 0, expectedCount)

// Bad — repeated reallocations as capacity grows
var items []Item
for _, x := range data {
    items = append(items, process(x))
}
```

### Use strings.Builder for String Concatenation

```go
// Good — single allocation
var b strings.Builder
for _, s := range parts {
    b.WriteString(s)
}
result := b.String()

// Bad — allocates a new string on every iteration
result := ""
for _, s := range parts {
    result += s
}
```

### Reuse Buffers in Hot Paths

```go
// Good — allocate once, reset per iteration
var buf bytes.Buffer
for _, item := range items {
    buf.Reset()
    buf.WriteString(item.Name)
    process(buf.Bytes())
}

// Bad — allocates a new buffer every iteration
for _, item := range items {
    var buf bytes.Buffer
    buf.WriteString(item.Name)
    process(buf.Bytes())
}
```

### Pointer vs Value Receivers

```go
// Use pointer receiver for:
// 1. Structs that are modified
// 2. Large structs (avoid copying)
func (s *LargeStruct) Process() { ... }

// Use value receiver for:
// 1. Small, immutable structs
// 2. Simple types
func (p Point) Distance() float64 { ... }
```

---

## Algorithm Optimisation

### Map Lookups vs Linear Search

```go
// Bad — O(n) per lookup
func findByID(items []Item, id int) *Item {
    for _, item := range items {
        if item.ID == id {
            return &item
        }
    }
    return nil
}

// Good — O(1) lookup after O(n) build
index := make(map[int]Item, len(items))
for _, item := range items {
    index[item.ID] = item
}
item := index[id]
```

### Cache Expensive Computations

```go
// Bad — recomputes every iteration
for i := 0; i < len(items); i++ {
    total += expensiveCalc(sharedData) * items[i].Value
}

// Good — compute once, reuse
cached := expensiveCalc(sharedData)
for i := 0; i < len(items); i++ {
    total += cached * items[i].Value
}
```

---

## Goroutines & Concurrency

### Avoid Goroutine Leaks

```go
// Bad — goroutine blocked forever if ctx is never cancelled
func leak() {
    ch := make(chan int)
    go func() {
        for {
            select {
            case v := <-ch:
                process(v)
            }
        }
    }()
}

// Good — always honour context cancellation
func noLeak(ctx context.Context) {
    ch := make(chan int)
    go func() {
        for {
            select {
            case v := <-ch:
                process(v)
            case <-ctx.Done():
                return
            }
        }
    }()
}
```

### Worker Pool Pattern

```go
func workerPool(ctx context.Context, jobs <-chan Job, numWorkers int) <-chan Result {
    results := make(chan Result)
    var wg sync.WaitGroup

    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobs {
                select {
                case results <- process(job):
                case <-ctx.Done():
                    return
                }
            }
        }()
    }

    go func() {
        wg.Wait()
        close(results)
    }()

    return results
}
```

### Channel Buffer Sizing

```go
// Unbuffered — synchronisation point between goroutines
ch := make(chan int)

// Buffered — async up to capacity; use when you know max pending work
ch := make(chan int, 100)

// Rule of thumb:
// - Unbuffered for hand-off / rendezvous
// - Buffered when you know the upper bound of pending items
// - Don't over-buffer — wastes memory and hides backpressure
```

---

## Database Performance (GORM)

> **Note:** This section uses GORM as the example ORM. For projects using `database/sql` directly or `pgx`/`sqlc`, the same principles apply — use prepared statements, batch queries, select only needed columns, and configure connection pool limits via `sql.DB.SetMaxOpenConns` / `SetMaxIdleConns`.



### Avoid N+1 Queries

```go
// Bad — N+1: one query per item to load its category
var items []Item
db.Find(&items)
for _, item := range items {
    var category Category
    db.Where("id = ?", item.CategoryID).First(&category)
    // Use category
}

// Good — single query with JOIN
db.Preload("Category").Find(&items)
// or
db.Joins("Category").Find(&items)
```

### Select Only Needed Fields

```go
// Bad — SELECT * when only a few fields are needed
db.Find(&items)

// Good — only fetch the columns you need
db.Select("id", "name", "status").Find(&items)
```

### Always Paginate List Queries

```go
// Good — bounded result set
db.Limit(pageSize).Offset(offset).Find(&items)
```

### Configure Connection Pool

```go
sqlDB, _ := db.DB()
sqlDB.SetMaxOpenConns(25)
sqlDB.SetMaxIdleConns(10)
sqlDB.SetConnMaxLifetime(5 * time.Minute)
```

### Use Prepared Statements for Repeated Queries

```go
stmt, _ := db.Prepare("SELECT * FROM items WHERE id = ?")
defer stmt.Close()

for _, id := range ids {
    stmt.QueryRow(id)
}
```

---

## HTTP Client

### Reuse the HTTP Client

```go
// Bad — new client per request means no connection pooling
func fetch(url string) {
    client := &http.Client{}
    client.Get(url)
}

// Good — package-level client with tuned transport
var httpClient = &http.Client{
    Timeout: 10 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
        IdleConnTimeout:     90 * time.Second,
    },
}

func fetch(url string) {
    httpClient.Get(url)
}
```

---

## JSON Performance

### Prefer Typed Structs Over `map[string]interface{}`

```go
// Good — faster marshalling/unmarshalling
type Response struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

// Bad — dynamic map is slower
var response map[string]interface{}
```

### Stream Large JSON Payloads

```go
decoder := json.NewDecoder(resp.Body)
for {
    var item Item
    if err := decoder.Decode(&item); err == io.EOF {
        break
    } else if err != nil {
        return err
    }
    process(item)
}
```

---

## Common Pitfalls

### `defer` Inside Loops

```go
// Bad — defers accumulate until the function returns, not until the loop iteration ends
for _, path := range paths {
    f, _ := os.Open(path)
    defer f.Close()  // Won't close until the enclosing function returns
    process(f)
}

// Good — wrap in an anonymous function so defer runs immediately
for _, path := range paths {
    func() {
        f, _ := os.Open(path)
        defer f.Close()
        process(f)
    }()
}
```

### Range Copies Values

```go
// Bad — modifies a copy, not the original slice element
for _, item := range items {
    item.Name = "updated"  // Modifies a copy
}

// Good — use the index
for i := range items {
    items[i].Name = "updated"
}
```

### Excessive Goroutine Creation

```go
// Bad — goroutine overhead dominates for trivial work
for i := 0; i < 1_000_000; i++ {
    go func(n int) { _ = n * 2 }(i)
}

// Good — batch work or use a worker pool; only spawn goroutines for substantial work
```

---

## Object Pooling with sync.Pool

`sync.Pool` reduces GC pressure by reusing allocated objects in hot paths:

```go
// Good — pool buffers to avoid per-request allocation
var bufPool = sync.Pool{
    New: func() any {
        return new(bytes.Buffer)
    },
}

func processRequest(data []byte) string {
    buf := bufPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset()
        bufPool.Put(buf)
    }()
    buf.Write(data)
    return buf.String()
}

// Bad — allocates a new buffer on every call
func processRequest(data []byte) string {
    var buf bytes.Buffer
    buf.Write(data)
    return buf.String()
}
```

Note: `sync.Pool` objects may be GC'd at any time. Do not use it for items that require explicit cleanup (e.g. file handles, DB connections).

---

## Escape Analysis

Use the compiler's escape analysis to understand which allocations go to the heap:

```bash
# -m=2 shows full escape analysis; -m is less verbose
go build -gcflags='-m=2' ./...
```

Key messages to look for:
- `moved to heap` — value escapes; this allocation is on the heap
- `does not escape` — stays on stack; no GC pressure

Common causes of unintended escapes:
- Storing a pointer into an interface (`interface{}` / `any`)
- Returning a pointer to a local variable
- Passing a local pointer to a goroutine

Reducing heap allocations in hot paths (serialization, request handling) can significantly lower GC pause times.

---

## Go Version-Specific Performance Features

### Go 1.21+ Performance

```go
// Good — slices.SortFunc is type-safe and avoids reflect overhead vs sort.Slice
import (
    "cmp"
    "slices"
)

slices.SortFunc(items, func(a, b Item) int {
    return cmp.Compare(a.Name, b.Name)
})

// Bad — sort.Slice uses interface{} boxing internally
sort.Slice(items, func(i, j int) bool {
    return items[i].Name < items[j].Name
})
```

```go
// Good — min/max built-ins avoid helper function overhead
largest := max(a, b, c)

// Bad — manual comparison chain
largest := a
if b > largest {
    largest = b
}
if c > largest {
    largest = c
}
```

### Go 1.22+ Performance

```go
// Good — range over integer: idiomatic and avoids off-by-one errors
for i := range 10 {
    process(i)
}

// Old style — verbose
for i := 0; i < 10; i++ {
    process(i)
}
```

In Go 1.22+, loop variables have per-iteration scope. Remove `tt := tt` copies in parallel table tests — they are unnecessary and add stack allocation overhead.

### Go 1.23+ Performance

```go
// Good — range-over-function iterators allow lazy, allocation-free traversal
// The iterator short-circuits when the consumer breaks early.
import "iter"

func ActiveItems(items []Item) iter.Seq[Item] {
    return func(yield func(Item) bool) {
        for _, item := range items {
            if item.IsActive {
                if !yield(item) {
                    return  // consumer broke early — stop immediately
                }
            }
        }
    }
}

// Caller — no intermediate slice allocated
for item := range ActiveItems(allItems) {
    if item.Name == target {
        break  // iterator stops immediately
    }
}

// Bad — allocates full filtered slice even if caller only needs first match
filtered := make([]Item, 0)
for _, item := range allItems {
    if item.IsActive {
        filtered = append(filtered, item)
    }
}
```

### Go 1.24+ Performance

```go
// Good — weak pointers allow GC to reclaim cached values under memory pressure
import "weak"

type Cache struct {
    entries map[string]weak.Pointer[ExpensiveObject]
}

func (c *Cache) Get(key string) *ExpensiveObject {
    if ptr, ok := c.entries[key]; ok {
        if val := ptr.Value(); val != nil {
            return val  // still alive
        }
    }
    val := computeExpensive(key)
    c.entries[key] = weak.Make(val)
    return val
}
```

> ⚠️ **Note:** Features in the following sections marked Go 1.25+ or Go 1.26+ are upcoming and not yet in a stable release. Current stable Go version is Go 1.24 (as of Feb 2026).

### Go 1.25+ Performance

```go
// Good — GOMAXPROCS now auto-detects cgroup CPU limits in containers (Go 1.25+)
// No code change needed — the runtime reads cgroup CPU bandwidth automatically.
// Previously required manual: runtime.GOMAXPROCS(containerCPULimit)
// Now: runtime defaults correctly; use runtime.SetDefaultGOMAXPROCS() to restore
// default behaviour if you override it.
```

```go
// Good — runtime/trace.FlightRecorder for low-overhead in-production trace capture
import "runtime/trace"

recorder := trace.NewFlightRecorder()
recorder.Start()

// ... production request handling ...

// Capture on anomaly (e.g. high latency detected)
var buf bytes.Buffer
if err := recorder.WriteTo(&buf); err == nil {
    saveTraceFile(buf.Bytes())
}
```

The experimental Green Tea GC (enabled by default in Go 1.26) begins in Go 1.25 as opt-in:
```bash
GOEXPERIMENT=greenteagc go run ./...
```

### Go 1.26+ Performance

```go
// Good — new(T, value) allocates and initialises in one expression (Go 1.26+)
p := new(int, 42)          // *int pointing to 42
q := new(Config, Config{   // *Config with fields set
    Host:    "localhost",
    Port:    5432,
    Timeout: 30 * time.Second,
})

// Old approach — two steps
p := new(int)
*p = 42
```

The Green Tea garbage collector is enabled by default in Go 1.26, reducing GC overhead significantly in GC-heavy workloads. No code changes required.

```go
// Good — go fix modernizer auto-applies idiomatic upgrades (Go 1.26+)
// Run in CI or before code review to flag outdated patterns:
// go fix -fix=modernize ./...
//
// Examples of what it fixes automatically:
// - sort.Slice → slices.SortFunc
// - strings.Index(...) >= 0 → strings.Contains(...)
// - reflect.DeepEqual on slices → slices.Equal
```

---

## Resources

- [Go Performance Book](https://github.com/dgryski/go-perfbook)
- [Profiling Go Programs](https://go.dev/blog/pprof)
- [Effective Go](https://go.dev/doc/effective_go)
- [Go Wiki: Performance](https://go.dev/wiki/Performance)
- [Go 1.21 Release Notes](https://go.dev/doc/go1.21)
- [Go 1.22 Release Notes](https://go.dev/doc/go1.22)
- [Go 1.23 Release Notes](https://go.dev/doc/go1.23)
- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)
- [Go 1.25 Release Notes](https://go.dev/doc/go1.25)
- [Go 1.26 Release Notes](https://go.dev/doc/go1.26)
- [runtime/trace FlightRecorder](https://pkg.go.dev/runtime/trace#FlightRecorder)
- [slices package](https://pkg.go.dev/slices)
- [iter package](https://pkg.go.dev/iter)
