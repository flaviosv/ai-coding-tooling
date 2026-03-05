# Django Code Review Reference

Supplements `review-checklist.md`, `clean-code-checklist.md`, and `solid-principles.md` for projects using Django and Django REST Framework.
Supported version range: Django 4.2 LTS (base) → Django 5.2 LTS (latest).

---

## General Django Patterns

Conventions that apply across all still-supported Django versions (4.2–5.2).

### Security

- [ ] No hardcoded secrets or credentials in any source file
- [ ] User input validated in serializers or forms — never trusted raw from `request.data` or `request.POST`
- [ ] Django ORM used exclusively for queries — no raw string SQL concatenation
- [ ] `permission_classes` set explicitly on every DRF view or ViewSet — never rely on global defaults alone
- [ ] Sensitive data (passwords, tokens, SSNs) not exposed in API responses, error messages, or logs
- [ ] `DEBUG=False` enforced in production — never `True` in deployed environments
- [ ] `ALLOWED_HOSTS` does not contain `*` in production settings
- [ ] `CSRF_COOKIE_SECURE=True` and `SESSION_COOKIE_SECURE=True` set in production
- [ ] `SECRET_KEY` loaded from an environment variable — not hardcoded in any settings file
- [ ] `manage.py check --deploy` passes in CI (catches common misconfigurations)
- [ ] `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, and `SECURE_CONTENT_TYPE_NOSNIFF` configured in production
- [ ] Raw SQL queries (when necessary) always use parameterized form: `cursor.execute(sql, [params])` — never f-strings or `.format()`

```python
# Good — parameterized raw query (use ORM wherever possible)
with connection.cursor() as cursor:
    cursor.execute("SELECT id FROM myapp_item WHERE category_id = %s", [category_id])

# Bad — SQL injection vector
cursor.execute(f"SELECT id FROM myapp_item WHERE category_id = {category_id}")
```

### Architecture and Design

- [ ] Layer responsibilities respected: no business logic in views or serializers; no HTTP concerns in models
- [ ] DRF built-ins used where appropriate — avoid reinventing pagination, filtering, or validation
- [ ] RESTful API design: correct HTTP verbs (`GET`, `POST`, `PUT`/`PATCH`, `DELETE`), consistent response shapes
- [ ] Code follows the established patterns in the project's `ARCHITECTURE.md`
- [ ] Signals used carefully — prefer explicit service calls over implicit signal chains
- [ ] `transaction.on_commit()` used for post-transaction side effects (e.g. sending email after a DB commit) — not plain signal handlers
- [ ] `queryset.delete()` and `queryset.update()` bypass `pre_delete`/`post_delete` and `pre_save`/`post_save` signals — any logic relying on those signals will be silently skipped

```python
# Good — explicit post-commit side effect
from django.db import transaction

def create_order(data):
    with transaction.atomic():
        order = Order.objects.create(**data)
        transaction.on_commit(lambda: send_confirmation_email.delay(order.pk))
    return order

# Bad — signal handler that may not fire if bulk operations are used, and runs inside the transaction
@receiver(post_save, sender=Order)
def on_order_created(sender, instance, created, **kwargs):
    if created:
        send_confirmation_email(instance)  # Runs inside the open transaction
```

### Performance

- [ ] `select_related()` used for ForeignKey / OneToOne traversal in loops
- [ ] `prefetch_related()` used for ManyToMany / reverse FK traversal in loops
- [ ] No N+1 query problems in list views or serializers
- [ ] `only()` or `values()` used when fetching a subset of fields
- [ ] Pagination applied to all list endpoints — no unbounded querysets returned from views
- [ ] Heavy or slow operations offloaded to background tasks (Celery)
- [ ] `bulk_create` / `bulk_update` used when inserting or updating many records in a loop
- [ ] `exists()` used for boolean checks — not `count() > 0` or `len(queryset)`

```python
# Good — fixed query count regardless of item count
items = Item.objects.select_related("category").prefetch_related("tags").filter(is_active=True)

