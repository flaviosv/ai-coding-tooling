# Django / DRF Test Code Review Guide

Supplements `test-review-checklist.md` and `python-tests-code-review.md` for projects using Django and Django REST Framework.

---

## DRF-Specific Review Points

### ❌ Using Django's Client Instead of APIClient

```python
# Bad — Django's test Client may not handle DRF content negotiation correctly
from django.test import Client

def test_item_list():
    client = Client()
    response = client.get("/api/v1/items/")

# Good
from rest_framework.test import APIClient

def test_item_list(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 200
```

### ❌ Missing `@pytest.mark.django_db`

```python
# Bad — will raise RuntimeError at runtime without the marker
def test_item_creation():
    item = Item.objects.create(name="Test", ...)

# Good
@pytest.mark.django_db
def test_item_creation():
    item = Item.objects.create(name="Test", ...)
    assert item.pk is not None
```

### ❌ Not Testing the Unauthenticated Path

```python
# Bad — only testing authenticated access
def test_item_list(authenticated_client):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200
# Missing: unauthenticated requests should return 401

# Good — test both
def test_item_list_returns_200_when_authenticated(authenticated_client):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200

def test_item_list_returns_401_when_unauthenticated(api_client):
    response = api_client.get("/api/v1/items/")
    assert response.status_code == 401
```

### ❌ Only Checking Status Code

```python
# Bad — status code alone doesn't verify the response payload
def test_item_list(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200

# Good — verify the response structure and content
def test_item_list(authenticated_client, item):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200
    assert "results" in response.data
    assert "count" in response.data
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["name"] == item.name
```

### ❌ Not Testing Permission Isolation

```python
# Bad — not verifying that users can only access their own data
def test_item_list(authenticated_client):
    response = authenticated_client.get("/api/v1/items/")
    assert response.status_code == 200

# Good — verify data isolation between users/tenants
def test_item_list_only_returns_own_items(
    api_client, user_a, user_b, item_for_a, item_for_b
):
    api_client.force_authenticate(user=user_a)
    response = api_client.get("/api/v1/items/")
    ids = [i["id"] for i in response.data["results"]]
    assert str(item_for_a.pk) in ids
    assert str(item_for_b.pk) not in ids
```

---

## Serializer Tests

What to verify when reviewing serializer tests:

```python
class TestItemSerializer:

    def test_valid_data_passes_validation(self, category):
        data = {"name": "Valid Item", "category": category.pk}
        s = ItemSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_missing_required_field_fails_validation(self, category):
        data = {"category": category.pk}  # missing name
        s = ItemSerializer(data=data)
        assert not s.is_valid()
        assert "name" in s.errors

    def test_read_only_fields_cannot_be_written(self, item):
        s = ItemSerializer(item, data={"id": "override", "name": item.name})
        s.is_valid()
        assert s.validated_data.get("id") is None

    def test_output_excludes_sensitive_fields(self, item):
        s = ItemSerializer(item)
        assert "password" not in s.data
        assert "secret_key" not in s.data
```

---

## N+1 Query Detection

List endpoints must always be checked for N+1 queries:

```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

@pytest.mark.django_db
def test_item_list_query_count_is_fixed(authenticated_client, category, db):
    Item.objects.bulk_create([
        Item(name=f"Item {i}", category=category) for i in range(20)
    ])

    with CaptureQueriesContext(connection) as ctx:
        response = authenticated_client.get("/api/v1/items/")

    assert response.status_code == 200
    assert len(ctx.captured_queries) <= 5, (
        f"Too many queries ({len(ctx.captured_queries)}). "
        "Check for missing select_related/prefetch_related."
    )
```

---

## factory_boy Review

### ❌ Repeated Inline `objects.create()` Calls

```python
# Bad — fixture data duplicated across multiple test files
@pytest.mark.django_db
def test_item_list(authenticated_client):
    category = Category.objects.create(name="Cat")
    item = Item.objects.create(name="Item", category=category, is_active=True)
    # repeated in every test file

# Good — factory in conftest.py; tests declare only what varies
@pytest.mark.django_db
def test_item_list(authenticated_client):
    ItemFactory(is_active=True)
    response = authenticated_client.get("/api/v1/items/")
    assert response.data["count"] == 1
```

