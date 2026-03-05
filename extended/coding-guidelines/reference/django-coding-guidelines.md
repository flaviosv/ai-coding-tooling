# Python + Django Coding Style Guide

> Load this file together with `python-coding-guidelines.md`. Rules here are additive and Django-specific.
> Supported version range: Django 4.2 LTS (base) → Django 5.2 LTS (latest).

---

## General Django Coding Conventions

Conventions that apply across all still-supported Django versions (4.2–5.2).

### Project Layout

- Follow the standard Django app layout: `models.py`, `views.py`, `urls.py`, `serializers.py`, `admin.py`, `tests/`
- Split large apps into sub-modules: `models/`, `views/`, `serializers/`, `services/` — keep each file focused on one responsibility
- Place business logic in a `services.py` module or a `services/` package — not in views, models, or serializers
- Use `django-environ` for environment variable loading with type coercion and `.env` support; use `django-configurations` when you need class-based settings with inheritance (`Base`, `Development`, `Production`). Do not use both — pick one
- Register signals in `AppConfig.ready()` inside `apps.py` — not at module level in `models.py` or `signals.py`

### Models

- Name models as singular PascalCase nouns (`User`, `OrderLine`) — not plurals (`Users`, `OrderLines`)
- Define `__str__` on every model for readable admin display and shell output
- Use `verbose_name` and `verbose_name_plural` in `Meta` for all models
- Set `related_name` on `ForeignKey` and `ManyToManyField` to make reverse relations explicit and readable
- Use `get_or_create`, `update_or_create`, `bulk_create`, and `bulk_update` over repeated single-record queries
- Define database indexes explicitly in `Meta.indexes` — do not rely solely on implicit FK indexing
- Keep models as thin data containers: field definitions, `Meta`, `__str__`, and database-level constraints. Push orchestration logic into services, not into model methods or managers
- Use `select_related` for ForeignKey traversal and `prefetch_related` for ManyToMany / reverse FK

```python
from django.db import models

class OrderLine(models.Model):
    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        related_name="lines",  # Explicit reverse name
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.PROTECT,
        related_name="order_lines",
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = "order line"
        verbose_name_plural = "order lines"
        indexes = [
            models.Index(fields=["order", "product"]),
        ]

    def __str__(self) -> str:
        return f"{self.product} x{self.quantity}"
```

### Views and URLs

- Keep views thin: validate input → call a service → return a response
- Name URL patterns explicitly — use `reverse()` or `reverse_lazy()`; never hardcode paths
- Choose views based on clarity: function-based views (FBVs) are more explicit and easier to read and test. Use class-based views (CBVs) or DRF ViewSets only when the class hierarchy genuinely reduces repetition (shared auth mixins, standard CRUD). Avoid Django's generic CBV mixins (`CreateView`, `UpdateView`) in APIs — the inheritance chains are opaque
- Apply `@require_http_methods` on FBVs to restrict allowed HTTP methods explicitly
- Always paginate list endpoints. Use `PageNumberPagination` by default; use `CursorPagination` for large, frequently updated datasets. Never return unbounded querysets in API responses

### Django REST Framework (DRF)

- Name serializers with the model name + `Serializer` suffix (`UserSerializer`, `OrderLineSerializer`)
- Use `ModelSerializer` for CRUD endpoints; use plain `Serializer` for custom input/output shapes
- Validate business rules in `validate_<field>` or `validate()` — not in views
- Use `ViewSet` + `Router` for standard CRUD; use `APIView` for non-standard endpoints
- Return proper HTTP status codes: `201` for creation, `204` for deletion, `400` for validation errors, `404` for not found, `403` for forbidden
- Use `DjangoFilterBackend` and `OrderingFilter` for filtering and sorting — avoid manual `request.GET` parsing
- Set `permission_classes` explicitly on every view or ViewSet — never rely only on global defaults

```python
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Item
from .services import create_item

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ["id", "name", "category", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "is_active"]

    def get_queryset(self):
        return Item.objects.filter(owner=self.request.user).select_related("category")
```

### ORM Patterns

