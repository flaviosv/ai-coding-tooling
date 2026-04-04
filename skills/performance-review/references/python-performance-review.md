# Python Reference — performance-review

---

## General Python Performance Patterns

### Avoid Unnecessary Work

#### Use Generators Instead of Lists When Possible

```python
# Good — lazy evaluation, memory efficient
def get_names(items):
    return (item.name for item in items)

for name in get_names(items):
    process(name)

# Bad
def get_names(items):
    return [item.name for item in items]
```

#### Use `any()` and `all()` for Short-Circuit Evaluation

```python
# Good — stops at first match
if any(item.is_active for item in items):
    ...

# Bad
if True in [item.is_active for item in items]:
    ...
```

### String Operations

#### Use `join()` for String Concatenation

```python
# Good — single allocation
result = "".join(["Hello", " ", "World"])

# Bad — new string each iteration
result = ""
for part in parts:
    result += part
```

#### Prefer f-strings for Formatting

```python
# Good — fastest option in Python 3.6+
label = f"Item: {item.name} ({item.id})"

# Acceptable — but slower
label = "Item: {} ({})".format(item.name, item.id)

# Avoid — old style
label = "Item: %s (%s)" % (item.name, item.id)
```

### Data Structures

#### Use Sets for Membership Testing

```python
# Good — O(1) lookup
active_ids = {item.id for item in items if item.is_active}
if item_id in active_ids:
    ...

# Bad — O(n) lookup
active_ids = [item.id for item in items if item.is_active]
if item_id in active_ids:
    ...
```

#### Use `collections.defaultdict` and `Counter`

```python
from collections import defaultdict, Counter

# Good — avoid repeated get/set pattern
counts_by_category = defaultdict(int)
for item in items:
    counts_by_category[item.category_id] += 1

# Good — counting occurrences efficiently
category_counts = Counter(item.category_id for item in items)
most_common = category_counts.most_common(5)
```

### Memoization with `functools.cache` / `lru_cache`

```python
from functools import cache, lru_cache

# Good — cache expensive pure function
@cache
def compute_fibonacci(n: int) -> int:
    if n < 2:
        return n
    return compute_fibonacci(n - 1) + compute_fibonacci(n - 2)

# lru_cache with bounded size to prevent unbounded memory growth
@lru_cache(maxsize=128)
def fetch_exchange_rate(currency: str) -> float:
    return external_api.get_rate(currency)
```

**Memory leak risk with instance methods:** `@cache` on an instance method captures `self` as a cache key, preventing GC of the instance. Use module-level functions or `functools.cached_property` for instance-level caching:

```python
# Bad — prevents GC of self
class RateCalculator:
    @cache
    def get_rate(self, currency: str) -> float: ...

# Good — cached_property for per-instance lazy computation
class RateCalculator:
    @functools.cached_property
    def default_rate(self) -> float:
        return self._compute_default()
```

### Common Anti-Patterns

#### Avoid `import *`

```python
# Bad — pollutes namespace, slower startup
from mymodule import *

# Good
from mymodule import specific_function
```

#### Avoid Exception Handling as Control Flow

```python
# Bad — exception handling has overhead
try:
    value = my_dict[key]
except KeyError:
    value = default

# Good
value = my_dict.get(key, default)
```

#### Avoid Repeated Dictionary Lookups

```python
# Bad — looks up the key twice
if "key" in my_dict and my_dict["key"] > 0:
    use(my_dict["key"])

# Good — single lookup
value = my_dict.get("key")
if value and value > 0:
    use(value)
```

### Profiling

Profile before optimising:

```bash
python -m cProfile -s cumtime script.py
py-spy top --pid <PID>
py-spy record -o profile.svg --pid <PID>
python -m memray run -o output.bin script.py
python -m memray flamegraph output.bin
```

## Python 3.9 (base supported version)

#### Dict Merge Operator

```python
# Good — avoids intermediate dicts
merged = defaults | overrides
config |= overrides

# Bad
merged = {**defaults, **overrides}
```

#### String Prefix/Suffix Removal

