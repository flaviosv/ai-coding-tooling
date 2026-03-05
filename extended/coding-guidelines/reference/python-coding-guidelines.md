# Python Reference — coding-guidelines

<!-- General section covers conventions that apply across ALL still-supported Python versions (3.9–3.14) -->
## General Python Coding Patterns

### Naming Conventions

- **Modules and packages**: lowercase with underscores (`user_service.py`, `auth_utils/`)
- **Classes**: PascalCase (`UserService`, `HttpClient`)
- **Functions and methods**: lowercase with underscores (`parse_config`, `get_user`)
- **Constants**: `UPPER_SNAKE_CASE` (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private members**: prefix with single underscore (`_internal_state`, `_validate`)
- **Name-mangled members**: prefix with double leading underscore only when subclass name collision is a real concern (`__internal`). Note: dunder names like `__slots__`, `__init__`, `__repr__` are protocol methods, not name-mangled attributes — do not confuse the two.
- **Type variables**: short PascalCase (`T`, `KT`, `VT`)
- **Acronyms**: treat as words — `HttpClient`, `JsonParser`, `url_path`

### File Organization

- One module per logical concern; keep files under ~300 lines
- Order within a file: module docstring → `__future__` imports → stdlib imports → third-party imports → local imports → constants → classes → functions → `if __name__ == "__main__"`
- Group imports in three blocks separated by blank lines: stdlib, third-party, local
- Use `__all__` in public modules to declare the public API explicitly

```python
# Good — explicit public API declaration
__all__ = ["UserService", "create_user", "UserNotFoundError"]
```

- Keep `__init__.py` files minimal — re-export only what is part of the public API. Heavy `__init__.py` imports cause slow startup and circular import risks.

### Code Structure

- Prefer flat over nested — limit nesting to 2–3 levels; use early returns and guard clauses

```python
# Good — guard clause exits early; no nesting
def process_item(item: Item) -> str:
    if item is None:
        raise ValueError("item must not be None")
    if not item.is_active:
        return ""
    return item.name.upper()

# Bad — nested if chain
def process_item(item: Item) -> str:
    if item is not None:
        if item.is_active:
            return item.name.upper()
    return ""
```

- Keep functions short; a function should do one thing
- Use dataclasses for plain data containers instead of raw dicts

```python
from dataclasses import dataclass, field

@dataclass
class Config:
    host: str
    port: int = 5432
    tags: list[str] = field(default_factory=list)  # never assign mutable literal as default

# Bad — mutable default argument is shared across all calls
def configure(tags=[]) -> None: ...

# Good — use None and assign inside
def configure(tags: list[str] | None = None) -> None:
    tags = tags or []
```

- Prefer composition over inheritance; limit inheritance depth to 2
- Use `__slots__` in performance-sensitive classes with many instances
- Write module-level docstrings and docstrings for all public classes and functions
- Define `__repr__` on classes that appear in logs, shells, or test output

```python
@dataclass
class User:
    id: int
    name: str

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r})"
```

### Error Handling

- Use specific exception types — never `except Exception` or bare `except` as a catch-all
- Raise exceptions with descriptive messages; include relevant context values

```python
# Good — specific type, informative message
raise ValueError(f"Invalid status {status!r}; expected one of {VALID_STATUSES}")

# Bad — bare except swallows everything including KeyboardInterrupt
try:
    process()
except:
    pass
```

- Define custom exceptions in a dedicated `exceptions.py` module per package
- Use `contextlib.suppress` only for genuinely ignorable exceptions

```python
from contextlib import suppress

# Good — deleting a file that may not exist is a known, harmless case
with suppress(FileNotFoundError):
    temp_path.unlink()

# Bad — suppress(Exception) is a catch-all and hides real bugs
```

- Clean up resources with `with` statements, not `try/finally` manually

### Idioms and Patterns

- Use list/dict/set comprehensions for simple transformations; use `for` loops for side effects
- Prefer generators for large sequences to avoid materializing everything in memory

```python
# Good — lazy generator; does not create a full list in memory
def active_names(items: list[Item]) -> Generator[str, None, None]:
    return (item.name for item in items if item.is_active)

# Good — list comprehension is fine when you need all results at once
names = [item.name for item in items if item.is_active]
```

- Use `enumerate` instead of manual index tracking; use `zip` for parallel iteration
- Use `pathlib.Path` for all filesystem operations — not `os.path`

```python
from pathlib import Path

# Good
config_path = Path("config") / "settings.json"
content = config_path.read_text(encoding="utf-8")

# Bad
import os
config_path = os.path.join("config", "settings.json")
```

- Use `logging` module — never `print` for application output
- Use f-strings for string formatting

```python
# Good — fastest and most readable
label = f"Item: {item.name} ({item.id})"
```

- Do not shadow built-in names (`id`, `list`, `type`, `input`, `filter`, `map`)

### Anti-Patterns to Avoid

```python
# Do not use mutable default arguments
def foo(items=[]) -> None: ...  # Bad — shared across all calls
def foo(items: list | None = None) -> None:  # Good
    items = items or []

# Do not use type(x) == SomeClass — use isinstance
if type(x) == str: ...   # Bad
if isinstance(x, str): ...  # Good

# Do not concatenate strings in a loop
result = ""
for part in parts:
    result += part  # Bad — O(n²)
result = "".join(parts)  # Good

# Do not rely on *args/**kwargs as a shortcut for untyped signatures
def process(*args, **kwargs) -> None: ...  # Bad — no type information
def process(name: str, value: int) -> None: ...  # Good
```

---

## Python 3.9  (base supported version)

### Built-in Generic Type Hints

```python
# Good — built-in generics; no typing imports needed (Python 3.9+)
def get_users(ids: list[int]) -> dict[str, list[str]]:
    ...

# Bad — importing List/Dict from typing is unnecessary in Python 3.9+
from typing import List, Dict
def get_users(ids: List[int]) -> Dict[str, List[str]]: ...
```

### String Prefix/Suffix Operations

```python
# Good — str.removeprefix/removesuffix are safer than slicing (Python 3.9+)
name = filename.removesuffix(".json")
base_url = url.removeprefix("https://")

# Bad — manual slicing or replace() is error-prone
name = filename[:-5] if filename.endswith(".json") else filename
```

### Dict Merge and Update Operators

```python
# Good — dict merge operator (Python 3.9+)
merged = defaults | overrides

# In-place update
config |= env_overrides

# Bad — {**a, **b} creates intermediate dicts; less readable
merged = {**defaults, **overrides}
```

---

## Python 3.10

### Union Type Syntax

```python
# Good — X | Y union syntax instead of Optional[X] or Union[X, Y] (Python 3.10+)
def get_user(user_id: int | None = None) -> User | None:
    ...

# Bad — verbose legacy syntax
from typing import Optional, Union
def get_user(user_id: Optional[int] = None) -> Optional[User]: ...
```

### Structural Pattern Matching

Use `match`/`case` for structural dispatch. Always include a `case _` catch-all or use `typing.assert_never` to make exhaustiveness explicit to the type checker.

```python
# Good — structural pattern matching for command dispatch (Python 3.10+)
def handle_command(command: dict) -> None:
    match command:
        case {"action": "create", "name": str(name)}:
            create_item(name)
        case {"action": "delete", "id": int(item_id)}:
            delete_item(item_id)
        case _:
            raise ValueError(f"Unknown command: {command}")
```

### `zip(strict=True)` to Catch Length Mismatches

```python
# Good — raises ValueError immediately if lengths differ (Python 3.10+)
for key, value in zip(keys, values, strict=True):
    result[key] = value

# Bad — silently truncates to the shorter sequence
for key, value in zip(keys, values):
    result[key] = value
```

### `TypeAlias` for Explicit Type Aliases

```python
# Good — explicit type alias declaration (Python 3.10+)
from typing import TypeAlias

UserId: TypeAlias = int
UserMap: TypeAlias = dict[str, list[int]]
```

---

## Python 3.11

### `asyncio.TaskGroup` for Structured Concurrency

```python
# Good — TaskGroup starts all tasks concurrently; all exceptions are collected (Python 3.11+)
async def fetch_all(urls: list[str]) -> list[bytes]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(url)) for url in urls]
    return [t.result() for t in tasks]

# Bad — sequential awaits; no concurrency
results = [await fetch(url) for url in urls]

# Avoid — asyncio.gather() swallows exceptions unless return_exceptions=True
results = await asyncio.gather(*[fetch(url) for url in urls])
```

- Never call blocking I/O inside an async function — use `asyncio.to_thread` to offload synchronous blocking calls.

### `ExceptionGroup` and `except*`

```python
# Good — except* handles multiple exception types from concurrent tasks (Python 3.11+)
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(op_one())
        tg.create_task(op_two())
except* ValueError as eg:
    for exc in eg.exceptions:
        log.error("Value error: %s", exc)
except* IOError as eg:
    for exc in eg.exceptions:
        log.error("IO error: %s", exc)
```

### `StrEnum` for String Enumerations

```python
# Good — StrEnum values are plain strings; no .value access needed (Python 3.11+)
from enum import StrEnum

class Status(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"

assert Status.ACTIVE == "active"  # True — direct string comparison works
```

### `tomllib` for Config Parsing

```python
# Good — standard library TOML parsing (Python 3.11+); no third-party dependency
import tomllib

with open("pyproject.toml", "rb") as f:
    config = tomllib.load(f)

timeout = config["app"]["timeout"]
```

### `Self` Type for Fluent Interfaces

```python
from typing import Self

class QueryBuilder:
    def where(self, condition: str) -> Self:
        self._conditions.append(condition)
        return self

    def limit(self, n: int) -> Self:
        self._limit = n
        return self
```

---

## Python 3.12

### `@override` Decorator

```python
from typing import override

class Base:
    def process(self) -> str:
        return "base"

class Derived(Base):
    @override
    def process(self) -> str:  # type checker verifies the parent method exists
        return "derived"

# Without @override, a typo creates a new method silently
class BrokenDerived(Base):
    def proccess(self) -> str:  # typo — no error without @override
        return "broken"
```

### `type` Statement for Type Aliases

```python
# Good — type statement is evaluated lazily; no runtime overhead (Python 3.12+)
type Vector = list[float]
type Matrix = list[Vector]
type UserId = int

# Bad (Python 3.10–3.11 style) — TypeAlias is evaluated eagerly
from typing import TypeAlias
Vector: TypeAlias = list[float]
```

### `itertools.batched()` for Chunked Processing

```python
from itertools import batched

# Good — clear intent; no off-by-one errors (Python 3.12+)
for batch in batched(records, 500):
    db.bulk_insert(batch)

# Bad — manual slice arithmetic
for i in range(0, len(records), 500):
    db.bulk_insert(records[i:i + 500])
```

---

## Python 3.13

### `copy.replace()` for Immutable Copies with Field Overrides

```python
from copy import replace
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    host: str
    port: int
    timeout: float = 30.0

base = Config("localhost", 5432)
prod = replace(base, host="db.prod.example.com")  # clean, explicit override

# Bad — manual reconstruction is verbose and error-prone
prod = Config(host="db.prod.example.com", port=base.port, timeout=base.timeout)
```

Works with dataclasses, namedtuples, and any class that implements `__replace__`.

### `warnings.deprecated` for Deprecation Notices

```python
from warnings import deprecated

@deprecated("Use new_function() instead — will be removed in v3.0")
def old_function() -> None:
    ...
```

### `typing.TypeIs` for Narrowing Predicates

```python
from typing import TypeIs

# Good — TypeIs tells the type checker that a True return narrows the type (Python 3.13+)
def is_string(value: object) -> TypeIs[str]:
    return isinstance(value, str)

items: list[str | int] = ["a", 1, "b"]
strings = [x for x in items if is_string(x)]
# strings is inferred as list[str]
```

---

## Python 3.14  (latest stable)

### Deferred Annotation Evaluation (PEP 749)

Annotations are now evaluated lazily by default. Forward references work without string quoting.

```python
# Good — forward references resolve lazily; no string quotes needed (Python 3.14+)
class Node:
    def children(self) -> list[Node]:  # "Node" not yet defined, but works
        return self._children

# Still valid but no longer required in Python 3.14+
class Node:
    def children(self) -> "list[Node]":  # quoted forward reference — works but unnecessary
        return self._children
```

### `annotationlib` for Runtime Annotation Introspection

```python
# Good — use annotationlib for correct runtime annotation resolution (Python 3.14+)
import annotationlib

hints = annotationlib.get_annotations(MyClass, format=annotationlib.Format.FORWARDREF)
```

### Free-Threaded CPython (PEP 703)

Available as a supported build. Activate with `-X gil=0` or `PYTHON_GIL=0`. Use standard `threading` patterns for CPU-bound parallel work.

```python
import threading

def cpu_task(n: int) -> int:
    return sum(i * i for i in range(n))

# With free-threading enabled, these run truly in parallel on multiple cores
threads = [threading.Thread(target=cpu_task, args=(10_000_000,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

# Note: verify third-party C extensions support free-threading before enabling
# Reference: https://py-free-threading.github.io/
```

---

## Resources

- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [pathlib](https://docs.python.org/3/library/pathlib.html)
- [contextlib](https://docs.python.org/3/library/contextlib.html)
- [asyncio](https://docs.python.org/3/library/asyncio.html)
- [Python 3.10 What's New](https://docs.python.org/3/whatsnew/3.10.html)
- [Python 3.11 What's New](https://docs.python.org/3/whatsnew/3.11.html)
- [Python 3.12 What's New](https://docs.python.org/3/whatsnew/3.12.html)
- [Python 3.13 What's New](https://docs.python.org/3/whatsnew/3.13.html)
- [Python 3.14 What's New](https://docs.python.org/3.14/whatsnew/3.14.html)
- [Free-threaded CPython compatibility tracker](https://py-free-threading.github.io/)
