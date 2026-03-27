# Playwright Reference — tests

Applies to TypeScript/JavaScript projects using `@playwright/test`.
For Python Playwright (`pytest-playwright`), adapt patterns — core concepts (POM, fixtures, assertions) are identical.

---

## General Playwright Testing Patterns

Universal conventions that apply across all currently supported Playwright versions (v1.40+).

### Test File Structure

```typescript
// tests/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Login', () => {
  test('valid credentials redirect to dashboard', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill('user@example.com');
    await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page).toHaveURL('/dashboard');
  });

  test('invalid credentials show inline error', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill('bad@example.com');
    await page.getByLabel('Password').fill('wrong');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByRole('alert')).toContainText('Invalid credentials');
  });
});
```

File naming: `<feature>.spec.ts` for tests, `<feature>.page.ts` for Page Object classes, `<name>.setup.ts` for setup projects, `<name>.fixture.ts` for fixture definitions.

---

### Locator Priority (Most to Least Preferred)

Use locators in this order — each level is more resilient to UI changes than the next:

1. **Role-based** — `getByRole('button', { name: 'Submit' })` — ARIA semantics; survives CSS refactors
2. **Label** — `getByLabel('Email')` — matches `<label>` associations
3. **Placeholder / text** — `getByPlaceholder('Enter email')`, `getByText('Welcome')`
4. **Test ID** — `getByTestId('submit-btn')` — explicit data attribute; best when role/label are ambiguous
5. **CSS / XPath** — last resort only; highly brittle

```typescript
// Good — role-based; works regardless of class changes
await page.getByRole('button', { name: 'Sign in' }).click();

// Good — label association; works regardless of layout changes
await page.getByLabel('Email').fill('user@example.com');

// Good — explicit test id for complex custom components
await page.getByTestId('date-picker-trigger').click();

// Bad — class name is an implementation detail; breaks with CSS refactors
await page.locator('button.btn-primary.login-submit').click();

// Bad — fragile XPath; breaks with any DOM restructure
await page.locator('//*[@id="app"]/div[2]/form/button').click();
```

---

### Web-First Assertions

`expect()` wraps assertions with auto-wait and retry. Never gate assertions on manual checks.

```typescript
// Good — auto-waits for element to satisfy the condition
await expect(page.getByText('Welcome back')).toBeVisible();
await expect(page.getByRole('alert')).toContainText('Error');
await expect(page).toHaveURL('/dashboard');
await expect(page.getByTestId('cart-count')).toHaveText('3');
await expect(page.locator('.item')).toHaveCount(5);

// Bad — isVisible() resolves immediately; fails on slow renders
expect(await page.getByText('Welcome back').isVisible()).toBe(true);
```

Common web-first assertions:

```typescript
await expect(locator).toBeVisible()
await expect(locator).toBeHidden()
await expect(locator).toBeEnabled()
await expect(locator).toBeDisabled()
await expect(locator).toHaveText('exact text')
await expect(locator).toContainText('partial text')
await expect(locator).toHaveValue('input value')
await expect(locator).toHaveCount(n)
await expect(locator).toHaveAttribute('href', '/about')
await expect(page).toHaveURL('/path')
await expect(page).toHaveTitle('Page Title')
```

---

### Page Object Model (POM)

Encapsulate all page interactions in a class. Tests call POM methods — never raw `page.locator()` in test bodies.

```typescript
// pages/login.page.ts
import type { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorAlert: Locator;

  constructor(readonly page: Page) {
    this.emailInput    = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton  = page.getByRole('button', { name: 'Sign in' });
    this.errorAlert    = page.getByRole('alert');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }
}

// tests/login.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';

test('valid credentials redirect to dashboard', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('user@example.com', process.env.TEST_USER_PASSWORD!);
  await expect(page).toHaveURL('/dashboard');
});
```

---

### Fixtures with `test.extend`

Extract shared setup into typed fixtures. Never duplicate browser context configuration or auth setup across test bodies.

```typescript
// fixtures/pages.fixture.ts
import { test as base, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { DashboardPage } from '../pages/dashboard.page';

type AppFixtures = {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
};

export const test = base.extend<AppFixtures>({
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await use(loginPage);
  },

  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },
});

export { expect } from '@playwright/test';
```

