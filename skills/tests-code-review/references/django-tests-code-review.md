# Django Test Code Review Reference

Supplements `test-review-checklist.md` for projects using Django and Django REST Framework.
Supported version range: Django 4.2 LTS (base) → Django 5.2 LTS (latest).

---

## General Django Test Anti-Patterns

Patterns that apply across all still-supported Django versions (4.2–5.2).

### Missing `@pytest.mark.django_db`

```python
# Bad — raises RuntimeError at runtime; no marker means no database access
def test_item_creation():
    item = Item.objects.create(name="Test")  # RuntimeError

# Good
@pytest.mark.django_db
def test_item_creation():
    item = Item.objects.create(name="Test")
    assert item.pk is not None
```

### Using Django's `Client` Instead of `APIClient` for DRF Views

```python
# Bad — Django's test Client may not handle DRF content negotiation,
# authentication headers, or JSON response parsing correctly
from django.test import Client

def test_item_list():
    client = Client()
    response = client.get("/api/v1/items/")

# Good
from rest_framework.test import APIClient

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

```python
# Bad — a 200 with wrong data is a broken test that passes
@pytest.mark.django_db
def test_item_list(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200  # Says nothing about correctness

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

Every protected endpoint must have a test verifying that unauthenticated requests are rejected:

```python
# Bad — only testing the happy path; unauthenticated access is untested
@pytest.mark.django_db
def test_item_list(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200

# Good — test both sides
@pytest.mark.django_db
def test_item_list_requires_authentication(api_client):
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 401
```

### Not Testing Data Isolation / Permission Boundaries

```python
# Bad — not verifying that user A cannot see user B's data
@pytest.mark.django_db
def test_item_list(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200

# Good — verify data isolation between users
@pytest.mark.django_db
def test_item_list_only_returns_own_items(api_client, db):
    user_a = UserFactory()
    user_b = UserFactory()
    item_a = ItemFactory(owner=user_a)
    ItemFactory(owner=user_b)  # Should not appear in user_a's response

    api_client.force_authenticate(user=user_a)
    response = api_client.get("/api/v1/items/")

    ids = [str(r["id"]) for r in response.data["results"]]
    assert str(item_a.pk) in ids
    assert len(ids) == 1
```

### Repeated Inline `objects.create()` Calls

```python
# Bad — fixture data duplicated across test files; hard to maintain
@pytest.mark.django_db
def test_item_list(authenticated_client):
    category = Category.objects.create(name="Cat")
    item = Item.objects.create(name="Item", category=category, is_active=True)
    response = authenticated_client.get("/api/v1/items/")
    assert response.data["count"] == 1

# Good — factory_boy factory; tests declare only what varies
@pytest.mark.django_db
def test_item_list(authenticated_client):
    ItemFactory(is_active=True)
    response = authenticated_client.get("/api/v1/items/")
    assert response.data["count"] == 1
```

---

## Serializer Test Review Points

### Missing Validation Coverage

Every serializer test must cover both the valid path and the key invalid paths:

```python
class TestItemSerializer:

    # Required: valid data passes
    def test_valid_data_passes_validation(self, category):
        s = ItemSerializer(data={"name": "Test", "category": category.pk})
        assert s.is_valid(), s.errors

    # Required: missing required field fails
    def test_missing_name_fails_validation(self, category):
        s = ItemSerializer(data={"category": category.pk})
        assert not s.is_valid()
        assert "name" in s.errors

    # Required: read-only fields cannot be written
    def test_read_only_id_field_not_writable(self, item):
        s = ItemSerializer(item, data={"id": "spoofed-id", "name": item.name})
        s.is_valid()
        assert s.validated_data.get("id") is None

    # Required: sensitive fields absent from output
    def test_output_excludes_password(self, user):
        s = UserSerializer(user)
        assert "password" not in s.data
```

---

## N+1 Query Detection

List endpoints must always be checked for N+1 queries. A test that does not verify query count will silently allow N+1 regressions:

```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

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

Flag any list endpoint test that does not include a `CaptureQueriesContext` assertion as P1 — the missing check guarantees N+1 regressions will go undetected.

---

## `transaction=True` Misuse

`@pytest.mark.django_db(transaction=True)` disables transaction wrapping and resets the database between tests by truncating tables — it is significantly slower than the default mode.

```python
# Bad — transaction=True for a simple CRUD test that has no transaction logic
@pytest.mark.django_db(transaction=True)
def test_item_creation():
    item = Item.objects.create(name="Test")
    assert item.pk is not None

# Good — use transaction=True only when the test requires it
# Legitimate uses:
# - on_commit() callbacks (they never fire without a real commit)
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

Flag `transaction=True` usage that does not involve one of the above scenarios as a P1 finding — it slows the test suite without benefit.

---

## Signal Side Effects Not Isolated

```python
# Bad — signal fires a real email during the test; test is slow, fragile, or impure
@pytest.mark.django_db
def test_user_creation():
    user = User.objects.create_user(email="alice@example.com", password="pass")
    # post_save signal fires → sends real welcome email

# Good — mock the receiver to isolate the test
from unittest.mock import patch

@pytest.mark.django_db
def test_user_creation_does_not_block_on_email():
    with patch("myapp.signals.send_welcome_email") as mock_send:
        user = User.objects.create_user(email="alice@example.com", password="pass")
    mock_send.assert_called_once_with(user)

# Alternative — disconnect the signal for the duration of the test
from django.db.models.signals import post_save

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

---

## `override_settings` Misuse

```python
# Bad — mutates global settings; leaks into other tests that run in the same process
from django.conf import settings
settings.FEATURE_X_ENABLED = True

# Good — scoped change that resets automatically after the test
from django.test import override_settings

@pytest.mark.django_db
@override_settings(FEATURE_X_ENABLED=True)
def test_feature_x_is_active(authenticated_client):
    response = authenticated_client.get("/api/v1/feature-x/")
    assert response.status_code == 200
```

---

## Celery Task Test Isolation

```python
# Bad — dispatches a real Celery task in a view test; flaky without a worker running
@pytest.mark.django_db
def test_create_dispatches_notification(authenticated_client, category):
    authenticated_client.post("/api/v1/items/", {"name": "X", "category": category.pk})
    # relies on a live Celery worker to complete the task

# Good — mock the task dispatch; test that it is called, not what it does
from unittest.mock import patch

@patch("myapp.views.send_notification_task.delay")
@pytest.mark.django_db
def test_create_dispatches_notification(mock_delay, authenticated_client, category):
    response = authenticated_client.post("/api/v1/items/", {"name": "X", "category": category.pk})
    assert response.status_code == 201
    mock_delay.assert_called_once()
```

---

## `force_authenticate` vs. Token Auth Misuse

```python
# Bad — using full JWT token flow for every test; adds latency and coupling
@pytest.mark.django_db
def test_item_list(api_client, user):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = str(RefreshToken.for_user(user).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 200

# Good — use force_authenticate for all tests except those that test auth itself
@pytest.mark.django_db
def test_item_list(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 200
```

Only test the JWT token flow in dedicated authentication tests.

---

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

---

## Django 4.2 — Specific Review Points

No review-specific anti-patterns unique to 4.2 beyond the general section above.

---

## Django 5.0

### `db_default` — `refresh_from_db()` Required

When a model field uses `db_default` (database-level default), the Python instance does not reflect the value until refreshed. Tests that check the field value without refreshing will fail or produce stale data:

```python
# Bad — created_at may be unset on the Python object
@pytest.mark.django_db
def test_order_created_at_is_set(db):
    order = Order.objects.create(customer=UserFactory())
    assert order.created_at is not None  # May be None on the Python object

# Good — refresh to read the database-set value
@pytest.mark.django_db
def test_order_created_at_is_set(db):
    order = Order.objects.create(customer=UserFactory())
    order.refresh_from_db()
    assert order.created_at is not None
```

---

## Django 5.1

### `LoginRequiredMiddleware` — Public Views Must Have Tests

If `LoginRequiredMiddleware` is active, every view decorated with `@login_not_required` must have a test confirming public access:

```python
# Bad — no test for unauthenticated access to a view decorated @login_not_required

# Good
@pytest.mark.django_db
def test_health_check_accessible_without_authentication(api_client):
    response = api_client.get("/api/health/")
    assert response.status_code == 200
```

---

## Django 5.2 (LTS — latest version)

### Composite Primary Key Lookups in Tests

Models with composite PKs require all key fields in ORM lookups. Tests that look up by a single field will raise an error or return unexpected results:

```python
# Bad — lookup by a single PK column on a composite-PK model
@pytest.mark.django_db
def test_membership_lookup(db):
    m = TenantMembershipFactory()
    found = TenantMembership.objects.get(pk=m.pk)  # pk is ambiguous on composite models

# Good — use all PK fields explicitly
@pytest.mark.django_db
def test_membership_lookup(db):
    m = TenantMembershipFactory()
    found = TenantMembership.objects.get(tenant_id=m.tenant_id, user_id=m.user_id)
    assert found == m
```

### Async Atomic Tests Require `transaction=True`

Tests for code using `transaction.aatomic()` (Django 5.2+) must use `transaction=True`:

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

---

## Resources

- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [pytest-django](https://pytest-django.readthedocs.io/en/latest/)
- [Django Testing Tools](https://docs.djangoproject.com/en/stable/topics/testing/tools/)
- [CaptureQueriesContext](https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.utils.CaptureQueriesContext)
- [factory_boy](https://factoryboy.readthedocs.io/en/stable/)
- [Django 5.0 Release Notes](https://docs.djangoproject.com/en/5.0/releases/5.0/)
- [Django 5.1 Release Notes](https://docs.djangoproject.com/en/5.1/releases/5.1/)
- [Django 5.2 Release Notes](https://docs.djangoproject.com/en/5.2/releases/5.2/)