- Never call `.all()` and then filter in Python — always filter at the ORM level
- Avoid N+1 queries: always `select_related` / `prefetch_related` when accessing related objects in loops
- Use `.only()` or `.defer()` to fetch a subset of fields when the full model is not needed
- Use `.exists()` instead of `.count() > 0` or `bool(queryset)` for existence checks
- Use `.values()` or `.values_list()` when you only need scalar data, not full model instances
- Wrap multi-step database operations in `transaction.atomic()` to preserve consistency
- Use `select_for_update()` inside `transaction.atomic()` when reading a row before updating it — acquires a row-level lock to prevent race conditions
- Use `F()` expressions for atomic field updates that reference the current value — never read-modify-write a field in Python for concurrent updates
- Use `Q()` objects for complex OR/AND filter conditions

```python
from django.db import transaction
from django.db.models import F, Q

# F() expression — atomic increment
Item.objects.filter(pk=pk).update(view_count=F("view_count") + 1)

# Q() — complex filter
results = Item.objects.filter(
    Q(is_active=True) & (Q(category=cat_a) | Q(category=cat_b))
)

# transaction.atomic() — multi-step consistency
def transfer_stock(from_id: int, to_id: int, qty: int) -> None:
    with transaction.atomic():
        Item.objects.filter(pk=from_id).update(stock=F("stock") - qty)
        Item.objects.filter(pk=to_id).update(stock=F("stock") + qty)
```

### Signals

- Use signals only for truly cross-cutting side effects where explicit calls would create circular imports or genuine decoupling needs
- Use `transaction.on_commit()` for any side effect that must happen after a successful transaction commit (e.g. dispatching a Celery task, sending a webhook)
- Register signals in `AppConfig.ready()` — not at module level

```python
# apps.py
class MyAppConfig(AppConfig):
    name = "myapp"

    def ready(self):
        import myapp.signals  # noqa: F401 — registers receivers

# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

@receiver(post_save, sender=Order)
def schedule_confirmation_email(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: send_confirmation_email.delay(instance.pk))
```

### Type Safety

- Use `django-stubs` with mypy (or `djangoext` with pyright) for type-safe ORM access
- Annotate queryset return types with `QuerySet[ModelName]`
- Use `Manager.from_queryset()` to define typed custom managers

```python
from django.db import models
from django.db.models import QuerySet

class ActiveItemManager(models.Manager):
    def get_queryset(self) -> QuerySet["Item"]:
        return super().get_queryset().filter(is_active=True)

class Item(models.Model):
    objects = models.Manager()
    active = ActiveItemManager()
```

### Caching

- Use Django's cache framework (`django.core.cache`) with Redis or Memcached for production
- Cache at the view level with `@cache_page` for public, non-personalized pages
- For per-user or permission-sensitive data, cache manually with explicit, scoped cache keys
- Always define an invalidation strategy before adding a cache — stale data is worse than a slow page
- Use `cache.get_or_set()` for a one-liner cache-aside pattern

```python
from django.core.cache import cache

def get_active_categories() -> list[dict]:
    return cache.get_or_set(
        "active_categories",
        lambda: list(Category.objects.filter(is_active=True).values("id", "name")),
        timeout=600,
    )
```

### Security

- Always use the ORM — raw SQL only when absolutely necessary; always use parameterized queries
- Use `{% csrf_token %}` in all forms; include `X-CSRFToken` header in AJAX requests
- Mark user-generated content as safe with `mark_safe` only when it is provably sanitized
- Set `SECURE_*` settings in production: `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SECURE_CONTENT_TYPE_NOSNIFF`
- Load `SECRET_KEY` from an environment variable — never hardcode it

### Anti-Patterns to Avoid

- Do not put business logic in views, models, or serializers — keep it in services
- Do not use `objects.all()` without a filter in a view — always paginate or scope the queryset
- Do not use `request.POST` directly — always pass through a form or serializer for validation
- Do not define or connect signals in `models.py` — register them in `AppConfig.ready()`
- Do not use `settings` directly in templates — pass needed values via the template context
- Do not mix `db_default` and `default` on the same field — they serve different purposes

---

## Django 4.2 (LTS — base version)

### Async Views

