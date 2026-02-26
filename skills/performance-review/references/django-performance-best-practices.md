# Django Performance Best Practices

Applies to: Django ORM, Django REST Framework (DRF)

---

## Database Query Optimization

### Use `select_related` for ForeignKey / OneToOne

```python
# Good — single JOIN query
items = Item.objects.select_related("category", "owner").filter(is_active=True)
for item in items:
    print(item.category.name)  # No extra query

# Bad — N+1: 1 query for items + 1 per item for category
items = Item.objects.filter(is_active=True)
for item in items:
    print(item.category.name)  # Extra query per item
```

### Use `prefetch_related` for ManyToMany / Reverse FK

```python
# Good — 2 queries total
categories = Category.objects.prefetch_related("item_set").all()
for category in categories:
    items = category.item_set.all()  # No extra query

# Bad — N+1
categories = Category.objects.all()
for category in categories:
    items = category.item_set.all()  # Extra query per category
```

### Use `only()` or `values()` for Specific Fields

```python
# Good — fetches only needed columns
items = Item.objects.only("id", "name", "is_active")

# Good — returns dicts (even lighter than model instances)
item_data = Item.objects.values("id", "name")

# Good — flat list of a single field
ids = Item.objects.values_list("id", flat=True)

# Bad — SELECT * when only a few fields are needed
items = Item.objects.all()
```

### Use `bulk_create` and `bulk_update`

```python
# Good — single INSERT
Item.objects.bulk_create([
    Item(name=f"Item {i}", category=category) for i in range(100)
])

# Good — single UPDATE
for item in items:
    item.is_active = False
Item.objects.bulk_update(items, ["is_active"])

# Bad — N queries
for i in range(100):
    Item.objects.create(name=f"Item {i}", category=category)
```

### Use `exists()` for Boolean Checks

```python
# Good — stops at first match
if Item.objects.filter(category=category, is_active=True).exists():
    ...

# Bad — counts everything
if Item.objects.filter(category=category, is_active=True).count() > 0:
    ...

# Bad — loads all objects into memory
if len(Item.objects.filter(category=category, is_active=True)) > 0:
    ...
```

### Use `count()` Instead of `len()` for Count-Only

```python
# Good — COUNT(*) at the DB level
total = Item.objects.filter(category=category).count()

# Bad — loads all records into memory just to count
total = len(Item.objects.filter(category=category))
```

---

## QuerySet Evaluation Points

QuerySets are lazy — they only hit the database when:
- Iterated over
- Sliced with a step (`qs[1:10]`)
- Converted with `list(qs)`
- Called with `.count()`, `.exists()`, `.get()`, `.first()`, `.last()`
- Serialized

```python
# This doesn't hit the DB yet
qs = Item.objects.filter(is_active=True).select_related("category")

# This evaluates (hits DB) — cache the result
items = list(qs)

# Both reuse cached list — no extra queries
if items:
    for item in items:
        ...
```

---

## Pagination

Always paginate list endpoints — never return unbounded querysets:

```python
# Good — DRF pagination handles this
class ItemViewSet(ModelViewSet):
    pagination_class = StandardResultsSetPagination

# Bad — returns all records
class ItemViewSet(ModelViewSet):
    pagination_class = None  # Never for large tables
```

---

## Database Indexes

Add indexes for frequently filtered or sorted fields:

```python
class Item(models.Model):
    id = models.UUIDField(primary_key=True)       # Primary key is indexed
    is_active = models.BooleanField(db_index=True) # Frequently filtered
    category = models.ForeignKey(Category, on_delete=models.CASCADE)  # FK auto-indexed

    class Meta:
        indexes = [
            models.Index(fields=["category", "is_active"]),  # Composite index
        ]
```

Don't add indexes blindly — verify query plans and measure impact.

---

## Caching

Use Django's cache framework for expensive, frequently read data:

```python
from django.core.cache import cache

def get_config(config_id: int) -> dict:
    cache_key = f"config_{config_id}"
    config = cache.get(cache_key)
    if config is None:
        config = Config.objects.get(pk=config_id).to_dict()
        cache.set(cache_key, config, timeout=300)  # 5 minutes
    return config

# Always invalidate on change
def update_config(config_id: int, data: dict) -> None:
    Config.objects.filter(pk=config_id).update(**data)
    cache.delete(f"config_{config_id}")
```

