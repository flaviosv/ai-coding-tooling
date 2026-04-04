# Gin Performance Best Practices

Applies to: Go projects using the Gin HTTP framework (v1.x).
Load in addition to `golang-performance-review.md`.

---

## Router & Middleware

### Avoid Per-Route Middleware Repetition

Repeating middleware per route multiplies call overhead and maintenance surface:

```go
// Bad
router.GET("/v1/items", AuthMiddleware(), ListItems)
router.POST("/v1/items", AuthMiddleware(), CreateItem)
router.GET("/v1/users", AuthMiddleware(), ListUsers)

// Good — apply once on the group
v1 := router.Group("/v1", AuthMiddleware())
v1.GET("/items", ListItems)
v1.POST("/items", CreateItem)
v1.GET("/users", ListUsers)
```

### Keep Middleware Lean

Every middleware runs on every matched request in its group. Avoid:

- Allocating new objects on each call — use `sync.Pool` for reusable buffers
- Synchronous calls to external services (DB, cache, outbound HTTP) unless unavoidable
- Logging full request/response bodies in production — log metadata only

## Request Binding

### Prefer `ShouldBind*` over Manual JSON Decode

Gin's `ShouldBindJSON` uses internal decoder pooling. `json.NewDecoder` allocates per request:

```go
// Bad
var req CreateItemRequest
json.NewDecoder(c.Request.Body).Decode(&req)

// Good — Gin manages the decoder pool
var req CreateItemRequest
if err := c.ShouldBindJSON(&req); err != nil {
    c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
    return
}
```

### Cap Request Body Size Early

Unbounded body reads can exhaust memory. Apply globally via middleware before route definitions:

```go
func BodyLimitMiddleware(limit int64) gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, limit)
        c.Next()
    }
}

router := gin.New()
router.Use(BodyLimitMiddleware(1 << 20)) // 1 MiB
```

## Response Rendering

### Use Typed Structs, Not `gin.H` for Repeated Response Shapes

`gin.H` is `map[string]any` — map marshalling requires runtime reflection over keys. Struct is faster and type-safe:

```go
// Bad
c.JSON(http.StatusOK, gin.H{"data": items, "total": count})

// Good — struct marshalling; faster and compiler-checked
type ListResponse[T any] struct {
    Data  []T   `json:"data"`
    Total int64 `json:"total"`
}
c.JSON(http.StatusOK, ListResponse[Item]{Data: items, Total: count})
```

Reserve `gin.H` for one-off or error responses where defining a struct would be disproportionate.

## Context Propagation

### Always Pass `c.Request.Context()` Downstream

`context.Background()` ignores client disconnects — downstream work outlives the client:

```go
// Bad
items, err := h.useCase.List(context.Background())

// Good — cancels downstream work when client disconnects
items, err := h.useCase.List(c.Request.Context())
```

Set timeouts at the use-case or repository layer — not in the handler — so timeout policy is consistent across all transports.

## Server Configuration

### Configure `http.Server` Timeouts Explicitly

`router.Run()` uses zero timeouts — vulnerable to slow-client and Slowloris DoS. Always wrap in `http.Server`:

```go
// Bad
router.Run(":8080")

// Good
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

Use `http.Server.Shutdown()` with a timeout to drain in-flight requests — avoids dropping active connections on SIGTERM:

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

## File Uploads

### Set `MaxMultipartMemory` for Upload Routes

Default multipart memory limit is 32 MiB. Tune to match expected payload sizes:

```go
router := gin.New()
router.MaxMultipartMemory = 8 << 20  // 8 MiB
router.POST("/upload", h.Upload)
```

## Streaming Large Responses

Stream large results or file downloads instead of buffering full payload in memory:

```go
// Stream JSON array without buffering all records
c.Stream(func(w io.Writer) bool {
    encoder := json.NewEncoder(w)
    for _, item := range items {
        if err := encoder.Encode(item); err != nil {
            return false
        }
    }
    return false
})

// Stream a file
c.File("/var/data/report.csv")
c.FileAttachment("/var/data/report.csv", "report.csv")
```

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

## Profiling in Production

Register pprof on an **internal-only** loopback listener — never on the public Gin router:

```go
// Good — internal debug server; not reachable from public network
import _ "net/http/pprof"
go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()

// Bad — pprof exposed on public Gin router
router.GET("/debug/pprof/*action", gin.WrapH(http.DefaultServeMux))
```
