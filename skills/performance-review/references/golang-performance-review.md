# Go Reference — performance-review

Supplements `performance-checklist.md` for Go projects.

---

## General Go Performance Patterns

### Profiling — Always Measure First

```go
// pprof HTTP endpoint — add to service startup
import _ "net/http/pprof"

func main() {
    go func() {
        log.Println(http.ListenAndServe("localhost:6060", nil))
    }()
}
```

Collect profiles:
```bash
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30
go tool pprof http://localhost:6060/debug/pprof/heap
curl -s http://localhost:6060/debug/pprof/goroutine?debug=1
```

### Benchmarks

```go
func BenchmarkProcess(b *testing.B) {
    data := setupTestData()
    b.ResetTimer()
    b.ReportAllocs()
    for b.Loop() { // Go 1.24+: b.Loop() preferred over i < b.N
        _ = Process(data)
    }
}
```

Run: `go test -bench=. -benchmem -benchtime=5s`

Compare: `go test -bench=. -count=6 | tee new.txt && benchstat old.txt new.txt`

### Escape Analysis

```bash
go build -gcflags='-m=2' ./...
```

Key signals:
- `moved to heap` — value escapes; heap allocation (GC pressure)
- `does not escape` — stays on stack; no GC pressure

Common causes of unintended heap escapes:
- Storing a pointer into `interface{}` / `any`
- Returning a pointer to a local variable
- Passing a local pointer to a goroutine

## Memory Optimisation

### Pre-allocate Slices

```go
// Good — single allocation with known capacity
items := make([]Item, 0, expectedCount)
for _, x := range data {
    items = append(items, process(x))
}

// Bad
var items []Item
for _, x := range data {
    items = append(items, process(x))
}
```

### Use `strings.Builder` for String Assembly

```go
// Good
var b strings.Builder
b.Grow(estimatedSize)
for _, s := range parts {
    b.WriteString(s)
}
result := b.String()

// Bad
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

`sync.Pool` objects may be GC'd at any time. Never use for items requiring explicit cleanup (file handles, DB connections).

### Pointer vs Value Receivers

```go
// Pointer receiver for: modified structs, large structs (avoid copy)
func (s *LargeStruct) Process() { ... }

// Value receiver for: small immutable structs, method should work on copy
func (p Point) Distance() float64 { ... }
```

## Algorithm Optimisation

### Map Lookups vs Linear Search

```go
// Bad — O(n) per lookup
func findByID(items []Item, id int) *Item {
    for i := range items {
        if items[i].ID == id { return &items[i] }
    }
    return nil
}

// Good — O(1) lookup after O(n) build
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

// Good
cached := expensiveCalc(sharedData)
for i := range items {
    total += cached * items[i].Value
}
```

## Goroutines and Concurrency

### Avoid Goroutine Leaks

```go
// Bad — goroutine blocked forever if channel never written
func leaky() {
    ch := make(chan int)
    go func() {
        v := <-ch
        process(v)
    }()
}

// Good — honour context cancellation
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
ch := make(chan int)     // Unbuffered — synchronisation / hand-off
ch := make(chan int, 100) // Buffered — async up to capacity; use when upper bound known
// Over-buffering wastes memory and hides backpressure
```

### Excessive Goroutine Creation

```go
// Bad — goroutine overhead dominates for trivial work
for i := range 1_000_000 {
    go func(n int) { _ = n * 2 }(i)
}
// Good — batch work or use a bounded worker pool
```

## Database Performance

> Examples use GORM. Same principles for `database/sql`, `pgx`, `sqlc`.

### Avoid N+1 Queries

```go
// Bad
var items []Item
db.Find(&items)
for _, item := range items {
    db.Where("id = ?", item.CategoryID).First(&category)
}

// Good
db.Preload("Category").Find(&items)
```

### Select Only Needed Columns

```go
// Bad — SELECT *
db.Find(&items)

// Good
db.Select("id", "name", "status").Find(&items)
```

### Paginate List Queries

```go
// Good — bounded result set
db.Limit(pageSize).Offset(offset).Find(&items)
// Prefer keyset pagination for large tables:
db.Where("id > ?", lastSeenID).Limit(pageSize).Find(&items)
```

### Configure Connection Pool

```go
sqlDB, _ := db.DB()
sqlDB.SetMaxOpenConns(25)
sqlDB.SetMaxIdleConns(10)
sqlDB.SetConnMaxLifetime(5 * time.Minute)
sqlDB.SetConnMaxIdleTime(2 * time.Minute)
```

## HTTP Client

### Reuse the HTTP Client

```go
// Bad — new client per request; no connection pooling
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