---

## `transaction=True` Misuse

### ❌ Using `transaction=True` When Not Needed

`@pytest.mark.django_db(transaction=True)` disables transaction wrapping and resets the DB between tests by truncating tables — it is **much slower**:

```python
# Bad — transaction=True used for a simple CRUD test; no transaction logic needed
@pytest.mark.django_db(transaction=True)
def test_item_creation():
    item = Item.objects.create(name="Test")
    assert item.pk is not None

# Good — use transaction=True only when the test involves:
# - on_commit() callbacks
# - LISTEN/NOTIFY (PostgreSQL)
# - Celery task dispatch with CELERY_TASK_ALWAYS_EAGER=True
# - Raw SAVEPOINT / rollback logic
@pytest.mark.django_db(transaction=True)
def test_on_commit_signal_fires(user):
    with patch("myapp.signals.send_welcome_email") as mock_send:
        # on_commit only fires after a real transaction commit
        user.email_verified = True
        user.save()
    mock_send.assert_called_once()
```

---

## Testing Signals

### ❌ Not Isolating Signal Side Effects

```python
# Bad — signal fires real email during test
@pytest.mark.django_db
def test_user_creation():
    user = User.objects.create_user(email="alice@example.com", password="pass")
    # post_save signal fires → sends real welcome email

# Good — disconnect the signal for the test or mock its receiver
from unittest.mock import patch

@pytest.mark.django_db
def test_user_creation_does_not_block_on_email():
    with patch("myapp.signals.send_welcome_email") as mock_send:
        user = User.objects.create_user(email="alice@example.com", password="pass")
    mock_send.assert_called_once_with(user)

# Alternative — disconnect by receiver reference
from django.test.utils import disconnect_signal

@pytest.mark.django_db
def test_user_creation_without_signal(settings):
    from myapp.signals import send_welcome_email
    from django.db.models.signals import post_save
    post_save.disconnect(send_welcome_email, sender=User)
    try:
        user = User.objects.create_user(email="alice@example.com", password="pass")
        assert user.pk is not None
    finally:
        post_save.connect(send_welcome_email, sender=User)
```

---

## `override_settings` Review

### ❌ Not Using `override_settings` for Settings-Dependent Tests

```python
# Bad — test modifies django.conf.settings directly; leaks into other tests
from django.conf import settings
settings.FEATURE_X_ENABLED = True

# Good — override_settings scopes the change to the test
from django.test import override_settings

@pytest.mark.django_db
@override_settings(FEATURE_X_ENABLED=True)
def test_feature_x_behaviour(authenticated_client):
    response = authenticated_client.get("/api/v1/feature-x/")
    assert response.status_code == 200
```

---

## Checklist for Django / DRF Tests

- [ ] `@pytest.mark.django_db` applied to all tests that touch the database
- [ ] `APIClient` used for DRF view tests — not Django's built-in `Client`
- [ ] Both authenticated **and** unauthenticated paths are tested
- [ ] Response structure verified beyond just the status code
- [ ] Data isolation / permission boundaries tested where applicable
- [ ] Serializer validation tested with both valid and invalid data
- [ ] Read-only fields verified as non-writable
- [ ] N+1 queries checked for list endpoints using `CaptureQueriesContext`
- [ ] Celery tasks mocked in view tests — not executed for real
- [ ] Model fixtures used for setup — avoid repeated `.objects.create()` calls inline
- [ ] `force_authenticate` used for most tests; JWT token flow tested separately only when needed
- [ ] `factory_boy` factories used for fixture data — not repeated inline `objects.create()` calls
- [ ] `transaction=True` used only when testing `on_commit`, Celery dispatch, or real transaction logic
- [ ] Signal side effects mocked or disconnected in tests that don't test signal behaviour
- [ ] `override_settings` used for settings-dependent tests — not direct `settings.X = Y`

---

## Resources

- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [pytest-django](https://pytest-django.readthedocs.io/en/latest/)
- [Django Testing Tools](https://docs.djangoproject.com/en/stable/topics/testing/tools/)
- [CaptureQueriesContext](https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.utils.CaptureQueriesContext)
