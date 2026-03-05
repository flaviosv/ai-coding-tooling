# Django Testing Guide

Applies to: Django projects using pytest and pytest-django.
Supported version range: Django 4.2 LTS (base) → Django 5.2 LTS (latest).

---

## General Django Testing Patterns

Conventions that apply across all still-supported Django versions (4.2–5.2).

### Setup

Install `pytest-django` and configure `pytest.ini` or `pyproject.toml`:

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = myproject.settings.test
addopts = -rafEX --strict-markers
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "myproject.settings.test"
addopts = "-rafEX --strict-markers"
```

### Database Access

Tests do not have database access by default. Mark tests that need it:

```python
import pytest

# Function-level: use the decorator
@pytest.mark.django_db
def test_item_creation():
    item = Item.objects.create(name="Test", category=category)
    assert item.pk is not None

# Class-level: mark the class so all methods share it
@pytest.mark.django_db
class TestItemModel:
    def test_str_returns_name(self, item):
        assert str(item) == item.name

# When the test exercises on_commit() callbacks, signals via transactions,
# or Celery task dispatch: use transaction=True
@pytest.mark.django_db(transaction=True)
def test_on_commit_callback_fires(user):
    with patch("myapp.signals.send_welcome_email") as mock_send:
        user.email_verified = True
        user.save()
    mock_send.assert_called_once()
```

### Fixtures — `conftest.py`

Define model fixtures in `conftest.py` to avoid repeated inline `objects.create()` calls:

```python
# tests/conftest.py
import pytest
from django.contrib.auth import get_user_model
from myapp.models import Category, Item

User = get_user_model()

@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="securepassword123",
    )

@pytest.fixture
def category(db):
    return Category.objects.create(name="Test Category")

@pytest.fixture
def item(db, category):
    return Item.objects.create(
        name="Test Item",
        category=category,
        is_active=True,
    )
```

### `factory_boy` for Flexible Fixtures

[factory_boy](https://factoryboy.readthedocs.io/) generates model instances with sensible defaults, reducing fixture boilerplate and making tests declare only what varies:

```bash
pip install factory_boy
```

```python
# tests/factories.py
import factory
from django.contrib.auth import get_user_model
from myapp.models import Category, Item

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "securepassword123")

class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Faker("word")

class ItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Item

    name = factory.Faker("sentence", nb_words=3)
    category = factory.SubFactory(CategoryFactory)
    is_active = True
```

```python
# Usage in tests — declare only what varies from defaults
@pytest.mark.django_db
def test_item_list_only_returns_active(authenticated_client):
    ItemFactory(is_active=True)
    ItemFactory(is_active=False)
    response = authenticated_client.get("/api/v1/items/")
    assert response.data["count"] == 1
```

### APIClient for DRF Views

Always use DRF's `APIClient` — not Django's built-in `Client` — for REST API tests:

```python
from rest_framework.test import APIClient
import pytest

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
```

Use `force_authenticate` for most tests. Test the actual JWT/session authentication flow separately when needed:

```python
from rest_framework_simplejwt.tokens import RefreshToken

@pytest.fixture
def jwt_token(user):
    return str(RefreshToken.for_user(user).access_token)

def test_jwt_authentication(api_client, jwt_token):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_token}")
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 200
```

### Testing ViewSets

Cover the full lifecycle: list, retrieve, create, update, delete, and edge cases for each:

```python
@pytest.mark.django_db
class TestItemViewSet:

    def test_list_returns_200_and_paginated_results(self, authenticated_client, item):
        response = authenticated_client.get("/api/v1/items/")
        assert response.status_code == 200
        assert "results" in response.data
        assert "count" in response.data

    def test_list_excludes_inactive_items(self, authenticated_client, category, db):
        active = ItemFactory(category=category, is_active=True)
        ItemFactory(category=category, is_active=False)
        response = authenticated_client.get("/api/v1/items/")
        ids = [str(r["id"]) for r in response.data["results"]]
        assert str(active.pk) in ids
        assert len(ids) == 1

    def test_create_returns_201_on_valid_data(self, authenticated_client, category):
        payload = {"name": "New Item", "category": category.pk}
        response = authenticated_client.post("/api/v1/items/", payload)
        assert response.status_code == 201
        assert response.data["name"] == "New Item"

    def test_create_returns_400_on_missing_name(self, authenticated_client, category):
        response = authenticated_client.post("/api/v1/items/", {"category": category.pk})
        assert response.status_code == 400
        assert "name" in response.data

    def test_list_returns_401_when_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/items/")
        assert response.status_code == 401
```

### Testing Serializers in Isolation

Test serializer validation and output without going through the HTTP layer:

```python
@pytest.mark.django_db
class TestItemSerializer:

    def test_valid_data_passes_validation(self, category):
        data = {"name": "Test Item", "category": category.pk}
        s = ItemSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_empty_name_fails_validation(self, category):
        data = {"name": "", "category": category.pk}
        s = ItemSerializer(data=data)
        assert not s.is_valid()
        assert "name" in s.errors

    def test_read_only_fields_not_writable(self, item):
        s = ItemSerializer(item, data={"id": "override", "name": item.name})
        s.is_valid()
        assert s.validated_data.get("id") is None

    def test_output_contains_expected_fields(self, item):
        s = ItemSerializer(item)
        assert "id" in s.data
        assert "name" in s.data
        assert "is_active" in s.data

    def test_output_excludes_sensitive_fields(self, user):
        s = UserSerializer(user)
        assert "password" not in s.data
