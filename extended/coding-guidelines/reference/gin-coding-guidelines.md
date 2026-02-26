# Go + Gin Coding Style Guide

> Load this file together with `go-coding-guidelines.md`. Rules here are additive and Gin-specific.

## Project Layout

- Place handler structs under a `handler/` or `api/` package — one file per resource (e.g. `item_handler.go`, `user_handler.go`)
- Register routes in a dedicated `RegisterRoutes` function, not in `main.go`
- Keep `main.go` thin: build dependencies, wire the router, start the server
- Group business logic in a `usecase/` or `service/` package — handlers must not contain business rules
- Repository interfaces live in the domain layer; GORM or `database/sql` implementations live in an `infra/` or `repository/` package

## Handler Structure

- Use constructor injection — pass dependencies to handlers at startup, not accessed as globals

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

- Handler methods follow the signature `func (h *Handler) ActionName(c *gin.Context)` — no extra parameters

## Route Registration

- Group routes by version and resource using `router.Group()`
- Apply shared middleware at the group level, not per-route
- Use `http.Status*` constants for all status codes — not raw integers

```go
func RegisterRoutes(router *gin.Engine, h *ItemHandler, auth gin.HandlerFunc) {
    v1 := router.Group("/v1")
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

## Request Binding

- Use `c.ShouldBindJSON` for request bodies and `c.ShouldBindQuery` for query params — never `c.BindJSON` (calls `c.AbortWithStatus(400)` automatically, bypassing error handling)
- Validate binding errors and return a consistent `400` response immediately

```go
var req CreateItemRequest
if err := c.ShouldBindJSON(&req); err != nil {
    c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
    return
}
```

- Define explicit request structs with `binding:` validation tags rather than reading params manually

```go
type CreateItemRequest struct {
    Name       string `json:"name"       binding:"required,min=1,max=255"`
    CategoryID string `json:"category_id" binding:"required,uuid"`
}
```

## Context Values

- Store middleware-set values under typed package-level constants — not bare string literals

```go
// Good
const contextKeyUserID = contextKey("user_id")

type contextKey string

// In middleware
c.Set(string(contextKeyUserID), userID)

// In handler — retrieve safely
raw, exists := c.Get(string(contextKeyUserID))
if !exists { ... }
userID, ok := raw.(string)
```

- Always check both `exists` and the type assertion — never use `c.MustGet` in production handlers

## Middleware

- Middleware function names end with `Middleware` (e.g. `AuthMiddleware`, `RateLimitMiddleware`)
- Every middleware that writes a response MUST call `c.Abort()` or `c.AbortWithStatus()` to stop the handler chain

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

- Middleware must not contain business logic — only cross-cutting concerns (auth, logging, rate limiting, tracing)

## Response Conventions

- Consistent JSON envelope across all list endpoints:
  ```json
  { "data": [...], "total": 123 }
  ```
- Consistent error response shape:
  ```json
  { "error": "human-readable message" }
  ```
- Use `gin.H` only for one-off error responses — recurring response shapes use typed structs

## Server Initialization

- Never call `router.Run()` directly in production — wrap with `http.Server` to set timeouts

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

- Set `gin.SetMode(gin.ReleaseMode)` before creating the router in production; `gin.TestMode` in tests

## Anti-Patterns to Avoid

- Do not access `c.Request.Body` after `ShouldBindJSON` — the body is consumed
- Do not store `*gin.Context` in goroutines — copy needed values out before spawning
- Do not call `c.Next()` inside a handler (only middleware calls it)
- Do not use `router.Use()` after routes are registered — middleware must be registered before routes
