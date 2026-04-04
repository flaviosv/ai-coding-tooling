# Go Gin Code Review Checklist

Supplements `review-checklist.md` and `golang-code-review.md` for Go projects using the Gin HTTP framework (v1.x).

---

## Security

- [ ] No secrets or credentials hardcoded in handler, middleware, or config initialization
- [ ] All path and query parameters validated before use — never passed raw to DB queries or OS calls
- [ ] Request body size capped with `http.MaxBytesReader` before any `ShouldBind*` call — applied globally as middleware, not per-handler
- [ ] CORS configured with an explicit `AllowOrigins` list — never `AllowAllOrigins: true` on authenticated APIs; `AllowAllOrigins: true` combined with `AllowCredentials: true` is a critical CORS/CSRF vulnerability
- [ ] `gin.SetMode(gin.ReleaseMode)` set before creating the router in production — not `DebugMode` (debug mode logs every registered route, leaking internal structure)
- [ ] `gin.Default()` not used in production without reviewing its built-in `Recovery` middleware — `Recovery` logs the full stack trace and may expose internal paths; use `gin.CustomRecovery` to control output
- [ ] pprof routes not registered on the public router — expose only on a loopback-only internal listener
- [ ] Auth middleware applied to all protected route groups — no unguarded sensitive routes
- [ ] `router.SetTrustedProxies()` explicitly configured — do not rely on default proxy trust (`nil` disables; provide explicit CIDR list when behind a load balancer)
- [ ] `*gin.Context` not stored in goroutines or long-lived structs — it is pooled and reused by Gin after the handler returns

## Error Handling

- [ ] `c.ShouldBindJSON` / `c.ShouldBind` / `c.ShouldBindQuery` used over `c.BindJSON` / `c.Bind` — the `Bind*` variants call `c.AbortWithStatus(400)` automatically and may suppress custom error handling logic
- [ ] Errors returned from use cases wrapped with context before mapping to HTTP status codes
- [ ] Custom error handling centralized — via `c.Error()` + a post-request error-handling middleware, or a shared error-mapping helper — not duplicated across handlers
- [ ] `c.Abort()` or `c.AbortWithStatusJSON()` called after writing any error response in middleware — handler chain must not continue after a rejection

```go
// Bad — handler continues after error response; auth bypass possible
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        if !tokenValid(c) {
            c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
            // Missing c.Abort() — c.Next() still runs downstream handlers
        }
        // ...
    }
}

// Good — chain stops after rejection
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        if !tokenValid(c) {
            c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
            return
        }
        c.Next()
    }
}
```

- [ ] Centralized error middleware using `c.Error()` pattern preferred for complex APIs:

```go
// Handler adds error to context instead of responding directly
func (h *Handler) Create(c *gin.Context) {
    var req CreateItemRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.Error(err)
        return
    }
    item, err := h.useCase.Create(c.Request.Context(), req)
    if err != nil {
        c.Error(err)
        return
    }
    c.JSON(http.StatusCreated, item)
}

// Error handler middleware runs after all handlers
func ErrorHandler() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Next()
        if len(c.Errors) > 0 {
            err := c.Errors.Last().Err
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        }
    }
}
```

## Performance

- [ ] Route groups used to share middleware — not applying the same middleware redundantly per-route
- [ ] `c.ShouldBindJSON` used over manual `json.NewDecoder(c.Request.Body).Decode(&req)` per request
- [ ] Blocking I/O (DB calls, outbound HTTP) never done without a context timeout derived from `c.Request.Context()`
- [ ] No unbounded list queries behind list endpoints — pagination enforced at the use case or repository layer
- [ ] `gin.H` (a `map[string]any`) used only for one-off or error responses — typed structs preferred for recurring response shapes (map marshalling is slower due to runtime reflection)
- [ ] `router.MaxMultipartMemory` configured explicitly for file-upload routes — not left at default 32 MiB

## Architecture & Design

- [ ] Handlers are thin: parse input → call use case / service → write response. No business logic in handlers
- [ ] Dependencies injected into handlers via constructor — not accessed as package-level global variables

