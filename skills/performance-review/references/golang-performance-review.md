# Go Reference — performance-review

Supplements `performance-checklist.md` for Go projects.

---

## General Go Performance Patterns

Universal performance guidance that applies across all supported Go versions (1.23+).

### Profiling — Always Measure First

```go
// pprof HTTP endpoint — add to service startup
import _ "net/http/pprof"

func main() {
    go func() {
        // Never expose on a public port
        log.Println(http.ListenAndServe("localhost:6060", nil))
    }()
    // ...
}
```

Collect profiles:
```bash
# CPU profile (30s)
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Heap profile
go tool pprof http://localhost:6060/debug/pprof/heap

# Goroutine count (leak detection)
curl -s http://localhost:6060/debug/pprof/goroutine?debug=1
```

### Benchmarks

```go
func BenchmarkProcess(b *testing.B) {
    data := setupTestData()
    b.ResetTimer()    // exclude setup from measurement
    b.ReportAllocs()  // report allocations per op
    for b.Loop() {    // Go 1.24+: b.Loop() preferred over i < b.N
        _ = Process(data)
    }
}
```

Run with: `go test -bench=. -benchmem -benchtime=5s`

Compare before/after: `go test -bench=. -count=6 | tee new.txt && benchstat old.txt new.txt`

### Escape Analysis

```bash
# Show which allocations escape to heap
go build -gcflags='-m=2' ./...
```

Key signals:
- `moved to heap` — value escapes; allocation is on the heap (GC pressure)
- `does not escape` — stays on stack; no GC pressure

Common causes of unintended heap escapes:
- Storing a pointer into an interface (`interface{}` / `any`)
- Returning a pointer to a local variable from a function
- Passing a local pointer to a goroutine

---

## Memory Optimisation

### Pre-allocate Slices

```go
// Good — single allocation with known capacity
items := make([]Item, 0, expectedCount)
for _, x := range data {
    items = append(items, process(x))
}

// Bad — repeated reallocations (doubling) as capacity grows
var items []Item
for _, x := range data {
    items = append(items, process(x))
}
```

### Use `strings.Builder` for String Assembly

```go
// Good — single allocation
var b strings.Builder
b.Grow(estimatedSize) // optional: pre-size the buffer
for _, s := range parts {
    b.WriteString(s)
}
result := b.String()

// Bad — allocates a new string on every + operation
result := ""
for _, s := range parts {
    result += s
}
```

### Reuse Buffers in Hot Paths with `sync.Pool`

```go
var bufPool = sync.Pool{
    New: func() any { return new(bytes.Buffer) },
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
```

Note: `sync.Pool` objects may be GC'd at any time. Never use it for items requiring explicit cleanup (file handles, DB connections).

### Pointer vs Value Receivers

```go
// Use pointer receiver for:
// 1. Structs that are modified
// 2. Large structs (avoid copying on every call)
func (s *LargeStruct) Process() { ... }

// Use value receiver for:
// 1. Small, immutable structs (e.g. Point, Color)
// 2. When the method should work on a copy
func (p Point) Distance() float64 { ... }
```

---

## Algorithm Optimisation

### Map Lookups vs Linear Search

```go
// Bad — O(n) per lookup; fine for small n, terrible for large n
func findByID(items []Item, id int) *Item {
    for i := range items {
        if items[i].ID == id {
            return &items[i]
        }
    }
    return nil
}

// Good — O(1) lookup after O(n) build; use when queried repeatedly
index := make(map[int]*Item, len(items))
for i := range items {
    index[items[i].ID] = &items[i]
}
item := index[id]
```

### Cache Expensive Computations

```go
// Bad — recomputes on every iteration
for i := range items {
    total += expensiveCalc(sharedData) * items[i].Value
}

// Good — compute once, reuse in loop
cached := expensiveCalc(sharedData)
for i := range items {
    total += cached * items[i].Value
}
```

---

## Goroutines and Concurrency

### Avoid Goroutine Leaks

```go
// Bad — goroutine blocked forever if channel is never written to
func leaky() {
    ch := make(chan int)
    go func() {
        v := <-ch // blocks indefinitely
        process(v)
    }()
}

// Good — always honour context cancellation
func safe(ctx context.Context) {
    ch := make(chan int)
    go func() {
        select {
        case v := <-ch:
            process(v)
        case <-ctx.Done():
            return
        }
    }()
}
```

### Worker Pool Pattern (Bounded Concurrency)

```go
func workerPool(ctx context.Context, jobs <-chan Job, numWorkers int) <-chan Result {
    results := make(chan Result)
    var wg sync.WaitGroup

    for range numWorkers {
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
// Unbuffered — synchronisation / hand-off between goroutines
ch := make(chan int)

// Buffered — async up to capacity; use when you know the upper bound
ch := make(chan int, 100)

// Over-buffering wastes memory and hides backpressure — don't set arbitrarily large buffers
```

