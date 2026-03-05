# Python Reference — tests-code-review

Supplements `test-review-checklist.md` for Python projects using pytest.

---

<!-- General section covers conventions that apply across ALL still-supported Python versions (3.9–3.14) -->
## General Python Test Anti-Patterns

### No Assertions

```python
# Bad — test passes but verifies nothing
def test_create_item() -> None:
    item = Item(name="Test")
    item.save()
    # No assertion!

# Good
def test_create_item() -> None:
    item = Item(name="Test")
    item.save()
    assert item.pk is not None
    assert item.name == "Test"
```

### Too Many Assertions in One Test

```python
# Bad — hard to know what failed when the test breaks
def test_item() -> None:
    item = create_item()
    assert item.name == "Test"
    assert item.is_active is True
    response = get_item_api(item.pk)
    assert response.status_code == 200
    assert response.data["name"] == "Test"

# Good — one behaviour per test
def test_item_creation_sets_active_by_default() -> None:
    item = Item(name="Test")
    item.save()
    assert item.is_active is True

def test_item_api_returns_correct_name(api_client, item) -> None:
    response = api_client.get(f"/api/v1/items/{item.pk}/")
    assert response.data["name"] == item.name
```

### Non-Descriptive Test Names

```python
# Bad
def test_1() -> None: ...
def test_item_ok() -> None: ...
def test_works() -> None: ...

# Good — name describes scenario and expected outcome
def test_item_list_returns_empty_when_no_items_exist() -> None: ...
def test_validate_raises_on_empty_name() -> None: ...
def test_auth_returns_401_with_expired_token() -> None: ...
```

### Testing Implementation, Not Behaviour

```python
# Bad — testing internal detail
def test_item_uses_manager() -> None:
    assert hasattr(Item, "_default_manager")

# Good — testing observable behaviour
def test_active_items_query_excludes_inactive() -> None:
    Item.objects.create(name="Active", is_active=True)
    Item.objects.create(name="Inactive", is_active=False)
    results = Item.objects.active()
    assert all(i.is_active for i in results)
```

### Shared Mutable State

```python
# Bad — test results depend on execution order
items: list = []

def test_add_item() -> None:
    items.append(Item(name="Test"))
    assert len(items) == 1

def test_item_list() -> None:
    assert len(items) == 0  # fails if test_add_item ran first

# Good — use fixtures with function scope
@pytest.fixture
def items() -> list:
    return []

def test_add_item(items: list) -> None:
    items.append(create_item())
    assert len(items) == 1
```

---

## Mock Anti-Patterns

### Mocking the Unit Under Test

```python
# Bad — mocking the code you're trying to test makes the test useless
@patch("myapp.serializers.ItemSerializer.validate")
def test_item_serializer_validates(mock_validate) -> None:
    mock_validate.return_value = {}
    # This test proves nothing about ItemSerializer

# Good — mock external dependencies only
@patch("myapp.services.send_email")
def test_item_creation_sends_email(mock_send_email) -> None:
    create_item_and_notify()
    mock_send_email.assert_called_once()
```

### Over-Mocking

```python
# Bad — mocking everything makes the test brittle and meaningless
@patch("myapp.models.Item.objects.create")
@patch("myapp.models.Item.objects.filter")
@patch("myapp.serializers.ItemSerializer.is_valid")
def test_create_item(mock_valid, mock_filter, mock_create) -> None:
    pass  # not testing anything real

# Good — use real objects for integration tests
def test_create_item_integration(client, category) -> None:
    response = client.post("/api/v1/items/", {"name": "Test", "category": category.pk})
    assert response.status_code == 201
```

### `MagicMock` for Async Functions

```python
# Bad — MagicMock is not awaitable; raises TypeError at runtime
mock_fetch = MagicMock(return_value={"id": 1})

async def test_async_service() -> None:
    result = await my_service(mock_fetch)  # TypeError: object MagicMock is not awaitable

# Good — AsyncMock for coroutines
from unittest.mock import AsyncMock

mock_fetch = AsyncMock(return_value={"id": 1})

async def test_async_service() -> None:
    result = await my_service(mock_fetch)
    assert result["id"] == 1
```

