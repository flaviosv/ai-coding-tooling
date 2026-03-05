# Gin Test Code Review Guide

Supplements `test-review-checklist.md` and `golang-tests-code-review.md` for Go projects using the Gin HTTP framework (v1.x).

---

## Setup Anti-Patterns

### Not Setting Test Mode

```go
// Bad — Gin defaults to debug mode; pollutes test output with route registration logs
// and affects some Gin internal behaviour
func TestItemHandlerList(t *testing.T) {
    handler := NewHandler(mockUseCase)
    w := httptest.NewRecorder()
    // ...
}

// Good — call once in TestMain, or at the top of each test function
func TestMain(m *testing.M) {
    gin.SetMode(gin.TestMode)
    os.Exit(m.Run())
}
```

### Not Using a Router for Tests That Exercise Routing

`gin.CreateTestContext` bypasses Gin's routing pipeline — path parameters and middleware registered on the router are not applied. Tests that require path parameter extraction or middleware effects must use a router:

```go
// Bad — c.Param("id") will be empty; routing not exercised
func TestItemHandlerGet(t *testing.T) {
    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Request = httptest.NewRequest("GET", "/v1/items/item-123", nil)
    handler.Get(c)
    // c.Param("id") is "" — handler may silently fail or return wrong item
}

// Good — router resolves /:id into c.Param("id")
func TestItemHandlerGet(t *testing.T) {
    gin.SetMode(gin.TestMode)
    router := gin.New()
    router.GET("/v1/items/:id", handler.Get)

    w := httptest.NewRecorder()
    req := httptest.NewRequest("GET", "/v1/items/item-123", nil)
    router.ServeHTTP(w, req)
    assert.Equal(t, http.StatusOK, w.Code)
}
```

Reserve `gin.CreateTestContext` for the specific case where you need to inject Gin context values (e.g. `c.Set("user_id", ...)`) without running the middleware chain.

---

## Assertion Anti-Patterns

### Only Checking Status Code

```go
// Bad — status alone does not verify payload correctness; a handler can return
// 200 with an empty body or wrong structure and this test will pass
func TestItemHandlerList(t *testing.T) {
    // ...
    assert.Equal(t, http.StatusOK, w.Code) // not enough
}

// Good — also verify the response body structure and key fields
assert.Equal(t, http.StatusOK, w.Code)

var resp struct {
    Data  []Item `json:"data"`
    Total int64  `json:"total"`
}
require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
assert.Len(t, resp.Data, 1)
assert.Equal(t, int64(1), resp.Total)
```

### Not Testing Error Paths

```go
// Bad — only the happy path is tested; error handling code is untested
func TestItemHandlerList(t *testing.T) {
    mock := &MockItemUseCase{
        ListFunc: func(ctx context.Context, limit, offset int) ([]Item, int64, error) {
            return []Item{{Name: "Widget"}}, 1, nil
        },
    }
    // Single scenario — use case errors, bad params, empty results not tested
}

// Good — table-driven covering all meaningful status code paths
tests := []struct {
    name           string
    queryParams    string
    mockErr        error
    expectedStatus int
}{
    {name: "success", queryParams: "?limit=50&offset=0", mockErr: nil, expectedStatus: http.StatusOK},
    {name: "invalid limit", queryParams: "?limit=0", expectedStatus: http.StatusBadRequest},
    {name: "use case error", queryParams: "?limit=50&offset=0",
        mockErr: errors.New("db unavailable"), expectedStatus: http.StatusInternalServerError},
}
```

---

## Request Construction Anti-Patterns

### Not Testing Request Body Binding Errors

Handlers using `ShouldBindJSON` must handle malformed JSON and missing `Content-Type`. Tests that only provide valid input leave the binding error path uncovered:

```go
// Bad — only tests valid JSON
func TestItemHandlerCreate(t *testing.T) {
    body := `{"name": "Widget", "category_id": "cat-1"}`
    // Only one scenario — binding errors never exercised
}

// Good — table-driven including bind-failure scenarios
tests := []struct {
    name           string
    body           string
    contentType    string
    expectedStatus int
}{
    {
        name: "valid", body: `{"name":"Widget","category_id":"cat-uuid-1"}`,
        contentType: "application/json", expectedStatus: http.StatusCreated,
    },
    {
        name: "malformed JSON", body: `{bad json}`,
        contentType: "application/json", expectedStatus: http.StatusBadRequest,
    },
    {
        name: "missing Content-Type", body: `{"name":"Widget","category_id":"cat-uuid-1"}`,
        contentType: "", expectedStatus: http.StatusBadRequest,
    },
    {
        name: "missing required field", body: `{"name":""}`,
        contentType: "application/json", expectedStatus: http.StatusBadRequest,
    },
}
```