```python
# Good — faster and clearer than slicing
name = filename.removesuffix(".json")
base = url.removeprefix("https://")

# Bad
name = filename[:-5] if filename.endswith(".json") else filename
```

#### Built-in Generic Type Hints

```python
# Good — built-in generics avoid importing from typing
def process(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

# Bad — unnecessary in Python 3.9+
from typing import List, Dict
def process(items: List[str]) -> Dict[str, int]: ...
```

## Python 3.10

#### Structural Pattern Matching for Dispatch

```python
# Good — avoids repeated isinstance/dict-get in hot dispatch paths
match event["type"]:
    case "click":
        handle_click(event)
    case "scroll":
        handle_scroll(event)
    case _:
        pass

# Bad
if event.get("type") == "click":
    handle_click(event)
elif event.get("type") == "scroll":
    handle_scroll(event)
```

#### `zip(strict=True)` to Catch Length Mismatches Early

```python
# Good — raises ValueError immediately if lengths differ
for key, value in zip(keys, values, strict=True):
    result[key] = value
```

## Python 3.11

Specialising Adaptive Interpreter: 10-60% speedups over 3.10. No code changes required.

#### `asyncio.TaskGroup` for Structured Concurrent I/O

```python
# Good — starts all tasks concurrently; all exceptions collected
async def fetch_all(urls: list[str]) -> list[bytes]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(url)) for url in urls]
    return [t.result() for t in tasks]

# Bad — sequential awaits
results = [await fetch(url) for url in urls]

# Avoid — gather() swallows exceptions unless return_exceptions=True
results = await asyncio.gather(*[fetch(url) for url in urls])
```

#### `tomllib` for Config Parsing

```python
# Good — stdlib TOML parsing (3.11+); no third-party dependency
import tomllib
with open("pyproject.toml", "rb") as f:
    config = tomllib.load(f)
```

## Python 3.12

#### `itertools.batched()` for Chunked Processing

```python
# Good — no manual slice arithmetic
from itertools import batched
for batch in batched(records, 500):
    db.bulk_insert(batch)

# Bad
for i in range(0, len(records), 500):
    db.bulk_insert(records[i:i + 500])
```

#### `type` Statement for Type Aliases

```python
# Good — evaluated lazily; no runtime overhead (3.12+)
type Vector = list[float]
type Matrix = list[Vector]

# Bad — TypeAlias evaluated eagerly at import time
from typing import TypeAlias
Vector: TypeAlias = list[float]
```

Subinterpreters (PEP 734): 3.12 introduced subinterpreters with their own GIL; stabilised in 3.13.

## Python 3.13

#### `copy.replace()` for Cheap Copy-with-Modification

```python
# Good — immutable copies with field overrides (3.13+)
from copy import replace
from dataclasses import dataclass

@dataclass
class Config:
    host: str
    port: int
    timeout: float = 30.0

base = Config("localhost", 5432)
prod = replace(base, host="db.prod.example.com")

# Bad — manual reconstruction per variant
prod = Config(host="db.prod.example.com", port=base.port, timeout=base.timeout)
```

Improved REPL and error messages; faster startup. No code changes required.

## Python 3.14 (latest stable)

#### Free-Threaded CPython (PEP 703)

Free-threaded CPython removes the GIL for CPU-bound parallel work. Run with `python -X gil=0` or `PYTHON_GIL=0`.

```python
# Good — true thread-level parallelism for CPU work
import threading

def cpu_intensive(n: int) -> int:
    return sum(i * i for i in range(n))

threads = [threading.Thread(target=cpu_intensive, args=(10_000_000,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
# Note: Not all C extensions support free-threading yet — check py-free-threading.github.io
```

#### Deferred Annotation Evaluation (PEP 749)

```python
# Good — forward references resolved lazily by default; no quotes needed
class Node:
    def children(self) -> list[Node]:
        return self._children
```

#### `annotationlib` for Runtime Annotation Introspection

```python
# Good — correct runtime annotation resolution (3.14+)
import annotationlib
hints = annotationlib.get_annotations(MyClass, format=annotationlib.Format.FORWARDREF)
```
