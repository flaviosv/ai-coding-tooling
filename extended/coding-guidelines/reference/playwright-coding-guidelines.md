# Playwright Reference — coding-guidelines

Authoritative style and idiom guide for TypeScript/JavaScript projects using `@playwright/test`.
Deviations from these rules are findings.
Sourced from the official Playwright documentation and best-practices guide.

---

## General Playwright Coding Style

### Naming Conventions

- **Test files**: `<feature>.spec.ts` — e.g., `login.spec.ts`, `checkout.spec.ts`, `user-profile.spec.ts`
- **Setup files**: `<name>.setup.ts` — e.g., `auth.setup.ts`
- **Page Object files**: `<page-name>.page.ts` — e.g., `login.page.ts`, `dashboard.page.ts`
- **Fixture files**: `<name>.fixture.ts` — e.g., `auth.fixture.ts`, `pages.fixture.ts`
- **Auth state files**: `<role>.json` inside `.auth/` — e.g., `.auth/user.json`, `.auth/admin.json`
- **Test names**: declarative present tense describing what the system does — not what the test does
- **`test.describe` labels**: noun phrase matching the feature or component — `'Login'`, `'Shopping Cart'`
- **Page Object classes**: PascalCase with `Page` suffix — `LoginPage`, `DashboardPage`, `CheckoutPage`

```typescript
// Good naming — declarative, describes system behaviour
test.describe('Checkout', () => {
  test('adds shipping address and proceeds to payment', async ({ page }) => { ... });
  test('shows error banner when card is declined', async ({ page }) => { ... });
  test('applies a valid promo code and reduces the total', async ({ page }) => { ... });
});

// Bad naming — imperative; describes test actions, not system behaviour
test.describe('Test checkout', () => {
  test('test add address', async ({ page }) => { ... });
  test('test declined card', async ({ page }) => { ... });
  test('test promo code', async ({ page }) => { ... });
});
```

---

### File Organization

Standard project layout for a Playwright test suite:

```
tests/
  e2e/
    login.spec.ts
    checkout.spec.ts
    user-profile.spec.ts
  setup/
    auth.setup.ts
  fixtures/
    pages.fixture.ts
    auth.fixture.ts
  pages/
    login.page.ts
    checkout.page.ts
    dashboard.page.ts
  helpers/
    api.ts            # direct API calls for test setup/teardown (not UI)
playwright.config.ts
.auth/                # gitignored — storage state files (live session tokens)
  user.json
  admin.json
```

---

### Locator Conventions

Define locators as `readonly Locator` properties initialised in the constructor — never construct them inline in action methods.

```typescript
// Good — locators as constructor-initialised readonly properties; single source of truth
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

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }
}

// Bad — locators constructed inside methods; duplicated on every call; impossible to reuse in assertions
export class LoginPage {
  async login(email: string, password: string) {
    await this.page.getByLabel('Email').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Sign in' }).click();
  }
}
```

Locator priority order (most to least resilient):

1. `getByRole` — maps to ARIA semantics; survives CSS and layout refactors
2. `getByLabel` — label associations for form fields
3. `getByPlaceholder` / `getByText` — visible text when role/label unavailable
4. `getByTestId` — explicit data attribute for components with no natural ARIA role
5. CSS / XPath — last resort; flag in review

---

### Async/Await Discipline

Every Playwright action and assertion must be awaited. Unawaited calls return a Promise that is silently ignored.

```typescript
// Bad — unawaited; these calls do nothing; test may pass incorrectly
page.click('#submit');
page.waitForURL('/success');
expect(page.getByText('Error')).toBeVisible();

// Good
await page.click('#submit');
await page.waitForURL('/success');
await expect(page.getByText('Error')).toBeVisible();
```

Enforce this rule statically: enable `@typescript-eslint/no-floating-promises` in `eslint.config.ts`.

---

### Configuration

All test-wide settings belong in `playwright.config.ts`. Never hardcode base URLs, timeouts, or browser options in test files.

```typescript
// playwright.config.ts — standard configuration pattern
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? '50%' : undefined,
  timeout: 30_000,
  use: {
    baseURL: process.env.BASE_URL!,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: '.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
});
```

---

### Assertions Style

Use web-first assertions (`expect(locator).*`) exclusively. Never check state imperatively.

```typescript
// Good — web-first; auto-waits and retries
await expect(page.getByRole('alert')).toContainText('Invalid credentials');
await expect(page).toHaveURL('/dashboard');
await expect(page.locator('.item')).toHaveCount(5);

// Bad — manual check; no retry; timing-unsafe
const text = await page.locator('#message').textContent();
expect(text).toContain('Success');

// Bad — isVisible() resolves immediately; fails under any render delay
expect(await page.getByText('Welcome').isVisible()).toBe(true);
```

---

### Anti-Patterns

```typescript
// Bad — hard-coded sleep; always replace with a condition-based assertion
await page.waitForTimeout(1000);

// Bad — page.$ and page.$$ are deprecated jQuery-style aliases; use locators
const el = await page.$('.submit-btn');

// Bad — CSS classes as selectors; fragile under CSS refactoring
await page.locator('.btn-primary.cta-button').click();

// Bad — hardcoded URL; tests cannot run in other environments
await page.goto('https://www.production-site.com/login');

// Bad — test.describe.serial without justification comment; kills parallelism
test.describe.serial('account flow', () => { ... });

// Bad — ignoreHTTPSErrors without environment guard; masks certificate issues
use: { ignoreHTTPSErrors: true }

// Bad — credentials in source code
await page.getByLabel('Password').fill('Admin@123');

// Bad — new browser launched inside a test; defeats the worker model
const browser = await chromium.launch();
```

---

## Resources

- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright Locators](https://playwright.dev/docs/locators)
- [Page Object Model](https://playwright.dev/docs/pom)
- [Test Fixtures](https://playwright.dev/docs/test-fixtures)
- [Playwright Configuration](https://playwright.dev/docs/test-configuration)
- [Web-First Assertions](https://playwright.dev/docs/test-assertions)
