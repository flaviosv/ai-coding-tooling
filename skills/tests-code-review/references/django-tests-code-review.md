# Django Test Code Review Reference

Supplements `test-review-checklist.md` for projects using Django and Django REST Framework.
Supported version range: Django 4.2 LTS (base) → Django 5.2 LTS (latest).

---

## General Django Test Anti-Patterns

### Missing `@pytest.mark.django_db`

```python
# Bad
def test_item_creation():
    item = Item.objects.create(name="Test")  # RuntimeError

# Good
@pytest.mark.django_db
def test_item_creation():
    item = Item.objects.create(name="Test")
    assert item.pk is not None
```

### Using Django's `Client` Instead of `APIClient` for DRF Views

Django's test Client may not handle DRF content negotiation, authentication headers, or JSON response parsing correctly.

```python
# Bad
def test_item_list():
    client = Client()
    response = client.get("/api/v1/items/")

# Good
@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_item_list(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 200
```

### Only Checking the Status Code

A 200 with wrong data is a broken test that passes.

```python
# Bad
@pytest.mark.django_db
def test_item_list(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200

# Good — verify structure and content
@pytest.mark.django_db
def test_item_list_returns_paginated_results(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200
    assert "results" in response.data
    assert "count" in response.data
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["name"] == item.name
```

### Not Testing the Unauthenticated Path

Every protected endpoint MUST have a test verifying unauthenticated requests are rejected.

```python
# Bad — only testing the happy path
@pytest.mark.django_db
def test_item_list(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200

# Good
@pytest.mark.django_db
def test_item_list_requires_authentication(api_client):
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 401
```

### Not Testing Data Isolation / Permission Boundaries

```python
# Bad — not verifying user A cannot see user B's data
@pytest.mark.django_db
def test_item_list(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200

# Good
@pytest.mark.django_db
def test_item_list_only_returns_own_items(api_client, db):
    user_a = UserFactory()
    user_b = UserFactory()
    item_a = ItemFactory(owner=user_a)
    ItemFactory(owner=user_b)
    api_client.force_authenticate(user=user_a)
    response = api_client.get("/api/v1/items/")
    ids = [str(r["id"]) for r in response.data["results"]]
    assert str(item_a.pk) in ids
    assert len(ids) == 1
```

### Repeated Inline `objects.create()` Calls

```python
# Bad — fixture data duplicated across files
@pytest.mark.django_db
def test_item_list(authenticated_client):
    category = Category.objects.create(name="Cat")
    item = Item.objects.create(name="Item", category=category, is_active=True)
    response = authenticated_client.get("/api/v1/items/")
    assert response.data["count"] == 1

# Good — factory_boy; tests declare only what varies
@pytest.mark.django_db
def test_item_list(authenticated_client):
    ItemFactory(is_active=True)
    response = authenticated_client.get("/api/v1/items/")
    assert response.data["count"] == 1
```

## Serializer Test Review Points

### Missing Validation Coverage

Every serializer test MUST cover valid path and key invalid paths:

```python
class TestItemSerializer:
    def test_valid_data_passes_validation(self, category):
        s = ItemSerializer(data={"name": "Test", "category": category.pk})
        assert s.is_valid(), s.errors

    def test_missing_name_fails_validation(self, category):
        s = ItemSerializer(data={"category": category.pk})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_read_only_id_field_not_writable(self, item):
        s = ItemSerializer(item, data={"id": "spoofed-id", "name": item.name})
        s.is_valid()
        assert s.validated_data.get("id") is None

    def test_output_excludes_password(self, user):
        s = UserSerializer(user)
        assert "password" not in s.data
```

## N+1 Query Detection

List endpoints MUST be checked for N+1 queries. A test without query count verification silently allows N+1 regressions.

```python
@pytest.mark.django_db
def test_item_list_query_count_is_fixed(authenticated_client, category, db):
    Item.objects.bulk_create([
        Item(name=f"Item {i}", category=category, is_active=True) for i in range(20)
    ])
    with CaptureQueriesContext(connection) as ctx:
        response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200
    assert len(ctx.captured_queries) <= 5, (
        f"Too many queries ({len(ctx.captured_queries)}). "
        "Check for missing select_related/prefetch_related."
    )
```

Flag any list endpoint test missing `CaptureQueriesContext` assertion as P1.

## `transaction=True` Misuse

`@pytest.mark.django_db(transaction=True)` disables transaction wrapping and resets via table truncation — significantly slower.

```python
# Bad — transaction=True for simple CRUD with no transaction logic
@pytest.mark.django_db(transaction=True)
def test_item_creation():
    item = Item.objects.create(name="Test")

# Good — use transaction=True only for:
# - on_commit() callbacks
# - LISTEN/NOTIFY (PostgreSQL)
# - Celery task dispatch with CELERY_TASK_ALWAYS_EAGER=True
# - Testing raw SAVEPOINT / rollback logic
@pytest.mark.django_db(transaction=True)
def test_on_commit_callback_fires_after_save(user):
    with patch("myapp.signals.send_welcome_email") as mock_send:
        user.email_verified = True
        user.save()
    mock_send.assert_called_once()
```

Flag `transaction=True` not involving the above scenarios as P1.

## Signal Side Effects Not Isolated

