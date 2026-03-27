# Playwright Reference — code-review

Supplements `review-checklist.md`, `clean-code-checklist.md`, and `solid-principles.md` for projects using `@playwright/test`.

---

## General Playwright Code Review Patterns

### Architecture and Design

- [ ] Page Object Model implemented — no raw `page.locator()` or `page.getByRole()` in test/automation logic outside POM classes
- [ ] POM classes own selectors — a selector used in multiple methods exists as a single `readonly Locator` property
- [ ] Fixtures (`test.extend`) isolate shared setup/teardown — no duplicated browser context configuration across files
- [ ] Configuration (base URL, timeouts, browsers, retries) lives in `playwright.config.ts` — not hardcoded per file
- [ ] Authentication via `storageState` — login performed once in a setup project and reused via context

```typescript
// Bad — base URL hardcoded; breaks across environments
await page.goto('https://production.example.com/orders');

// Good — base URL from config, sourced from environment
// playwright.config.ts: use: { baseURL: process.env.BASE_URL }
await page.goto('/orders');
```

### Code Quality

- [ ] Every Playwright action and assertion is awaited — unawaited calls silently do nothing
- [ ] `page.waitForTimeout()` absent — all waits are condition-based assertions
- [ ] `page.$` / `page.$$` (deprecated jQuery-style) absent — use `page.locator()` or typed getBy methods
- [ ] `getByRole`, `getByLabel`, `getByTestId` used for interactive elements — CSS class and nth-child selectors absent
- [ ] Locators defined as `readonly Locator` properties on POM classes — not constructed inline in action methods

```typescript
// Bad — unawaited action; executes nothing; test passes incorrectly
page.click('#submit');
page.waitForURL('/success');

// Good
await page.click('#submit');
await page.waitForURL('/success');

// Bad — assertion always passes; the await is on the locator, not the assertion
expect(page.getByRole('dialog')).toBeVisible();

// Good
await expect(page.getByRole('dialog')).toBeVisible();
```

### Route Handlers — Always Resolve

- [ ] Every `page.route()` handler calls exactly one of `route.fulfill()`, `route.continue()`, or `route.abort()` in every code path
- [ ] No conditional handlers that leave the request hanging on unmatched branches

```typescript
// Bad — hanging route; request never resolved if condition is false; test times out
await page.route('**/api/users', async (route) => {
  if (shouldMock) {
    await route.fulfill({ status: 200, body: '{}' });
  }
  // else: request hangs forever
});

// Good — always respond
await page.route('**/api/users', async (route) => {
  if (shouldMock) {
    await route.fulfill({ status: 200, body: '{}' });
  } else {
    await route.continue();
  }
});
```

### Security

- [ ] No hardcoded credentials in test files or `playwright.config.ts` — use `process.env.*`
- [ ] Storage state files (`.auth/*.json`) listed in `.gitignore` — they contain live session tokens
- [ ] `ignoreHTTPSErrors: true` only present in development config; never globally for all environments
- [ ] Base URL has no production fallback — misconfigured CI should fail loudly, not run against prod

```typescript
// Bad — credential committed to source control
setup('authenticate', async ({ page }) => {
  await page.getByLabel('Password').fill('SuperSecret123!');
});

// Good — credential from CI secret
setup('authenticate', async ({ page }) => {
  await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
});

// Bad — falls back to production if BASE_URL is unset
use: { baseURL: process.env.BASE_URL ?? 'https://app.production.com' }

// Good — fail loudly if required env var is missing
const baseURL = process.env.BASE_URL;
if (!baseURL) throw new Error('BASE_URL environment variable is required');
export default defineConfig({ use: { baseURL } });
```

### Configuration Quality

- [ ] Workers and parallelism configured explicitly — not left at single-worker defaults in CI
- [ ] `retries` gated on `process.env.CI` — local runs do not retry to hide flakiness
- [ ] Trace, screenshot, and video recording set to `'on-first-retry'` or `'only-on-failure'` — not `'on'`
- [ ] Timeouts set per environment — default 30 s may be too long or too short

```typescript
// playwright.config.ts — production-ready baseline
export default defineConfig({
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? '50%' : undefined,
  use: {
    baseURL: process.env.BASE_URL!,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },
});
```

### Test Scope and Independence

- [ ] `test.describe.serial` usage has a justification comment explaining why order is required
- [ ] Route mocks cover both success and error paths — not only happy path
- [ ] Tests do not launch a new `browser` instance — always use the `page` fixture

```typescript
// Bad — launches a new browser process inside a test; expensive and defeats worker model
test('example', async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  // ...
  await browser.close();
});

// Good — page fixture provides a fresh context within the managed worker browser
test('example', async ({ page }) => {
  // page is isolated within the worker's browser process
});
```

---

## Resources

- [Playwright Configuration](https://playwright.dev/docs/test-configuration)
- [Page Object Model](https://playwright.dev/docs/pom)
- [Playwright Fixtures](https://playwright.dev/docs/test-fixtures)
- [Authentication (storageState)](https://playwright.dev/docs/auth)
- [Network Mocking](https://playwright.dev/docs/mock)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
