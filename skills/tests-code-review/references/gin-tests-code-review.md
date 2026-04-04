# Gin Test Code Review Guide

Supplements `test-review-checklist.md` and `golang-tests-code-review.md` for Go projects using the Gin HTTP framework (v1.x).

---

## Setup Anti-Patterns

### Not Setting Test Mode

```go
// Bad
func TestItemHandlerList(t *testing.T) {
    handler := NewHandler(mockUseCase)
    w := httptest.NewRecorder()
}

// Good — call once in TestMain or at top of each test
func TestMain(m *testing.M) {
    gin.SetMode(gin.TestMode)
    os.Exit(m.Run())
}
```

### Not Using a Router for Tests That Exercise Routing

`gin.CreateTestContext` bypasses routing — path parameters and middleware registered on the router are not applied. Tests requiring path param extraction or middleware effects MUST use a router.

```go
// Bad — c.Param("id") will be empty
func TestItemHandlerGet(t *testing.T) {
    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Request = httptest.NewRequest("GET", "/v1/items/item-123", nil)
    handler.Get(c)
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

Reserve `gin.CreateTestContext` for injecting Gin context values (e.g. `c.Set("user_id", ...)`) without running the middleware chain.

## Assertion Anti-Patterns

### Only Checking Status Code

```go
// Bad — status alone does not verify payload correctness
assert.Equal(t, http.StatusOK, w.Code)

// Good — also verify response body structure and key fields
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
// Bad — only happy path tested
mock := &MockItemUseCase{
    ListFunc: func(ctx context.Context, limit, offset int) ([]Item, int64, error) {
        return []Item{{Name: "Widget"}}, 1, nil
    },
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

## Request Construction Anti-Patterns

### Not Testing Request Body Binding Errors

Handlers using `ShouldBindJSON` MUST handle malformed JSON and missing `Content-Type`. Tests with only valid input leave the binding error path uncovered.

```go
// Bad — only tests valid JSON
body := `{"name": "Widget", "category_id": "cat-1"}`

// Good — table-driven including bind-failure scenarios
tests := []struct {
    name           string
    body           string
    contentType    string
    expectedStatus int
}{
    {name: "valid", body: `{"name":"Widget","category_id":"cat-uuid-1"}`,
        contentType: "application/json", expectedStatus: http.StatusCreated},
    {name: "malformed JSON", body: `{bad json}`,
        contentType: "application/json", expectedStatus: http.StatusBadRequest},
    {name: "missing Content-Type", body: `{"name":"Widget","category_id":"cat-uuid-1"}`,
        contentType: "", expectedStatus: http.StatusBadRequest},
    {name: "missing required field", body: `{"name":""}`,
        contentType: "application/json", expectedStatus: http.StatusBadRequest},
}
```

### Missing Context Values That Handlers Depend On

Handlers reading values set by auth middleware (e.g. `user_id`, `tenant_id`) silently get zero values when absent.

```go
// Bad — handler calls c.GetString("user_id") but context has no value
c, _ := gin.CreateTestContext(w)
c.Request = httptest.NewRequest("POST", "/v1/items",
    strings.NewReader(`{"name":"Widget","category_id":"cat-1"}`))
handler.Create(c) // user_id is ""

// Good — populate all context values the handler reads
c.Set("user_id", "user-abc-123")
c.Set("tenant_id", "tenant-xyz")
```

## Middleware Separation Anti-Patterns

### Handler Tests That Re-test Middleware Logic

Auth, rate-limiting, and logging are middleware responsibilities. Handler tests passing raw Authorization headers and expecting middleware-level rejections test the wrong layer.

```go
// Bad — handler test checking auth token format; that is middleware's job
req.Header.Set("Authorization", "invalid-token")
router.ServeHTTP(w, req)
assert.Equal(t, http.StatusUnauthorized, w.Code)

// Good — handler test assumes middleware has already run
c, _ := gin.CreateTestContext(w)
c.Set("user_id", "user-123") // precondition: auth middleware has run
c.Request = httptest.NewRequest("GET", "/v1/items", nil)
handler.List(c)
assert.Equal(t, http.StatusOK, w.Code)
```

### Middleware Not Tested for `c.Abort()` Behaviour

Middleware that writes an error response without calling `c.Abort()` allows subsequent handlers to run. Tests MUST verify the chain is stopped.

```go
// Good — verify protected handler did not execute after middleware rejection
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
    req := httptest.NewRequest("GET", "/protected", nil)
    router.ServeHTTP(w, req)
    assert.Equal(t, http.StatusUnauthorized, w.Code)
    assert.False(t, handlerCalled, "handler must not run when auth middleware rejects the request")
}
```

## Checklist for Gin Handler and Middleware Tests

- [ ] `gin.SetMode(gin.TestMode)` set globally in `TestMain` or at start of every test function
- [ ] `router.ServeHTTP(w, req)` used for tests requiring route parameter resolution or middleware wiring
- [ ] `gin.CreateTestContext` used only for injecting Gin context values directly
- [ ] Both success and error status codes tested for every handler
- [ ] Response body structure validated, not just status code
- [ ] Path parameters verified by registering route with parameter pattern and correct URL
- [ ] Query parameters included in request URL when handler reads them
- [ ] Request body tests include: valid input, malformed JSON, missing `Content-Type`, missing required fields
- [ ] All Gin context values the handler reads (`c.Get`, `c.GetString`, `c.MustGet`) set in tests
- [ ] Use case / service dependencies mocked — no real DB or external calls in unit handler tests
- [ ] Table-driven tests used when multiple status codes or scenarios exist
- [ ] Middleware tested in its own test function, not re-exercised inside handler tests
- [ ] Middleware tests verify `c.Abort()` stops handler chain on error
- [ ] Middleware tests verify downstream context values set correctly on success path
