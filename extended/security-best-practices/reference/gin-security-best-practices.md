# Go Gin Security Spec

Supplements `golang-general-backend-security.md` for projects using the Gin HTTP framework (v1.x).
Load both files together when working on a Gin-based service.

---

## 0) Scope

This document covers Gin-specific security patterns not captured in the general Go backend spec.
All rules in the general spec (`golang-general-backend-security.md`) still apply.

---

## 1) Gin-Specific Rules

### GIN-SEC-001: Never use `gin.Default()` in production without auditing its built-in middleware

Severity: Medium

`gin.Default()` registers `Logger` and `Recovery` middleware. `Recovery` catches panics and logs the
full stack trace to stdout, which may expose internal file paths, type names, and request data.

Required:

- SHOULD use `gin.New()` and register only middleware you have reviewed and configured.
- If `Recovery` is needed, use `gin.CustomRecovery` to control the error response and log output.
- Never log `c.Request` in a recovery handler — request headers may carry authentication tokens.

Insecure patterns:

```go
// Bad — default recovery logs full stack trace; may expose internals
router := gin.Default()

// Also bad — CustomRecovery that logs the full request object (includes auth headers)
router.Use(gin.CustomRecovery(func(c *gin.Context, recovered any) {
    log.Error("panic", "request", c.Request, "error", recovered) // leaks headers
    c.AbortWithStatus(http.StatusInternalServerError)
}))
```

Fix:

```go
// Good — controlled recovery output with no header leakage
router := gin.New()
router.Use(gin.Logger())
router.Use(gin.CustomRecovery(func(c *gin.Context, recovered any) {
    log.Error("panic recovered",
        "method", c.Request.Method,
        "path", c.Request.URL.Path,
        "error", recovered,
    )
    c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
}))
```

Detection hints:

- Search for `gin.Default()` in production entrypoints.
- Search for `c.Request` inside recovery handler closures.

---

### GIN-SEC-002: `c.Abort()` MUST be called after writing an error response in middleware

Severity: High

If middleware writes an error response without calling `c.Abort()`, subsequent middleware and the
handler still execute. This can allow requests to bypass authentication or authorization checks.

Required:

- MUST call `c.Abort()` or `c.AbortWithStatusJSON()` immediately after writing any error response in middleware.

Insecure patterns:

```go
// Bad — downstream handlers still run after auth failure; auth bypass possible
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        if !tokenValid(c) {
            c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
            // Missing c.Abort() — c.Next() still runs all downstream handlers
        }
        c.Next()
    }
}
```

Fix:

```go
// Good — chain stops immediately after rejection
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

Detection hints:

- Search for `c.JSON(`, `c.String(`, `c.Data(` inside middleware functions not followed by `c.Abort()` or `return`.

---

### GIN-SEC-003: Avoid `c.MustGet` in production handlers

Severity: Medium

`c.MustGet` panics if the key is absent. If the route is missing the middleware that sets the key
(e.g. `AuthMiddleware`), `MustGet` causes an uncontrolled 500 panic instead of a controlled 401/403.

Required:

- MUST use `c.Get` with an existence check in all production handler code.
- Reserve `c.MustGet` for test helpers only, where panics are acceptable.

Insecure patterns:

```go
// Bad — panics if "user_id" is not set (e.g. route accidentally added without auth middleware)
userID := c.MustGet("user_id").(string)
```

Fix:

```go
// Good — controlled failure if key is absent
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

Detection hints:

- Search for `c.MustGet(` in non-test files.

---

### GIN-SEC-004: CORS MUST be configured with an explicit origin allowlist

Severity: High (Critical when combined with cookie-based authentication)

Required:

- MUST NOT use `AllowAllOrigins: true` on any API that uses cookie-based or session-based auth.
- MUST configure an explicit `AllowOrigins` list.
- MUST NOT combine `AllowCredentials: true` with wildcard or `AllowAllOrigins: true` — this is a CORS misconfiguration that enables cross-site request forgery.

Insecure patterns:

```go
// Bad — wildcard origins with credentials; CORS bypass + CSRF risk
router.Use(cors.New(cors.Config{
    AllowAllOrigins:  true,
    AllowCredentials: true,
}))
```

Fix:

```go
// Good — explicit allowlist with credentials
router.Use(cors.New(cors.Config{
    AllowOrigins:     []string{"https://app.example.com"},
    AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
    AllowHeaders:     []string{"Authorization", "Content-Type"},
    AllowCredentials: true,
    MaxAge:           12 * time.Hour,
}))
```

Detection hints:

- Search for `AllowAllOrigins: true` and `AllowOrigins: []string{"*"}`.
- Cross-reference with `AllowCredentials: true`.

---

### GIN-SEC-005: Request body size MUST be capped before binding

Severity: Medium (High for upload-heavy APIs)

`c.ShouldBindJSON` reads `c.Request.Body` without a size limit by default. An attacker can send an
arbitrarily large body to exhaust server memory.

Required:

- MUST wrap `c.Request.Body` with `http.MaxBytesReader` before any `Bind*` or `ShouldBind*` call.
- SHOULD apply this globally as middleware — not per-handler — to avoid missing it on new routes.

Insecure patterns:

```go
// Bad — unbounded read; memory exhaustion possible under adversarial input
var req CreateItemRequest
if err := c.ShouldBindJSON(&req); err != nil {
    c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
    return
}
```

Fix:

```go
// Good — global middleware applied before route definitions
func BodyLimitMiddleware(limit int64) gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, limit)
        c.Next()
    }
}

// Wire it early
router := gin.New()
router.Use(BodyLimitMiddleware(1 << 20)) // 1 MiB
```

Detection hints:

- Search for `ShouldBindJSON`, `BindJSON`, `ShouldBind` without a preceding `MaxBytesReader` assignment on `c.Request.Body`.

---

### GIN-SEC-006: Use `gin.SetMode(gin.ReleaseMode)` in production

Severity: Low (Information Disclosure)

In debug mode, Gin logs every registered route on startup and prints detailed error output that may
expose internal route structure and handler names to anyone with log access.

Required:

- MUST call `gin.SetMode(gin.ReleaseMode)` before creating the router in production.
- MUST call `gin.SetMode(gin.TestMode)` in test code.

Insecure patterns:

- `gin.SetMode(gin.DebugMode)` explicitly set in production configuration.
- No call to `gin.SetMode` at all (defaults to debug).

Fix:

```go
// In production entrypoint — before gin.New() or gin.Default()
gin.SetMode(gin.ReleaseMode)
router := gin.New()
```

Detection hints:

- Search for `gin.SetMode` in entrypoint files; if absent, or set to `DebugMode` in production config, flag it.

---

### GIN-SEC-007: `*gin.Context` MUST NOT be stored in goroutines or long-lived structs

Severity: High

`*gin.Context` is pooled and reused by Gin after the handler returns. Holding a reference to `c`
in a goroutine or struct after the handler exits results in a data race and may expose another
request's data to your goroutine.

Required:

- MUST NOT pass `c` to a goroutine or store it in any struct that outlives the handler call.
- MUST copy all needed values out of `c` before launching a goroutine.

Insecure patterns:

```go
// Bad — c is reused after handler returns; race condition and data leakage risk
go func() {
    process(c.Param("id"), c.GetString("user_id"))
}()

// Also bad — storing c in a struct field
type Worker struct {
    ctx *gin.Context // dangerous
}
```

Fix:

```go
// Good — extract values before spawning
id := c.Param("id")
userID := c.GetString("user_id")
go func() {
    process(id, userID)
}()
```

Detection hints:

- Search for goroutine literals (`go func()`) inside handler functions that capture `c` in the closure.
- Search for struct fields of type `*gin.Context`.

---

### GIN-SEC-008: Trusted proxies MUST be explicitly configured

Severity: Medium

By default (Gin v1.7.1+), Gin trusts no proxies. However, when running behind a load balancer or
reverse proxy, `c.ClientIP()` depends on `X-Forwarded-For` headers. If trusted proxies are not
configured, `ClientIP()` may return the wrong IP, breaking IP-based rate limiting and audit logging.
If configured too broadly (trusting all IPs), it allows IP spoofing via crafted headers.

Required:

- MUST call `router.SetTrustedProxies()` with the specific IP addresses or CIDR ranges of your load balancers.
- MUST NOT pass `nil` (disables proxy trust entirely) when behind a load balancer — `ClientIP()` will not reflect the real client IP.
- MUST NOT trust `0.0.0.0/0` — this allows any client to spoof their IP via `X-Forwarded-For`.

Fix:

```go
// Good — trust only the known load balancer IPs
router.SetTrustedProxies([]string{"10.0.0.0/8", "172.16.0.0/12"})
```

Detection hints:

- Search for `SetTrustedProxies`; if absent, verify whether the service runs behind a proxy.
- Flag `SetTrustedProxies(nil)` when the service is behind a load balancer.
- Flag `SetTrustedProxies([]string{"0.0.0.0/0"})` — equivalent to trusting all IPs.

---

### GIN-SEC-009: File upload paths MUST be sanitized before use

Severity: High (Path Traversal)

`file.Filename` from a multipart upload is controlled by the client. Using it directly to construct
a filesystem path enables path traversal attacks (`../../etc/passwd`).

Required:

- MUST NOT use `file.Filename` directly as a filesystem path.
- MUST generate a server-side filename (e.g. a UUID) and apply it when saving uploaded files.

Insecure patterns:

```go
// Bad — client controls the save path via file.Filename
c.SaveUploadedFile(file, "./uploads/" + file.Filename)
```

Fix:

```go
// Good — server-generated filename; original name only used for display/logging
import "github.com/google/uuid"

safeFilename := uuid.New().String() + filepath.Ext(file.Filename)
dst := filepath.Join("/var/uploads", safeFilename)
c.SaveUploadedFile(file, dst)
```

Detection hints:

- Search for `c.SaveUploadedFile(` and `file.Filename` used in path construction.
- Search for string concatenation with `file.Filename` as a path component.

---

## 2) Scanning Heuristics for Gin

High-signal patterns when auditing a Gin service:

- `gin.Default()` — review what Recovery middleware logs
- `c.MustGet(` — panic risk if middleware is missing from any route
- `AllowAllOrigins: true` combined with `AllowCredentials: true` — CORS/CSRF critical
- `c.JSON(` / `c.String(` inside middleware without adjacent `c.Abort()` or `return`
- `go func()` inside handlers that capture `c *gin.Context` directly
- `c.ShouldBindJSON` / `c.BindJSON` without a preceding `http.MaxBytesReader` assignment
- `gin.SetMode` absent or set to `DebugMode` in production entrypoint
- `file.Filename` used directly in path construction (`filepath.Join`, string concatenation)
- `SetTrustedProxies` absent when service is known to run behind a load balancer

---

## 3) Resources

- [Gin Framework Documentation](https://gin-gonic.com/docs/)
- [Gin Security Notes — Don't Trust All Proxies](https://github.com/gin-gonic/gin#dont-trust-all-proxies)
- [OWASP CORS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/CORS_Cheat_Sheet.html)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [go-playground/validator](https://github.com/go-playground/validator)
