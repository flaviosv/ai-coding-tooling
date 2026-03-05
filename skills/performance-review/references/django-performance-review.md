# Django Performance Review Reference

Applies to: Django ORM, Django REST Framework (DRF).
Supported version range: Django 4.2 LTS (base) → Django 5.2 LTS (latest).

---

## General Django Performance Patterns

These patterns apply across all still-supported Django versions (4.2–5.2).

### N+1 Query Prevention

N+1 queries are the most common Django performance defect. Every list endpoint and every serializer that traverses a relation is a candidate.

#### `select_related` — ForeignKey / OneToOne

```python
# Good — single JOIN query regardless of item count
entries = Entry.objects.select_related("blog").filter(pub_date__gt=cutoff)
for entry in entries:
    print(entry.blog.name)  # No extra query

# Bad — 1 query for entries + 1 per entry for blog
entries = Entry.objects.filter(pub_date__gt=cutoff)
for entry in entries:
    print(entry.blog.name)  # Extra DB hit each iteration
```

Follow chains to avoid repeated round-trips:

```python
# Single query with two JOINs
books = Book.objects.select_related("author__hometown")
```

#### `prefetch_related` — ManyToMany / Reverse FK

```python
# Good — 2 queries total regardless of category count
categories = Category.objects.prefetch_related("item_set").all()
for cat in categories:
    for item in cat.item_set.all():  # No extra query — already prefetched
        print(item.name)

# Bad — N+1
categories = Category.objects.all()
for cat in categories:
    for item in cat.item_set.all():  # 1 extra query per category
        print(item.name)
```

Use `Prefetch` objects for filtered sub-querysets:

```python
from django.db.models import Prefetch

active_items = Item.objects.filter(is_active=True)
categories = Category.objects.prefetch_related(
    Prefetch("item_set", queryset=active_items, to_attr="active_items")
)
# Now cat.active_items is a list — no extra queries
```

Combine both when traversal spans both FK and M2M:

```python
Restaurant.objects.select_related("best_pizza").prefetch_related("best_pizza__toppings")
```

### Fetch Only What You Need

```python
# Good — fetches only named columns; lighter than full model instances
items = Item.objects.only("id", "name", "is_active")

# Good — returns plain dicts; even lighter
item_data = Item.objects.values("id", "name")

# Good — flat list of a single field
ids = list(Item.objects.values_list("id", flat=True))

# Bad — SELECT * when only a few fields are used
items = Item.objects.all()
for item in items:
    print(item.name)  # Only name is used, but entire row is fetched
```

### Bulk Operations

```python
# Good — single INSERT
Item.objects.bulk_create([
    Item(name=f"Item {i}", category=category) for i in range(200)
])

# Good — single UPDATE
for item in items:
    item.is_active = False
Item.objects.bulk_update(items, ["is_active"])

# Bad — N queries
for i in range(200):
    Item.objects.create(name=f"Item {i}", category=category)
```

### Existence and Count Checks

```python
# Good — stops at first match (LIMIT 1)
if Item.objects.filter(category=category, is_active=True).exists():
    ...

# Good — COUNT(*) at the DB level
total = Item.objects.filter(category=category).count()

# Bad — loads all records into memory just to check existence
if len(Item.objects.filter(category=category, is_active=True)) > 0:
    ...

# Bad — loads all records to count them
total = len(Item.objects.filter(category=category))
```

### Atomic Field Updates with `F()` Expressions

```python
from django.db.models import F

# Good — single UPDATE at the database level; no race condition
Item.objects.filter(pk=item_id).update(view_count=F("view_count") + 1)

# Good — compare two fields without fetching the row
discounted = Item.objects.filter(sale_price__lt=F("regular_price"))

# Bad — read-modify-write in Python; race condition under concurrency
item = Item.objects.get(pk=item_id)
item.view_count += 1
item.save()
```

### Database-Side Filtering — Never Filter in Python