### Excessive Goroutine Creation

```go
// Bad — goroutine overhead dominates for trivial work; scheduler thrashes
for i := range 1_000_000 {
    go func(n int) { _ = n * 2 }(i)
}

// Good — batch work or use a bounded worker pool
```

---

## Database Performance

> Examples use GORM. For `database/sql`, `pgx`, or `sqlc`: same principles apply — use prepared statements, select only needed columns, configure connection pool limits.

### Avoid N+1 Queries

```go
// Bad — one query per item to load its association
var items []Item
db.Find(&items)
for _, item := range items {
    db.Where("id = ?", item.CategoryID).First(&category)
}

// Good — single join query
db.Preload("Category").Find(&items)
// or
db.Joins("Category").Find(&items)
```

### Select Only Needed Columns

```go
// Bad — SELECT * transfers unused columns, decodes unused data
db.Find(&items)

// Good — only fetch what you need
db.Select("id", "name", "status").Find(&items)
```

### Paginate List Queries

```go
// Good — bounded result set prevents full-table scans
db.Limit(pageSize).Offset(offset).Find(&items)
// Prefer keyset pagination over OFFSET for large tables:
db.Where("id > ?", lastSeenID).Limit(pageSize).Find(&items)
```

### Configure Connection Pool

```go
sqlDB, err := db.DB()
if err != nil {
    return fmt.Errorf("getting sql.DB: %w", err)
}
sqlDB.SetMaxOpenConns(25)
sqlDB.SetMaxIdleConns(10)
sqlDB.SetConnMaxLifetime(5 * time.Minute)
sqlDB.SetConnMaxIdleTime(2 * time.Minute)
```

---

## HTTP Client

### Reuse the HTTP Client

```go
// Bad — new client per request; no connection pooling; TCP handshake on every call
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
```

---

## JSON Performance

### Prefer Typed Structs Over `map[string]interface{}`

```go
// Good — compile-time field names, faster marshalling/unmarshalling
type Response struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

// Bad — dynamic map: slower, no compile-time field names, allocates more
var response map[string]interface{}
```

### Stream Large JSON Payloads

```go
// Good — decodes one item at a time; constant memory regardless of payload size
decoder := json.NewDecoder(resp.Body)
for {
    var item Item
    if err := decoder.Decode(&item); err == io.EOF {
        break
    } else if err != nil {
        return fmt.Errorf("decoding item: %w", err)
    }
    process(item)
}
```

---

## Common Pitfalls

### `defer` Inside Loops

```go
// Bad — defers accumulate until the function returns; file handles stay open
for _, path := range paths {
    f, _ := os.Open(path)
    defer f.Close() // closes after ALL iterations complete
    process(f)
}

// Good — anonymous function forces defer to run each iteration
for _, path := range paths {
    func() {
        f, err := os.Open(path)
        if err != nil {
            return
        }
        defer f.Close()
        process(f)
    }()
}
```

### Range Copies Values

```go
// Bad — modifies a copy of the element, not the original
for _, item := range items {
    item.Name = "updated" // modifies a copy
}

// Good — use the index to modify in place
for i := range items {
    items[i].Name = "updated"
}
```

---

## Go 1.23 Performance Features

### Range-Over-Function Iterators (Lazy Traversal)

```go
// Good — lazy iterator; stops immediately when consumer breaks
import "iter"

func ActiveItems(items []Item) iter.Seq[Item] {
    return func(yield func(Item) bool) {
        for _, item := range items {
            if item.IsActive {
                if !yield(item) {
                    return // consumer broke — stop immediately
                }
            }
        }
    }
}

// Caller — no intermediate slice allocated; stops at first match
for item := range ActiveItems(allItems) {
    if item.Name == target {
        break
    }
}

// Bad — builds full intermediate slice even if only first match is needed
filtered := make([]Item, 0)
for _, item := range allItems {
    if item.IsActive {
        filtered = append(filtered, item)
    }
}
```

### `slices` and `maps` Packages (Go 1.21+, idiomatic in 1.23)

```go
// Good — slices.SortFunc is type-safe and avoids reflect overhead vs sort.Slice
import ("cmp"; "slices")

slices.SortFunc(items, func(a, b Item) int {
    return cmp.Compare(a.Name, b.Name)
})

// Bad — sort.Slice uses interface boxing internally
sort.Slice(items, func(i, j int) bool {
    return items[i].Name < items[j].Name
})
```

