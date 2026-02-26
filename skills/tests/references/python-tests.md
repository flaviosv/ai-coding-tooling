# Python Testing Guide (pytest)

Applies to: Python projects using pytest.

---

## Overview

pytest is the standard test runner for Python projects. Key features:
- Auto-discovery of test files (`test_*.py` or `*_test.py`)
- Fixture system for setup and teardown
- `@pytest.mark.parametrize` for data-driven tests
- Rich plugin ecosystem (`pytest-cov`, `pytest-django`, etc.)

---

## Running Tests

```bash
# Run all tests
pytest

# Run a specific file
pytest path/to/test_module.py

# Run a specific test by name
pytest -k "test_create_item"

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Re-run last failed tests
pytest --lf

# Show local variables on failure
pytest -l
```

---

## Fixtures

Fixtures provide reusable setup and teardown. Define them in `conftest.py`:

```python
# conftest.py
import pytest

@pytest.fixture
def sample_data():
    return {"name": "Test", "value": 42}

@pytest.fixture(scope="session")
def expensive_resource():
    resource = create_expensive_resource()
    yield resource
    resource.cleanup()
```

**Fixture scopes:**
- `function` (default) — new fixture per test
- `class` — shared within a test class
- `module` — shared within a test module
- `session` — shared across the entire test run

---

## Parametrize

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert double(input) == expected

# Use pytest.param with IDs for clarity
@pytest.mark.parametrize("value,error", [
    pytest.param("", "blank", id="empty-string"),
    pytest.param(None, "null", id="none-value"),
    pytest.param("a" * 300, "too-long", id="too-long"),
])
def test_validation(value, error):
    ...
```

---

## Mocking with pytest-mock

`pytest-mock` provides a `mocker` fixture that integrates cleanly with pytest and auto-resets after each test (no manual `patcher.stop()`):

```bash
pip install pytest-mock
```

```python
# Good — mocker fixture; patch auto-resets after the test
def test_external_call(mocker):
    mock_get = mocker.patch("myapp.services.requests.get")
    mock_get.return_value.json.return_value = {"data": "value"}
    result = my_service_function()
    assert result == "value"
    mock_get.assert_called_once_with("https://api.example.com/data")

# Spy — wraps the real function, records calls without replacing behaviour
def test_calls_processor(mocker):
    spy = mocker.spy(item_service, "process")
    item_service.run_all()
    assert spy.call_count == 3
```

Use `mocker.patch.object` to patch a method on an existing instance:

```python
def test_sends_email(mocker, user_service):
    mock_send = mocker.patch.object(user_service.mailer, "send")
    user_service.register("alice@example.com")
    mock_send.assert_called_once()
```

---

## Mocking with unittest.mock

```python
from unittest.mock import patch, MagicMock, AsyncMock

# Patch a function in the module under test
@patch("myapp.services.requests.get")
def test_external_call(mock_get):
    mock_get.return_value.json.return_value = {"data": "value"}
    result = my_service_function()
    assert result == "value"
    mock_get.assert_called_once_with("https://api.example.com/data")

# Context manager form
def test_with_context_manager():
    with patch("myapp.services.send_email") as mock_email:
        trigger_email_function()
        mock_email.assert_called_once()

# MagicMock for object dependencies
def test_with_mock_object():
    mock_service = MagicMock()
    mock_service.get_data.return_value = [{"id": 1}]
    result = process_with_service(mock_service)
    assert len(result) == 1

# AsyncMock for async functions (Python 3.8+)
async def test_async_service(mocker):
    mock_fetch = mocker.patch("myapp.services.fetch_data", new_callable=AsyncMock)
    mock_fetch.return_value = {"id": 1}
    result = await my_async_service()
    assert result["id"] == 1
```

---

## Assert Patterns

```python
# Basic assertions
assert result == expected
assert result is not None
assert len(results) == 3

# Exception assertions
with pytest.raises(ValueError) as exc_info:
    validate_data(invalid_input)
assert "required" in str(exc_info.value)

