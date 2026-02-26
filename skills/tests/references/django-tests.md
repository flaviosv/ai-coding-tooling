# Django Testing Guide (pytest-django)

Applies to: Django projects using pytest and pytest-django.

---

## Setup

Install `pytest-django` and configure `pytest.ini` (or `pyproject.toml`):

```ini
[pytest]
DJANGO_SETTINGS_MODULE = myproject.settings.test
addopts = -rafEX
```

---

## Database Access

Tests do not have database access by default. Mark tests that need it:

```python
import pytest

@pytest.mark.django_db
def test_item_creation():
    item = Item.objects.create(name="Test", category=category)
    assert item.pk is not None

# Use the db fixture as an alternative
def test_with_db_fixture(db):
    ...

# For tests that require real transactions
@pytest.mark.django_db(transaction=True)
def test_with_transactions():
    ...
```

---

## APIClient for DRF Views

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

@pytest.mark.django_db
def test_item_list(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200
    assert len(response.data["results"]) == 1
```

---

## Model Fixtures

Define model fixtures in `conftest.py` to avoid repeated setup across tests:

```python
# conftest.py
import pytest
from myapp.models import User, Category, Item

@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
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

---

## Testing ViewSets

```python
@pytest.mark.django_db
class TestItemViewSet:

    def test_list_returns_200(self, authenticated_client, item):
        response = authenticated_client.get("/api/v1/items/")
        assert response.status_code == 200

    def test_list_excludes_inactive_items(self, authenticated_client, category, db):
        active = Item.objects.create(name="Active", category=category, is_active=True)
        inactive = Item.objects.create(name="Inactive", category=category, is_active=False)
        response = authenticated_client.get("/api/v1/items/")
        ids = [i["id"] for i in response.data["results"]]
        assert str(active.pk) in ids
        assert str(inactive.pk) not in ids

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

---

## Testing Serializers

```python
@pytest.mark.django_db
class TestItemSerializer:

    def test_valid_data_passes_validation(self, category):
        data = {"name": "Test Item", "category": category.pk}
        serializer = ItemSerializer(data=data)
        assert serializer.is_valid()

    def test_empty_name_fails_validation(self, category):
        data = {"name": "", "category": category.pk}
        serializer = ItemSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_output_contains_expected_fields(self, item):
        serializer = ItemSerializer(item)
        assert "id" in serializer.data
        assert "name" in serializer.data
        assert "is_active" in serializer.data
```

---

## factory_boy for Model Fixtures

[factory_boy](https://factoryboy.readthedocs.io/) generates model instances with sensible defaults, reducing fixture boilerplate:

```bash
pip install factory_boy
```

```python
# tests/factories.py
import factory
from myapp.models import User, Category, Item

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")

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

Usage in tests — cleaner than inline `.objects.create()`:

```python
@pytest.mark.django_db
def test_item_list_only_returns_active(authenticated_client):
    ItemFactory(is_active=True)
    ItemFactory(is_active=False)
    response = authenticated_client.get("/api/v1/items/")
    assert len(response.data["results"]) == 1
```

---

## override_settings

Use `@override_settings` for tests that need specific Django settings without modifying the test settings file:

```python
from django.test import override_settings

@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_email_sent(user):
    from django.core import mail
    trigger_welcome_email(user)
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
def test_feature_without_cache(authenticated_client):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200
```

---

## Testing Management Commands

```python
from django.core.management import call_command
import io

@pytest.mark.django_db
def test_sync_products_command():
    out = io.StringIO()
    call_command("sync_products", verbosity=2, stdout=out)
    assert "Synced" in out.getvalue()

@pytest.mark.django_db
def test_purge_expired_tokens_command():
    ExpiredTokenFactory.create_batch(5)
    call_command("purge_expired_tokens")
    assert Token.objects.filter(is_expired=True).count() == 0
```

---

## Testing Async Views (Django 4.1+)

```python
import pytest

@pytest.mark.django_db(transaction=True)  # async views need real transactions
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

---

## Testing Celery Tasks

```python
from unittest.mock import patch

# Test task logic directly — don't run through the real Celery worker
@pytest.mark.django_db
def test_notification_task_creates_record(item):
    send_notification_task(item_id=item.pk, message="Test")
    assert Notification.objects.filter(item=item).count() == 1

# Test that a view triggers the task (not what the task does)
@patch("myapp.views.send_notification_task.delay")
def test_view_triggers_notification_task(mock_task, authenticated_client, item):
    authenticated_client.post(f"/api/v1/items/{item.pk}/notify/")
    mock_task.assert_called_once_with(item.pk)
```

---

## Detecting N+1 Queries

```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

@pytest.mark.django_db
def test_item_list_has_no_n_plus_1(authenticated_client, category, db):
    Item.objects.bulk_create([
        Item(name=f"Item {i}", category=category) for i in range(10)
    ])

    with CaptureQueriesContext(connection) as ctx:
        response = authenticated_client.get("/api/v1/items/")

    assert response.status_code == 200
    assert len(ctx.captured_queries) <= 3, (
        f"Too many queries ({len(ctx.captured_queries)}). "
        "Check for missing select_related/prefetch_related."
    )
```

---

## Authentication Patterns

```python
# Option 1: force_authenticate — recommended for unit/integration tests
api_client.force_authenticate(user=user)

# Option 2: JWT token — use when testing the authentication flow itself
from rest_framework_simplejwt.tokens import RefreshToken

@pytest.fixture
def jwt_token(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def test_with_jwt(api_client, jwt_token):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_token}")
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 200
```

---

## Resources

- [factory_boy Documentation](https://factoryboy.readthedocs.io/en/stable/)
- [pytest-django Documentation](https://pytest-django.readthedocs.io/en/latest/)
- [Django Testing Tools](https://docs.djangoproject.com/en/stable/topics/testing/tools/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [CaptureQueriesContext](https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.utils.CaptureQueriesContext)
- [Django Test Database](https://docs.djangoproject.com/en/stable/topics/testing/overview/#the-test-database)
- [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/)
