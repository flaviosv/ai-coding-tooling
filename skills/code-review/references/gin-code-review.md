# Go Gin Code Review Checklist

Supplements `review-checklist.md` and `golang-code-review.md` for Go projects using the Gin HTTP framework.

---

## Security

- [ ] No secrets or credentials hardcoded in handler, middleware, or config initialization
- [ ] All path and query parameters validated before use — never passed raw to DB queries or OS calls
- [ ] Request body size limited with `c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, maxBytes)` before binding
- [ ] CORS configured with an explicit origin allowlist — never `AllowAllOrigins: true` on authenticated APIs
- [ ] `gin.SetMode(gin.ReleaseMode)` set in production — not `DebugMode`
- [ ] pprof routes not registered on the public router in production
- [ ] Auth middleware applied to all protected route groups — no unguarded sensitive routes

---

## Error Handling

- [ ] `c.ShouldBindJSON` / `c.ShouldBind` used over `c.BindJSON` / `c.Bind` — the `Bind*` variants call `c.AbortWithStatus(400)` automatically and may suppress handler logic
- [ ] Errors returned from use cases wrapped with context before being mapped to HTTP status codes
- [ ] Custom error handler centralized (e.g. via `gin.CustomRecovery` or a shared error-mapping helper) — not duplicated across handlers
- [ ] `c.Abort()` or `c.AbortWithStatus()` called after writing an error response in middleware — handler chain must not continue

```go
// Bad — handler continues after error response
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        if !isValid(c) {
            c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
            // Missing c.Abort() — next handler still runs
        }
        c.Next()
    }
}

// Good
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        if !isValid(c) {
            c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
            return
        }
        c.Next()
    }
}
```

---

## Performance

- [ ] Route groups used to share middleware — not applying the same middleware per-route
- [ ] `c.JSON` / `c.ShouldBindJSON` used over manual `json.Marshal` / `json.Unmarshal` in handlers
- [ ] Avoid blocking I/O (DB calls, HTTP calls) without a context timeout derived from `c.Request.Context()`
- [ ] No unbounded list queries behind list endpoints — pagination enforced at the use case or repository layer
- [ ] `gin.H` (a `map[string]any`) used only for small, one-off responses — typed structs preferred for recurring shapes

---

## Architecture & Design

- [ ] Handlers are thin: parse input → call use case / service → write response. No business logic in handlers
- [ ] Dependencies injected into handlers via constructor, not accessed as global variables

```go
// Bad — global dependency
func ListItems(c *gin.Context) {
    items, err := globalDB.Find(&[]Item{})
    // ...
}

// Good — injected use case
type Handler struct {
    useCase ItemUseCase
}

func (h *Handler) List(c *gin.Context) {
    items, err := h.useCase.List(c.Request.Context())
    // ...
}
```

- [ ] Route definitions separated from handler logic — a `RegisterRoutes` function (or equivalent) wires routes, not `main.go`
- [ ] Middleware responsibility is narrow — auth middleware does not parse request bodies; validation middleware does not handle auth

---

## Code Quality

- [ ] `c.Param("id")` and `c.Query("key")` results validated for expected format before use
- [ ] All context values set with `c.Set` use package-level typed constants as keys — not bare string literals
- [ ] HTTP status codes use `http.Status*` constants — not raw integer literals
- [ ] Response shapes consistent across endpoints — similar resources use the same envelope structure

```go
// Bad — inconsistent response shapes
c.JSON(200, items)                         // bare slice
c.JSON(200, gin.H{"data": items, "total": count}) // wrapped

// Good — consistent envelope
type ListResponse[T any] struct {
    Data  []T   `json:"data"`
    Total int64 `json:"total"`
}
c.JSON(http.StatusOK, ListResponse[Item]{Data: items, Total: total})
```

---

## Gin Idioms

- [ ] `gin.RouterGroup` used for versioned and grouped routes (`/v1/items`, `/v1/users`)
- [ ] Middleware applied at the correct group level — not repeated on every route within a group
- [ ] `c.Request.Context()` propagated to all downstream calls (DB, external HTTP, cache)
- [ ] `c.Get("key")` return value type-asserted safely — always check the `exists` bool before using the value

```go
// Bad — unchecked type assertion; panics if key is absent
userID := c.MustGet("user_id").(string)

// Good — safe retrieval
userID, exists := c.Get("user_id")
if !exists {
    c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "missing user context"})
    return
}
uid, ok := userID.(string)
if !ok {
    c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "invalid user context"})
    return
}
```

---

## Testing

- [ ] Handler tests use `gin.SetMode(gin.TestMode)` and `gin.CreateTestContext(httptest.NewRecorder())`
- [ ] Middleware tested in isolation with a minimal router — not through full integration tests
- [ ] Both success and error paths covered for every handler
- [ ] Response body structure asserted, not just the status code

---

## Resources

- [Gin Framework Documentation](https://gin-gonic.com/docs/)
- [Gin GitHub](https://github.com/gin-gonic/gin)
- [net/http/httptest](https://pkg.go.dev/net/http/httptest)