## JSON Performance

### Prefer Typed Structs Over `map[string]interface{}`

```go
// Good — compile-time field names, faster marshal/unmarshal
type Response struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

// Bad — dynamic map: slower, more allocations
var response map[string]interface{}
```

### Stream Large JSON Payloads

```go
// Good — constant memory regardless of payload size
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

## Common Pitfalls

### `defer` Inside Loops

```go
// Bad — defers accumulate until function returns; handles stay open
for _, path := range paths {
    f, _ := os.Open(path)
    defer f.Close()
    process(f)
}

// Good — anonymous function forces defer each iteration
for _, path := range paths {
    func() {
        f, err := os.Open(path)
        if err != nil { return }
        defer f.Close()
        process(f)
    }()
}
```

### Range Copies Values

```go
// Bad — modifies a copy
for _, item := range items {
    item.Name = "updated"
}

// Good — index to modify in place
for i := range items {
    items[i].Name = "updated"
}
```

## Go 1.23 Performance Features

### Range-Over-Function Iterators (Lazy Traversal)

```go
// Good — lazy iterator; stops when consumer breaks
func ActiveItems(items []Item) iter.Seq[Item] {
    return func(yield func(Item) bool) {
        for _, item := range items {
            if item.IsActive {
                if !yield(item) { return }
            }
        }
    }
}

for item := range ActiveItems(allItems) {
    if item.Name == target { break }
}

// Bad — builds full intermediate slice even if only first match needed
filtered := make([]Item, 0)
for _, item := range allItems {
    if item.IsActive {
        filtered = append(filtered, item)
    }
}
```

### `slices` and `maps` Packages (Go 1.21+, idiomatic in 1.23)

```go
// Good — slices.SortFunc is type-safe, avoids reflect overhead
slices.SortFunc(items, func(a, b Item) int {
    return cmp.Compare(a.Name, b.Name)
})

// Bad — sort.Slice uses interface boxing
sort.Slice(items, func(i, j int) bool {
    return items[i].Name < items[j].Name
})
```

```go
// Good — min/max built-ins
largest := max(a, b, c)

// Bad
largest := a
if b > largest { largest = b }
if c > largest { largest = c }
```

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

## Go 1.25 Performance Features (upcoming)

> Not yet stable (current: Go 1.24, March 2026). Apply only on pre-release builds.

### Automatic GOMAXPROCS in Containers

Go 1.25 auto-detects cgroup CPU limits. No code change required. Previously required `runtime.GOMAXPROCS(containerCPULimit)` via libraries like `automaxprocs`.

```go
// Go 1.25+: GOMAXPROCS set correctly automatically in containers.
// runtime.SetDefaultGOMAXPROCS() — restores auto-detection if overridden
```

### `runtime/trace.FlightRecorder` for In-Production Profiling

```go
recorder := trace.NewFlightRecorder()
recorder.Start()
// ... production request handling ...
// Capture trace on anomaly
var buf bytes.Buffer
if err := recorder.WriteTo(&buf); err == nil {
    saveTraceFile(buf.Bytes())
}
```

### Green Tea GC (opt-in 1.25, default 1.26)

```bash
GOEXPERIMENT=greenteagc go run ./...
```

## Go 1.26 Performance Features (upcoming)

> Not yet stable (current: Go 1.24, March 2026). Apply only on pre-release builds.

### Green Tea GC — Default in 1.26

Enabled by default. No code changes required. Reduces GC stop-the-world pauses and improves throughput in allocation-heavy workloads. Check that no production code sets `GOGC=off` or excessively large `GOGC` values that were workarounds for old GC behaviour.

### `go fix -fix=modernize`

```bash
go fix -fix=modernize ./...
# Fixes: sort.Slice → slices.SortFunc, strings.Index >= 0 → strings.Contains, reflect.DeepEqual → slices.Equal
```

### `new(T, value)` (Go 1.26+)

```go
// Good — single expression, compiler may optimise more aggressively
p := new(Config, Config{Host: "localhost", Port: 5432, Timeout: 30 * time.Second})

// Old — two steps
p := new(Config)
*p = Config{Host: "localhost", Port: 5432, Timeout: 30 * time.Second}
```