Use the extended `test` in spec files instead of the base import:

```typescript
import { test, expect } from '../fixtures/pages.fixture';

test('shows welcome message on dashboard', async ({ dashboardPage }) => {
  await dashboardPage.goto();
  await expect(dashboardPage.welcomeHeading).toBeVisible();
});
```

---

### Authentication via Storage State

Log in once in a setup project, save state, and reuse across all tests. Never perform a full browser login in each test.

```typescript
// tests/setup/auth.setup.ts
import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '../../.auth/user.json');

setup('authenticate as regular user', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env.TEST_USER_EMAIL!);
  await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL('/dashboard');
  await page.context().storageState({ path: authFile });
});
```

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'authenticated',
      use: {
        ...devices['Desktop Chrome'],
        storageState: '.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],
});
```

---

### Network Mocking

Use `page.route()` to intercept and control API responses. Always call `route.fulfill()`, `route.continue()`, or `route.abort()` in every code path.

```typescript
test('shows error banner when API returns 500', async ({ page }) => {
  await page.route('**/api/orders', route =>
    route.fulfill({ status: 500, body: JSON.stringify({ error: 'Internal error' }) })
  );
  await page.goto('/orders');
  await expect(page.getByRole('alert')).toContainText('Failed to load orders');
});

test('displays fetched orders', async ({ page }) => {
  await page.route('**/api/orders', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ id: 1, number: '#001', status: 'shipped' }]),
    })
  );
  await page.goto('/orders');
  await expect(page.getByText('#001')).toBeVisible();
  await expect(page.getByText('shipped')).toBeVisible();
});
```

---

### Anti-Patterns

```typescript
// Bad — hard-coded sleep; flaky on slow CI, needlessly slow on fast CI
await page.waitForTimeout(3000);
// Good — wait for the condition that signals readiness
await expect(page.getByTestId('data-table')).toBeVisible();

// Bad — unawaited action; executes nothing; test may pass incorrectly
page.click('#submit');
// Good
await page.click('#submit');

// Bad — accessing textContent() without auto-retry; timing-unsafe
const text = await page.locator('#message').textContent();
expect(text).toBe('Done');
// Good
await expect(page.locator('#message')).toHaveText('Done');

// Bad — page.$ and page.$$ are deprecated; use locators
const el = await page.$('.submit-btn');
// Good
const el = page.getByRole('button', { name: 'Submit' });
```

---

## v1.45+ — Clock API

Time manipulation for tests that depend on `Date.now()`, `setTimeout`, `setInterval`, or `requestAnimationFrame`.

```typescript
test('session expires after inactivity timeout', async ({ page }) => {
  await page.clock.install({ time: new Date('2024-06-01T10:00:00') });
  await page.goto('/dashboard');

  // Fast-forward by 30 minutes without waiting in real time
  await page.clock.fastForward('30:00');

  await expect(page.getByText('Session expired')).toBeVisible();
});

test('countdown timer reaches zero', async ({ page }) => {
  await page.clock.install({ time: new Date('2024-12-31T23:59:00') });
  await page.goto('/countdown');
  await expect(page.getByTestId('countdown')).toHaveText('1 minute remaining');

  await page.clock.fastForward(60_000); // advance 60 seconds
  await expect(page.getByTestId('countdown')).toHaveText("Time's up!");
});
```

---

## v1.46+ — ARIA Snapshots

Assert the full accessible tree structure of a component. Useful for verifying complex UI without brittle text-matching.

```typescript
test('navigation menu exposes correct links', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('navigation')).toMatchAriaSnapshot(`
    - navigation:
      - link "Home"
      - link "Products"
      - link "About"
      - link "Contact"
  `);
});
```

---

## Resources

- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright Test Fixtures](https://playwright.dev/docs/test-fixtures)
- [Page Object Model](https://playwright.dev/docs/pom)
- [Authentication (storageState)](https://playwright.dev/docs/auth)
- [Network Mocking](https://playwright.dev/docs/mock)
- [Web-First Assertions](https://playwright.dev/docs/test-assertions)
- [Clock API](https://playwright.dev/docs/clock) (v1.45+)
- [ARIA Snapshots](https://playwright.dev/docs/aria-snapshots) (v1.46+)