---

## Parametrize Anti-Patterns

### Poorly Named Parametrize Cases

```python
# Bad — when a case fails, pytest output shows only the index number
@pytest.mark.parametrize("data,expected", [
    ({}, 400),
    ({"name": ""}, 400),
    ({"name": "Valid"}, 201),
])
def test_create(data, expected) -> None: ...

# Good — use pytest.param with IDs for readable failure output
@pytest.mark.parametrize("data,expected", [
    pytest.param({}, 400, id="missing-all-fields"),
    pytest.param({"name": ""}, 400, id="empty-name"),
    pytest.param({"name": "Valid", "category": 1}, 201, id="valid-data"),
])
def test_create(data, expected) -> None: ...
```

### Under-Using Parametrize

```python
# Bad — duplicated test bodies with minor data variation
def test_validate_empty_name() -> None:
    with pytest.raises(ValueError):
        validate_name("")

def test_validate_none_name() -> None:
    with pytest.raises(ValueError):
        validate_name(None)

def test_validate_too_long_name() -> None:
    with pytest.raises(ValueError):
        validate_name("a" * 300)

# Good — parametrize 3+ similar cases
@pytest.mark.parametrize("value,reason", [
    pytest.param("", "empty string", id="empty"),
    pytest.param(None, "null value", id="none"),
    pytest.param("a" * 300, "too long", id="too-long"),
])
def test_validate_name_rejects_invalid_input(value: str | None, reason: str) -> None:
    with pytest.raises(ValueError):
        validate_name(value)
```

---

## Float Comparison Anti-Patterns

```python
# Bad — floating-point representation errors cause intermittent failures
assert calculate_tax(100.0) == 8.5

# Good — pytest.approx with appropriate tolerance
assert calculate_tax(100.0) == pytest.approx(8.5, rel=1e-6)

# Good — absolute tolerance for small or near-zero values
assert vector_length(3.0, 4.0) == pytest.approx(5.0, abs=1e-9)
```

---

## Fixture Scope Anti-Patterns

```python
# Bad — session-scoped fixture is shared and can be mutated across tests
@pytest.fixture(scope="session")
def user_data() -> dict:
    return {"name": "Alice", "role": "admin"}  # mutable dict — any test can mutate it

# Good — function scope for mutable state (default)
@pytest.fixture
def user_data() -> dict:
    return {"name": "Alice", "role": "admin"}  # fresh dict per test

# session scope is appropriate for expensive read-only resources
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DB_URL)
    yield engine
    engine.dispose()
```

---

## Python Test Review Checklist

- [ ] Test has at least one meaningful assertion
- [ ] Test name describes the scenario and expected outcome
- [ ] Arrange-Act-Assert structure is visible
- [ ] One concept is being tested per function
- [ ] Only external dependencies are mocked — not the code under test
- [ ] No shared mutable state between tests
- [ ] Fixtures used for setup instead of repeated code
- [ ] `@pytest.mark.parametrize` used for 3+ similar test cases
- [ ] `pytest.param` with `id=` used for named parametrize cases
- [ ] Exceptions tested with `pytest.raises`
- [ ] Test is deterministic — no random values, no `time.sleep`
- [ ] `AsyncMock` used for async function mocks — not `MagicMock`
- [ ] Float comparisons use `pytest.approx` — not `==`
- [ ] Session/module-scoped fixtures are read-only — mutable fixtures use function scope
- [ ] `X | Y` union syntax used in test helper type signatures — not `Optional[X]` (Python 3.10+)
- [ ] `ExceptionGroup` asserted when testing code that uses `asyncio.TaskGroup` (Python 3.11+)
- [ ] `@override` applied to intentional test base class method overrides (Python 3.12+)
- [ ] `itertools.batched()` used in batch-test assertions — not manual slice arithmetic (Python 3.12+)
- [ ] `copy.replace()` used to build test payload variants — not repeated literal dicts (Python 3.13+)