```

### Detecting N+1 Queries

Use `CaptureQueriesContext` to assert fixed query counts in list views and serializers:

```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

@pytest.mark.django_db
def test_item_list_has_no_n_plus_1(authenticated_client, category, db):
    Item.objects.bulk_create([
        Item(name=f"Item {i}", category=category, is_active=True) for i in range(10)
    ])

    with CaptureQueriesContext(connection) as ctx:
        response = authenticated_client.get("/api/v1/items/")

    assert response.status_code == 200
    assert len(ctx.captured_queries) <= 3, (
        f"Too many queries ({len(ctx.captured_queries)}). "
        "Check for missing select_related/prefetch_related."
    )
```

### Testing Celery Tasks

Test task logic directly — do not run through the real Celery worker. Separate "task logic is correct" from "view dispatches task":

```python
from unittest.mock import patch

# Test what the task does
@pytest.mark.django_db
def test_notification_task_creates_notification(item):
    send_notification_task(item_id=item.pk, message="Hello")
    assert Notification.objects.filter(item=item).count() == 1

# Test that the view dispatches the task (not what the task does)
@patch("myapp.views.send_notification_task.delay")
@pytest.mark.django_db
def test_create_view_dispatches_notification_task(mock_delay, authenticated_client, category):
    payload = {"name": "New Item", "category": category.pk}
    response = authenticated_client.post("/api/v1/items/", payload)
    assert response.status_code == 201
    mock_delay.assert_called_once()
```

### `override_settings`

Scope settings changes to individual tests — never mutate `django.conf.settings` directly:

```python
from django.test import override_settings

@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_email_is_sent(user):
    from django.core import mail
    trigger_welcome_email(user)
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
def test_endpoint_works_without_cache(authenticated_client):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200
```

### Testing Management Commands

```python
from django.core.management import call_command
import io

@pytest.mark.django_db
def test_sync_products_command_outputs_synced(db):
    out = io.StringIO()
    call_command("sync_products", verbosity=2, stdout=out)
    assert "Synced" in out.getvalue()

@pytest.mark.django_db
def test_purge_expired_tokens_removes_expired_tokens(db):
    TokenFactory.create_batch(5, is_expired=True)
    TokenFactory.create_batch(3, is_expired=False)
    call_command("purge_expired_tokens")
    assert Token.objects.filter(is_expired=True).count() == 0
    assert Token.objects.filter(is_expired=False).count() == 3
```

### Testing Permission Boundaries

Always test that users can only access data they are authorized to see:

```python
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

---

## Django 4.2 (LTS — base version)

### Async View Testing

Django 4.2 supports async views. Test them with `pytest-asyncio` and Django's `async_client`:

```python
import pytest

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_async_item_list(async_client, user):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = str(RefreshToken.for_user(user).access_token)
    response = await async_client.get(
        "/api/v1/items/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 200
```

Note: async views require `transaction=True` because async tests run in a different thread from the test database transaction.

### `CONN_HEALTH_CHECKS` in Test Settings

Set `CONN_HEALTH_CHECKS=False` in test settings to avoid health-check overhead on the test database:

```python
# settings/test.py
DATABASES = {
    "default": {
        **DATABASES["default"],
        "CONN_MAX_AGE": 0,         # Fresh connection per test is fine
        "CONN_HEALTH_CHECKS": False,
    }
}
```

---

## Django 5.0

### `db_default` — Verify Database-Level Defaults in Tests

When models use `db_default` (database-level defaults), verify that fields are populated after `save()`:

```python
@pytest.mark.django_db
def test_order_created_at_is_set_by_database(db):
    order = Order.objects.create(customer=UserFactory())
    order.refresh_from_db()
    assert order.created_at is not None
```

---

## Django 5.1

### `LoginRequiredMiddleware` Testing

If `LoginRequiredMiddleware` is active, ensure views that should be public are annotated and tested:

```python
from django.views.decorators.login_required import login_not_required

# views.py
@login_not_required
def public_health_check(request):
    return JsonResponse({"status": "ok"})

# tests
@pytest.mark.django_db
def test_health_check_accessible_without_auth(api_client):
    response = api_client.get("/api/health/")
    assert response.status_code == 200
```

---

## Django 5.2 (LTS — latest version)

### Composite Primary Key Fixtures

Models with composite PKs require all PK fields to be specified in factories and fixtures:

```python
class TenantMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TenantMembership

    tenant_id = factory.Sequence(lambda n: n + 1)
    user_id = factory.SubFactory(UserFactory, _id_only=True)

@pytest.mark.django_db
def test_tenant_membership_lookup(db):
    membership = TenantMembershipFactory()
    found = TenantMembership.objects.get(
        tenant_id=membership.tenant_id,
        user_id=membership.user_id,
    )
    assert found == membership
```

### Async Atomic Transactions in Tests

When testing code that uses `transaction.aatomic()` (Django 5.2+), use `transaction=True`:

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

- [pytest-django Documentation](https://pytest-django.readthedocs.io/en/latest/)
- [factory_boy Documentation](https://factoryboy.readthedocs.io/en/stable/)
- [Django Testing Tools](https://docs.djangoproject.com/en/stable/topics/testing/tools/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [CaptureQueriesContext](https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.utils.CaptureQueriesContext)
- [Django Async Support](https://docs.djangoproject.com/en/stable/topics/async/)
- [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/)
- [Django 5.2 Release Notes](https://docs.djangoproject.com/en/5.2/releases/5.2/)