```go
// Bad — global dependency
func ListItems(c *gin.Context) {
    items, err := globalDB.Find(&[]Item{})
    // ...
}

// Good — constructor injection
type Handler struct {
    useCase ItemUseCase
}

func NewHandler(uc ItemUseCase) *Handler {
    return &Handler{useCase: uc}
}

func (h *Handler) List(c *gin.Context) {
    items, err := h.useCase.List(c.Request.Context())
    // ...
}
```

- [ ] Route definitions separated from handler logic — a `RegisterRoutes` function (not `main.go`) wires routes and attaches middleware
- [ ] Middleware responsibility is narrow — auth middleware does not parse request bodies; validation middleware does not handle auth; logging middleware does not perform auth checks
- [ ] `gin.New()` used in production (not `gin.Default()`) with explicitly chosen middleware registered via `router.Use()`
- [ ] `http.Server` used to wrap the Gin router — `router.Run()` not called directly in production (no timeout configuration possible via `Run`)

## Code Quality

- [ ] Request structs use `binding:` validation tags from `go-playground/validator/v10` — not manual field-by-field checks in handler bodies

```go
type CreateItemRequest struct {
    Name       string `json:"name"        binding:"required,min=1,max=255"`
    CategoryID string `json:"category_id" binding:"required,uuid"`
}
```

- [ ] `c.Param("id")` and `c.Query("key")` results validated for expected format before use
- [ ] Context values set with `c.Set` use package-level typed constants as keys — not bare string literals
- [ ] HTTP status codes use `http.Status*` constants — not raw integer literals
- [ ] Response shapes consistent across endpoints — similar resources use the same envelope structure

```go
// Bad — inconsistent response shapes
c.JSON(200, items)
c.JSON(200, gin.H{"data": items, "total": count})

// Good — consistent typed envelope
type ListResponse[T any] struct {
    Data  []T   `json:"data"`
    Total int64 `json:"total"`
}
c.JSON(http.StatusOK, ListResponse[Item]{Data: items, Total: total})
```

- [ ] `c.Request.Body` not read again after `ShouldBindJSON` — the body stream is consumed on first read

## Gin Idioms

- [ ] `gin.RouterGroup` used for versioned and grouped routes (e.g. `/v1/items`, `/v2/users`)
- [ ] Middleware applied at the group level — not repeated on every route within a group

```go
func RegisterRoutes(r *gin.Engine, h *ItemHandler, auth gin.HandlerFunc) {
    v1 := r.Group("/v1")
    {
        items := v1.Group("/items", auth)
        items.GET("", h.List)
        items.POST("", h.Create)
        items.GET("/:id", h.Get)
        items.PUT("/:id", h.Update)
        items.DELETE("/:id", h.Delete)
    }
}
```

- [ ] `c.Request.Context()` propagated to all downstream calls (DB, external HTTP, cache)
- [ ] `c.Get("key")` return value type-asserted safely — existence bool always checked before using the value; `c.MustGet` not used in production handlers (panics if key is absent)

```go
// Bad — panics if "user_id" key is absent (e.g. route missing auth middleware)
userID := c.MustGet("user_id").(string)

// Good — safe retrieval
raw, exists := c.Get("user_id")
if !exists {
    c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "missing user context"})
    return
}
userID, ok := raw.(string)
if !ok {
    c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "invalid user context"})
    return
}
```

- [ ] Goroutines launched from handlers copy needed values out of `*gin.Context` before spawning — never capture `c` directly in a goroutine closure

```go
// Bad — c is reused after handler returns; data race
go func() {
    process(c.Param("id"), c.GetString("user_id"))
}()

// Good — copy values before spawning
id := c.Param("id")
userID := c.GetString("user_id")
go func() {
    process(id, userID)
}()
```

- [ ] Custom validators registered via `binding.Validator.Engine().(*validator.Validate).RegisterValidation(...)` — not reimplemented manually in handler bodies

## Testing

- [ ] Handler tests use `gin.SetMode(gin.TestMode)` at the start of every test function
- [ ] `httptest.NewRecorder()` and `router.ServeHTTP(w, req)` pattern used — not `gin.CreateTestContext` for full-stack integration tests
- [ ] Both success and error paths covered for every handler
- [ ] Response body structure asserted, not just the status code
- [ ] Middleware tested in isolation with a minimal router — not through full end-to-end integration tests
