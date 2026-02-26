# Gin Testing Guide

Applies to: Go projects using the Gin HTTP framework.
Load in addition to `golang-testing-guide.md`.

---

## Handler Test Setup

Always set Gin to test mode before creating a test context:

```go
func TestItemHandlerList(t *testing.T) {
    gin.SetMode(gin.TestMode)

    // ...
}
```

Use `httptest.NewRecorder()` and `gin.CreateTestContext()` — never a live server:

```go
w := httptest.NewRecorder()
c, _ := gin.CreateTestContext(w)
c.Request = httptest.NewRequest("GET", "/v1/items", nil)
```

---

## Table-Driven Handler Tests

```go
func TestItemHandlerList(t *testing.T) {
    gin.SetMode(gin.TestMode)

    tests := []struct {
        name           string
        queryParams    string
        mockItems      []Item
        mockErr        error
        expectedStatus int
        expectedCount  int64
    }{
        {
            name:           "returns 200 and items on success",
            queryParams:    "?limit=50&offset=0",
            mockItems:      []Item{{Name: "Item1"}},
            expectedStatus: http.StatusOK,
            expectedCount:  1,
        },
        {
            name:           "returns 400 on invalid limit",
            queryParams:    "?limit=9999",
            mockErr:        errors.New("limit exceeds maximum"),
            expectedStatus: http.StatusBadRequest,
        },
        {
            name:           "returns 500 on use case error",
            mockErr:        errors.New("unexpected error"),
            expectedStatus: http.StatusInternalServerError,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            mockUseCase := &MockItemUseCase{
                ListFunc: func(ctx context.Context) ([]Item, int64, error) {
                    return tt.mockItems, tt.expectedCount, tt.mockErr
                },
            }
            handler := NewHandler(mockUseCase)

            w := httptest.NewRecorder()
            c, _ := gin.CreateTestContext(w)
            c.Request = httptest.NewRequest("GET", "/v1/items"+tt.queryParams, nil)

            handler.List(c)

            assert.Equal(t, tt.expectedStatus, w.Code)

            if tt.expectedStatus == http.StatusOK {
                var response map[string]interface{}
                require.NoError(t, json.Unmarshal(w.Body.Bytes(), &response))
                assert.Equal(t, float64(tt.expectedCount), response["count"])
            }
        })
    }
}
```

---

## Testing with Context Values

Pass request-scoped values (user ID, pagination, etc.) through the Gin context:

```go
func TestHandlerWithContextValues(t *testing.T) {
    gin.SetMode(gin.TestMode)

    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Set("user_id", "user-123")
    c.Request = httptest.NewRequest("GET", "/v1/items", nil)

    handler.List(c)

    assert.Equal(t, http.StatusOK, w.Code)
}
```

---

## Testing Path Parameters

```go
func TestItemHandlerGet(t *testing.T) {
    gin.SetMode(gin.TestMode)

    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Params = gin.Params{{Key: "id", Value: "item-123"}}
    c.Request = httptest.NewRequest("GET", "/v1/items/item-123", nil)

    handler.Get(c)

    assert.Equal(t, http.StatusOK, w.Code)
}
```

---

## Testing Request Bodies (POST / PUT)

```go
func TestItemHandlerCreate(t *testing.T) {
    gin.SetMode(gin.TestMode)

    body := `{"name": "New Item", "category_id": "cat-1"}`

    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Request = httptest.NewRequest("POST", "/v1/items", strings.NewReader(body))
    c.Request.Header.Set("Content-Type", "application/json")

    handler.Create(c)

    assert.Equal(t, http.StatusCreated, w.Code)
}
```

---

## Middleware Testing

Test middleware in isolation by wiring it into a minimal router:

```go
func TestAuthMiddleware(t *testing.T) {
    gin.SetMode(gin.TestMode)

    router := gin.New()
    router.Use(AuthMiddleware())
    router.GET("/protected", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{"user": c.GetString("user_id")})
    })

    tests := []struct {
        name           string
        authHeader     string
        expectedStatus int
    }{
        {name: "valid token", authHeader: "Bearer valid-token", expectedStatus: http.StatusOK},
        {name: "missing token", authHeader: "", expectedStatus: http.StatusUnauthorized},
        {name: "invalid token", authHeader: "Bearer bad", expectedStatus: http.StatusUnauthorized},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            w := httptest.NewRecorder()
            req := httptest.NewRequest("GET", "/protected", nil)
            if tt.authHeader != "" {
                req.Header.Set("Authorization", tt.authHeader)
            }
            router.ServeHTTP(w, req)
            assert.Equal(t, tt.expectedStatus, w.Code)
        })
    }
}
```

For middleware that sets context values, verify the downstream handler receives them:

```go
func TestAuthMiddlewareSetsUserID(t *testing.T) {
    gin.SetMode(gin.TestMode)

    var capturedUserID string
    router := gin.New()
    router.Use(AuthMiddleware())
    router.GET("/me", func(c *gin.Context) {
        capturedUserID = c.GetString("user_id")
        c.Status(http.StatusOK)
    })

    w := httptest.NewRecorder()
    req := httptest.NewRequest("GET", "/me", nil)
    req.Header.Set("Authorization", "Bearer valid-token-for-user-abc")
    router.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
    assert.Equal(t, "user-abc", capturedUserID)
}
```

---

## Full Router Integration Test

When you need to test the full routing stack (path matching, middleware chain, handler):

```go
func TestRouterIntegration(t *testing.T) {
    gin.SetMode(gin.TestMode)

    // Wire the real router (same as in main.go)
    router := SetupRouter(mockUseCase)

    tests := []struct {
        method         string
        path           string
        body           string
        contentType    string
        expectedStatus int
    }{
        {method: "GET", path: "/v1/items", expectedStatus: http.StatusOK},
        {method: "POST", path: "/v1/items",
            body: `{"name":"New"}`, contentType: "application/json",
            expectedStatus: http.StatusCreated},
        {method: "GET", path: "/v1/items/nonexistent", expectedStatus: http.StatusNotFound},
        {method: "DELETE", path: "/v1/items/id-1", expectedStatus: http.StatusNoContent},
    }

    for _, tt := range tests {
        t.Run(tt.method+" "+tt.path, func(t *testing.T) {
            var bodyReader io.Reader
            if tt.body != "" {
                bodyReader = strings.NewReader(tt.body)
            }
            w := httptest.NewRecorder()
            req := httptest.NewRequest(tt.method, tt.path, bodyReader)
            if tt.contentType != "" {
                req.Header.Set("Content-Type", tt.contentType)
            }
            router.ServeHTTP(w, req)
            assert.Equal(t, tt.expectedStatus, w.Code)
        })
    }
}
```

---

## Handler Test Checklist

- [ ] `gin.SetMode(gin.TestMode)` called at the start of every handler test
- [ ] `httptest.NewRecorder()` and `gin.CreateTestContext()` used
- [ ] Success **and** error status codes tested
- [ ] Response body structure validated, not just the status code
- [ ] Query parameters, path parameters, and request body parsed correctly
- [ ] Context values (`c.Set`) populated when the handler reads them
- [ ] Use case / service dependencies mocked — not real implementations

---

## Resources

- [Gin Testing Documentation](https://gin-gonic.com/docs/testing/)
- [net/http/httptest](https://pkg.go.dev/net/http/httptest)
- [Gin Framework](https://github.com/gin-gonic/gin)
