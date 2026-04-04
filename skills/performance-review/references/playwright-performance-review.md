# Playwright Reference — performance-review

Supplements `performance-checklist.md` for projects using `@playwright/test`.

---

## General Playwright Performance Patterns

Focus optimisation on the slowest 10% of tests — they dominate total suite time.

### Identify Slow Tests First

```bash
npx playwright show-report
npx playwright test --reporter=list
npx playwright test --reporter=json > results.json
```

## Parallelism

### Under-Utilised Workers

```typescript
// Bad
export default defineConfig({ workers: 1 });

// Good — independent tests run concurrently
export default defineConfig({
  fullyParallel: true,
  workers: process.env.CI ? '50%' : undefined,
});
```

Tests MUST be independent. Shared mutable state prevents safe parallelism.

### `test.describe.serial` Overuse

Each `test.describe.serial` block runs sequentially in a single worker. Every unnecessary use multiplies suite time.

```typescript
// Bad — serialises independent tests
test.describe.serial('user account', () => {
  test('loads profile', async ({ page }) => { ... });
  test('views billing', async ({ page }) => { ... });
});

// Good — all run in parallel
test.describe('user account', () => {
  test('loads profile page', async ({ page }) => { ... });
  test('views billing history', async ({ page }) => { ... });
});

// Only use serial when execution order is genuinely required
test.describe.serial('multi-step import wizard', () => {
  test('step 1: upload file', async ({ page }) => { ... });
  test('step 2: map columns', async ({ page }) => { ... });
  test('step 3: confirm and import', async ({ page }) => { ... });
});
```

## Authentication

### Re-Login in Every Test

Full browser login costs 1–3s per test. With 100 tests: 1.5–5 min wasted.

```typescript
// Bad — full login before every test
test.beforeEach(async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env.TEST_USER_EMAIL!);
  await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('/dashboard');
});

// Good — login once in setup project; restore via storageState
projects: [
  { name: 'setup', testMatch: /auth\.setup\.ts/ },
  {
    name: 'authenticated',
    use: { storageState: '.auth/user.json' },
    dependencies: ['setup'],
  },
],
```

## Locators and Waiting

### `waitForTimeout` — Every Occurrence Is a Performance Bug

Adds fixed dead time regardless of page state. Leading cause of flakiness.

```typescript
// Bad
await page.waitForTimeout(2000);
await page.click('#submit');

// Good — waits only as long as needed
await page.click('#submit');
await expect(page.getByTestId('success-banner')).toBeVisible();
```

### DOM Polling Instead of Event-Based Waiting

```typescript
// Bad — polls DOM every 200ms
await page.waitForFunction(() => document.querySelectorAll('.item').length >= 5, { polling: 200 });

// Good — built-in auto-wait, no polling overhead
await expect(page.locator('.item')).toHaveCount(5);
```

## Browser Contexts and Resources

### Launching a New Browser Per Test

Each worker gets one browser process. Launching inside a test adds 200–500ms overhead.

```typescript
// Bad
test('example', async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await browser.close();
});

// Good — use managed page fixture
test('example', async ({ page }) => { /* fresh context; no launch overhead */ });
```

### Trace, Screenshot, and Video Recording

Recording on every test adds disk I/O and CPU overhead proportional to test count.

```typescript
// Bad
use: { trace: 'on', screenshot: 'on', video: 'on' }

// Good — zero overhead on passing tests
use: { trace: 'on-first-retry', screenshot: 'only-on-failure', video: 'on-first-retry' }
```

## Network

### Unnecessary External Requests

Third-party scripts add 50–500ms latency per test and introduce flakiness.

```typescript
// Good — block irrelevant external resources
test.beforeEach(async ({ page }) => {
  await page.route('**/google-analytics.com/**', route => route.abort());
  await page.route('**/hotjar.com/**', route => route.abort());
  await page.route('**/*.{woff,woff2,ttf}', route => route.abort());
});
```

Apply selectively — only abort resources irrelevant to assertions.

### Overly Broad Route Intercepts

```typescript
// Bad
await page.route('**', route => route.fulfill({ status: 200, body: '{}' }));

// Good — only mock specific API endpoints
await page.route('**/api/v1/orders', route =>
  route.fulfill({ status: 200, body: JSON.stringify(mockOrders) })
);
```

## Retries and Flakiness

### Excessive Global Retries

```typescript
// Bad — 3 retries masks flakiness, triples worst-case CI time
retries: 3,

// Good
retries: process.env.CI ? 2 : 0,
```

Common flakiness root causes — fix these rather than increasing retries:

- `waitForTimeout` with insufficient time → condition-based waits
- Asserting element count before render complete → `toHaveCount()` with auto-wait
- Shared test state across parallel workers → self-contained tests
- External network dependency → mock with `page.route()`
- Real-time clock assertions → Clock API (v1.45+)

## Performance Checklist for Playwright Suites

- [ ] `fullyParallel: true` enabled; `workers` set to at least `'50%'` in CI
- [ ] Authentication uses `storageState` — no `page.goto('/login')` in `beforeEach`
- [ ] No `page.waitForTimeout()` calls anywhere in the suite
- [ ] `trace`, `screenshot`, `video` set to `'on-first-retry'` or `'only-on-failure'` — not `'on'`
- [ ] No `browser.launch()` inside test bodies — always use the `page` fixture
- [ ] `test.describe.serial` usage audited — present only where execution order is genuinely required
- [ ] Third-party analytics and CDN requests mocked with `route.abort()` where irrelevant to assertions
- [ ] `retries` set to `process.env.CI ? 2 : 0` — not globally set to 3+
