# Gin Testing Guide

Applies to: Go projects using the Gin HTTP framework (v1.x).
Load in addition to `golang-tests.md`.

---

## Test Mode Setup

Always set Gin to test mode before any test that creates a Gin context or router. This suppresses debug logging and affects some Gin internals:

```go
func TestMain(m *testing.M) {
    gin.SetMode(gin.TestMode)
    os.Exit(m.Run())
}
```

Or per-test function when `TestMain` is not used:

```go
func TestItemHandlerList(t *testing.T) {
    gin.SetMode(gin.TestMode)
    // ...
}
```

---

## Handler Tests via `router.ServeHTTP`

The recommended pattern for handler tests is to create a minimal router, register the handler under test, and drive it with `httptest`:

```go
func TestItemHandlerList(t *testing.T) {
    gin.SetMode(gin.TestMode)

    mockUseCase := &MockItemUseCase{
        ListFunc: func(ctx context.Context, limit, offset int) ([]Item, int64, error) {
            return []Item{{Name: "Widget"}}, 1, nil
        },
    }
    handler := NewHandler(mockUseCase)

    router := gin.New()
    router.GET("/v1/items", handler.List)

    w := httptest.NewRecorder()
    req := httptest.NewRequest(http.MethodGet, "/v1/items?limit=50&offset=0", nil)
    router.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
    var resp map[string]interface{}
    require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
    assert.Equal(t, float64(1), resp["total"])
}
```

Prefer `router.ServeHTTP(w, req)` over `gin.CreateTestContext` for most handler tests — it exercises Gin's full dispatch pipeline including parameter extraction and middleware chains.

---

## Table-Driven Handler Tests

Use table-driven tests to cover all relevant status codes and scenarios in a single test function:

```go
func TestItemHandlerList(t *testing.T) {
    gin.SetMode(gin.TestMode)

    tests := []struct {
        name           string
        queryParams    string
        mockItems      []Item
        mockErr        error
        expectedStatus int
        expectedTotal  int64
    }{
        {
            name:           "returns 200 and items on success",
            queryParams:    "?limit=50&offset=0",
            mockItems:      []Item{{Name: "Widget"}},
            expectedStatus: http.StatusOK,
            expectedTotal:  1,
        },
        {
            name:           "returns 400 on invalid query params",
            queryParams:    "?limit=99999",
            expectedStatus: http.StatusBadRequest,
        },
        {
            name:           "returns 500 on use case error",
            queryParams:    "?limit=50&offset=0",
            mockErr:        errors.New("db connection failed"),
            expectedStatus: http.StatusInternalServerError,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            mock := &MockItemUseCase{
                ListFunc: func(ctx context.Context, limit, offset int) ([]Item, int64, error) {
                    return tt.mockItems, tt.expectedTotal, tt.mockErr
                },
            }
            handler := NewHandler(mock)

            router := gin.New()
            router.GET("/v1/items", handler.List)

            w := httptest.NewRecorder()
            req := httptest.NewRequest(http.MethodGet, "/v1/items"+tt.queryParams, nil)
            router.ServeHTTP(w, req)

            assert.Equal(t, tt.expectedStatus, w.Code)
        })
    }
}
```

---

## Testing Request Bodies (POST / PUT / PATCH)

Set the `Content-Type` header when testing endpoints that bind JSON:

