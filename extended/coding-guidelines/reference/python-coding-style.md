# Python Coding Style Guide

## Naming Conventions

- **Modules and packages**: lowercase with underscores (`user_service.py`, `auth_utils/`)
- **Classes**: PascalCase (`UserService`, `HttpClient`)
- **Functions and methods**: lowercase with underscores (`parse_config`, `get_user`)
- **Constants**: `UPPER_SNAKE_CASE` (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private members**: prefix with single underscore (`_internal_state`, `_validate`)
- **Name-mangled members**: double underscore only when truly needed (`__slots__`)
- **Type variables**: short PascalCase (`T`, `KT`, `VT`)
- **Acronyms**: treat as words — `HttpClient`, `JsonParser`, `url_path`

## File Organization

- One module per logical concern; keep files under ~300 lines
- Order within a file: module docstring → `__future__` imports → stdlib imports → third-party imports → local imports → constants → classes → functions → `if __name__ == "__main__"`
- Group imports in three blocks separated by blank lines: stdlib, third-party, local
- Use `__all__` in public modules to declare the public API explicitly

## Code Structure

- Prefer flat over nested — limit nesting to 2–3 levels; use early returns and guard clauses
- Keep functions short; a function should do one thing
- Use dataclasses or named tuples for plain data containers instead of raw dicts
- Prefer composition over inheritance; limit inheritance depth to 2
- Use `__slots__` in performance-sensitive classes with many instances
- Write module-level docstrings and docstrings for all public classes and functions

## Type Annotations

- Annotate all function signatures (parameters + return type)
- Use built-in generics (`list[str]`, `dict[str, int]`) — no `List`/`Dict` from `typing` (Python 3.9+)
- Use `X | Y` union syntax instead of `Optional[X]` or `Union[X, Y]` (Python 3.10+)
- Use `typing.Protocol` for structural typing instead of abstract base classes where appropriate
- Use `typing.TypeAlias` or `type` statement for type aliases (Python 3.12+)
- Avoid `Any` — use `object` or `Protocol` to express intent without losing type information

## Error Handling

- Use specific exception types — never `except Exception` or bare `except` as a catch-all
- Raise exceptions with descriptive messages; include relevant context values
- Define custom exceptions in a dedicated `exceptions.py` module per package
- Use `contextlib.suppress` for intentionally swallowed exceptions
- Clean up resources with `with` statements, not `try/finally` manually

## Idioms and Patterns

- Use list/dict/set comprehensions for simple transformations; use `for` loops for side effects
- Prefer generators for large sequences to avoid materializing everything in memory
- Use `enumerate` instead of manual index tracking; use `zip` for parallel iteration
- Use `pathlib.Path` for all filesystem operations — not `os.path`
- Use `logging` module — never `print` for application output
- Use f-strings for string formatting (Python 3.6+)

## Modern Python Features (apply when the project's Python version supports them)

- **Python 3.9+**: use `str.removeprefix` / `str.removesuffix`; use built-in generics in annotations
- **Python 3.10+**: use `match`/`case` for structural pattern matching; use `zip(strict=True)` to catch length mismatches
- **Python 3.11+**: use `ExceptionGroup` and `except*` for multiple concurrent exceptions; use `StrEnum` for string enumerations
- **Python 3.12+**: use `@override` decorator; use `itertools.batched()` for chunking iterables
- **Python 3.13+**: use `copy.replace()` for immutable copies with field overrides; use `warnings.deprecated` for deprecation notices
- **Python 3.14+**: use deferred annotation evaluation (PEP 749) for forward references; use `annotationlib` for annotation introspection at runtime

## Anti-Patterns to Avoid

- Do not use mutable default arguments (`def foo(items=[])`) — use `None` and assign inside
- Do not use `*args` / `**kwargs` as a shortcut for untyped or lazy function signatures
- Do not rely on dict ordering as a contract in Python < 3.7 code
- Do not use `type(x) == SomeClass` — use `isinstance(x, SomeClass)`
- Do not use bare string exceptions or catch `BaseException` unless re-raising
- Do not concatenate strings in a loop — use `"".join(parts)`
- Do not shadow built-in names (`id`, `list`, `type`, `input`, `filter`, `map`)
