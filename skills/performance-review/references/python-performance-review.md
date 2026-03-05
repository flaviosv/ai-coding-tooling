# Python Reference — performance-review

<!-- General section covers conventions that apply across ALL still-supported Python versions (3.9–3.14) -->
## General Python Performance Patterns

### Avoid Unnecessary Work

#### Use Generators Instead of Lists When Possible

```python
# Good — lazy evaluation, memory efficient
def get_names(items):
    return (item.name for item in items)

# Use when you need to iterate once
for name in get_names(items):
    process(name)

# Bad — creates full list in memory
def get_names(items):
    return [item.name for item in items]
```

#### Use `any()` and `all()` for Short-Circuit Evaluation

```python
# Good — stops at first match
if any(item.is_active for item in items):
    ...

# Bad — evaluates everything
if True in [item.is_active for item in items]:
    ...
```

### String Operations

#### Use `join()` for String Concatenation

```python
# Good — single allocation
parts = ["Hello", " ", "World"]
result = "".join(parts)

# Bad — creates new string each iteration
result = ""
for part in parts:
    result += part
```

#### Prefer f-strings for Formatting

```python
# Good — fastest option in Python 3.6+
label = f"Item: {item.name} ({item.id})"

# Acceptable — but slower than f-strings
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
if item_id in active_ids:  # Linear scan
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

# Good — cache the result of an expensive pure function
@cache  # equivalent to @lru_cache(maxsize=None)
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
# Bad — prevents GC of self (memory leak for long-lived instance caches)
class RateCalculator:
    @cache
    def get_rate(self, currency: str) -> float: ...

# Good — cached_property for per-instance lazy computation (no GC issue)
import functools

class RateCalculator:
    @functools.cached_property
    def default_rate(self) -> float:
        return self._compute_default()
```

### Common Anti-Patterns

#### Avoid `import *`

```python
# Bad — imports everything, pollutes namespace, slower startup
from mymodule import *

# Good — explicit imports
from mymodule import specific_function
```

#### Avoid Exception Handling as Control Flow

```python
# Bad — exception handling has overhead
try:
    value = my_dict[key]
except KeyError:
    value = default

# Good — use dict.get()
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

When you suspect a performance issue, profile before optimising:

```bash
# Python built-in profiler
python -m cProfile -s cumtime script.py

# Statistical profiler — attaches to a running process without restart; safe for production
py-spy top --pid <PID>
py-spy record -o profile.svg --pid <PID>  # flame graph

# Memory profiler — tracks allocations and produces flame graphs and memory timelines
python -m memray run -o output.bin script.py
python -m memray flamegraph output.bin
```

---

## Python 3.9  (base supported version)

### Dict Merge Operator

```python
# Good — dict merge operator; avoids creating intermediate dicts
merged = defaults | overrides

# Dict update operator for in-place merge
config |= overrides

# Bad — {**a, **b} creates two intermediate dicts
merged = {**defaults, **overrides}
```

### String Prefix/Suffix Removal

```python
# Good — str.removeprefix/removesuffix are faster and clearer than slicing
name = filename.removesuffix(".json")
base = url.removeprefix("https://")

# Bad — manual slicing or replace()
name = filename[:-5] if filename.endswith(".json") else filename
```

### Built-in Generic Type Hints

```python
# Good — built-in generics avoid importing from typing
def process(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

# Bad — importing List/Dict from typing is unnecessary in Python 3.9+
from typing import List, Dict
def process(items: List[str]) -> Dict[str, int]: ...
```

---

## Python 3.10

### Structural Pattern Matching for Dispatch

```python
# Good — match/case avoids repeated isinstance/dict-get in hot dispatch paths
match event["type"]:
    case "click":
        handle_click(event)
    case "scroll":
        handle_scroll(event)
    case _:
        pass

# Bad — repeated get() calls on each branch
if event.get("type") == "click":
    handle_click(event)
elif event.get("type") == "scroll":
    handle_scroll(event)
```

### `zip(strict=True)` to Catch Length Mismatches Early

```python
# Good — raises ValueError immediately if lengths differ, prevents silent bugs
for key, value in zip(keys, values, strict=True):
    result[key] = value
```

---

## Python 3.11

### Specialising Adaptive Interpreter

Python 3.11 introduced the Specialising Adaptive Interpreter. Benchmarks show 10–60% speedups over 3.10 for typical workloads. No code changes required; upgrading the interpreter alone is sufficient.

### `asyncio.TaskGroup` for Structured Concurrent I/O

```python
# Good — TaskGroup starts all tasks concurrently; all exceptions are collected
async def fetch_all(urls: list[str]) -> list[bytes]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(url)) for url in urls]
    return [t.result() for t in tasks]

