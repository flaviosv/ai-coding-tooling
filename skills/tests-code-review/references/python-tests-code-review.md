# Python Test Code Review Guide

Supplements `test-review-checklist.md` for Python projects using pytest.

---

## Test Structure Anti-Patterns

### ❌ No Assertions

```python
# Bad — test passes but verifies nothing
def test_create_item():
    item = Item(name="Test")
    item.save()
    # No assertion!

# Good
def test_create_item():
    item = Item(name="Test")
    item.save()
    assert item.pk is not None
    assert item.name == "Test"
```

### ❌ Too Many Assertions in One Test

```python
# Bad — hard to know what failed when the test breaks
def test_item():
    item = create_item()
    assert item.name == "Test"
    assert item.is_active is True
    assert item.category is not None
    response = get_item_api(item.pk)
    assert response.status_code == 200
    assert response.data["name"] == "Test"
    # ...10 more assertions

# Good — one behaviour per test
def test_item_creation_sets_active_by_default():
    item = Item(name="Test")
    item.save()
    assert item.is_active is True

def test_item_api_returns_correct_name(api_client, item):
    response = api_client.get(f"/api/v1/items/{item.pk}/")
    assert response.data["name"] == item.name
```

### ❌ Non-Descriptive Test Names

```python
# Bad
def test_1():
def test_item_ok():
def test_works():

# Good — name describes scenario and expected outcome
def test_item_list_returns_empty_when_no_items_exist():
def test_serializer_raises_validation_error_on_empty_name():
def test_auth_returns_401_with_expired_token():
```

### ❌ Testing Implementation, Not Behaviour

```python
# Bad — testing internal detail
def test_item_uses_manager():
    assert hasattr(Item, "_default_manager")

# Good — testing observable behaviour
def test_active_items_query_excludes_inactive():
    Item.objects.create(name="Active", is_active=True, ...)
    Item.objects.create(name="Inactive", is_active=False, ...)
    results = Item.objects.active()
    assert all(i.is_active for i in results)
```

### ❌ Shared Mutable State

```python
# Bad — test results depend on execution order
items = []

def test_add_item():
    items.append(Item(name="Test"))
    assert len(items) == 1

def test_item_list():
    assert len(items) == 0  # Fails if test_add_item ran first

# Good — use fixtures with function scope
@pytest.fixture
def items():
    return []

def test_add_item(items):
    items.append(create_item())
    assert len(items) == 1
```

---

## Mock Anti-Patterns

### ❌ Mocking the Thing Under Test

```python
# Bad — mocking the code you're trying to test makes the test useless
@patch("myapp.serializers.ItemSerializer.validate")
def test_item_serializer_validates(mock_validate):
    mock_validate.return_value = {}
    # This test proves nothing about ItemSerializer

# Good — mock external dependencies only
@patch("myapp.services.send_email")
def test_item_creation_sends_email(mock_send_email):
    create_item_and_notify()
    mock_send_email.assert_called_once()
```

### ❌ Over-Mocking

```python
# Bad — mocking the ORM makes the test brittle and meaningless
@patch("myapp.models.Item.objects.create")
@patch("myapp.models.Item.objects.filter")
@patch("myapp.serializers.ItemSerializer.is_valid")
def test_create_item(mock_valid, mock_filter, mock_create):
    # Not testing anything real

# Good — use real DB for integration tests
@pytest.mark.django_db
def test_create_item_integration(authenticated_client, category):
    response = authenticated_client.post("/api/v1/items/", {"name": "Test", ...})
    assert response.status_code == 201
    assert Item.objects.filter(name="Test").exists()
```

---

## Parametrize Review

### ❌ Poorly Named Parametrize Cases

