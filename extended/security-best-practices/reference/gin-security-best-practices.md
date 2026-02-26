# Go Gin Security Spec

Supplements `golang-general-backend-security.md` for projects using the Gin HTTP framework.
Load both files together when working on a Gin-based service.

---

## 0) Scope

This document covers Gin-specific security patterns that are not captured in the general Go
backend spec. All rules in the general spec (`golang-general-backend-security.md`) still apply.

---

## 1) Gin-Specific Rules

### GIN-SEC-001: Never use `gin.Default()` in production without reviewing its built-in middleware

Severity: Medium

`gin.Default()` registers `Logger` and `Recovery` middleware. `Recovery` logs the full stack trace
to stdout, which may leak internal paths and types.

Required:

- SHOULD use `gin.New()` and register only the middleware you have reviewed and configured.
- If `Recovery` is used, replace with `gin.CustomRecovery` to control the error response and log
  format (avoid leaking stack traces in structured logs shipped to external services).

Insecure patterns:

- `gin.Default()` without reviewing what `Recovery` logs.
- `gin.CustomRecovery` that logs `c.Request` (includes headers, which may carry auth tokens).

Detection hints:

- Search for `gin.Default()`.
- Inspect the `Recovery` middleware configuration.

Fix:

```go
// Bad — default recovery may log sensitive data
router := gin.Default()

// Good — custom recovery with controlled output
router := gin.New()
router.Use(gin.Logger())
router.Use(gin.CustomRecovery(func(c *gin.Context, recovered any) {
    log.Error("panic recovered", "error", recovered)
    c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
}))
```

---

### GIN-SEC-002: `c.Abort()` MUST be called after writing an error response in middleware

Severity: High

If middleware writes an error response without calling `c.Abort()`, subsequent middleware and the
handler still execute. This can bypass auth checks.

Required:

- MUST call `c.Abort()` or `c.AbortWithStatus()` / `c.AbortWithStatusJSON()` immediately after
  writing any error response in middleware.

Insecure patterns:

```go
// Bad — handler runs even though auth failed
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        if !tokenValid(c) {
            c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
            // Missing c.Abort() — c.Next() still runs
        }
        c.Next()
    }
}
```

Detection hints:

- Search for `c.JSON(`, `c.String(`, `c.Data(` inside middleware functions that are not followed
  by `c.Abort()` or `return`.

Fix:

```go
// Good
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

---

### GIN-SEC-003: Avoid `c.MustGet` in production handlers

Severity: Medium

`c.MustGet` panics if the key is absent. If middleware that sets the key fails silently or is not
applied to a route, `MustGet` causes a 500 panic rather than a controlled 401/403.

Required:

- MUST use `c.Get` + existence check in handler code.
- Reserve `c.MustGet` for test helpers only.

Insecure patterns:

```go
// Bad — panics if "user_id" is not set (e.g. route missing auth middleware)
userID := c.MustGet("user_id").(string)
```

Detection hints:

- Search for `c.MustGet(` in non-test files.

Fix:

```go
// Good
raw, exists := c.Get("user_id")
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

---

### GIN-SEC-004: CORS MUST be configured with an explicit origin allowlist

Severity: High (Critical when paired with cookie auth)

Required:

- MUST NOT use `AllowAllOrigins: true` on any API that uses cookie-based auth.
- MUST configure an explicit `AllowOrigins` list.
- MUST NOT combine `AllowCredentials: true` with wildcard origins.

Insecure patterns:

```go
// Bad — allows any origin with credentials (CORS bypass + CSRF risk)
router.Use(cors.New(cors.Config{
    AllowAllOrigins:  true,
    AllowCredentials: true,
}))
```

Detection hints:

- Search for `AllowAllOrigins`, `AllowOrigins: []string{"*"}`.
- Cross-reference with `AllowCredentials: true`.

Fix:

```go
// Good
router.Use(cors.New(cors.Config{
    AllowOrigins:     []string{"https://app.example.com"},
    AllowMethods:     []string{"GET", "POST", "PUT", "DELETE"},
    AllowHeaders:     []string{"Authorization", "Content-Type"},
    AllowCredentials: true,
    MaxAge:           12 * time.Hour,
}))
```

---

### GIN-SEC-005: Request body size MUST be capped before binding

Severity: Medium (High for upload-heavy APIs)

`c.ShouldBindJSON` reads `c.Request.Body` without a size limit by default. An attacker can send
an arbitrarily large body to exhaust memory.

Required:

- MUST wrap `c.Request.Body` with `http.MaxBytesReader` before calling any `Bind*` or `ShouldBind*`.
- SHOULD apply this globally as middleware rather than per-handler.

Insecure patterns:

```go
// Bad — no body size limit
var req CreateItemRequest
if err := c.ShouldBindJSON(&req); err != nil {
    // ...
}
```

Detection hints:

- Search for `ShouldBindJSON`, `BindJSON`, `ShouldBind` without a preceding `MaxBytesReader` call.

Fix:

```go
// Good — global middleware
func BodyLimitMiddleware(limit int64) gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, limit)
        c.Next()
    }
}
```

---

### GIN-SEC-006: Use `gin.SetMode(gin.ReleaseMode)` in production

Severity: Low (Information Disclosure)

In debug mode, Gin logs every registered route and prints detailed error information that may
expose internal route structure.

Required:

- MUST call `gin.SetMode(gin.ReleaseMode)` before creating the router in production.
- MUST call `gin.SetMode(gin.TestMode)` in tests.

Insecure patterns:

- `gin.SetMode(gin.DebugMode)` in production config.
- No call to `gin.SetMode` (defaults to debug).

Detection hints:

- Search for `gin.SetMode`; if absent or set to `DebugMode`, flag for production environments.

---

### GIN-SEC-007: `*gin.Context` MUST NOT be stored or passed to goroutines

Severity: High

`*gin.Context` is reused by Gin's pool after the handler returns. Holding a reference to it in a
goroutine results in a data race and may expose another request's data.

Required:

- MUST NOT store `c` in a goroutine or any long-lived struct.
- MUST copy all needed values out of the context before launching a goroutine.

Insecure patterns:

```go
// Bad — c is reused after handler returns; race condition
go func() {
    process(c.Param("id"), c.GetString("user_id"))
}()
```

Detection hints:

- Search for goroutine literals (`go func()`) inside handler functions that capture `c`.

Fix:

```go
// Good — copy values before spawning
id := c.Param("id")
userID := c.GetString("user_id")
go func() {
    process(id, userID)
}()
```

---

## 2) Scanning Heuristics for Gin

High-signal patterns when auditing a Gin service:

- `gin.Default()` — review Recovery middleware log output
- `c.MustGet(` — panic risk if middleware is missing
- `AllowAllOrigins: true` + `AllowCredentials: true` — CORS/CSRF critical
- `c.JSON(` / `c.String(` inside middleware without adjacent `c.Abort()` or `return`
- `go func()` inside handlers capturing `c *gin.Context`
- `c.ShouldBindJSON` / `c.BindJSON` without prior `http.MaxBytesReader`
- `gin.SetMode` absent or set to `DebugMode` in production entrypoint

---

## 3) Resources

- [Gin Framework Documentation](https://gin-gonic.com/docs/)
- [Gin Security Notes (GitHub)](https://github.com/gin-gonic/gin#dont-trust-all-proxies)
- [golang-general-backend-security.md](../../../skills/security-best-practices/references/golang-general-backend-security.md) — base Go security spec
- [OWASP CORS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/CORS_Cheat_Sheet.html)