# Bad — sequential awaits; no concurrency
results = [await fetch(url) for url in urls]

# Avoid — asyncio.gather() swallows exceptions unless return_exceptions=True
results = await asyncio.gather(*[fetch(url) for url in urls])
```

### `tomllib` for Config Parsing

```python
# Good — standard library TOML parsing (Python 3.11+); no third-party dependency
import tomllib

with open("pyproject.toml", "rb") as f:
    config = tomllib.load(f)
```

---

## Python 3.12

### `itertools.batched()` for Chunked Processing

```python
# Good — itertools.batched() for chunked processing; no manual slice arithmetic
from itertools import batched

for batch in batched(records, 500):
    db.bulk_insert(batch)

# Bad — manual chunking with slice arithmetic
for i in range(0, len(records), 500):
    db.bulk_insert(records[i:i + 500])
```

### `type` Statement for Type Aliases

```python
# Good — type statement is evaluated lazily; no runtime overhead (Python 3.12+)
type Vector = list[float]
type Matrix = list[Vector]

# Bad — TypeAlias is evaluated eagerly at import time (Python 3.10–3.11 style)
from typing import TypeAlias
Vector: TypeAlias = list[float]
```

### Subinterpreters for True Parallelism (Preview)

Python 3.12 introduced support for running subinterpreters with their own GIL. Use via `interpreters` module (PEP 734, stabilised in 3.13).

---

## Python 3.13

### `copy.replace()` for Cheap Copy-with-Modification

```python
# Good — copy.replace() for immutable copies with field overrides (Python 3.13+)
from copy import replace
from dataclasses import dataclass

@dataclass
class Config:
    host: str
    port: int
    timeout: float = 30.0

base = Config("localhost", 5432)
prod = replace(base, host="db.prod.example.com")

# Bad — manual reconstruction repeated per variant
prod = Config(host="db.prod.example.com", port=base.port, timeout=base.timeout)
```

### Improved REPL and Error Messages

Python 3.13 delivers faster startup and improved error messages. No code changes required.

---

## Python 3.14  (latest stable)

### Free-Threaded CPython (PEP 703)

Python 3.14 includes free-threaded CPython as a supported (non-experimental) build. This removes the GIL for CPU-bound parallel work when running `python -X gil=0` or setting `PYTHON_GIL=0`.

```python
# Good — free-threaded CPython allows true thread-level parallelism for CPU work
# Run with: python -X gil=0 script.py  (or set PYTHON_GIL=0)
import threading

def cpu_intensive(n: int) -> int:
    return sum(i * i for i in range(n))

# With free-threading enabled, these threads run in parallel on multiple cores
threads = [threading.Thread(target=cpu_intensive, args=(10_000_000,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

# Note: Not all third-party C extensions support free-threading yet — check compatibility
# Check: https://py-free-threading.github.io/
```

### Deferred Annotation Evaluation (PEP 749)

```python
# Good — forward references are now resolved lazily by default; no quotes needed
# This eliminates runtime cost for annotation evaluation
class Node:
    def children(self) -> list[Node]:  # "Node" is not yet defined, but works now
        return self._children
```

### `annotationlib` for Runtime Annotation Introspection

```python
# Good — use annotationlib for correct runtime annotation resolution (Python 3.14+)
import annotationlib

hints = annotationlib.get_annotations(MyClass, format=annotationlib.Format.FORWARDREF)
```

---

## Resources

- [Python Data Model](https://docs.python.org/3/reference/datamodel.html)
- [Time Complexity of Python Built-ins](https://wiki.python.org/moin/TimeComplexity)
- [Python Profilers (cProfile, profile)](https://docs.python.org/3/library/profile.html)
- [collections — Container Datatypes](https://docs.python.org/3/library/collections.html)
- [functools — Higher-order Functions](https://docs.python.org/3/library/functools.html)
- [asyncio.TaskGroup](https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup)
- [itertools.batched](https://docs.python.org/3/library/itertools.html#itertools.batched)
- [Python 3.11 What's New — Specialising Adaptive Interpreter](https://docs.python.org/3/whatsnew/3.11.html)
- [Python 3.12 What's New](https://docs.python.org/3/whatsnew/3.12.html)
- [Python 3.13 What's New](https://docs.python.org/3/whatsnew/3.13.html)
- [Python 3.14 What's New](https://docs.python.org/3.14/whatsnew/3.14.html)
- [Free-threaded CPython compatibility tracker](https://py-free-threading.github.io/)
- [py-spy — Sampling Profiler](https://github.com/benfred/py-spy)
- [memray — Memory Profiler](https://bloomberg.github.io/memray/)