```python
# Good — filter and aggregate in the database
categories_with_items = Category.objects.annotate(
    item_count=Count("item")
).filter(item_count__gt=0)

# Bad — loads all categories into memory, filters in Python
all_categories = Category.objects.annotate(item_count=Count("item"))
active = [c for c in all_categories if c.item_count > 0]
```

### Pagination

Always paginate list endpoints. Never return unbounded querysets from views:

```python
# Good — DRF pagination class applied
class ItemViewSet(ModelViewSet):
    queryset = Item.objects.select_related("category").filter(is_active=True)
    pagination_class = PageNumberPagination

# Bad — all records returned with no limit
class ItemViewSet(ModelViewSet):
    queryset = Item.objects.all()
    pagination_class = None
```

For large, append-only tables (e.g. events, logs), prefer `CursorPagination` over `PageNumberPagination` — offset-based pagination degrades as offset grows.

### Database Indexes

```python
class Item(models.Model):
    is_active = models.BooleanField(db_index=True)       # Single-column index
    category = models.ForeignKey(Category, on_delete=models.CASCADE)  # FK auto-indexed

    class Meta:
        indexes = [
            models.Index(fields=["category", "is_active"]),  # Composite index for combined filters
        ]
```

Do not add indexes without measuring — every index slows writes. Verify query plans with `EXPLAIN ANALYZE`.

For PostgreSQL, add indexes without locking the table:

```python
# migrations/0005_add_item_index.py
from django.db import migrations, models

class Migration(migrations.Migration):
    atomic = False  # Required for CONCURRENTLY

    operations = [
        migrations.AddIndex(
            model_name="item",
            index=models.Index(fields=["category", "is_active"], name="item_cat_active_idx"),
        ),
    ]
```

### QuerySet Laziness and Caching

QuerySets are lazy — they hit the database only at evaluation (iteration, slicing, `count()`, `exists()`, `get()`, `first()`, `last()`, serialization). Evaluate once and reuse the result:

```python
qs = Item.objects.filter(is_active=True).select_related("category")

# This evaluates (DB hit) — cache the result
items = list(qs)

# Both reuse the Python list — no additional queries
if items:
    for item in items:
        process(item)
```

### `iterator()` for Large Datasets

```python
# Good — streams records in chunks; constant memory usage regardless of row count
for item in Item.objects.filter(is_active=True).iterator(chunk_size=500):
    process(item)

# Bad — loads all 100k rows into memory at once
for item in Item.objects.filter(is_active=True):
    process(item)
```

### `select_for_update()` Contention

`select_for_update()` acquires row-level locks until the transaction commits. Avoid it in high-traffic paths:

```python
# Use only when genuine write consistency is required
with transaction.atomic():
    item = Item.objects.select_for_update().get(pk=item_id)
    item.reserve()
    item.save()

# Prefer F() expressions or optimistic locking for high-throughput counters
Item.objects.filter(pk=item_id).update(stock=F("stock") - 1)
```

### Caching

Use Django's cache framework for expensive, frequently read data:

```python
from django.core.cache import cache

def get_config(config_id: int) -> dict:
    cache_key = f"config:{config_id}"
    result = cache.get(cache_key)
    if result is None:
        result = Config.objects.get(pk=config_id).to_dict()
        cache.set(cache_key, result, timeout=300)
    return result

# Always invalidate on mutation
def update_config(config_id: int, data: dict) -> None:
    Config.objects.filter(pk=config_id).update(**data)
    cache.delete(f"config:{config_id}")
```

Use `cache.get_or_set()` for a one-liner cache-aside pattern:

```python
config = cache.get_or_set(
    f"config:{config_id}",
    lambda: Config.objects.get(pk=config_id).to_dict(),
    timeout=300,
)
```

### Database Connection Configuration

Django opens a new database connection per thread by default. Tune `CONN_MAX_AGE` to reuse connections across requests:

```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "CONN_MAX_AGE": 60,       # Reuse connections for up to 60 seconds
        "CONN_HEALTH_CHECKS": True,  # Django 4.1+: validate connection before reuse
    }
}
```

