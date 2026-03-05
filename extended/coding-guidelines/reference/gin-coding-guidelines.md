# Go + Gin Coding Style Guide

> Load this file together with `go-coding-guidelines.md`. Rules here are additive and Gin-specific.

## Project Layout

- Place handler structs under a `handler/` or `api/` package — one file per resource (e.g. `item_handler.go`, `user_handler.go`)
- Register routes in a dedicated `RegisterRoutes` function — not in `main.go`
- Keep `main.go` thin: build the dependency graph, wire the router, start the server
- Group business logic in a `usecase/` or `service/` package — handlers must not contain business rules
- Repository interfaces live in the domain layer; GORM or `database/sql` implementations live in an `infra/` or `repository/` package
- Keep middleware in a `middleware/` package — cross-cutting concerns do not belong inside `handler/`

## Handler Structure

- Use constructor injection — pass dependencies to handlers at startup; never access them as package-level global variables

```go
// Good
type ItemHandler struct {
    useCase usecase.ItemUseCase
}

func NewItemHandler(uc usecase.ItemUseCase) *ItemHandler {
    return &ItemHandler{useCase: uc}
}

func (h *ItemHandler) List(c *gin.Context) {
    items, total, err := h.useCase.List(c.Request.Context())
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
        return
    }
    c.JSON(http.StatusOK, ListResponse[Item]{Data: items, Total: total})
}
```

- Handler methods follow the signature `func (h *Handler) ActionName(c *gin.Context)` — no extra parameters beyond `*gin.Context`
- Handlers are thin: parse input → validate → call use case → write response. No business logic inside handlers

## Router Initialization

- Use `gin.New()` in production — not `gin.Default()`. Register only the middleware you have reviewed and configured:

```go
// Good — explicit, reviewed middleware stack
router := gin.New()
router.Use(gin.Logger())
router.Use(gin.CustomRecovery(func(c *gin.Context, recovered any) {
    log.Error("panic recovered", "error", recovered)
    c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
}))
```

- Set `gin.SetMode(gin.ReleaseMode)` before creating the router in production; `gin.TestMode` in tests

## Route Registration

- Group routes by version and resource using `router.Group()`
- Apply shared middleware at the group level — not per-route

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

- Register middleware before routes — `router.Use()` after route registration has no effect on routes registered before it
- Use `http.Status*` constants for all status codes — not raw integers

## Request Binding

- Use `c.ShouldBindJSON` for request bodies and `c.ShouldBindQuery` for query params — never `c.BindJSON` or `c.Bind` (these call `c.AbortWithStatus(400)` automatically, bypassing custom error handling)
- Validate binding errors and return a consistent `400` response immediately

```go
var req CreateItemRequest
if err := c.ShouldBindJSON(&req); err != nil {
    c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
    return
}
```

- Define explicit request structs with `binding:` validation tags (from `go-playground/validator/v10`) rather than reading and validating params manually

```go
type CreateItemRequest struct {
    Name       string `json:"name"        binding:"required,min=1,max=255"`
    CategoryID string `json:"category_id" binding:"required,uuid"`
}
```

- Register custom validators via `binding.Validator.Engine().(*validator.Validate).RegisterValidation(...)` — do not re-implement validation logic inside handler bodies

## Context Values

- Store middleware-set values under typed package-level constants — not bare string literals

```go
type contextKey string

const contextKeyUserID = contextKey("user_id")

// In middleware — set value
c.Set(string(contextKeyUserID), userID)

// In handler — retrieve safely
raw, exists := c.Get(string(contextKeyUserID))
if !exists {
    c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
    return
}
userID, ok := raw.(string)
if !ok {
    c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "invalid context"})
    return
}
```

- Never use `c.MustGet` in production handlers — it panics if the key is absent (e.g. if the route is missing the auth middleware)
- Always check both `exists` and the type assertion result

## Middleware

- Middleware function names end with `Middleware` (e.g. `AuthMiddleware`, `RateLimitMiddleware`, `BodyLimitMiddleware`)
- Every middleware that writes an error response MUST call `c.Abort()` or `c.AbortWithStatusJSON()` to stop the handler chain

```go
// Good — chain stops after error response
func RequireAdmin() gin.HandlerFunc {
    return func(c *gin.Context) {
        if !isAdmin(c) {
            c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "forbidden"})
            return
        }
        c.Next()
    }
}
```

- Middleware must not contain business logic — only cross-cutting concerns (auth, logging, rate limiting, request ID, tracing)
- Never store `*gin.Context` in a goroutine or long-lived struct — copy needed values before spawning

```go
// Bad — data race; c is reused by Gin's pool after the handler returns
go func() {
    process(c.Param("id"), c.GetString("user_id"))
}()

// Good — copy out before spawning
id := c.Param("id")
userID := c.GetString("user_id")
go func() {
    process(id, userID)
}()
```

## Response Conventions

- Consistent JSON envelope across all list endpoints:
  ```json
  { "data": [...], "total": 123 }
  ```
- Consistent error response shape:
  ```json
  { "error": "human-readable message" }
  ```
- Use `gin.H` only for one-off error responses — recurring response shapes use typed structs (struct marshalling is faster than map marshalling)

## Server Initialization

- Never call `router.Run()` directly in production — wrap with `http.Server` to configure timeouts:

```go
srv := &http.Server{
    Addr:              ":" + cfg.Port,
    Handler:           router,
    ReadHeaderTimeout: 5 * time.Second,
    ReadTimeout:       10 * time.Second,
    WriteTimeout:      30 * time.Second,
    IdleTimeout:       120 * time.Second,
    MaxHeaderBytes:    1 << 20,
}
```

- Use `http.Server.Shutdown()` with a context timeout for graceful shutdown on SIGTERM/SIGINT
- Configure `router.SetTrustedProxies()` explicitly when running behind a load balancer or reverse proxy

## Anti-Patterns to Avoid

- Do not access `c.Request.Body` after `ShouldBindJSON` — the body stream is consumed on first read
- Do not store `*gin.Context` in goroutines — copy needed values out before spawning
- Do not call `c.Next()` inside a handler function — `c.Next()` is for middleware only
- Do not use `router.Use()` after routes are already registered — middleware must be registered before routes
- Do not use `gin.Default()` without reviewing its built-in `Recovery` middleware — it may log sensitive stack trace data
- Do not use `c.BindJSON` or `c.Bind` in new code — they call `c.AbortWithStatus(400)` automatically, suppressing custom error handling