```go
// Good — min/max built-ins; no helper function overhead
largest := max(a, b, c)

// Bad — manual comparison chain
largest := a
if b > largest { largest = b }
if c > largest { largest = c }
```

---

## Go 1.24 Performance Features

### `b.Loop()` for Accurate Benchmarks

```go
// Good — b.Loop() handles warmup and timing more accurately than i < b.N
func BenchmarkProcess(b *testing.B) {
    data := generateData()
    b.ResetTimer()
    for b.Loop() {
        _ = Process(data)
    }
}
```

### Weak Pointers for GC-Friendly Caches

```go
// Good — cache values can be GC'd under memory pressure; no unbounded growth
import "weak"

type Cache struct {
    mu      sync.Mutex
    entries map[string]weak.Pointer[ExpensiveObject]
}

func (c *Cache) Get(key string, compute func() *ExpensiveObject) *ExpensiveObject {
    c.mu.Lock()
    defer c.mu.Unlock()
    if ptr, ok := c.entries[key]; ok {
        if val := ptr.Value(); val != nil {
            return val
        }
    }
    val := compute()
    c.entries[key] = weak.Make(val)
    return val
}

// Bad — unbounded sync.Map cache grows forever under load
```

---

## Go 1.25 Performance Features (upcoming)

> Go 1.25 is not yet in stable release (current stable: Go 1.24, March 2026). Apply only on pre-release builds.

### Automatic GOMAXPROCS in Containers

Go 1.25 auto-detects cgroup CPU limits in containers. No code change required. The runtime reads cgroup CPU bandwidth automatically.

Previously required: `runtime.GOMAXPROCS(containerCPULimit)` via libraries like `automaxprocs`.

```go
// Go 1.25+: GOMAXPROCS is set correctly automatically in containerised environments.
// Only override if you have a specific reason:
// runtime.SetDefaultGOMAXPROCS() — restores auto-detection if overridden
```

### `runtime/trace.FlightRecorder` for In-Production Profiling

```go
import "runtime/trace"

recorder := trace.NewFlightRecorder()
recorder.Start()

// ... production request handling ...

// Capture trace on anomaly (e.g. high-latency request detected)
var buf bytes.Buffer
if err := recorder.WriteTo(&buf); err == nil {
    saveTraceFile(buf.Bytes())
}
```

### Green Tea GC (opt-in in 1.25, default in 1.26)

```bash
# Opt-in in Go 1.25 — reduces GC overhead in GC-heavy workloads
GOEXPERIMENT=greenteagc go run ./...
```

---

## Go 1.26 Performance Features (upcoming)

> Go 1.26 is not yet in stable release (current stable: Go 1.24, March 2026). Apply only on pre-release builds.

### Green Tea GC — Default in 1.26

The Green Tea garbage collector is enabled by default in Go 1.26. No code changes required. It reduces GC stop-the-world pauses and improves throughput in allocation-heavy workloads.

Check that no production code sets `GOGC=off` or excessively large `GOGC` values that were workarounds for old GC behaviour.

### `go fix -fix=modernize` for Performance Anti-Pattern Detection

```bash
# Run in CI — auto-applies idiomatic upgrades that also improve performance
go fix -fix=modernize ./...

# Examples of what it fixes automatically:
# - sort.Slice → slices.SortFunc (avoids reflect boxing)
# - strings.Index(...) >= 0 → strings.Contains(...)
# - reflect.DeepEqual on slices → slices.Equal
```

### `new(T, value)` Reduces Two-Step Allocation Patterns

```go
// Good (Go 1.26+) — single expression, compiler may optimise more aggressively
p := new(Config, Config{Host: "localhost", Port: 5432, Timeout: 30 * time.Second})

// Old — two steps
p := new(Config)
*p = Config{Host: "localhost", Port: 5432, Timeout: 30 * time.Second}
```

---

## Resources

- [Profiling Go Programs](https://go.dev/blog/pprof)
- [Go Performance Book](https://github.com/dgryski/go-perfbook)
- [Go Wiki: Performance](https://go.dev/wiki/Performance)
- [Effective Go](https://go.dev/doc/effective_go)
- [slices package](https://pkg.go.dev/slices)
- [maps package](https://pkg.go.dev/maps)
- [iter package](https://pkg.go.dev/iter)
- [weak package](https://pkg.go.dev/weak)
- [sync.Pool](https://pkg.go.dev/sync#Pool)
- [runtime/trace FlightRecorder](https://pkg.go.dev/runtime/trace#FlightRecorder)
- [Go 1.23 Release Notes](https://go.dev/doc/go1.23)
- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)
- [Go 1.25 Release Notes](https://go.dev/doc/go1.25)
- [Go 1.26 Release Notes](https://go.dev/doc/go1.26)