### Missing Context Values That Handlers Depend On

Handlers that read values set by auth middleware (e.g. `user_id`, `tenant_id`) silently get zero values or wrong behaviour when those values are absent:

```go
// Bad — handler calls c.GetString("user_id") but context has no value set;
// item may be created without an owner, or handler may behave unexpectedly
func TestItemHandlerCreate(t *testing.T) {
    gin.SetMode(gin.TestMode)
    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Request = httptest.NewRequest("POST", "/v1/items",
        strings.NewReader(`{"name":"Widget","category_id":"cat-1"}`))
    c.Request.Header.Set("Content-Type", "application/json")
    handler.Create(c) // user_id is "" — incorrect test precondition
}

// Good — populate all context values the handler reads
c.Set("user_id", "user-abc-123")
c.Set("tenant_id", "tenant-xyz")
```

---

## Middleware Separation Anti-Patterns

### Handler Tests That Re-test Middleware Logic

Auth, rate-limiting, and logging are middleware responsibilities. Handler tests that pass raw Authorization headers and expect middleware-level rejections are testing the wrong layer — and testing nothing if the middleware is not actually wired in the test:

```go
// Bad — handler test checking auth token format; that is middleware's job
func TestItemHandlerList(t *testing.T) {
    req.Header.Set("Authorization", "invalid-token")
    router.ServeHTTP(w, req)
    assert.Equal(t, http.StatusUnauthorized, w.Code)
    // This only passes if AuthMiddleware is wired in the test router.
    // If it is, this test duplicates TestAuthMiddleware. If it is not, it tests nothing.
}

// Good — handler test assumes middleware has already run (user_id is in context)
// Auth middleware is tested separately in TestAuthMiddleware
func TestItemHandlerList(t *testing.T) {
    gin.SetMode(gin.TestMode)
    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Set("user_id", "user-123") // precondition: auth middleware has run
    c.Request = httptest.NewRequest("GET", "/v1/items", nil)
    handler.List(c)
    assert.Equal(t, http.StatusOK, w.Code)
}
```

### Middleware Not Tested for `c.Abort()` Behaviour

Middleware that writes an error response without calling `c.Abort()` allows subsequent handlers to run. Tests must verify the chain is actually stopped:

```go
// Good — verify the protected handler did not execute after middleware rejection
func TestAuthMiddlewareBlocksProtectedRoute(t *testing.T) {
    gin.SetMode(gin.TestMode)

    handlerCalled := false
    router := gin.New()
    router.Use(AuthMiddleware())
    router.GET("/protected", func(c *gin.Context) {
        handlerCalled = true
        c.Status(http.StatusOK)
    })

    w := httptest.NewRecorder()
    req := httptest.NewRequest("GET", "/protected", nil) // no auth header
    router.ServeHTTP(w, req)

    assert.Equal(t, http.StatusUnauthorized, w.Code)
    assert.False(t, handlerCalled, "handler must not run when auth middleware rejects the request")
}
```

---

## Checklist for Gin Handler and Middleware Tests

- [ ] `gin.SetMode(gin.TestMode)` set globally in `TestMain` or at the start of every test function
- [ ] `router.ServeHTTP(w, req)` used for tests that require route parameter resolution or middleware wiring
- [ ] `gin.CreateTestContext` used only for injecting Gin context values directly — not as a general-purpose handler test harness
- [ ] Both success and error status codes tested for every handler
- [ ] Response body structure validated — not just the status code
- [ ] Path parameters verified by registering the route with a parameter pattern and using the correct URL in the request
- [ ] Query parameters included in the request URL when the handler reads them
- [ ] Request body tests include: valid input, malformed JSON, missing `Content-Type`, missing required fields
- [ ] All Gin context values the handler reads (`c.Get`, `c.GetString`, `c.MustGet`) are set in tests
- [ ] Use case / service dependencies mocked — no real DB or external calls in unit handler tests
- [ ] Table-driven tests used when multiple status codes or scenarios exist
- [ ] Middleware tested in its own test function — not re-exercised inside handler tests
- [ ] Middleware tests verify that `c.Abort()` stops the handler chain when an error is returned
- [ ] Middleware tests verify that downstream context values are set correctly on the success path

---

## Resources

- [Gin Testing Documentation](https://gin-gonic.com/docs/testing/)
- [net/http/httptest](https://pkg.go.dev/net/http/httptest)
- [Gin Framework](https://github.com/gin-gonic/gin)
