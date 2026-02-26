# Python + Django Coding Style Guide

> Load this file together with `python-coding-style.md`. Rules here are additive and Django-specific.

## Project Layout

- Follow the standard Django app layout: `models.py`, `views.py`, `urls.py`, `serializers.py`, `admin.py`, `tests/`
- Split large apps into sub-modules: `models/`, `views/`, `services/` — keep each file focused
- Place business logic in `services.py` or a `services/` package, not in views or models
- Keep `settings.py` clean — use `django-environ` or `django-configurations` for environment-based config
- Use `apps.py` and `AppConfig.ready()` for signal registration — not module-level code

## Models

- Name models as singular PascalCase nouns (`User`, `OrderLine`, not `Users`, `order_lines`)
- Define `__str__` on every model for readable admin and shell output
- Use `verbose_name` and `verbose_name_plural` in `Meta` for all models
- Prefer `related_name` on ForeignKey/M2M fields to make reverse relations explicit
- Use `get_or_create`, `update_or_create`, and `bulk_create` / `bulk_update` over repeated single queries
- Define database indexes explicitly with `Meta.indexes` — do not rely on implicit indexing
- Use `select_related` for ForeignKey traversal and `prefetch_related` for M2M / reverse FK

## Views and URLs

- Prefer class-based views (CBVs) for standard CRUD; use function-based views (FBVs) for simple one-off logic
- Name URL patterns explicitly — use `reverse()` or `reverse_lazy()`, never hardcode paths
- Keep views thin: validate input, call a service, return a response
- Use `LoginRequiredMixin` or `@login_required` for authentication; use `PermissionRequiredMixin` for authorization
- Apply `@require_http_methods` on FBVs to restrict allowed HTTP methods explicitly

## Django REST Framework (DRF)

- Name serializers with the model name + `Serializer` suffix (`UserSerializer`, `OrderLineSerializer`)
- Use `ModelSerializer` for CRUD endpoints; use plain `Serializer` for custom input/output shapes
- Validate business rules in `validate_<field>` or `validate()` — not in views
- Use `ViewSet` + Router for standard CRUD; use `APIView` for non-standard endpoints
- Return proper HTTP status codes: `201` for creation, `204` for deletion, `400` for validation errors, `404` for not found
- Use `DjangoFilterBackend` for filtering, `OrderingFilter` for sorting — avoid manual query param parsing

## ORM Patterns

- Never call `.all()` and then filter in Python — always filter at the ORM level
- Avoid N+1 queries: always `select_related` / `prefetch_related` when accessing related objects in loops
- Use `.only()` or `.defer()` to fetch a subset of fields when the full model is not needed
- Use `.exists()` instead of `.count() > 0` or `bool(queryset)` for existence checks
- Use `.values()` or `.values_list()` when you only need scalar data, not model instances
- Wrap multi-step database operations in `transaction.atomic()` to preserve consistency

## Templates and Static Files

- Keep template logic minimal — no business logic in templates
- Use template tags and filters for reusable presentation logic
- Organize templates under `<app>/templates/<app>/` to namespace them correctly
- Reference static files with `{% static %}` — never hardcode paths

## Security

- Always use Django's ORM — never raw SQL unless absolutely necessary; parameterize raw queries
- Use `{% csrf_token %}` in all forms; verify CSRF in AJAX with the `X-CSRFToken` header
- Mark user-generated content safe only with `mark_safe` when it is provably sanitized
- Set `SECURE_*` settings in production (`SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, etc.)

## Anti-Patterns to Avoid

- Do not put business logic in models — keep models as data containers with minimal behavior
- Do not use `objects.all()` without a filter in a view — always paginate or scope the queryset
- Do not use `request.POST` directly — always pass through a form or serializer for validation
- Do not define signals in `models.py` — register them in `AppConfig.ready()`
- Do not use `settings` directly in templates — pass needed values via context
