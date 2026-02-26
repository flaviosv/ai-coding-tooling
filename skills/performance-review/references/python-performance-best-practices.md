# Python Performance Best Practices

Applies to: Python 3.9+

---

## Avoid Unnecessary Work

### Use Generators Instead of Lists When Possible

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

### Use `any()` and `all()` for Short-Circuit Evaluation

```python
# Good — stops at first match
if any(item.is_active for item in items):
    ...

# Bad — evaluates everything
if True in [item.is_active for item in items]:
    ...
```

---

## String Operations

### Use `join()` for String Concatenation

```python
# Good — single allocation
parts = ["Hello", " ", "World"]
result = "".join(parts)

# Bad — creates new string each iteration
result = ""
for part in parts:
    result += part
```

### Prefer f-strings for Formatting

```python
# Good — fastest option in Python 3.6+
label = f"Item: {item.name} ({item.id})"

# Acceptable — but slower than f-strings
label = "Item: {} ({})".format(item.name, item.id)

# Avoid — old style
label = "Item: %s (%s)" % (item.name, item.id)
```

---

## Data Structures

### Use Sets for Membership Testing

```python
# Good — O(1) lookup
active_ids = {item.id for item in queryset.filter(is_active=True)}
if item_id in active_ids:
    ...

# Bad — O(n) lookup
active_ids = [item.id for item in queryset.filter(is_active=True)]
if item_id in active_ids:  # Linear scan
    ...
```

### Use `collections.defaultdict` and `Counter`

```python
from collections import defaultdict, Counter

# Good — avoid repeated get/set pattern
counts_by_category = defaultdict(int)
for item in items:
    counts_by_category[item.category_id] += 1

# Good — counting occurrences
category_counts = Counter(item.category_id for item in items)
most_common = category_counts.most_common(5)
```

---

## Memoization with functools.cache / lru_cache

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

⚠️ **Memory leak risk with instance methods:** `@cache` on an instance method captures `self` as a cache key, preventing GC of the instance. Use module-level functions or `functools.cached_property` for instance-level caching instead:

```python
# Bad — prevents GC of self (memory leak for long-lived instance caches)
class RateCalculator:
    @cache
    def get_rate(self, currency: str) -> float: ...

# Good — cached_property for per-instance lazy computation (no GC issue)
class RateCalculator:
    @functools.cached_property
    def default_rate(self) -> float:
        return self._compute_default()
```

---

## Function Design

### Cache Attribute Lookups in Hot Loops

> ⚠️ This micro-optimisation is largely irrelevant in Python 3.11+ where the Specialising Adaptive Interpreter handles attribute lookup optimisation automatically. Prefer the list comprehension form for readability.

```python
# Good — list comprehension is generally the fastest and most readable
results = [process(item) for item in items]

# Rarely needed in modern Python (3.11+) — attribute caching
append = results.append
for item in items:
    append(process(item))
```

---

## Profiling

When you suspect a performance issue, profile before optimising:

```bash
# Python built-in profiler
python -m cProfile -s cumtime script.py

# Line-by-line profiling (requires line_profiler)
@profile
def slow_function():
    ...
```

**Production-safe profilers:**
- **`py-spy`** — sampling profiler that attaches to a running process without restarting it. Safe for production use:
  ```bash
  py-spy top --pid <PID>           # live top-like view
  py-spy record -o profile.svg --pid <PID>  # flame graph
  ```
- **`memray`** — memory profiler that tracks allocations and produces flame graphs and memory timelines:
  ```bash
  python -m memray run -o output.bin script.py
  python -m memray flamegraph output.bin
  ```

---

## Common Anti-Patterns

### ❌ `import *`

```python
# Bad — imports everything, pollutes namespace, slower startup
from mymodule import *

# Good — explicit imports
from mymodule import specific_function
```

### ❌ Exception Handling as Control Flow

```python
# Bad — exception handling has overhead
try:
    value = my_dict[key]
except KeyError:
    value = default

# Good — use dict.get()
value = my_dict.get(key, default)
```

### ❌ Repeated Dictionary Lookups