```python
# Bad — when a case fails, the output is hard to read
@pytest.mark.parametrize("data,expected", [
    ({}, 400),
    ({"name": ""}, 400),
    ({"name": "Valid"}, 201),
])
def test_create(data, expected):
    ...

# Good — use pytest.param with IDs
@pytest.mark.parametrize("data,expected", [
    pytest.param({}, 400, id="missing-all-fields"),
    pytest.param({"name": ""}, 400, id="empty-name"),
    pytest.param({"name": "Valid", "category": 1}, 201, id="valid-data"),
])
def test_create(data, expected):
    ...
```

---

## Async Test Anti-Patterns

### ❌ Using `MagicMock` for Async Functions

```python
# Bad — MagicMock is not awaitable; will raise "object MagicMock is not awaitable"
mock_fetch = MagicMock(return_value={"id": 1})

async def test_async_service():
    result = await my_service(mock_fetch)  # TypeError at runtime

# Good — AsyncMock for coroutines
from unittest.mock import AsyncMock

mock_fetch = AsyncMock(return_value={"id": 1})

async def test_async_service():
    result = await my_service(mock_fetch)
    assert result["id"] == 1
```

### ❌ Not Testing Async Cancellation

```python
# Good — test that cancellation is handled cleanly
import asyncio

async def test_long_operation_cancels_cleanly():
    task = asyncio.create_task(long_running_operation())
    await asyncio.sleep(0)  # allow task to start
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
```

---

## Float Comparison

### ❌ Direct Float Equality

```python
# Bad — floating-point representation errors cause intermittent failures
assert calculate_tax(100.0) == 8.5

# Good — pytest.approx with appropriate tolerance
assert calculate_tax(100.0) == pytest.approx(8.5, rel=1e-6)

# Good — absolute tolerance for small values
assert vector_length(3.0, 4.0) == pytest.approx(5.0, abs=1e-9)
```

---

## Fixture Scope Anti-Patterns

### ❌ Module/Session Scope for Mutable Fixtures

```python
# Bad — session-scoped fixture is shared and can be mutated across tests
@pytest.fixture(scope="session")
def user_data():
    return {"name": "Alice", "role": "admin"}  # mutable dict — any test can modify it

# Good — function scope for mutable state (default)
@pytest.fixture
def user_data():
    return {"name": "Alice", "role": "admin"}  # fresh dict per test

# session scope is appropriate for expensive read-only resources
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DB_URL)
    yield engine
    engine.dispose()
```

---

## Checklist for Python Tests

- [ ] Test has at least one meaningful assertion
- [ ] Test name describes the scenario and expected outcome
- [ ] Arrange-Act-Assert structure is visible
- [ ] One concept is being tested per function
- [ ] Only external dependencies are mocked — not the code under test
- [ ] No shared mutable state between tests
- [ ] Fixtures used for setup instead of repeated code
- [ ] `@pytest.mark.parametrize` used for 3+ similar test cases
- [ ] Exceptions tested with `pytest.raises`
- [ ] Test is deterministic — no random values, no `time.sleep`
- [ ] `X | Y` union syntax used in test helper type signatures — not `Optional[X]` (Python 3.10+)
- [ ] `ExceptionGroup` asserted when testing code that uses `asyncio.TaskGroup` (Python 3.11+)
- [ ] `@override` applied to intentional test base class method overrides (Python 3.12+)
- [ ] `itertools.batched()` used in batch-test assertions — not manual slice arithmetic (Python 3.12+)
- [ ] `copy.replace()` used to build test payload variants — not repeated literal dicts (Python 3.13+)
- [ ] `AsyncMock` used for async function mocks — not `MagicMock`
- [ ] Float comparisons use `pytest.approx` — not `==`
- [ ] Session/module-scoped fixtures are read-only — mutable fixtures use function scope

---

## Python Version-Specific Test Review Points

### Python 3.10+ Review

#### ❌ Using `Optional[X]` Instead of `X | None` in Test Signatures

```python
# Bad — verbose legacy syntax in test helpers
from typing import Optional

def make_item(name: Optional[str] = None) -> Item:
    return Item(name=name or "Default")

# Good — union syntax (Python 3.10+)
def make_item(name: str | None = None) -> Item:
    return Item(name=name or "Default")
```

