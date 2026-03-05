# Gin Performance Best Practices

Applies to: Go projects using the Gin HTTP framework (v1.x).
Load in addition to `golang-performance-review.md`.

---

## Router & Middleware

### Avoid Per-Route Middleware Repetition

Gin applies middleware sequentially on every request that matches the route. Repeating the same middleware per route multiplies the call overhead and maintenance surface:

```go
// Bad — middleware applied redundantly on every route; hard to maintain
router.GET("/v1/items", AuthMiddleware(), ListItems)
router.POST("/v1/items", AuthMiddleware(), CreateItem)
router.GET("/v1/users", AuthMiddleware(), ListUsers)

// Good — apply once on the group; single registration, same runtime cost per request
v1 := router.Group("/v1", AuthMiddleware())
v1.GET("/items", ListItems)
v1.POST("/items", CreateItem)
v1.GET("/users", ListUsers)
```

### Keep Middleware Lean

Every middleware runs on every matched request in its group. Avoid in middleware:

- Allocating new objects on each call — use `sync.Pool` for reusable buffers
- Synchronous calls to external services (DB lookups, cache misses, outbound HTTP) unless unavoidable
- Logging full request/response bodies in production — log metadata (method, path, status, latency) only

---

## Request Binding

### Prefer `ShouldBind*` over Manual JSON Decode

Gin's `ShouldBindJSON` uses internal decoder pooling. Creating a new `json.NewDecoder` per request allocates on every call:

```go
// Bad — allocates a new decoder on every request
var req CreateItemRequest
if err := json.NewDecoder(c.Request.Body).Decode(&req); err != nil {
    c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
    return
}

// Good — Gin manages the decoder pool
var req CreateItemRequest
if err := c.ShouldBindJSON(&req); err != nil {
    c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
    return
}
```

### Cap Request Body Size Early

Unbounded body reads can exhaust memory under sustained load or against adversarial input. Apply the limit before any binding — globally via middleware is preferred over per-handler:

```go
// Global body-limit middleware — register before route definitions
func BodyLimitMiddleware(limit int64) gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, limit)
        c.Next()
    }
}

// Wire it
router := gin.New()
router.Use(BodyLimitMiddleware(1 << 20)) // 1 MiB
```

---

## Response Rendering

### Use Typed Structs, Not `gin.H` for Repeated Response Shapes

`gin.H` is `map[string]any` — marshalling a map requires runtime reflection over keys. A concrete struct is faster and type-safe:

```go
// Bad — map marshalling; slower for recurring response shapes
c.JSON(http.StatusOK, gin.H{"data": items, "total": count})

// Good — struct marshalling; faster and compiler-checked
type ListResponse[T any] struct {
    Data  []T   `json:"data"`
    Total int64 `json:"total"`
}
c.JSON(http.StatusOK, ListResponse[Item]{Data: items, Total: count})
```

Reserve `gin.H` for one-off or error responses where defining a struct would be disproportionate.

---

## Context Propagation

### Always Pass `c.Request.Context()` Downstream

Using `context.Background()` in downstream calls ignores client disconnects — the DB or HTTP call may continue running after the client has gone away, wasting resources:

```go
// Bad — ignores request cancellation; downstream work outlives the client
items, err := h.useCase.List(context.Background())

// Good — cancels downstream work when client disconnects or timeout fires
items, err := h.useCase.List(c.Request.Context())
```

Set timeouts at the use-case or repository layer — not in the handler — so timeout policy is consistent across all transports (HTTP, gRPC, CLI, queue consumer).

---

## Server Configuration

### Configure `http.Server` Timeouts Explicitly

`router.Run()` uses `net/http`'s default server with zero timeouts — vulnerable to slow-client and Slowloris DoS attacks. Always wrap the router in an `http.Server`:

```go
// Bad — zero timeouts; one slow client can hold a connection open indefinitely
router.Run(":8080")

// Good — explicit timeout budget per phase
srv := &http.Server{
    Addr:              ":8080",
    Handler:           router,
    ReadHeaderTimeout: 5 * time.Second,
    ReadTimeout:       10 * time.Second,
    WriteTimeout:      30 * time.Second,
    IdleTimeout:       120 * time.Second,
    MaxHeaderBytes:    1 << 20,
}
log.Fatal(srv.ListenAndServe())
```

### Graceful Shutdown

Use `http.Server.Shutdown()` with a timeout to drain in-flight requests before exit — avoids dropping active connections on SIGTERM:

```go
srv := &http.Server{Addr: ":8080", Handler: router}

go func() {
    if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
        log.Fatalf("listen: %s\n", err)
    }
}()

quit := make(chan os.Signal, 1)
signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
<-quit

ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
if err := srv.Shutdown(ctx); err != nil {
    log.Fatal("Server Shutdown error:", err)
}
```

---

## File Uploads

### Set `MaxMultipartMemory` for Upload Routes

The default multipart memory limit is 32 MiB. For routes that do not accept file uploads, this is generous. For upload-heavy APIs, tune it to match expected payload sizes:

```go
router := gin.New()
router.MaxMultipartMemory = 8 << 20  // 8 MiB — override default 32 MiB
router.POST("/upload", h.Upload)
```

---

## Streaming Large Responses

Stream large list results or file downloads instead of buffering the full payload in memory:

```go
// Stream a JSON array without buffering all records
c.Stream(func(w io.Writer) bool {
    encoder := json.NewEncoder(w)
    for _, item := range items {
        if err := encoder.Encode(item); err != nil {
            return false
        }
    }
    return false
})

// Stream a file to the client
c.File("/var/data/report.csv")                    // inline
c.FileAttachment("/var/data/report.csv", "report.csv") // forces download
```

---

## Pagination

Always paginate list endpoints. Never return unbounded result sets:

```go
type PaginationQuery struct {
    Limit  int `form:"limit,default=50"  binding:"min=1,max=200"`
    Offset int `form:"offset,default=0"  binding:"min=0"`
}

func (h *Handler) List(c *gin.Context) {
    var q PaginationQuery
    if err := c.ShouldBindQuery(&q); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    items, total, err := h.useCase.List(c.Request.Context(), q.Limit, q.Offset)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
        return
    }
    c.JSON(http.StatusOK, ListResponse[Item]{Data: items, Total: total})
}
```

---

## Profiling in Production

Register pprof on an **internal-only** loopback listener — never on the public Gin router:

```go
// Good — internal debug server; not reachable from the public network
import _ "net/http/pprof"

go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()

// Bad — pprof exposed on the public Gin router
router.GET("/debug/pprof/*action", gin.WrapH(http.DefaultServeMux))
```

---

## Resources

- [Gin Framework Documentation](https://gin-gonic.com/docs/)
- [Gin GitHub](https://github.com/gin-gonic/gin)
- [net/http Server](https://pkg.go.dev/net/http#Server)
- [Go Performance Guide](https://github.com/dgryski/go-perfbook)