For very high concurrency, add `pgbouncer` in front of PostgreSQL rather than relying solely on Django's per-thread pooling.

### Async Offloading with Celery

Move slow operations out of the request/response cycle:

```python
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def send_notification(self, record_id: int) -> None:
    try:
        record = Record.objects.get(pk=record_id)
        # ... idempotent work
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

# In view — fast response, task runs in background
class RecordViewSet(ModelViewSet):
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        send_notification.delay(response.data["id"])
        return response
```

Design all Celery tasks to be idempotent — safe to retry without unintended side effects.

### Development Profiling Tools

```bash
pip install django-debug-toolbar django-silk
```

- `django-debug-toolbar` — shows SQL queries, query counts, and timing per request. The primary tool for catching N+1 in development.
- `django-silk` — request and SQL profiling with timeline views. Useful for staging profiling.

Do not enable either in production — both carry significant overhead.

---

## Django 4.2 (LTS — base version)

### `CONN_HEALTH_CHECKS` Setting

Introduced in Django 4.1, stabilized in 4.2:

```python
DATABASES = {
    "default": {
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,  # Silently reconnects stale connections before reuse
    }
}
```

### `QuerySet.aiterator()` Absence

`aiterator()` is not available until Django 5.1. Use `sync_to_async` + `iterator()` for async large-dataset streaming in Django 4.2:

```python
from asgiref.sync import sync_to_async

async def export_items():
    items = await sync_to_async(list)(
        Item.objects.filter(is_active=True).iterator(chunk_size=500)
    )
    for item in items:
        await process(item)
```

---

## Django 5.0

### `db_default` — Push Defaults to the Database

`db_default` computes defaults at the database level, avoiding a Python round-trip:

```python
from django.db.models.functions import Now
from django.db import models

class Order(models.Model):
    created_at = models.DateTimeField(db_default=Now())
    # The DB sets created_at — no Python call required at insert time
```

No extra migration step for existing rows — the DB handles it on insert.

---

## Django 5.1

### `QuerySet.aiterator()` — Native Async Streaming

Django 5.1 adds `aiterator()` for memory-efficient async streaming of large querysets:

```python
# Good — streams without loading all records into memory
async def export_items():
    async for item in Item.objects.filter(is_active=True).aiterator(chunk_size=500):
        await process(item)
```

---

## Django 5.2 (LTS — latest version)

### Async `transaction.aatomic()`

Django 5.2 adds `transaction.aatomic()` as an async context manager, removing the need for `sync_to_async(transaction.atomic)` workarounds in async views:

```python
# Good — native async atomic block (Django 5.2+)
from django.db import transaction

async def transfer_funds(from_id: int, to_id: int, amount: int) -> None:
    async with transaction.aatomic():
        sender = await Account.objects.select_for_update().aget(pk=from_id)
        receiver = await Account.objects.select_for_update().aget(pk=to_id)
        sender.balance -= amount
        receiver.balance += amount
        await sender.asave()
        await receiver.asave()
```

### Composite Primary Keys

Models with composite PKs (`CompositePrimaryKey`) avoid the overhead of a surrogate integer PK on junction tables. Ensure the ORM is not performing extra queries to resolve relationships with composite-key models.

---

## Resources

- [Django QuerySet API](https://docs.djangoproject.com/en/stable/ref/models/querysets/)
- [Django Database Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/)
- [Django Caching Framework](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Django Async Support](https://docs.djangoproject.com/en/stable/topics/async/)
- [DRF Pagination](https://www.django-rest-framework.org/api-guide/pagination/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html#tips-and-best-practices)
- [django-debug-toolbar](https://django-debug-toolbar.readthedocs.io/en/latest/)
- [django-silk](https://github.com/jazzband/django-silk)
- [Django 5.2 Release Notes](https://docs.djangoproject.com/en/5.2/releases/5.2/)