```python
# Bad — looks up the key twice
if "key" in my_dict and my_dict["key"] > 0:
    use(my_dict["key"])

# Good — single lookup
value = my_dict.get("key")
if value and value > 0:
    use(value)
```

---

## Python Version-Specific Performance Features

### Python 3.9+ Performance

```python
# Good — dict merge operator avoids creating intermediate dicts
merged = defaults | overrides

# Bad — {**a, **b} creates two intermediate dicts
merged = {**defaults, **overrides}
```

```python
# Good — str.removeprefix/removesuffix are faster and clearer than slicing
name = filename.removesuffix(".json")

# Bad — manual slicing or replace()
name = filename[:-5] if filename.endswith(".json") else filename
```

### Python 3.10+ Performance

```python
# Good — match/case avoids repeated isinstance checks in hot dispatch paths
match event["type"]:
    case "click":
        handle_click(event)
    case "scroll":
        handle_scroll(event)
    case _:
        pass

# Bad — repeated isinstance/get for the same key
if event.get("type") == "click":
    handle_click(event)
elif event.get("type") == "scroll":
    handle_scroll(event)
```

### Python 3.11+ Performance

Python 3.11 introduced the Specialising Adaptive Interpreter — benchmarks show 10–60% speedups over 3.10 for typical workloads. No code changes required; upgrading the interpreter is sufficient.

```python
# Good — asyncio.TaskGroup for structured concurrent I/O (Python 3.11+)
# All tasks start concurrently and all exceptions are collected.
async def fetch_all(urls: list[str]) -> list[bytes]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(url)) for url in urls]
    return [t.result() for t in tasks]

# Bad — sequential awaits
results = [await fetch(url) for url in urls]
```

### Python 3.12+ Performance

```python
# Good — itertools.batched() for chunked processing; no manual slice arithmetic
from itertools import batched

for batch in batched(records, 500):
    db.bulk_insert(batch)

# Bad — manual chunking
for i in range(0, len(records), 500):
    db.bulk_insert(records[i:i + 500])
```

### Python 3.14+ Performance

```python
# Good — free-threaded CPython removes the GIL for CPU-bound parallel work (Python 3.14+)
# Run with: python -X gil=0 script.py
# Or set: PYTHON_GIL=0 environment variable
# Previously, threading was ineffective for CPU-bound work due to the GIL.
# With free-threading, threads can now execute Python bytecode truly in parallel.
# Note: Not all third-party C extensions support free-threading yet — check compatibility.

import threading

def cpu_intensive(n: int) -> int:
    return sum(i * i for i in range(n))

# With free-threading, these threads run in parallel on multiple cores
threads = [threading.Thread(target=cpu_intensive, args=(10_000_000,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
```

### Python 3.13+ Performance

```python
# Good — copy.replace() for cheap copy-with-modification of dataclass-like objects
from copy import replace
from dataclasses import dataclass

@dataclass
class Config:
    host: str
    port: int
    timeout: float = 30.0

base = Config("localhost", 5432)
prod = replace(base, host="db.prod.example.com")

# Bad — manual reconstruction
prod = Config(host="db.prod.example.com", port=base.port, timeout=base.timeout)
```

---

## Resources

- [Python Data Model](https://docs.python.org/3/reference/datamodel.html)
- [Time Complexity of Python Built-ins](https://wiki.python.org/moin/TimeComplexity)
- [Python Profilers (cProfile, profile)](https://docs.python.org/3/library/profile.html)
- [collections — Container Datatypes](https://docs.python.org/3/library/collections.html)
- [functools — Higher-order Functions](https://docs.python.org/3/library/functools.html)
- [Python Performance Tips (Python Wiki)](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)
- [Python 3.11 What's New](https://docs.python.org/3/whatsnew/3.11.html)
- [Python 3.12 What's New](https://docs.python.org/3/whatsnew/3.12.html)
- [Python 3.13 What's New](https://docs.python.org/3/whatsnew/3.13.html)
- [asyncio.TaskGroup](https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup)
- [itertools.batched](https://docs.python.org/3/library/itertools.html#itertools.batched)
