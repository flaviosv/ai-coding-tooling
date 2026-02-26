# Python / Django Code Review Checklist (3.9+)

Supplements the generic `review-checklist.md` for projects using Python and Django/DRF.

---

## Security

- [ ] No hardcoded secrets or credentials
- [ ] User input validated in serializers or forms — never trusted raw
- [ ] Django ORM used exclusively — no raw string SQL concatenation
- [ ] `permission_classes` set explicitly on all views
- [ ] Sensitive data not exposed in error messages or API responses

### Django Deployment Security

- [ ] `DEBUG=False` in production — never `True` in deployed environments
- [ ] `ALLOWED_HOSTS` does not contain `*` in production
- [ ] `CSRF_COOKIE_SECURE=True` and `SESSION_COOKIE_SECURE=True` set in production settings
- [ ] `SECRET_KEY` loaded from environment variable — not hardcoded in settings
- [ ] `manage.py check --deploy` passes in CI (catches common misconfigurations)

---

## Performance

- [ ] `select_related()` used for ForeignKey / OneToOne traversal
- [ ] `prefetch_related()` used for ManyToMany / reverse FK traversal
- [ ] No N+1 query problems in list views or loops
- [ ] `only()` or `values()` used when fetching specific fields only
- [ ] Pagination applied to all list endpoints
- [ ] Heavy or slow operations offloaded to background tasks (e.g. Celery)
- [ ] No unnecessary database queries inside loops

---

## Architecture & Design

- [ ] Layer responsibilities respected (no business logic in views; no HTTP concerns in models)
- [ ] DRF built-ins used where appropriate — avoid reinventing pagination, filtering, or validation
- [ ] RESTful API design: correct HTTP verbs, consistent response structures
- [ ] Code follows established patterns in the codebase
- [ ] Signals used carefully — prefer explicit calls over implicit signal chains. Key pitfalls: signals bypass database transactions (use `transaction.on_commit()` for post-transaction side effects), create hidden ordering dependencies, and make code hard to trace
- [ ] `queryset.delete()` and `queryset.update()` bypass `pre_delete`/`post_delete` and `pre_save`/`post_save` signals — side effects that rely on these signals will not fire

---

## Code Quality

- [ ] Clean, readable code — no unnecessary complexity
- [ ] Proper error handling: DRF exceptions in views, custom exceptions in services/use cases
- [ ] Type hints on function signatures
- [ ] No unused imports, variables, or functions
- [ ] No `print()` or debug artifacts in production code
- [ ] Code style consistent with the project's linter configuration (e.g. Ruff, flake8)

---

## Python Best Practices

- [ ] Python idioms applied (list comprehensions, generators where appropriate)
- [ ] `collections.defaultdict`, `Counter`, and `any()`/`all()` preferred over manual equivalents
- [ ] f-strings used for string formatting
- [ ] Sets used for O(1) membership testing instead of lists
- [ ] `dict.get()` preferred over try/except KeyError for optional key access

---

## Django Best Practices

- [ ] Migrations created for all model changes
- [ ] Migration safety reviewed for large tables: adding a non-nullable column without a default causes a table lock; adding an index should use `migrations.AddIndex` with `concurrently=True` (PostgreSQL) to avoid downtime
- [ ] Celery tasks are idempotent and handle failures gracefully
- [ ] `django-filter` or DRF filtering used for query filtering — not manual querystring parsing
- [ ] `bulk_create` / `bulk_update` used when inserting or updating many records
- [ ] `exists()` used for boolean checks, not `count() > 0` or `len()`

---

## Documentation

- [ ] API views documented (e.g. with `@extend_schema` for OpenAPI, or docstrings)
- [ ] Complex logic has explanatory inline comments
- [ ] Public methods and classes have docstrings

---

## Modern Python Features by Version

- [ ] `str.removeprefix()` / `str.removesuffix()` used instead of manual slicing (Python 3.9+)
- [ ] Built-in generic types in annotations (`list[int]`, `dict[str, int]`) — not `List[int]` from `typing` (Python 3.9+)
- [ ] Dict merge (`|`) and update-in-place (`|=`) operators used instead of `{**a, **b}` (Python 3.9+)
- [ ] `X | Y` union syntax in type annotations (`str | None` instead of `Optional[str]`) (Python 3.10+)
- [ ] `match`/`case` structural pattern matching used over long `if/elif isinstance()` chains (Python 3.10+)
- [ ] `zip(strict=True)` used when iterating two sequences that must be the same length (Python 3.10+)
- [ ] `ExceptionGroup` / `except*` used for concurrent exception handling (asyncio task groups) (Python 3.11+)
- [ ] `Self` type used for methods that return their own instance (Python 3.11+)
- [ ] `StrEnum` used for string-valued enumerations instead of raw string constants (Python 3.11+)
- [ ] `tomllib` used for reading TOML configuration files — not a third-party library (Python 3.11+)
- [ ] `@override` decorator from `typing` applied to overriding methods (Python 3.12+)
- [ ] `type` statement used for type aliases (`type Vector = list[float]`) — not `TypeAlias` (Python 3.12+)
- [ ] `itertools.batched()` used for chunking iterables instead of manual slicing (Python 3.12+)
- [ ] `copy.replace()` used to derive modified copies of dataclass-like objects (Python 3.13+)
- [ ] `typing.ReadOnly` used for read-only fields in `TypedDict` (Python 3.13+)
- [ ] `warnings.deprecated()` used for deprecation notices — not manual `DeprecationWarning` (Python 3.13+)
- [ ] `@warnings.deprecated` is now stable — use it for marking deprecated public APIs (Python 3.13+)
- [ ] Deferred annotation evaluation (PEP 649) is the default in Python 3.14 — code that inspects `__annotations__` at runtime should use `annotationlib` for compatibility (Python 3.14+)

---

## Resources

- [Django Documentation](https://docs.djangoproject.com/en/stable/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Database Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/)
- [DRF Serializers](https://www.django-rest-framework.org/api-guide/serializers/)
- [drf-spectacular (@extend_schema)](https://drf-spectacular.readthedocs.io/en/latest/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html#tips-and-best-practices)
- [django-filter](https://django-filter.readthedocs.io/en/stable/)
- [Python 3.9 What's New](https://docs.python.org/3/whatsnew/3.9.html)
- [Python 3.10 What's New](https://docs.python.org/3/whatsnew/3.10.html)
- [Python 3.11 What's New](https://docs.python.org/3/whatsnew/3.11.html)
- [Python 3.12 What's New](https://docs.python.org/3/whatsnew/3.12.html)
- [Python 3.13 What's New](https://docs.python.org/3/whatsnew/3.13.html)
