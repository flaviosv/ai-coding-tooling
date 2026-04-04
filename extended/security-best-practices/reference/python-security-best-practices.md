# Python General Security Reference

General Python security rules for any Python application.
Framework-specific rules supplement this file — load both together:
- Django: `python-django-web-server-security.md`
- FastAPI: `python-fastapi-web-server-security.md`
- Flask: `python-flask-web-server-security.md`
- LangChain/LangGraph: `langchain-langgraph-security-best-practices.md`

---

## 0) Scope

This document covers security patterns that apply to **all Python code**, regardless of framework.
Framework-specific files reference "general Python security rules" — this is that file.
Do not repeat patterns already covered by framework-specific files.

## 1) Injection Prevention

### PY-SEC-001: Never pass user-controlled input to `subprocess` with `shell=True`

Severity: Critical

`shell=True` passes the command string to the OS shell (`/bin/sh -c`). Any user-controlled
fragment can inject shell metacharacters (`;`, `|`, `&&`, `` ` ``) and execute arbitrary commands.

Required:
- MUST use list form for all `subprocess` calls.
- MUST NOT set `shell=True` unless the full command string is entirely developer-controlled and contains no user-supplied data.
- SHOULD use `subprocess.run(..., check=True)` to raise on non-zero exit codes.

```python
# Bad
filename = request.data["file"]
subprocess.run(f"convert {filename} output.pdf", shell=True)

# Good
subprocess.run(["convert", filename, "output.pdf"], check=True)
```

### PY-SEC-002: Never use `eval()` or `exec()` on external or user-supplied data

Severity: Critical

`eval` and `exec` execute arbitrary Python code. Input from users, databases, files, or
environment variables must never be passed to either function.

Required:
- MUST NOT call `eval()` or `exec()` with any value that originates outside the developer's control.
- SHOULD use `ast.literal_eval()` when safe parsing of Python literals (strings, numbers, lists, dicts) is needed.
- MUST NOT use `ast.literal_eval()` for expressions — it is safe only for literals.
- SHOULD use a purpose-built parser or schema validation (Pydantic, marshmallow) for structured input.

```python
# Bad
formula = request.data["formula"]
result = eval(formula)

# Good
import ast
config_value = ast.literal_eval(config_string)  # only for trusted constant strings
```

### PY-SEC-003: Use parameterized queries for all database access

Severity: Critical

String concatenation or f-string formatting to build SQL queries allows SQL injection even when
input appears "safe". This applies to all database drivers.

Required:
- MUST use parameterized queries or ORM query builders for all database access.
- MUST NOT use f-strings, `%` formatting, or `.format()` to interpolate values into SQL strings.

```python
# Bad
cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")

# Good
cursor.execute("SELECT * FROM users WHERE username = %s", (username,))

# Good — ORM (Django/SQLAlchemy)
User.objects.filter(username=username)
```

### PY-SEC-004: Use `yaml.safe_load` — never `yaml.load` without an explicit Loader

Severity: High

`yaml.load` with no `Loader` (or with `yaml.FullLoader` / `yaml.Loader`) can deserialize
arbitrary Python objects, enabling remote code execution via crafted YAML.

Required:
- MUST use `yaml.safe_load()` for all YAML parsing of untrusted data.
- MUST NOT use `yaml.load(data)` without `Loader=yaml.SafeLoader`.

```python
# Bad
data = yaml.load(user_yaml)

# Good
data = yaml.safe_load(user_yaml)
```

## 2) Deserialization

### PY-SEC-005: Never deserialize untrusted data with `pickle`, `marshal`, or `shelve`

Severity: Critical

`pickle`, `marshal`, and `shelve` can execute arbitrary code during deserialization. Any data
originating from outside the application must be treated as untrusted.

Required:
- MUST NOT use `pickle.loads()`, `marshal.loads()`, or `shelve` to deserialize data from user
  input, network, files, or any external source.
- SHOULD use JSON + Pydantic for structured serialization across trust boundaries.
- MUST apply schema validation to all deserialized data before use.

```python
# Bad
data = pickle.loads(request.body)

# Good
import json
from pydantic import BaseModel

class Payload(BaseModel):
    user_id: int
    action: str

data = Payload(**json.loads(request.body))
```

## 3) Cryptography

### PY-SEC-006: Use `secrets` for all security-sensitive random generation

Severity: High

`random` is a pseudo-random number generator seeded from a predictable source. It MUST NOT
be used for tokens, nonces, session IDs, CSRF tokens, password reset links, or API keys.

Required:
- MUST use `secrets.token_hex()`, `secrets.token_urlsafe()`, or `secrets.choice()` for any
  security-sensitive random value.
- MUST NOT use `random`, `uuid4`, or `os.urandom` wrapped in `random` for security purposes.
  (`os.urandom` is acceptable directly; `uuid4` is acceptable only for identifiers, not secrets.)

```python
# Bad
import random, string
token = "".join(random.choices(string.ascii_letters + string.digits, k=32))

# Good
import secrets
token = secrets.token_urlsafe(32)
api_key = secrets.token_hex(24)
```

### PY-SEC-007: Never use MD5 or SHA-1 for password hashing or security purposes

Severity: Critical

MD5 and SHA-1 are cryptographically broken. They are unsuitable for password hashing, HMAC
key derivation, or digital signatures in security contexts.

Required:
- MUST NOT use `hashlib.md5` or `hashlib.sha1` for passwords, tokens, or security-critical digests.
- MUST use `hashlib.pbkdf2_hmac` with SHA-256 (minimum 260,000 iterations), or a library such
  as `bcrypt` or `argon2-cffi` for password hashing.
- MUST use `hashlib.sha256` or stronger for non-password integrity checks.

```python
# Bad
import hashlib
stored = hashlib.md5(password.encode()).hexdigest()

# Good — bcrypt
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

# Good — argon2
from argon2 import PasswordHasher
ph = PasswordHasher()
hashed = ph.hash(password)
```

### PY-SEC-008: Use constant-time comparison for security-sensitive string equality

Severity: High

Python's `==` operator short-circuits on the first differing byte, enabling timing attacks
against tokens, MACs, and signatures.

Required:
- MUST use `hmac.compare_digest()` for all equality checks involving secrets, tokens, MACs, or signatures.
- MUST NOT use `==`, `!=`, or `in` for these comparisons.

```python
# Bad
if user_token == stored_token:
    ...

# Good
import hmac
if hmac.compare_digest(user_token.encode(), stored_token.encode()):
    ...
```

## 4) Secrets and Credentials

### PY-SEC-009: Load all credentials from environment variables — never hardcode

Severity: Critical

Hardcoded credentials in source code are committed to version control and appear in logs,
error traces, and stack dumps. They cannot be rotated without a code change.

Required:
- MUST load all credentials (API keys, DB passwords, signing keys) from environment variables
  or a secrets manager — never from source code or committed config files.
- MUST use `os.environ["KEY"]` (raises `KeyError` if missing) for required secrets, not
  `os.getenv("KEY", "fallback")` which silently uses an insecure default.
- MUST NOT log or print credential values at any log level.

```python
# Bad
DB_PASSWORD = "s3cr3t"
API_KEY = "sk-prod-..."

# Bad — silent fallback hides missing config
api_key = os.getenv("API_KEY", "dev-key-123")

# Good
import os
DB_PASSWORD = os.environ["DB_PASSWORD"]
API_KEY = os.environ["API_KEY"]
```

### PY-SEC-010: Do not expose secrets in error messages, logs, or tracebacks

Severity: High

Exception messages and log output are often stored, aggregated, and forwarded to third-party
services (Sentry, Datadog, CloudWatch). Secrets in these outputs are effectively leaked.

Required:
- MUST NOT include credential values in exception messages or log statements.
- SHOULD redact known secret fields before logging structured data.
- MUST ensure that `repr()` and `str()` of domain objects do not expose credential fields.

```python
# Bad
logger.error(f"Login failed for user {username} with password {password}")

# Good
logger.error(f"Login failed for user {username}")
```

## 5) Input Validation

### PY-SEC-011: Validate all external input at system boundaries

Severity: High

Input from HTTP requests, message queues, files, environment variables, and CLI arguments
must be validated before use. Internal code should not need to re-validate already-trusted data.

Required:
- MUST validate type, range, and format of all input at the boundary where it enters the system.
- SHOULD use Pydantic models (or equivalent schema validation) for structured input — not manual
  `isinstance` chains.
- MUST reject input that fails validation with a specific error — never silently coerce or ignore.

```python
# Bad
def create_order(data: dict) -> Order:
    return Order(user_id=data["user_id"], amount=data["amount"])

# Good
from pydantic import BaseModel, Field, PositiveFloat

class CreateOrderInput(BaseModel):
    user_id: int
    amount: PositiveFloat = Field(..., le=100_000)

def create_order(data: CreateOrderInput) -> Order:
    return Order(user_id=data.user_id, amount=data.amount)
```

### PY-SEC-012: Validate and sandbox all user-supplied file paths

Severity: High

User-supplied paths (from query parameters, form fields, or API payloads) can contain `..`
sequences enabling path traversal outside the intended directory.

Required:
- MUST resolve the user-supplied path with `Path.resolve()` and verify it is within the allowed root.
- MUST NOT construct paths with f-strings or `+` from untrusted input.
- SHOULD maintain an explicit allowlist of permitted directories.

```python
# Bad — path traversal: ../../etc/passwd
open(os.path.join("/uploads", user_path))

# Good
from pathlib import Path

UPLOAD_ROOT = Path("/uploads").resolve()

def safe_open(user_path: str) -> Path:
    resolved = (UPLOAD_ROOT / user_path).resolve()
    if not resolved.is_relative_to(UPLOAD_ROOT):
        raise PermissionError("Access denied: path outside upload directory")
    return resolved
```

## 6) Assert Abuse

### PY-SEC-013: Never use `assert` for security checks or input validation

Severity: High

Python `assert` statements are removed entirely when the interpreter runs with the `-O`
(optimize) flag, which is commonly set in production Docker images and CI pipelines.
Any security check implemented with `assert` is silently disabled in optimized builds.

Required:
- MUST NOT use `assert` for permission checks, input validation, or authentication guards.
- MUST use explicit `if` conditions with `raise` to enforce security invariants.

```python
# Bad
assert user.is_authenticated, "Must be logged in"
assert len(password) >= 8, "Password too short"

# Good
if not user.is_authenticated:
    raise PermissionError("Must be logged in")
if len(password) < 8:
    raise ValueError("Password must be at least 8 characters")
```

## 7) Dependency Security

### PY-SEC-014: Run dependency vulnerability scanning in CI

Severity: High

Third-party packages introduce transitive dependencies with known CVEs. Vulnerability
scanning must run automatically on every build — not only at install time.

Required:
- MUST run `pip audit` or `safety check` in CI on every pull request.
- MUST pin all direct dependencies to specific versions in production (`==`, not `>=`).
- SHOULD pin transitive dependencies with a lock file (`pip-compile`, `uv lock`, or `poetry.lock`).
- MUST NOT merge dependency updates without reviewing the changelog for security-relevant changes.

```bash
# Good
pip audit
# or
safety check -r requirements.txt
```

### PY-SEC-015: Avoid `setup.py` execution from untrusted packages

Severity: Medium

Installing packages that use `setup.py` (instead of PEP 517/518 `pyproject.toml`) can execute
arbitrary Python code during installation. This is a supply-chain attack vector.

Required:
- SHOULD prefer packages that use PEP 517/518 build backends (`flit`, `hatchling`, `setuptools`
  with `pyproject.toml`) — they do not execute arbitrary code at install time.
- SHOULD use `pip install --no-build-isolation` with a pre-audited source distribution only when
  `setup.py` packages cannot be avoided.
- MUST review the source of any `setup.py` package before adding it as a dependency.
