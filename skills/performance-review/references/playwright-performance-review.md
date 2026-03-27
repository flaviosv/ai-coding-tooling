# Playwright Reference — performance-review

Supplements `performance-checklist.md` for projects using `@playwright/test`.

---

## General Playwright Performance Patterns

Performance in Playwright suites is measured by total CI execution time, flakiness-induced re-runs, and resource overhead per test. Focus optimisation on the slowest 10% of tests — they dominate total suite time.

### Identify Slow Tests First

```bash
# HTML report shows per-test duration — open after a run
npx playwright show-report

# List reporter prints duration inline during execution
npx playwright test --reporter=list

# JSON output for programmatic analysis
npx playwright test --reporter=json > results.json
```

---

## Parallelism

### Under-Utilised Workers

```typescript
// Bad — single worker; every test runs sequentially; CI time = sum of all test durations
export default defineConfig({
  workers: 1,
});

// Good — parallel workers; independent tests run concurrently; CI time ≈ slowest test cluster
export default defineConfig({
  fullyParallel: true,
  workers: process.env.CI ? '50%' : undefined, // 50% of CPUs in CI; auto on local
});
```

**Prerequisite:** tests must be independent. Shared mutable state between tests prevents safe parallelism.

### `test.describe.serial` Overuse

Each `test.describe.serial` block runs sequentially in a single worker. Every unnecessary use is a multiplier on suite time.

```typescript
// Bad — serialises all tests including independent ones
test.describe.serial('user account', () => {
  test('loads profile', async ({ page }) => { ... });    // independent
  test('views billing', async ({ page }) => { ... });    // independent
  test('views orders', async ({ page }) => { ... });     // independent
});

// Good — each test is self-contained; all run in parallel
test.describe('user account', () => {
  test('loads profile page', async ({ page }) => { ... });
  test('views billing history', async ({ page }) => { ... });
  test('views order list', async ({ page }) => { ... });
});

// Only use serial when execution order is genuinely required (e.g., a wizard flow)
test.describe.serial('multi-step import wizard', () => {
  // wizard state persists across steps in this UI
  test('step 1: upload file', async ({ page }) => { ... });
  test('step 2: map columns', async ({ page }) => { ... });
  test('step 3: confirm and import', async ({ page }) => { ... });
});
```

---

## Authentication

### Re-Login in Every Test

Full browser login is 1–3 seconds per test. With 100 authenticated tests: 1.5–5 minutes wasted on authentication overhead alone.

```typescript
// Bad — full login sequence before every test
test.beforeEach(async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env.TEST_USER_EMAIL!);
  await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('/dashboard');
});

// Good — login once in a setup project; restore session via storageState
// playwright.config.ts:
projects: [
  { name: 'setup', testMatch: /auth\.setup\.ts/ },
  {
    name: 'authenticated',
    use: { storageState: '.auth/user.json' },
    dependencies: ['setup'],
  },
],
```

---

## Locators and Waiting

### `waitForTimeout` — Every Occurrence Is a Performance Bug

`waitForTimeout` adds fixed dead time to every execution, regardless of actual page state. It is also the leading cause of flakiness — too short on slow CI, needlessly slow on fast CI.

```typescript
// Bad — adds 2 s to every test execution unconditionally
await page.waitForTimeout(2000);
await page.click('#submit');

// Good — waits only as long as needed
await page.click('#submit');
await expect(page.getByTestId('success-banner')).toBeVisible();
```

### DOM Polling Instead of Event-Based Waiting

```typescript
// Bad — polls the DOM every 200 ms; CPU overhead + minimum polling delay
await page.waitForFunction(() => {
  return document.querySelectorAll('.item').length >= 5;
}, { polling: 200 });

// Good — Playwright's built-in auto-wait handles this with no polling overhead
await expect(page.locator('.item')).toHaveCount(5);
```

---

## Browser Contexts and Resources

### Launching a New Browser Per Test

