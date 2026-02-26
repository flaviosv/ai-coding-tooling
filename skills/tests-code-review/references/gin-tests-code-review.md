# Gin Test Code Review Guide

Supplements `test-review-checklist.md` and `golang-tests-code-review.md` for Go projects using the Gin HTTP framework.

---

## DRF-Equivalent Review Points for Gin

### ❌ Not Setting Test Mode

```go
// Bad — Gin runs in debug mode, pollutes test output and affects behaviour
func TestItemHandlerList(t *testing.T) {
    handler := NewHandler(mockUseCase)
    handler.List(nil) // nil context — will panic
}

// Good
func TestItemHandlerList(t *testing.T) {
    gin.SetMode(gin.TestMode) // Always first
    // ...
}
```

### ❌ Not Using httptest

```go
// Bad — no response capture, no assertions possible
func TestItemHandler(t *testing.T) {
    handler := NewHandler(mockUseCase)
    handler.List(nil)
}

// Good
func TestItemHandlerList(t *testing.T) {
    gin.SetMode(gin.TestMode)

    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Request = httptest.NewRequest("GET", "/v1/items", nil)

    handler.List(c)

    assert.Equal(t, http.StatusOK, w.Code)
}
```

### ❌ Only Checking Status Code

```go
// Bad — status alone doesn't verify payload correctness
func TestItemHandlerList(t *testing.T) {
    // ...
    assert.Equal(t, http.StatusOK, w.Code) // Not enough

// Good — also verify the response body structure
    var response map[string]interface{}
    require.NoError(t, json.Unmarshal(w.Body.Bytes(), &response))
    assert.Equal(t, float64(1), response["count"])
    assert.NotEmpty(t, response["results"])
}
```

### ❌ Not Testing Error Paths

```go
// Bad — only testing the happy path
func TestItemHandlerList(t *testing.T) {
    mockUseCase := &MockItemUseCase{
        ListFunc: func(ctx context.Context) ([]Item, error) {
            return []Item{{Name: "Item1"}}, nil
        },
    }
    // Only one scenario tested

// Good — table-driven to cover all relevant status codes
tests := []struct {
    name           string
    mockErr        error
    expectedStatus int
}{
    {name: "success", mockErr: nil, expectedStatus: http.StatusOK},
    {name: "use case error", mockErr: errors.New("internal"), expectedStatus: http.StatusInternalServerError},
}
```

### ❌ Not Testing Path Parameters or Query Params

```go
// Bad — skips parsing verification
func TestItemHandlerGet(t *testing.T) {
    c, _ := gin.CreateTestContext(httptest.NewRecorder())
    c.Request = httptest.NewRequest("GET", "/v1/items/", nil)
    // Missing ID param — handler may fail silently

// Good
    c.Params = gin.Params{{Key: "id", Value: "item-123"}}
    c.Request = httptest.NewRequest("GET", "/v1/items/item-123", nil)
}
```

---

## Auth Context Review

### ❌ Missing Auth Context Values

Many handlers read a user ID or tenant ID from the Gin context (set by auth middleware). Tests that skip this will see the wrong behaviour:

```go
// Bad — handler calls c.GetString("user_id") but context has no value set
func TestItemHandlerCreate(t *testing.T) {
    gin.SetMode(gin.TestMode)
    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Request = httptest.NewRequest("POST", "/v1/items", strings.NewReader(`{"name":"test"}`))
    c.Request.Header.Set("Content-Type", "application/json")
    handler.Create(c) // handler gets empty user_id → may silently create items without owner

// Good — populate all context values the handler reads
    c.Set("user_id", "user-abc-123")
    c.Set("tenant_id", "tenant-1")
}
```

### ❌ Not Testing That `c.BindJSON` Error Path Is Handled

```go
// Bad — only tests valid JSON; missing the malformed body path
func TestItemHandlerCreate(t *testing.T) {
    body := `{"name": "New Item"}`  // only valid path tested

// Good — table-driven to cover bind error
tests := []struct {
    name           string
    body           string
    contentType    string
    expectedStatus int
}{
    {name: "valid", body: `{"name":"New Item"}`, contentType: "application/json", expectedStatus: http.StatusCreated},
    {name: "malformed JSON", body: `{bad json}`, contentType: "application/json", expectedStatus: http.StatusBadRequest},
    {name: "missing content-type", body: `{"name":"New Item"}`, contentType: "", expectedStatus: http.StatusBadRequest},
}
```

---

## Middleware Separation Review

### ❌ Handler Tests That Re-test Middleware Logic

```go
// Bad — handler test checking auth token format; that's middleware's responsibility
func TestItemHandlerList(t *testing.T) {
    c.Request.Header.Set("Authorization", "invalid")
    handler.List(c)
    assert.Equal(t, http.StatusUnauthorized, w.Code) // auth is middleware's job, not handler's

// Good — handler tests assume auth middleware has already run (user_id is in context)
// Auth middleware is tested separately in TestAuthMiddleware
func TestItemHandlerList(t *testing.T) {
    c.Set("user_id", "user-123") // middleware pre-condition satisfied
    handler.List(c)
    assert.Equal(t, http.StatusOK, w.Code)
}
```

---

## Checklist for Gin Handler Tests

- [ ] `gin.SetMode(gin.TestMode)` called at the start of every handler test function
- [ ] `httptest.NewRecorder()` and `gin.CreateTestContext()` used for all handler tests
- [ ] Both success **and** error status codes tested
- [ ] Response body structure verified beyond just the status code
- [ ] Path parameters (`c.Params`) set when the handler reads them
- [ ] Query parameters included in the request URL when used
- [ ] Request body set with correct `Content-Type` header for POST/PUT/PATCH
- [ ] Gin context values (`c.Set`) populated when the handler reads them
- [ ] Use case / service dependencies mocked — no real implementations in handler tests
- [ ] Table-driven tests used when multiple status codes or scenarios exist
- [ ] All Gin context values the handler reads (`c.Get`, `c.GetString`) are set in tests
- [ ] Malformed request body path tested (JSON parse failure → 400)
- [ ] Middleware logic not re-tested in handler tests — each concern tested in isolation

---

## Resources

- [Gin Testing Documentation](https://gin-gonic.com/docs/testing/)
- [net/http/httptest](https://pkg.go.dev/net/http/httptest)
- [Gin Framework](https://github.com/gin-gonic/gin)