Use `async def` for I/O-bound views. Wrap ORM calls with `sync_to_async` — the ORM is synchronous by default in 4.2:

```python
from asgiref.sync import sync_to_async
from django.http import JsonResponse

async def item_detail(request, pk: int):
    item = await sync_to_async(Item.objects.select_related("category").get)(pk=pk)
    return JsonResponse({"name": item.name, "category": item.category.name})
```

### `CONN_HEALTH_CHECKS` (Django 4.1+)

```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,  # Silently reconnects stale persistent connections
    }
}
```

---

## Django 5.0

### `db_default` — Database-Level Field Defaults

Use `db_default` for fields whose default is a database function. It executes at the database layer without a round-trip through Python:

```python
from django.db import models
from django.db.models.functions import Now

class Order(models.Model):
    created_at = models.DateTimeField(db_default=Now())
    updated_at = models.DateTimeField(auto_now=True)
    # Do NOT combine db_default and default on the same field
```

### Facets in ModelAdmin

`ModelAdmin.show_facets` controls facet COUNT queries in the admin. Avoid `ShowFacets.ALWAYS` on large tables:

```python
from django.contrib import admin
from django.contrib.admin import ShowFacets

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    show_facets = ShowFacets.ALLOW  # Default — user can toggle; not forced on
```

---

## Django 5.1

### `LoginRequiredMiddleware`

When `LoginRequiredMiddleware` is active, all views require authentication by default. Explicitly mark public views:

```python
from django.views.decorators.login_required import login_not_required
from django.http import JsonResponse

@login_not_required
def health_check(request):
    return JsonResponse({"status": "ok"})
```

Do not leave views undecorated and assume they are public — with the middleware active, they are locked.

### `QuerySet.aiterator()` for Async Streaming

Use `aiterator()` for memory-efficient async streaming of large querysets (Django 5.1+):

```python
async def export_items():
    async for item in Item.objects.filter(is_active=True).aiterator(chunk_size=500):
        await write_to_export(item)
```

---

## Django 5.2 (LTS — latest version)

### Composite Primary Keys

Use `CompositePrimaryKey` for junction tables where multi-column identity is the natural key:

```python
from django.db import models

class TenantMembership(models.Model):
    tenant_id = models.SmallIntegerField()
    user_id = models.SmallIntegerField()

    class Meta:
        pk = models.CompositePrimaryKey("tenant_id", "user_id")

# ORM lookups must include all PK fields
TenantMembership.objects.get(tenant_id=1, user_id=42)
```

Do not use composite PKs as a workaround for missing surrogate keys — only use them when the domain genuinely has a composite natural key.

### Async Atomic Transactions (`aatomic`)

Django 5.2 introduces `transaction.aatomic()` for async atomic blocks, removing the `sync_to_async(transaction.atomic)` workaround:

```python
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

### Python 3.10+ Type Syntax (Required by Django 5.2)

Django 5.2 requires Python 3.10+. Apply the updated annotation syntax throughout:

```python
# Good — union type syntax (Python 3.10+)
def get_item(pk: int) -> Item | None:
    return Item.objects.filter(pk=pk).first()

# Good — built-in generic annotations (Python 3.9+)
def get_active_ids() -> list[int]:
    return list(Item.objects.filter(is_active=True).values_list("id", flat=True))

# Good — match/case over isinstance chains (Python 3.10+)
def describe_status(status: str) -> str:
    match status:
        case "active":
            return "Currently active"
        case "inactive":
            return "Inactive"
        case _:
            return "Unknown"
```

---

## Resources

- [Django Documentation](https://docs.djangoproject.com/en/stable/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [django-stubs](https://github.com/typeddjango/django-stubs)
- [django-environ](https://django-environ.readthedocs.io/en/latest/)
- [django-configurations](https://django-configurations.readthedocs.io/en/stable/)
- [django-filter](https://django-filter.readthedocs.io/en/stable/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/en/latest/)
- [Django Async Support](https://docs.djangoproject.com/en/stable/topics/async/)
- [Django 5.2 Release Notes](https://docs.djangoproject.com/en/5.2/releases/5.2/)
- [Django Supported Versions](https://www.djangoproject.com/download/#supported-versions)