---

## select_for_update() Contention

`select_for_update()` acquires a row-level lock until the transaction commits. Avoid it in high-traffic paths:

```python
# Use only when genuinely needed for consistency — it serializes requests on the same rows
with transaction.atomic():
    item = Item.objects.select_for_update().get(pk=item_id)
    item.reserve()
    item.save()

# Prefer F() expressions or optimistic locking (version field) for high-throughput counters
```

---

## Async Offloading with Celery

Move slow operations out of the request cycle:

```python
from celery import shared_task

@shared_task
def send_notification(record_id: int) -> None:
    record = Record.objects.get(pk=record_id)
    # ... heavy work

# In view — fast response, task runs in background
class RecordViewSet(ModelViewSet):
    def create(self, request):
        record = self.perform_create(self.get_serializer(data=request.data))
        send_notification.delay(record.pk)  # Non-blocking
        return Response(status=201)

# Bad — blocks the request
class RecordViewSet(ModelViewSet):
    def create(self, request):
        record = self.perform_create(...)
        send_notification_synchronously(record)  # Blocks until done
        return Response(status=201)

# Design Celery tasks to be idempotent — safe to retry on failure
@shared_task(bind=True, max_retries=3)
def send_notification(self, record_id: int) -> None:
    try:
        record = Record.objects.get(pk=record_id)
        # ... idempotent work
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)  # exponential backoff
```

---

## F() Expressions for Database-Side Arithmetic

Use `F()` to perform arithmetic at the database level — avoiding a round-trip and race conditions:

```python
from django.db.models import F

# Good — single UPDATE in the database; no race condition
Item.objects.filter(pk=item_id).update(view_count=F("view_count") + 1)

# Bad — read + write in Python; race condition under concurrency
item = Item.objects.get(pk=item_id)
item.view_count += 1
item.save()
```

`F()` also works in annotations and filters:

```python
# Good — compare two fields in the database
discounted = Item.objects.filter(sale_price__lt=F("regular_price"))
```

---

## Database Connection Pooling

Django opens a new database connection per thread (or per request in a thread-per-request server). Without tuning, this creates connection pressure at scale:

```python
# settings.py — keep connections alive for up to 60 seconds instead of closing after each request
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "CONN_MAX_AGE": 60,  # seconds; 0 = close after each request (default)
    }
}
```

For very high connection counts, add a connection pooler (e.g. `pgbouncer`) in front of PostgreSQL rather than relying solely on Django's per-thread pooling.

---

## Development Profiling Tooling

Install these tools to identify performance issues during development:

```bash
pip install django-debug-toolbar django-silk
```

- **`django-debug-toolbar`** — shows SQL queries, query counts, and timing per request in the browser. The most important tool for catching N+1 issues in development.
- **`django-silk`** — request and SQL profiling with timeline views. Useful for profiling complex views or identifying slow queries in staging.

Do not enable these in production — they carry significant overhead.

---

## `QuerySet.iterator()` for Large Datasets

```python
# Good — processes records in chunks, low memory usage
for item in Item.objects.filter(is_active=True).iterator(chunk_size=500):
    process(item)

# Bad — loads all 100k records into memory at once
for item in Item.objects.filter(is_active=True):
    process(item)
```

---

## Avoid `annotate()` + Python-Side Filtering

```python
# Good — filter in the database
categories_with_items = Category.objects.annotate(
    item_count=Count("item")
).filter(item_count__gt=0)

# Bad — loads all categories, filters in Python
all_categories = Category.objects.annotate(item_count=Count("item"))
categories_with_items = [c for c in all_categories if c.item_count > 0]
```

---

## Resources

- [Django QuerySet API](https://docs.djangoproject.com/en/stable/ref/models/querysets/)
- [Django Database Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/)
- [Django Caching Framework](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Django Database Access Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/)
- [DRF Pagination](https://www.django-rest-framework.org/api-guide/pagination/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html#tips-and-best-practices)