# Approximate equality (for floats)
assert result == pytest.approx(3.14, rel=1e-3)
```

---

## Test Classes

```python
class TestItemService:
    """Group related tests for ItemService."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = ItemService()

    def test_create_returns_instance(self):
        item = self.service.create(name="Test")
        assert item.name == "Test"

    def test_create_raises_on_empty_name(self):
        with pytest.raises(ValueError):
            self.service.create(name="")
```

---

## Markers

```python
import pytest

@pytest.mark.slow
def test_slow_operation():
    ...

@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    ...

@pytest.mark.xfail(reason="Known issue")
def test_known_broken_behavior():
    ...
```

Register custom markers in `pytest.ini`:

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with -m "not slow")
    integration: marks integration tests
```

---

## CI / CD Integration

### Run Tests Locally Before Committing

```bash
# Run pre-commit hooks manually (if configured)
pre-commit run --all-files

# Run all tests
pytest

# Run with coverage
pytest --cov=myapp --cov-report=term-missing
```

### Common CI Commands

```bash
# Run all tests with coverage and JUnit XML output
pytest --cov=myapp --cov-report=xml --junitxml=results.xml

# Run only fast unit tests
pytest -m "not slow and not integration"

# Stop on first failure
pytest -x

# Verbose output
pytest -v
```

### Recommended CI Pipeline Order

1. **Linting** — run first so cheap errors fail fast (e.g. `ruff check .`, `flake8`)
2. **Unit tests** — no I/O, run fast
3. **Integration tests** — database, external services
4. **Coverage report** — uploaded to coverage tracking service

### Markers Configuration

```ini
[pytest]
markers =
    slow: marks tests as slow
    integration: marks integration tests
    unit: marks pure unit tests (no I/O)
```

### Coverage Configuration

```ini
[coverage:run]
omit =
    */migrations/*
    */tests/*
    manage.py
    conftest.py
```

---

## Common Anti-Patterns

### ❌ Testing implementation details

```python
# Bad — testing a private method directly
def test_internal_method():
    obj._private_method()

# Good — test via the public interface
def test_public_behavior():
    result = obj.public_method()
    assert result == expected
```

### ❌ Using `time.sleep` in tests

```python
# Bad — makes tests slow and unreliable
time.sleep(1)
assert task_completed

# Good — mock time or use proper synchronization primitives
```

### ❌ Shared mutable state

```python
# Bad — test results depend on execution order
shared_list = []

def test_one():
    shared_list.append(1)

def test_two():
    assert len(shared_list) == 0  # Fails if test_one ran first

# Good — use fixtures with function scope
@pytest.fixture
def empty_list():
    return []
```

---

## Python Version-Specific Testing Patterns

### Python 3.10+ Testing

```python
# Good — X | Y union syntax in test helper signatures
def make_item(name: str | None = None, category: int | None = None) -> Item:
    return Item(name=name or "Default", category_id=category or 1)

# Bad — verbose legacy Optional
from typing import Optional
def make_item(name: Optional[str] = None, category: Optional[int] = None) -> Item: ...
```

```python
# Good — match/case in test helpers for readable assertion dispatch
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

### Python 3.11+ Testing

```python
# Good — ExceptionGroup for asserting multiple concurrent failures from TaskGroup
import asyncio
import pytest

@pytest.mark.asyncio
async def test_task_group_collects_all_errors():
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

```python
# Good — Self type for fluent builder test fixtures
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

# Usage in tests
def test_inactive_item_excluded_from_listing():
    item = ItemBuilder().with_name("Hidden").inactive().build()
    item.save()
    results = Item.objects.active()
    assert item not in results
```

### Python 3.12+ Testing

```python
# Good — @override ensures test base class method overrides are intentional
from typing import override

class BaseAPITestCase:
    def get_auth_headers(self) -> dict[str, str]:
        return {}

class AdminTestCase(BaseAPITestCase):
    @override
    def get_auth_headers(self) -> dict[str, str]:  # type checker verifies parent exists
        return {"Authorization": f"Bearer {self.admin_token}"}
```

```python
# Good — itertools.batched() for testing batch processing
from itertools import batched

def test_bulk_import_processes_in_batches(mock_processor):
    records = list(range(250))
    bulk_import(records, batch_size=100)

    expected_calls = len(list(batched(records, 100)))
    assert mock_processor.call_count == expected_calls
```

### Python 3.13+ Testing

```python
# Good — copy.replace() for building test payload variants cleanly
from copy import replace
from dataclasses import dataclass

@dataclass
class CreateUserPayload:
    name: str
    email: str
    role: str = "user"

base = CreateUserPayload(name="Alice", email="alice@example.com")

def test_admin_user_creation():
    result = create_user(replace(base, role="admin"))
    assert result.role == "admin"

def test_regular_user_creation():
    result = create_user(base)
    assert result.role == "user"
```

---

## Async Tests with pytest-asyncio

```bash
pip install pytest-asyncio
```

Configure in `pytest.ini` or `pyproject.toml`:

```ini
[pytest]
asyncio_mode = auto  # auto-detect async test functions; no need for @pytest.mark.asyncio per test
```

```python
import pytest
import asyncio

# Good — async test function; pytest-asyncio runs it in an event loop
async def test_async_fetch():
    result = await fetch_data("https://example.com/api")
    assert result["status"] == "ok"

# Testing concurrent tasks with TaskGroup (Python 3.11+)
async def test_parallel_fetch():
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch_item(1))
        t2 = tg.create_task(fetch_item(2))
    assert t1.result()["id"] == 1
    assert t2.result()["id"] == 2
```

---

## Property-Based Testing with Hypothesis

[hypothesis](https://hypothesis.readthedocs.io/) generates test cases from strategy definitions:

```bash
pip install hypothesis
```

```python
from hypothesis import given, strategies as st

# Good — hypothesis generates hundreds of input combinations automatically
@given(st.text(min_size=1, max_size=200))
def test_slugify_never_raises(text):
    result = slugify(text)
    assert isinstance(result, str)
    assert len(result) <= len(text)

# Good — test that encode/decode is a round-trip
@given(st.integers(min_value=0, max_value=10_000))
def test_encode_decode_roundtrip(value):
    assert decode(encode(value)) == value
```

Use hypothesis for functions with wide input domains (parsers, encoders, validators, data transforms).

---

## Resources

- [pytest Documentation](https://docs.pytest.org/en/stable/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/reference/fixtures.html)
- [pytest.mark.parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-mock](https://pytest-mock.readthedocs.io/en/latest/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/en/latest/)
- [Hypothesis](https://hypothesis.readthedocs.io/en/latest/)
- [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/)