Each test worker gets one browser process. Tests within a worker get a fresh context automatically. Launching a new browser inside a test adds 200–500 ms of browser startup overhead and defeats the worker model.

```typescript
// Bad — launches a new browser process per test; significant overhead
test('example', async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  // ... test body ...
  await browser.close();
});

// Good — use the managed page fixture; context is isolated within the worker
test('example', async ({ page }) => {
  // fresh browser context; no launch overhead
});
```

### Trace, Screenshot, and Video Recording

Recording on every test adds disk I/O and CPU overhead proportional to test count.

```typescript
// Bad — records trace, screenshots, and video for every test; significant overhead
use: {
  trace: 'on',
  screenshot: 'on',
  video: 'on',
}

// Good — record only on failure or first retry; zero overhead on passing tests
use: {
  trace: 'on-first-retry',
  screenshot: 'only-on-failure',
  video: 'on-first-retry',
}
```

---

## Network

### Unnecessary External Requests

Third-party scripts (analytics, chat widgets, CDN fonts, A/B test tools) add 50–500 ms of network latency per test and introduce flakiness from external service availability.

```typescript
// Good — block irrelevant external resources before each test
test.beforeEach(async ({ page }) => {
  // Block analytics and tracking scripts
  await page.route('**/google-analytics.com/**', route => route.abort());
  await page.route('**/hotjar.com/**', route => route.abort());
  // Block fonts if not needed for visual assertions
  await page.route('**/*.{woff,woff2,ttf}', route => route.abort());
});
```

Apply selectively — only abort resources that are irrelevant to the test's assertions.

### Overly Broad Route Intercepts

```typescript
// Bad — intercepts ALL requests including page navigation; unpredictable side effects
await page.route('**', route => route.fulfill({ status: 200, body: '{}' }));

// Good — targeted routes; only mock the specific API endpoints under test
await page.route('**/api/v1/orders', route =>
  route.fulfill({ status: 200, body: JSON.stringify(mockOrders) })
);
```

---

## Retries and Flakiness

### Excessive Global Retries

```typescript
// Bad — 3 retries masks flakiness and triples worst-case CI time
retries: 3,

// Good — 2 retries in CI only; investigate and fix recurring failures
retries: process.env.CI ? 2 : 0,
```

Common root causes of Playwright flakiness — fix these rather than increasing retries:

- `waitForTimeout` with insufficient time → replace with condition-based waits
- Asserting element count before all items have rendered → `toHaveCount()` with auto-wait
- Shared test state across parallel workers → make each test self-contained
- Dependency on external network services → mock with `page.route()`
- Real-time clock assertions → use Clock API (v1.45+) to control time

---

## Performance Checklist for Playwright Suites

- [ ] `fullyParallel: true` enabled; `workers` set to at least `'50%'` in CI
- [ ] Authentication uses `storageState` — no `page.goto('/login')` in `beforeEach`
- [ ] No `page.waitForTimeout()` calls anywhere in the suite
- [ ] `trace`, `screenshot`, `video` set to `'on-first-retry'` or `'only-on-failure'` — not `'on'`
- [ ] No `browser.launch()` inside test bodies — always use the `page` fixture
- [ ] `test.describe.serial` usage audited — present only where execution order is genuinely required
- [ ] Third-party analytics and CDN requests mocked with `route.abort()` where irrelevant to assertions
- [ ] `retries` set to `process.env.CI ? 2 : 0` — not globally set to 3+

---

## Resources

- [Playwright Parallelism](https://playwright.dev/docs/test-parallel)
- [Playwright Configuration](https://playwright.dev/docs/test-configuration)
- [Authentication (storageState)](https://playwright.dev/docs/auth)
- [Network Routing](https://playwright.dev/docs/network)
- [Playwright Retries](https://playwright.dev/docs/test-retries)
- [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer)
- [Clock API](https://playwright.dev/docs/clock) (v1.45+)
