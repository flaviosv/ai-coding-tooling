# Gin Performance Best Practices

Applies to: Go projects using the Gin HTTP framework.
Load in addition to `golang-performance-review.md`.

---

## Router & Middleware

### Avoid Per-Route Middleware Repetition

```go
// Bad — middleware applied redundantly on every route
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

Each middleware runs on every request in its group. Avoid:
- Allocating new objects on every call — use `sync.Pool` for reusable buffers
- Synchronous calls to external services (DB lookups, HTTP calls) in middleware unless unavoidable
- Logging full request/response bodies in production — log metadata only

---

## Request Binding

### Prefer `ShouldBind*` over Manual JSON Decode

Gin's `c.ShouldBindJSON` reuses an internal decoder pool under the hood. Avoid creating a new `json.NewDecoder` per request:

```go
// Bad — allocates a new decoder per request
var req CreateItemRequest
if err := json.NewDecoder(c.Request.Body).Decode(&req); err != nil {
    c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
    return
}

// Good — Gin manages the decoder
var req CreateItemRequest
if err := c.ShouldBindJSON(&req); err != nil {
    c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
    return
}
```

### Limit Request Body Size Early

Unbounded body reads can exhaust memory under load. Apply the limit before binding:

```go
// Good — cap body before ShouldBindJSON
c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 1<<20) // 1 MB
var req CreateItemRequest
if err := c.ShouldBindJSON(&req); err != nil {
    c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
    return
}
```

Apply globally via middleware for consistency:

```go
func BodyLimitMiddleware(limit int64) gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, limit)
        c.Next()
    }
}
```

---

## Response Rendering

### Use Typed Structs, Not `gin.H` for Repeated Shapes

`gin.H` is `map[string]any` — marshalling a map is slower than marshalling a concrete struct because reflection must traverse map keys at runtime.

```go
// Bad — map marshalling; slower for recurring response shapes
c.JSON(http.StatusOK, gin.H{"data": items, "total": count})

// Good — struct marshalling; faster and type-safe
type ListResponse[T any] struct {
    Data  []T   `json:"data"`
    Total int64 `json:"total"`
}
c.JSON(http.StatusOK, ListResponse[Item]{Data: items, Total: count})
```

Use `gin.H` only for one-off or error responses where a struct would be disproportionate.

---

## Context Propagation

### Always Pass `c.Request.Context()` Downstream

```go
// Bad — ignores request cancellation; DB call may outlive the client
items, err := h.useCase.List(context.Background())

// Good — cancels downstream work when client disconnects
items, err := h.useCase.List(c.Request.Context())
```

Set timeouts at the use-case or repository layer, not in the handler, so timeout policy is consistent across transports.

---

## Connection and Server Tuning

### Configure Server Timeouts

Gin uses `net/http` under the hood. Always wrap it with an explicit `http.Server`:

```go
// Bad — zero timeouts; vulnerable to slow-client DoS
router.Run(":8080")

// Good — explicit timeouts
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

---

## Streaming and Large Responses

### Stream Large Payloads Instead of Buffering

For large list results or file downloads, stream directly to the response writer:

```go
// Good — streams JSON array without buffering the full payload
c.Stream(func(w io.Writer) bool {
    encoder := json.NewEncoder(w)
    for _, item := range items {
        if err := encoder.Encode(item); err != nil {
            return false
        }
    }
    return false
})

// For file downloads — stream the file
c.File("/path/to/file")           // small, known files
c.FileAttachment(path, filename)  // forces Content-Disposition: attachment
```

---

## Pagination

Always paginate list endpoints. Never return unbounded result sets:

```go
// Good — extract and validate pagination params, pass to use case
type PaginationQuery struct {
    Limit  int `form:"limit,default=50" binding:"min=1,max=200"`
    Offset int `form:"offset,default=0" binding:"min=0"`
}

func (h *Handler) List(c *gin.Context) {
    var q PaginationQuery
    if err := c.ShouldBindQuery(&q); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    items, total, err := h.useCase.List(c.Request.Context(), q.Limit, q.Offset)
    // ...
}
```

---

## Profiling in Production

Register pprof on an **internal-only** listener, never on the public Gin router:

```go
// Good — internal debug server on loopback only
go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil)) // pprof auto-registered via blank import
}()

// Bad — pprof on public Gin router
import _ "net/http/pprof"
router.GET("/debug/pprof/*action", gin.WrapH(http.DefaultServeMux))
```

---

## Resources

- [Gin Framework Documentation](https://gin-gonic.com/docs/)
- [Gin GitHub](https://github.com/gin-gonic/gin)
- [net/http Server Timeouts](https://pkg.go.dev/net/http#Server)
- [Go Performance Guide](https://github.com/dgryski/go-perfbook)
