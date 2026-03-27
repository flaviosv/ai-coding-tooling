# Playwright Security Spec

Security guidance for projects using `@playwright/test`. Covers credential handling, storage state protection, CI secrets, and safe network configuration in test suites.

---

## Scope

This document covers Playwright-specific security patterns. All rules apply to test suites and browser automation scripts that use `@playwright/test`.

---

## PW-SEC-001: Credentials MUST NOT be hardcoded in test files or configuration

**Severity: Critical**

Hardcoded credentials are committed to source control and exposed in PR diffs, git history, and any repository fork or mirror.

**Required:**
- MUST use `process.env.*` for all test user credentials and API tokens
- MUST store credentials in CI/CD secrets (GitHub Actions Secrets, GitLab CI Variables, etc.)
- MUST document required environment variables in `.env.example` using placeholder names only — never actual values

**Insecure patterns:**

```typescript
// Bad — password committed to source control
setup('authenticate', async ({ page }) => {
  await page.getByLabel('Email').fill('testuser@example.com');
  await page.getByLabel('Password').fill('TestP@ssword123');
});

// Bad — API key in playwright.config.ts
use: {
  extraHTTPHeaders: { 'X-API-Key': 'sk-live-example-key' },
}
```

**Fix:**

```typescript
// Good — credentials from environment variables
setup('authenticate', async ({ page }) => {
  await page.getByLabel('Email').fill(process.env.TEST_USER_EMAIL!);
  await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
});

// Good — .env.example documents required vars without values
// TEST_USER_EMAIL=
// TEST_USER_PASSWORD=
// BASE_URL=http://localhost:3000
```

**Detection hints:**
- Search for `.fill(` calls with string literals that resemble passwords, keys, or tokens
- Search `playwright.config.ts` for `extraHTTPHeaders` containing literal token values

---

## PW-SEC-002: Storage state files MUST be excluded from version control

**Severity: High**

Storage state files (`.auth/user.json`, `storageState.json`, etc.) contain live session cookies and local storage tokens. Committing them exposes active, usable sessions.

**Required:**
- MUST add all storage state paths to `.gitignore` before the first commit
- MUST use a dedicated `.auth/` directory for storage state — makes gitignore management unambiguous
- MUST regenerate storage state in CI on every run — never check in a pre-generated file

**Check `.gitignore`:**

```gitignore
# Storage state files — contain live session tokens
.auth/
playwright/.auth/
**/*.auth.json
auth.json
```

**Detection hints:**
- Search for files matching `*.json` inside `playwright/` or `.auth/` directories that are tracked by git (`git ls-files | grep -E '\.auth|storageState'`)
- Search `playwright.config.ts` for `storageState:` values; verify each resolves to a gitignored path

---

## PW-SEC-003: `ignoreHTTPSErrors` MUST NOT be enabled globally for production or audit runs

**Severity: High**

`ignoreHTTPSErrors: true` disables TLS certificate validation. It allows tests to run against endpoints with expired, self-signed, or mismatched certificates — masking real security issues in the environment under test.

**Required:**
- MUST NOT set `ignoreHTTPSErrors: true` in the global `use` block without an environment guard
- MAY enable it for `local` environments using a self-signed dev certificate — with an explicit justification comment
- MUST gate it behind an environment variable so it cannot accidentally apply to staging or production runs

**Insecure pattern:**

```typescript
// Bad — suppresses TLS validation for all environments, including production audit runs
export default defineConfig({
  use: { ignoreHTTPSErrors: true },
});
```

**Fix:**

```typescript
// Good — only in local dev with self-signed certificate; explicitly guarded
export default defineConfig({
  use: {
    // Self-signed cert used in local Docker environment only
    ignoreHTTPSErrors: process.env.ENVIRONMENT === 'local',
  },
});
```

**Detection hints:**
- Search for `ignoreHTTPSErrors: true` without an adjacent environment variable check
- Flag any `ignoreHTTPSErrors: true` in shared CI configuration

---

## PW-SEC-004: Route handlers MUST always resolve the request