```go
func TestItemHandlerCreate(t *testing.T) {
    gin.SetMode(gin.TestMode)

    tests := []struct {
        name           string
        body           string
        contentType    string
        expectedStatus int
    }{
        {
            name:           "creates item with valid JSON",
            body:           `{"name": "Widget", "category_id": "cat-uuid-1"}`,
            contentType:    "application/json",
            expectedStatus: http.StatusCreated,
        },
        {
            name:           "returns 400 on malformed JSON",
            body:           `{not valid json}`,
            contentType:    "application/json",
            expectedStatus: http.StatusBadRequest,
        },
        {
            name:           "returns 400 when Content-Type missing",
            body:           `{"name": "Widget"}`,
            contentType:    "",
            expectedStatus: http.StatusBadRequest,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            mock := &MockItemUseCase{
                CreateFunc: func(ctx context.Context, req CreateItemRequest) (*Item, error) {
                    return &Item{ID: "item-1", Name: req.Name}, nil
                },
            }
            handler := NewHandler(mock)

            router := gin.New()
            router.POST("/v1/items", handler.Create)

            w := httptest.NewRecorder()
            req := httptest.NewRequest(http.MethodPost, "/v1/items", strings.NewReader(tt.body))
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

## Testing Path Parameters

Path parameters are resolved by the router when using `router.ServeHTTP`. Register the route with the parameter pattern:

```go
func TestItemHandlerGet(t *testing.T) {
    gin.SetMode(gin.TestMode)

    mock := &MockItemUseCase{
        GetFunc: func(ctx context.Context, id string) (*Item, error) {
            if id == "item-123" {
                return &Item{ID: "item-123", Name: "Widget"}, nil
            }
            return nil, ErrNotFound
        },
    }
    handler := NewHandler(mock)

    router := gin.New()
    router.GET("/v1/items/:id", handler.Get)

    tests := []struct {
        name           string
        path           string
        expectedStatus int
    }{
        {name: "found", path: "/v1/items/item-123", expectedStatus: http.StatusOK},
        {name: "not found", path: "/v1/items/nonexistent", expectedStatus: http.StatusNotFound},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            w := httptest.NewRecorder()
            req := httptest.NewRequest(http.MethodGet, tt.path, nil)
            router.ServeHTTP(w, req)
            assert.Equal(t, tt.expectedStatus, w.Code)
        })
    }
}
```

---

## Testing Context Values (Middleware-Set Values)

Handlers that read values set by middleware (e.g. `user_id` from auth middleware) need those values in the context. Use `gin.CreateTestContext` when you need to inject context values directly without running the middleware:

```go
func TestItemHandlerCreateWithUserContext(t *testing.T) {
    gin.SetMode(gin.TestMode)

    mock := &MockItemUseCase{
        CreateFunc: func(ctx context.Context, req CreateItemRequest) (*Item, error) {
            return &Item{ID: "item-new", Name: req.Name}, nil
        },
    }
    handler := NewHandler(mock)

    w := httptest.NewRecorder()
    c, _ := gin.CreateTestContext(w)
    c.Set("user_id", "user-abc-123")
    c.Request = httptest.NewRequest(http.MethodPost, "/v1/items",
        strings.NewReader(`{"name":"Widget","category_id":"cat-1"}`))
    c.Request.Header.Set("Content-Type", "application/json")

    handler.Create(c)

    assert.Equal(t, http.StatusCreated, w.Code)
}
```

---

## Middleware Testing

Test middleware in isolation by wiring it into a minimal router and exercising it via `ServeHTTP`:

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
        {name: "valid token", authHeader: "Bearer valid-token-for-user-abc", expectedStatus: http.StatusOK},
        {name: "missing token", authHeader: "", expectedStatus: http.StatusUnauthorized},
        {name: "invalid token", authHeader: "Bearer bad-token", expectedStatus: http.StatusUnauthorized},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            w := httptest.NewRecorder()
            req := httptest.NewRequest(http.MethodGet, "/protected", nil)
            if tt.authHeader != "" {
                req.Header.Set("Authorization", tt.authHeader)
            }
            router.ServeHTTP(w, req)
            assert.Equal(t, tt.expectedStatus, w.Code)
        })
    }
}

// Test that middleware sets expected context values
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
    req := httptest.NewRequest(http.MethodGet, "/me", nil)
    req.Header.Set("Authorization", "Bearer valid-token-for-user-abc")
    router.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
    assert.Equal(t, "user-abc", capturedUserID)
}
```

---

## Full Router Integration Test

When you need to verify the full routing stack — path matching, middleware chain, and handler in concert — use the same `setupRouter` function that `main.go` uses:

```go
func TestRouterIntegration(t *testing.T) {
    gin.SetMode(gin.TestMode)

    router := SetupRouter(mockUseCase) // same factory used in main.go

    tests := []struct {
        method         string
        path           string
        body           string
        contentType    string
        expectedStatus int
    }{
        {method: "GET",    path: "/v1/items",         expectedStatus: http.StatusOK},
        {method: "POST",   path: "/v1/items",
            body: `{"name":"Widget","category_id":"cat-1"}`, contentType: "application/json",
            expectedStatus: http.StatusCreated},
        {method: "GET",    path: "/v1/items/nonexistent", expectedStatus: http.StatusNotFound},
        {method: "DELETE", path: "/v1/items/item-1",  expectedStatus: http.StatusNoContent},
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

## Asserting Response Body Structure

Do not stop at asserting the status code. Verify the response body shape and key fields:

```go
// After asserting status code, unmarshal and check body
assert.Equal(t, http.StatusOK, w.Code)

var resp struct {
    Data  []Item `json:"data"`
    Total int64  `json:"total"`
}
require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
assert.Len(t, resp.Data, 1)
assert.Equal(t, int64(1), resp.Total)
assert.Equal(t, "Widget", resp.Data[0].Name)
```

---

## Handler Test Checklist

- [ ] `gin.SetMode(gin.TestMode)` set globally in `TestMain` or at the start of every test function
- [ ] `httptest.NewRecorder()` and `router.ServeHTTP(w, req)` used for route-aware tests
- [ ] `gin.CreateTestContext` used only when injecting context values directly without running middleware
- [ ] Success and error status codes both tested per handler
- [ ] Response body structure validated — not just the status code
- [ ] Query parameters, path parameters, and request body all tested where the handler reads them
- [ ] Request body tests cover valid JSON, malformed JSON, and missing `Content-Type`
- [ ] Context values (`c.Set`) populated when the handler reads them
- [ ] Use case / service dependencies mocked — no real implementations in unit handler tests
- [ ] Middleware tested in isolation with its own minimal router — not re-tested inside handler tests

---

## Resources

- [Gin Testing Documentation](https://gin-gonic.com/docs/testing/)
- [net/http/httptest](https://pkg.go.dev/net/http/httptest)
- [Gin Framework](https://github.com/gin-gonic/gin)
- [testify/assert](https://github.com/stretchr/testify)
