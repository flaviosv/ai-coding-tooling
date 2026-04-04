# Python Reference — tests

Applies to: Python projects using pytest.

---

## General Python Testing Patterns

### Test Discovery and Running

```bash
pytest                                          # all tests
pytest path/to/test_module.py                   # specific file
pytest -k "test_create_item"                    # by name pattern
pytest -v                                       # verbose
pytest -x                                       # stop on first failure
pytest --lf                                     # re-run last failed
pytest -l                                       # show locals on failure
pytest --cov=myapp --cov-report=term-missing    # with coverage
```

### File and Directory Organization

```
tests/
├── conftest.py          # shared fixtures for the whole test suite
├── unit/
│   ├── conftest.py      # fixtures scoped to unit tests only
│   └── test_*.py
├── integration/
│   ├── conftest.py      # fixtures scoped to integration tests only
│   └── test_*.py
└── pytest.ini           # or pyproject.toml [tool.pytest.ini_options]
```

### Fixtures

Define reusable setup/teardown in `conftest.py`:

```python
@pytest.fixture
def sample_data() -> dict:
    return {"name": "Test", "value": 42}

@pytest.fixture
def user_service() -> UserService:
    return UserService()

@pytest.fixture(scope="session")
def expensive_resource():
    resource = create_expensive_resource()
    yield resource
    resource.cleanup()
```

**Fixture scopes:**
- `function` (default) — new fixture per test; always use for mutable state
- `class` — shared within a test class
- `module` — shared within a test module
- `session` — shared across the entire test run; use only for expensive read-only resources

### Parametrize

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input: int, expected: int) -> None:
    assert double(input) == expected

# Use pytest.param with IDs for readable failure output
@pytest.mark.parametrize("value,error", [
    pytest.param("", "blank", id="empty-string"),
    pytest.param(None, "null", id="none-value"),
    pytest.param("a" * 300, "too-long", id="too-long"),
])
def test_validation(value: str | None, error: str) -> None:
    with pytest.raises(ValidationError, match=error):
        validate_input(value)
```

Use `@pytest.mark.parametrize` when you have 3+ similar test cases with the same structure. For 1–2 cases, write separate named test functions.

### Mocking with `pytest-mock`

`pytest-mock` provides a `mocker` fixture that integrates with pytest and auto-resets after each test:

```python
# Good — patch auto-resets after the test
def test_external_call(mocker) -> None:
    mock_get = mocker.patch("myapp.services.requests.get")
    mock_get.return_value.json.return_value = {"data": "value"}
    result = my_service_function()
    assert result == "value"
    mock_get.assert_called_once_with("https://api.example.com/data")

# Good — spy wraps the real function, records calls without replacing behaviour
def test_calls_processor(mocker) -> None:
    spy = mocker.spy(item_service, "process")
    item_service.run_all()
    assert spy.call_count == 3

# Good — patch a method on an existing instance
def test_sends_email(mocker, user_service) -> None:
    mock_send = mocker.patch.object(user_service.mailer, "send")
    user_service.register("alice@example.com")
    mock_send.assert_called_once()
```

### Mocking with `unittest.mock`

```python
from unittest.mock import patch, MagicMock, AsyncMock

@patch("myapp.services.requests.get")
def test_external_call(mock_get) -> None:
    mock_get.return_value.json.return_value = {"data": "value"}
    result = my_service_function()
    assert result == "value"
    mock_get.assert_called_once_with("https://api.example.com/data")

def test_with_context_manager() -> None:
    with patch("myapp.services.send_email") as mock_email:
        trigger_email_function()
        mock_email.assert_called_once()

def test_with_mock_object() -> None:
    mock_service = MagicMock()
    mock_service.get_data.return_value = [{"id": 1}]
    result = process_with_service(mock_service)
    assert len(result) == 1

# AsyncMock for async functions — MagicMock is not awaitable
async def test_async_service(mocker) -> None:
    mock_fetch = mocker.patch("myapp.services.fetch_data", new_callable=AsyncMock)
    mock_fetch.return_value = {"id": 1}
    result = await my_async_service()
    assert result["id"] == 1
```

### Assert Patterns

```python
# Basic — use pytest's plain assert; no assertEqual needed
assert result == expected
assert result is not None
assert len(results) == 3

# Exception assertions
with pytest.raises(ValueError) as exc_info:
    validate_data(invalid_input)
assert "required" in str(exc_info.value)