**Severity: Medium**

A `page.route()` handler that never calls `route.fulfill()`, `route.continue()`, or `route.abort()` leaves the HTTP request pending indefinitely. Under parallel execution, accumulating pending connections can exhaust the test runner's file descriptor limit.

**Required:**
- MUST call exactly one of `route.fulfill()`, `route.continue()`, or `route.abort()` in every code path of every route handler

**Insecure/buggy pattern:**

```typescript
// Bad — request hangs if condition is false; resource leak under parallel execution
await page.route('**/api/data', async (route) => {
  if (someCondition) {
    await route.fulfill({ status: 200, body: '{}' });
  }
  // else: request is never resolved
});
```

**Fix:**

```typescript
// Good — every code path resolves the request
await page.route('**/api/data', async (route) => {
  if (someCondition) {
    await route.fulfill({ status: 200, body: '{}' });
  } else {
    await route.continue(); // pass through to the real server
  }
});
```

**Detection hints:**
- Search for `page.route(` handlers with conditional logic where not all branches call `route.fulfill/continue/abort`

---

## PW-SEC-005: Trace and video artifacts MUST be scoped to failures; full capture requires a data retention policy

**Severity: Medium**

Playwright traces, screenshots, and videos capture rendered page state, network request headers, and cookies. When stored as CI artifacts, they may contain session tokens, rendered passwords, or PII visible on screen.

**Required:**
- MUST NOT use `trace: 'on'` or `video: 'on'` in CI without a documented artifact access policy and retention limit
- SHOULD use `trace: 'on-first-retry'` and `screenshot: 'only-on-failure'` in CI — captures enough for debugging without exposing full session data on every run
- MUST review trace artifact access permissions — traces should not be publicly downloadable from CI

**Guidance:**

```typescript
// Safer CI configuration — only capture on failure
export default defineConfig({
  use: {
    trace: 'on-first-retry',       // not 'on'
    screenshot: 'only-on-failure', // not 'on'
    video: 'on-first-retry',       // not 'on'
  },
});
```

---

## PW-SEC-006: Base URL MUST be explicit in CI; production MUST NOT be a fallback value

**Severity: Medium**

When `BASE_URL` is unset in CI and a fallback value is a production URL, a misconfigured pipeline silently runs tests against production — potentially creating data, triggering notifications, or consuming quota.

**Required:**
- MUST require `BASE_URL` to be explicitly set in CI — throw an error if it is absent
- MUST NOT use a production URL as a `??` fallback in `playwright.config.ts`
- SHOULD separate test environments from production by network policy or credential scope, not only by URL

**Insecure pattern:**

```typescript
// Bad — silently runs against production if BASE_URL is unset in CI
use: { baseURL: process.env.BASE_URL ?? 'https://app.production.com' }
```

**Fix:**

```typescript
// Good — CI pipeline must explicitly provide BASE_URL
const baseURL = process.env.BASE_URL;
if (!baseURL) throw new Error('BASE_URL environment variable is required — do not fall back to production');

export default defineConfig({ use: { baseURL } });
```

---

## Scanning Heuristics for Playwright Suites

High-signal patterns to audit:

- `.fill(` with a string literal resembling a password, token, or key → `PW-SEC-001`
- Storage state files (`.auth/*.json`, `storageState.json`) tracked in git → `PW-SEC-002`
- `ignoreHTTPSErrors: true` without an environment variable guard → `PW-SEC-003`
- `page.route(` handler with conditional logic and no guaranteed `fulfill/continue/abort` → `PW-SEC-004`
- `trace: 'on'` or `video: 'on'` in CI configuration → review `PW-SEC-005`
- `baseURL` with a production URL as a fallback value → `PW-SEC-006`

---

## Resources

- [Playwright Authentication](https://playwright.dev/docs/auth)
- [Playwright Configuration](https://playwright.dev/docs/test-configuration)
- [Playwright Network](https://playwright.dev/docs/network)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [GitLab CI/CD Variables](https://docs.gitlab.com/ee/ci/variables/)