#### ❌ Long `if/elif` Chains in Test Dispatch Helpers

```python
# Bad — repeated condition checks in test helpers
def get_expected_status(action: str) -> int:
    if action == "create":
        return 201
    elif action == "delete":
        return 204
    elif action == "update":
        return 200
    else:
        return 400

# Good — structural pattern matching (Python 3.10+)
def get_expected_status(action: str) -> int:
    match action:
        case "create": return 201
        case "delete": return 204
        case "update": return 200
        case _: return 400
```

### Python 3.11+ Review

#### ❌ Not Testing ExceptionGroups When Using asyncio.TaskGroup

```python
# Bad — only catches one exception; TaskGroup raises ExceptionGroup
with pytest.raises(ValueError):
    async with asyncio.TaskGroup() as tg:
        tg.create_task(fail_with_value_error())
        tg.create_task(fail_with_runtime_error())

# Good — assert ExceptionGroup containing all expected exceptions
with pytest.raises(ExceptionGroup) as exc_info:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(fail_with_value_error())
        tg.create_task(fail_with_runtime_error())

errors = exc_info.value.exceptions
assert any(isinstance(e, ValueError) for e in errors)
assert any(isinstance(e, RuntimeError) for e in errors)
```

### Python 3.12+ Review

#### ❌ Missing `@override` on Test Base Class Method Overrides

```python
# Bad — typo silently creates a new method; the intended override never runs
class SpecificTestCase(BaseTestCase):
    def setup_fixutres(self) -> None:  # typo: "fixutres"
        self.item = Item(name="Test")

# Good — @override catches this at type-check time
from typing import override

class SpecificTestCase(BaseTestCase):
    @override
    def setup_fixtures(self) -> None:  # type checker errors if parent method doesn't exist
        self.item = Item(name="Test")
```

#### ❌ Manual Chunking Instead of `itertools.batched()`

```python
# Bad — manual slice arithmetic in batch-processing tests
def test_bulk_import(mock_processor):
    records = list(range(250))
    bulk_import(records, batch_size=100)
    expected_batches = [records[i:i+100] for i in range(0, len(records), 100)]
    assert mock_processor.call_count == len(expected_batches)

# Good — itertools.batched() is clearer and less error-prone (Python 3.12+)
from itertools import batched

def test_bulk_import(mock_processor):
    records = list(range(250))
    bulk_import(records, batch_size=100)
    assert mock_processor.call_count == len(list(batched(records, 100)))
```

### Python 3.13+ Review

#### ❌ Repeated Dict Literals Instead of `copy.replace()` for Test Variants

```python
# Bad — repeated construction with minor variations
def test_admin_creation():
    create_user({"name": "Alice", "email": "alice@example.com", "role": "admin"})

def test_regular_creation():
    create_user({"name": "Alice", "email": "alice@example.com", "role": "user"})

# Good — copy.replace() makes the variation explicit (Python 3.13+)
from copy import replace
from dataclasses import dataclass

@dataclass
class UserPayload:
    name: str
    email: str
    role: str = "user"

BASE = UserPayload(name="Alice", email="alice@example.com")

def test_admin_creation():
    create_user(replace(BASE, role="admin"))

def test_regular_creation():
    create_user(BASE)
```

---

## Resources

- [pytest Documentation](https://docs.pytest.org/en/stable/)
- [pytest Anti-patterns](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [pytest.mark.parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [Python 3.10 What's New](https://docs.python.org/3/whatsnew/3.10.html)
- [Python 3.11 What's New](https://docs.python.org/3/whatsnew/3.11.html)
- [Python 3.12 What's New](https://docs.python.org/3/whatsnew/3.12.html)
- [Python 3.13 What's New](https://docs.python.org/3/whatsnew/3.13.html)