# Approximate equality for floats — never use == on floats
assert calculate_tax(100.0) == pytest.approx(8.5, rel=1e-6)
assert vector_length(3.0, 4.0) == pytest.approx(5.0, abs=1e-9)
```

### Test Classes

```python
class TestItemService:
    """Group related tests for ItemService."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.service = ItemService()

    def test_create_returns_instance(self) -> None:
        item = self.service.create(name="Test")
        assert item.name == "Test"

    def test_create_raises_on_empty_name(self) -> None:
        with pytest.raises(ValueError):
            self.service.create(name="")
```

### Markers

```python
@pytest.mark.slow
def test_slow_operation() -> None:
    ...

@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature() -> None:
    ...

@pytest.mark.xfail(reason="Known issue — tracked in #123")
def test_known_broken_behavior() -> None:
    ...
```

Register custom markers in `pytest.ini` or `pyproject.toml` to avoid unregistered-marker warnings:

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with -m "not slow")
    integration: marks integration tests
    unit: marks pure unit tests (no I/O)
```

### Conftest and Fixture Sharing

```python
# conftest.py — fixtures here are available to all tests in the same directory and below
@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)

@pytest.fixture
def auth_headers(user_factory) -> dict[str, str]:
    user = user_factory(role="admin")
    token = generate_token(user)
    return {"Authorization": f"Bearer {token}"}
```

Prefer `conftest.py` over test-level fixtures for anything shared across more than one test file.

### Property-Based Testing with Hypothesis

```python
from hypothesis import given, strategies as st

# Good — hypothesis generates hundreds of input combinations automatically
@given(st.text(min_size=1, max_size=200))
def test_slugify_never_raises(text: str) -> None:
    result = slugify(text)
    assert isinstance(result, str)
    assert len(result) <= len(text)

# Good — test that encode/decode is a round-trip
@given(st.integers(min_value=0, max_value=10_000))
def test_encode_decode_roundtrip(value: int) -> None:
    assert decode(encode(value)) == value
```

Use Hypothesis for functions with wide input domains: parsers, encoders, validators, data transforms.

### Async Tests with `pytest-asyncio`

Configure in `pytest.ini` or `pyproject.toml`:

```ini
[pytest]
asyncio_mode = auto  # auto-detect async test functions; no need for @pytest.mark.asyncio per test
```

```python
# Good — async test function; pytest-asyncio runs it in an event loop
async def test_async_fetch() -> None:
    result = await fetch_data("https://example.com/api")
    assert result["status"] == "ok"
```

### CI/CD Integration

```bash
pytest --cov=myapp --cov-report=xml --junitxml=results.xml  # coverage + JUnit XML for CI
pytest -m "not slow and not integration"                      # only fast unit tests
pytest -x                                                     # stop on first failure
```

Recommended CI pipeline order: linting -> unit tests -> integration tests -> coverage report.

### Common Anti-Patterns

#### Do Not Test Implementation Details

```python
# Bad
def test_internal_method() -> None:
    obj._private_method()
    # ...

# Good — test via the public interface
def test_public_behavior() -> None:
    result = obj.public_method()
    assert result == expected
```

#### Do Not Use `time.sleep` in Tests

```python
# Bad — makes tests slow and unreliable
time.sleep(1)
assert task_completed

# Good — mock time or use proper synchronization primitives
```

#### Do Not Use Shared Mutable State

```python
# Bad — test results depend on execution order
shared_list: list = []

def test_one() -> None:
    shared_list.append(1)

def test_two() -> None:
    assert len(shared_list) == 0  # fails if test_one ran first

# Good — use fixtures with function scope
@pytest.fixture
def empty_list() -> list:
    return []
```

#### Do Not Use `MagicMock` for Async Functions

```python
# Bad — MagicMock is not awaitable; raises TypeError at runtime
mock_fetch = MagicMock(return_value={"id": 1})
result = await my_service(mock_fetch)  # TypeError
# ...

# Good — AsyncMock for coroutines
mock_fetch = AsyncMock(return_value={"id": 1})
```

## Python 3.9 (base supported version)

### Built-in Generic Annotations in Test Signatures

```python
# Good — built-in generics; no typing imports needed
def make_item(tags: list[str] | None = None) -> Item:
    return Item(tags=tags or [])

# Bad
from typing import List, Optional
def make_item(tags: Optional[List[str]] = None) -> Item: ...
```

### Builder Pattern for Test Fixtures

```python
@dataclass
class ItemBuilder:
    name: str = "Default Item"
    is_active: bool = True
    tags: list[str] = field(default_factory=list)

    def build(self) -> Item:
        return Item(name=self.name, is_active=self.is_active, tags=self.tags)

def test_inactive_item_excluded_from_listing() -> None:
    item = ItemBuilder(name="Hidden", is_active=False).build()
    item.save()
    assert item not in list_active_items()
```

## Python 3.10

### Union Type Syntax in Test Helper Signatures (Python 3.10+)

```python
# Good — X | Y union syntax
def make_item(name: str | None = None, category: int | None = None) -> Item:
    return Item(name=name or "Default", category_id=category or 1)

# Bad
from typing import Optional
def make_item(name: Optional[str] = None, category: Optional[int] = None) -> Item: ...
```

### Structural Pattern Matching in Test Dispatch Helpers (Python 3.10+)

```python
# Good — match/case for readable assertion dispatch
def assert_api_error(response, expected_code: int) -> None:
    match response.status_code:
        case 400:
            assert "validation" in response.json().get("detail", "").lower()
        case 404:
            assert "not found" in response.json().get("detail", "").lower()
        case 422:
            assert "errors" in response.json()
        case _:
            pytest.fail(f"Unexpected status {response.status_code}")
```

## Python 3.11

### `ExceptionGroup` for Concurrent Task Failures

When testing code that uses `asyncio.TaskGroup`, expect `ExceptionGroup`, not individual exceptions:

```python
async def test_task_group_collects_all_errors() -> None:
    async def fail(msg: str) -> None:
        raise ValueError(msg)
    with pytest.raises(ExceptionGroup) as exc_info:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fail("error-a"))
            tg.create_task(fail("error-b"))
    errors = exc_info.value.exceptions
    assert len(errors) == 2
    assert all(isinstance(e, ValueError) for e in errors)
```

### `Self` Type for Fluent Builder Fixtures (Python 3.11+)

```python
from typing import Self

class ItemBuilder:
    def __init__(self) -> None:
        self._name = "Default Item"
        self._active = True

    def with_name(self, name: str) -> Self:
        self._name = name
        return self

    def inactive(self) -> Self:
        self._active = False
        return self

    def build(self) -> Item:
        return Item(name=self._name, is_active=self._active)

def test_inactive_item_excluded_from_listing() -> None:
    item = ItemBuilder().with_name("Hidden").inactive().build()
    item.save()
    assert item not in list_active_items()
```

### Testing Concurrent I/O with `asyncio.TaskGroup` (Python 3.11+)

```python
async def test_parallel_fetch() -> None:
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch_item(1))
        t2 = tg.create_task(fetch_item(2))
    assert t1.result()["id"] == 1
    assert t2.result()["id"] == 2
```

## Python 3.12

### `@override` on Test Base Class Method Overrides (Python 3.12+)

```python
from typing import override

class BaseAPITestCase:
    def get_auth_headers(self) -> dict[str, str]:
        return {}

class AdminTestCase(BaseAPITestCase):
    @override
    def get_auth_headers(self) -> dict[str, str]:  # type checker verifies parent method exists
        return {"Authorization": f"Bearer {self.admin_token}"}
```

Without `@override`, a typo in the method name silently creates a new method and the intended override never runs.

### `itertools.batched()` in Batch-Processing Tests (Python 3.12+)

```python
from itertools import batched

def test_bulk_import_processes_in_batches(mock_processor) -> None:
    records = list(range(250))
    bulk_import(records, batch_size=100)
    expected_calls = len(list(batched(records, 100)))
    assert mock_processor.call_count == expected_calls

# Bad — manual slice arithmetic is error-prone
expected_batches = [records[i:i+100] for i in range(0, len(records), 100)]
```

## Python 3.13

### `copy.replace()` for Building Test Payload Variants (Python 3.13+)

```python
# Good — copy.replace() makes the variation explicit and avoids repeated literals
from copy import replace
from dataclasses import dataclass

@dataclass
class CreateUserPayload:
    name: str
    email: str
    role: str = "user"

BASE = CreateUserPayload(name="Alice", email="alice@example.com")

def test_admin_user_creation() -> None:
    result = create_user(replace(BASE, role="admin"))
    assert result.role == "admin"

def test_regular_user_creation() -> None:
    result = create_user(BASE)
    assert result.role == "user"

# Bad — repeated dict literals with minor variations
def test_admin_user_creation() -> None:
    create_user({"name": "Alice", "email": "alice@example.com", "role": "admin"})
# ...
```

## Python 3.14 (latest stable)

### Testing Free-Threaded Code (Python 3.14+)

When testing code that uses free-threaded CPython (`-X gil=0`), use standard `threading` patterns. Test thread safety by running concurrent operations and asserting final state:

```python
import threading

def test_counter_is_thread_safe() -> None:
    counter = ThreadSafeCounter()
    threads = [threading.Thread(target=counter.increment) for _ in range(100)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert counter.value == 100
```

### Deferred Annotation Evaluation in Test Fixtures (Python 3.14+)

```python
# Good — forward references resolve lazily; no string quotes needed
@pytest.fixture
def item_factory() -> Callable[[str], Item]:
    def _make(name: str) -> Item:
        return Item(name=name)
    return _make
```