# Bad — N+1: one extra query per item in the loop
items = Item.objects.filter(is_active=True)
for item in items:
    print(item.category.name)  # Extra DB hit each iteration
```

### Code Quality

- [ ] Type hints on all public function and method signatures
- [ ] No unused imports, variables, or functions
- [ ] No `print()` or debug artifacts in production code
- [ ] Code style consistent with the project's linter (Ruff or flake8)
- [ ] `f-strings` used for string formatting — not `%` or `.format()` where avoidable
- [ ] Proper error handling: DRF exception classes in views, custom exceptions in service layer

### Django Best Practices

- [ ] Migrations created for all model changes and committed alongside model changes
- [ ] Migration safety reviewed for large tables: adding a non-nullable column without a default causes a full table lock; use a two-step migration (add nullable → backfill → add constraint) for zero-downtime
- [ ] Adding a database index should use `AddIndex` with `concurrently=True` (PostgreSQL) to avoid table locks in production
- [ ] `Celery` tasks designed to be idempotent and retryable
- [ ] `django-filter` or DRF built-in filtering used for query filtering — not manual `request.GET` parsing
- [ ] `F()` expressions used for atomic field updates that reference the current value — never read-modify-write a field in Python for concurrent updates

```python
# Good — atomic increment at the database level; no race condition
from django.db.models import F
Item.objects.filter(pk=item_id).update(view_count=F("view_count") + 1)

# Bad — race condition under concurrent requests
item = Item.objects.get(pk=item_id)
item.view_count += 1
item.save()
```

### Documentation

- [ ] API views documented with `@extend_schema` (drf-spectacular) or equivalent docstrings
- [ ] Complex business logic annotated with inline comments
- [ ] Public methods and classes have docstrings

### Resources

- [Django Documentation](https://docs.djangoproject.com/en/stable/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Database Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/)
- [drf-spectacular (@extend_schema)](https://drf-spectacular.readthedocs.io/en/latest/)
- [django-filter](https://django-filter.readthedocs.io/en/stable/)

---

## Django 4.2 (LTS — base version)

Everything available as of Django 4.2 that reviewers should enforce.

### Async Views

Django 4.1+ supports async views natively. Django 4.2 stabilizes async support.

- [ ] Async views defined with `async def` when the handler is I/O-bound
- [ ] ORM calls inside async views wrapped with `sync_to_async` — the ORM is synchronous by default
- [ ] Sync and async callables not mixed without the `sync_to_async` / `async_to_sync` adapters

```python
# Good — async view with ORM wrapped in sync_to_async
from asgiref.sync import sync_to_async
from django.http import JsonResponse

async def item_detail(request, pk):
    item = await sync_to_async(Item.objects.get)(pk=pk)
    return JsonResponse({"name": item.name})

# Bad — direct ORM call in async view raises SynchronousOnlyOperation
async def item_detail(request, pk):
    item = Item.objects.get(pk=pk)  # SynchronousOnlyOperation
    return JsonResponse({"name": item.name})
```

### QuerySet Async Interface (Django 4.1+)

Use the async ORM interface (`aiterator`, `aget`, `acreate`, `afirst`, `acount`, etc.) introduced in Django 4.1 instead of `sync_to_async` wrappers for simple operations:

```python
# Good — native async ORM method (Django 4.1+)
async def get_active_authors():
    async for author in Author.objects.filter(is_active=True):
        book = await author.books.afirst()
```

### Migrations: `django.db.migrations.utils.get_migration_name_timestamp` removed

- [ ] Custom migration tooling not relying on removed internal utilities — use `django.db.migrations` public API only.

---

## Django 5.0

New features in Django 5.0 relevant to review findings.

### Field-Level Facets in Admin

Not a common review point, but verify that `ModelAdmin.show_facets` is not set to `ShowFacets.ALWAYS` on admin views over very large tables — the facet counts run COUNT queries and may be expensive.

### Database-Computed Default Values

Django 5.0 adds `db_default` for database-level default expressions:

- [ ] `db_default` used instead of application-level defaults for fields whose default is a database function (e.g. `Now()`, `Value(0)`)
- [ ] `default` and `db_default` are not mixed on the same field — they serve different purposes

```python
from django.db.models.functions import Now
from django.db import models

