# Django Performance Review Reference

Applies to: Django ORM, Django REST Framework (DRF). Version range: Django 4.2 LTS → 5.2 LTS.

---

## General Django Performance Patterns

### N+1 Query Prevention

Most common Django performance defect. Every list endpoint/serializer traversing a relation is a candidate.

#### `select_related` — ForeignKey / OneToOne

```python
# Good
entries = Entry.objects.select_related("blog").filter(pub_date__gt=cutoff)
for entry in entries:
    print(entry.blog.name)

# Bad — 1 query per entry for blog
entries = Entry.objects.filter(pub_date__gt=cutoff)
for entry in entries:
    print(entry.blog.name)
```

Follow chains: `Book.objects.select_related("author__hometown")`

#### `prefetch_related` — ManyToMany / Reverse FK

```python
# Good — 2 queries total
categories = Category.objects.prefetch_related("item_set").all()
for cat in categories:
    for item in cat.item_set.all():
        print(item.name)

# Bad — N+1
categories = Category.objects.all()
for cat in categories:
    for item in cat.item_set.all():
        print(item.name)
```

Use `Prefetch` objects for filtered sub-querysets:

```python
active_items = Item.objects.filter(is_active=True)
categories = Category.objects.prefetch_related(
    Prefetch("item_set", queryset=active_items, to_attr="active_items")
)
```

Combine both when traversal spans FK and M2M:

```python
Restaurant.objects.select_related("best_pizza").prefetch_related("best_pizza__toppings")
```

### Fetch Only What You Need

```python
# Good — named columns only
items = Item.objects.only("id", "name", "is_active")

# Good — plain dicts
item_data = Item.objects.values("id", "name")

# Good — flat list
ids = list(Item.objects.values_list("id", flat=True))

# Bad — SELECT * when only name used
items = Item.objects.all()
for item in items:
    print(item.name)
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
# Good — LIMIT 1
if Item.objects.filter(category=category, is_active=True).exists():
    ...

# Good — COUNT(*)
total = Item.objects.filter(category=category).count()

# Bad — loads all records to check/count
if len(Item.objects.filter(category=category, is_active=True)) > 0:
    ...
```

### Atomic Field Updates with `F()` Expressions

```python
# Good — single UPDATE, no race condition
Item.objects.filter(pk=item_id).update(view_count=F("view_count") + 1)

# Good — compare fields without fetching
discounted = Item.objects.filter(sale_price__lt=F("regular_price"))

# Bad — read-modify-write race condition
item = Item.objects.get(pk=item_id)
item.view_count += 1
item.save()
```

### Database-Side Filtering — Never Filter in Python

```python
# Good
categories_with_items = Category.objects.annotate(
    item_count=Count("item")
).filter(item_count__gt=0)

# Bad — filters in Python
all_categories = Category.objects.annotate(item_count=Count("item"))
active = [c for c in all_categories if c.item_count > 0]
```

### Pagination

MUST paginate list endpoints. Never return unbounded querysets:

```python
# Good
class ItemViewSet(ModelViewSet):
    queryset = Item.objects.select_related("category").filter(is_active=True)
    pagination_class = PageNumberPagination

# Bad
class ItemViewSet(ModelViewSet):
    queryset = Item.objects.all()
    pagination_class = None
```

For large append-only tables (events, logs), prefer `CursorPagination` — offset-based pagination degrades as offset grows.

### Database Indexes

```python
class Item(models.Model):
    is_active = models.BooleanField(db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=["category", "is_active"]),
        ]
```

MUST measure before adding indexes — every index slows writes. Verify with `EXPLAIN ANALYZE`.

For PostgreSQL, add indexes without locking:

```python
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

QuerySets are lazy — hit DB only at evaluation (iteration, slicing, `count()`, `exists()`, `get()`, `first()`, `last()`, serialization). Evaluate once and reuse:

```python
qs = Item.objects.filter(is_active=True).select_related("category")
items = list(qs)
if items:
    for item in items:
        process(item)
```

### `iterator()` for Large Datasets

```python
# Good — streams in chunks, constant memory
for item in Item.objects.filter(is_active=True).iterator(chunk_size=500):
    process(item)

# Bad — loads all rows into memory
for item in Item.objects.filter(is_active=True):
    process(item)
```

### `select_for_update()` Contention

Acquires row-level locks until transaction commits. Avoid in high-traffic paths:

```python
# Use only when genuine write consistency required
with transaction.atomic():
    item = Item.objects.select_for_update().get(pk=item_id)
    item.reserve()
    item.save()

# Prefer F() or optimistic locking for high-throughput counters
Item.objects.filter(pk=item_id).update(stock=F("stock") - 1)
```

### Caching

```python
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

One-liner cache-aside: `cache.get_or_set(key, lambda: ..., timeout=300)`

### Database Connection Configuration

Tune `CONN_MAX_AGE` to reuse connections:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,  # 4.1+: validate before reuse
    }
}
```

For high concurrency, add `pgbouncer` rather than relying on Django's per-thread pooling.

### Async Offloading with Celery

Move slow operations out of request/response cycle:

```python
@shared_task(bind=True, max_retries=3)
def send_notification(self, record_id: int) -> None:
    try:
        record = Record.objects.get(pk=record_id)
        # ... idempotent work
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

class RecordViewSet(ModelViewSet):
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        send_notification.delay(response.data["id"])
        return response
```

MUST design all Celery tasks to be idempotent.

### Development Profiling Tools

- `django-debug-toolbar` — SQL queries, counts, timing per request. Primary N+1 detection tool.
- `django-silk` — request/SQL profiling with timeline views. Useful for staging.

MUST NOT enable either in production — significant overhead.

## Version-Specific Features

### Django 4.2 LTS

**`CONN_HEALTH_CHECKS`**: Stabilized in 4.2. Silently reconnects stale connections before reuse.

**`aiterator()` not available** until 5.1. Use `sync_to_async` + `iterator()` for async large-dataset streaming:

```python
async def export_items():
    items = await sync_to_async(list)(
        Item.objects.filter(is_active=True).iterator(chunk_size=500)
    )
    for item in items:
        await process(item)
```

### Django 5.0 — `db_default`

Push defaults to database level, avoiding Python round-trip:

```python
class Order(models.Model):
    created_at = models.DateTimeField(db_default=Now())
```

### Django 5.1 — `QuerySet.aiterator()`

Native async streaming for large querysets:

```python
# Good
async def export_items():
    async for item in Item.objects.filter(is_active=True).aiterator(chunk_size=500):
        await process(item)
```

### Django 5.2 LTS — Async `transaction.aatomic()`

Native async atomic block, replacing `sync_to_async(transaction.atomic)` workarounds:

```python
# Good
async def transfer_funds(from_id: int, to_id: int, amount: int) -> None:
    async with transaction.aatomic():
        sender = await Account.objects.select_for_update().aget(pk=from_id)
        receiver = await Account.objects.select_for_update().aget(pk=to_id)
        sender.balance -= amount
        receiver.balance += amount
        await sender.asave()
        await receiver.asave()
```

### Django 5.2 LTS — Composite Primary Keys

`CompositePrimaryKey` avoids surrogate integer PK overhead on junction tables. Ensure ORM is not performing extra queries to resolve relationships with composite-key models.