```python
# Bad — signal fires real email during test
@pytest.mark.django_db
def test_user_creation():
    user = User.objects.create_user(email="alice@example.com", password="pass")

# Good — mock the receiver
@pytest.mark.django_db
def test_user_creation_does_not_block_on_email():
    with patch("myapp.signals.send_welcome_email") as mock_send:
        user = User.objects.create_user(email="alice@example.com", password="pass")
    mock_send.assert_called_once_with(user)

# Good — disconnect the signal for the test duration
@pytest.mark.django_db
def test_user_creation_without_side_effect():
    from myapp.signals import send_welcome_email
    post_save.disconnect(send_welcome_email, sender=User)
    try:
        user = User.objects.create_user(email="alice@example.com", password="pass")
        assert user.pk is not None
    finally:
        post_save.connect(send_welcome_email, sender=User)
```

## `override_settings` Misuse

```python
# Bad — mutates global settings; leaks into other tests
from django.conf import settings
settings.FEATURE_X_ENABLED = True

# Good — scoped change that resets automatically
@pytest.mark.django_db
@override_settings(FEATURE_X_ENABLED=True)
def test_feature_x_is_active(authenticated_client):
    response = authenticated_client.get("/api/v1/feature-x/")
    assert response.status_code == 200
```

## Celery Task Test Isolation

```python
# Bad — dispatches real Celery task; flaky without worker
@pytest.mark.django_db
def test_create_dispatches_notification(authenticated_client, category):
    authenticated_client.post("/api/v1/items/", {"name": "X", "category": category.pk})

# Good — mock task dispatch; test that it is called, not what it does
@patch("myapp.views.send_notification_task.delay")
@pytest.mark.django_db
def test_create_dispatches_notification(mock_delay, authenticated_client, category):
    response = authenticated_client.post("/api/v1/items/", {"name": "X", "category": category.pk})
    assert response.status_code == 201
    mock_delay.assert_called_once()
```

## `force_authenticate` vs. Token Auth Misuse

```python
# Bad — full JWT token flow for every test; adds latency and coupling
@pytest.mark.django_db
def test_item_list(api_client, user):
    token = str(RefreshToken.for_user(user).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get("/api/v1/items/")

# Good — use force_authenticate for all tests except dedicated auth tests
@pytest.mark.django_db
def test_item_list(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 200
```

## Checklist for Django / DRF Test Code Review

- [ ] `@pytest.mark.django_db` applied to all tests that touch the database
- [ ] `APIClient` used for DRF view tests — not Django's built-in `Client`
- [ ] Both authenticated and unauthenticated paths tested for every protected endpoint
- [ ] Response structure verified beyond just the status code
- [ ] Data isolation and permission boundaries explicitly tested
- [ ] Serializer tests cover valid data, missing required fields, read-only field protection, and sensitive field exclusion
- [ ] N+1 queries checked for list endpoints using `CaptureQueriesContext`
- [ ] Celery tasks mocked in view tests — not dispatched for real
- [ ] `factory_boy` factories used for fixture data — not repeated inline `objects.create()` calls
- [ ] `force_authenticate` used for all tests except dedicated auth-flow tests
- [ ] `transaction=True` used only when testing `on_commit`, real transactions, or Celery dispatch — not for basic CRUD
- [ ] Signal side effects mocked or disconnected in tests that do not test signal behaviour
- [ ] `override_settings` used for settings-dependent tests — not direct `settings.X = Y` mutation

## Django 5.0 — `db_default` Requires `refresh_from_db()`

When a model field uses `db_default`, the Python instance does not reflect the value until refreshed.

```python
# Bad
@pytest.mark.django_db
def test_order_created_at_is_set(db):
    order = Order.objects.create(customer=UserFactory())
    assert order.created_at is not None  # May be None

# Good
@pytest.mark.django_db
def test_order_created_at_is_set(db):
    order = Order.objects.create(customer=UserFactory())
    order.refresh_from_db()
    assert order.created_at is not None
```

## Django 5.1 — `LoginRequiredMiddleware` Public View Tests

If `LoginRequiredMiddleware` is active, every `@login_not_required` view MUST have a test confirming public access.

```python
# Good
@pytest.mark.django_db
def test_health_check_accessible_without_authentication(api_client):
    response = api_client.get("/api/health/")
    assert response.status_code == 200
```

## Django 5.2 (LTS)

### Composite Primary Key Lookups in Tests

Models with composite PKs require all key fields in ORM lookups.

```python
# Bad — lookup by single PK column on composite-PK model
@pytest.mark.django_db
def test_membership_lookup(db):
    m = TenantMembershipFactory()
    found = TenantMembership.objects.get(pk=m.pk)

# Good — use all PK fields explicitly
@pytest.mark.django_db
def test_membership_lookup(db):
    m = TenantMembershipFactory()
    found = TenantMembership.objects.get(tenant_id=m.tenant_id, user_id=m.user_id)
    assert found == m
```

### Async Atomic Tests Require `transaction=True`

Tests for code using `transaction.aatomic()` (Django 5.2+) MUST use `transaction=True`.

```python
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_async_fund_transfer_is_atomic(db):
    sender = await sync_to_async(AccountFactory)(balance=100)
    receiver = await sync_to_async(AccountFactory)(balance=0)
    await transfer_funds(sender.pk, receiver.pk, 50)
    await sender.arefresh_from_db()
    await receiver.arefresh_from_db()
    assert sender.balance == 50
    assert receiver.balance == 50
```