# Good — database sets created_at; no application-level default needed
class Order(models.Model):
    created_at = models.DateTimeField(db_default=Now())

# Redundant — mixing both is confusing
class Order(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())
```

### Simplified URL Routing with `path()` Converters

No new review requirements over 4.2 for URL routing.

---

## Django 5.1

New features in Django 5.1 relevant to review findings.

### QuerySet `aiterator()`

Django 5.1 adds `QuerySet.aiterator()` for async iteration over large datasets:

- [ ] `aiterator()` used instead of loading large querysets into memory in async contexts

```python
# Good — streams records without loading all into memory (Django 5.1+)
async def export_items():
    async for item in Item.objects.filter(is_active=True).aiterator(chunk_size=500):
        await process(item)
```

### Login Required Middleware

Django 5.1 introduces `django.contrib.auth.middleware.LoginRequiredMiddleware`:

- [ ] If `LoginRequiredMiddleware` is active, views that must be public are explicitly decorated with `@login_not_required` — not left undecorated and accidentally locked
- [ ] If the middleware is NOT active, all views that require authentication are protected with `@login_required` or `LoginRequiredMixin`

---

## Django 5.2 (LTS — latest version)

New content specific to Django 5.2.

### Composite Primary Keys

Django 5.2 introduces composite primary keys (`CompositePrimaryKey`):

- [ ] Composite PKs used only when the domain genuinely requires multi-column identity — not as a workaround for missing surrogate keys
- [ ] Relationships targeting models with composite PKs use the correct multi-column FK syntax
- [ ] Serializers and API views handle composite PK lookup correctly (URL pattern includes all key fields)

```python
from django.db import models

# Good — composite PK for a junction table where (tenant, user) is the natural key
class TenantMembership(models.Model):
    tenant_id = models.SmallIntegerField()
    user_id = models.SmallIntegerField()

    class Meta:
        pk = models.CompositePrimaryKey("tenant_id", "user_id")
```

### Support for `django.contrib.postgres.fields.HStoreField` Updates

No specific new review checklist items over 5.1 for HStore.

### Async ORM Transactions

Django 5.2 adds support for `aatomic()` (async `transaction.atomic()`):

- [ ] `async with transaction.aatomic():` used for multi-step async ORM writes — not `sync_to_async(transaction.atomic)` workarounds

```python
# Good — native async atomic transaction (Django 5.2+)
from django.db import transaction

async def transfer_funds(from_id, to_id, amount):
    async with transaction.aatomic():
        sender = await Account.objects.select_for_update().aget(pk=from_id)
        receiver = await Account.objects.select_for_update().aget(pk=to_id)
        sender.balance -= amount
        receiver.balance += amount
        await sender.asave()
        await receiver.asave()
```

### Python Version Support

Django 5.2 requires Python 3.10+. Enforce:

- [ ] `str | None` union syntax used instead of `Optional[str]` (Python 3.10+)
- [ ] `match`/`case` used instead of long `if/elif isinstance()` chains where appropriate (Python 3.10+)
- [ ] Built-in generic annotations (`list[int]`, `dict[str, int]`) — not `List[int]` from `typing`

---

## Resources

- [Django 4.2 Release Notes](https://docs.djangoproject.com/en/4.2/releases/4.2/)
- [Django 5.0 Release Notes](https://docs.djangoproject.com/en/5.0/releases/5.0/)
- [Django 5.1 Release Notes](https://docs.djangoproject.com/en/5.1/releases/5.1/)
- [Django 5.2 Release Notes](https://docs.djangoproject.com/en/5.2/releases/5.2/)
- [Django Supported Versions](https://www.djangoproject.com/download/#supported-versions)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Database Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/)
- [Django Async Support](https://docs.djangoproject.com/en/stable/topics/async/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/en/latest/)
- [django-filter](https://django-filter.readthedocs.io/en/stable/)