---

## Python Version-Specific Review Points

### Python 3.9  (base)

#### Legacy `Optional` in Test Helper Signatures

```python
# Bad — outdated
from typing import Optional, List

def make_item(name: Optional[str] = None, tags: Optional[List[str]] = None) -> Item: ...

# Good — built-in generics (Python 3.9+)
def make_item(name: str | None = None, tags: list[str] | None = None) -> Item: ...
```

### Python 3.10

#### `Optional[X]` Instead of `X | None` in Test Signatures

```python
# Bad — verbose legacy syntax in test helpers
from typing import Optional

def make_item(name: Optional[str] = None) -> Item:
    return Item(name=name or "Default")

# Good — union syntax (Python 3.10+)
def make_item(name: str | None = None) -> Item:
    return Item(name=name or "Default")
```

#### Long `if/elif` Chains in Test Dispatch Helpers

```python
# Bad — repeated condition checks
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

### Python 3.11

#### Not Testing `ExceptionGroup` When Using `asyncio.TaskGroup`

```python
# Bad — only catches one exception; TaskGroup raises ExceptionGroup containing all failures
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

### Python 3.12

#### Missing `@override` on Test Base Class Method Overrides

```python
# Bad — typo silently creates a new method; the intended override never runs
class SpecificTestCase(BaseTestCase):
    def setup_fixutres(self) -> None:  # typo: "fixutres" — no error, no override
        self.item = Item(name="Test")

# Good — @override catches the typo at type-check time (Python 3.12+)
from typing import override

class SpecificTestCase(BaseTestCase):
    @override
    def setup_fixtures(self) -> None:  # type checker errors if parent method doesn't exist
        self.item = Item(name="Test")
```

#### Manual Chunking Instead of `itertools.batched()`

```python
# Bad — manual slice arithmetic in batch-processing tests
def test_bulk_import(mock_processor) -> None:
    records = list(range(250))
    bulk_import(records, batch_size=100)
    expected_batches = [records[i:i+100] for i in range(0, len(records), 100)]
    assert mock_processor.call_count == len(expected_batches)

# Good — itertools.batched() is clearer and less error-prone (Python 3.12+)
from itertools import batched

def test_bulk_import(mock_processor) -> None:
    records = list(range(250))
    bulk_import(records, batch_size=100)
    assert mock_processor.call_count == len(list(batched(records, 100)))
```

### Python 3.13

#### Repeated Dict Literals Instead of `copy.replace()` for Test Variants

```python
# Bad — repeated construction with minor variations; diff is hard to spot
def test_admin_creation() -> None:
    create_user({"name": "Alice", "email": "alice@example.com", "role": "admin"})

def test_regular_creation() -> None:
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

def test_admin_creation() -> None:
    create_user(replace(BASE, role="admin"))

def test_regular_creation() -> None:
    create_user(BASE)
```

### Python 3.14  (latest stable)

#### Missing Thread Safety Assertions in Free-Threaded Tests

When the project targets free-threaded CPython (`-X gil=0`), test concurrent scenarios explicitly:

```python
import threading

# Good — assert final state is correct after concurrent modification
def test_shared_counter_under_concurrent_access() -> None:
    counter = ThreadSafeCounter()
    threads = [threading.Thread(target=counter.increment) for _ in range(100)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert counter.value == 100  # must be exactly 100; data races would give a lower value
```

---

## Resources

- [pytest Documentation](https://docs.pytest.org/en/stable/)
- [pytest Good Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [pytest.mark.parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Python 3.10 What's New](https://docs.python.org/3/whatsnew/3.10.html)
- [Python 3.11 What's New](https://docs.python.org/3/whatsnew/3.11.html)
- [Python 3.12 What's New](https://docs.python.org/3/whatsnew/3.12.html)
- [Python 3.13 What's New](https://docs.python.org/3/whatsnew/3.13.html)
- [Python 3.14 What's New](https://docs.python.org/3.14/whatsnew/3.14.html)
