# Playwright Reference — tests-code-review

Supplements `test-review-checklist.md` for projects using `@playwright/test`.

---

## General Playwright Test Review Patterns

### Test Naming

```typescript
// Bad — generic; a failing test reports nothing about what broke
test('test login', async ({ page }) => { ... });
test('test checkout', async ({ page }) => { ... });

// Good — scenario + expected outcome; a failing name explains itself
test('invalid credentials show inline error under the password field', async ({ page }) => { ... });
test('successful login redirects to /dashboard', async ({ page }) => { ... });

// Good — grouped with describe; first word of describe + test name reads as a sentence
test.describe('Login', () => {
  test('valid credentials redirect to dashboard', async ({ page }) => { ... });
  test('locked account shows link to contact support', async ({ page }) => { ... });
  test('forgot password link navigates to reset flow', async ({ page }) => { ... });
});
```

---

### Assertions

#### Hard-Coded Waits — Flag All Occurrences

```typescript
// Bad — arbitrary sleep; flaky on CI under load, slow when not needed
await page.waitForTimeout(2000);
await page.click('#submit');

// Good — assert the condition that makes the next step meaningful
await page.click('#submit');
await expect(page.getByRole('dialog')).toBeVisible();
```

Every `page.waitForTimeout()` is a finding. No exceptions — replace with a condition-based assertion.

#### Non-Retrying Assertions

```typescript
// Bad — isVisible() resolves immediately; fails if element renders with any delay
expect(await page.getByText('Welcome').isVisible()).toBe(true);

// Good — expect() wraps with auto-wait and retry logic
await expect(page.getByText('Welcome')).toBeVisible();
```

#### Asserting Existence Without Content

```typescript
// Bad — confirms the element exists but not what it communicates; passes on wrong error messages
await expect(page.getByRole('alert')).toBeVisible();

// Good — asserts the exact intent
await expect(page.getByRole('alert')).toContainText('Invalid email address');
```

#### Missing `await` on Assertions

```typescript
// Bad — unawaited assertion always passes regardless of actual state
expect(page.getByRole('dialog')).toBeVisible();

// Good
await expect(page.getByRole('dialog')).toBeVisible();
```

Enable `@typescript-eslint/no-floating-promises` to catch this at the editor level.

---

### Locators

#### Brittle CSS and XPath Selectors

```typescript
// Bad — CSS class; breaks when designer renames classes
await page.locator('button.btn-primary.login-submit').click();

// Bad — nth-child position; breaks on any DOM reorder
await page.locator('#form > div:nth-child(3) > input').fill('value');

// Bad — fragile XPath chain
await page.locator('//*[@id="tsf"]/div[2]/div[1]/div[1]/div/div[2]/input').click();

// Good — role-based; semantically stable
await page.getByRole('button', { name: 'Sign in' }).click();
await page.getByLabel('Email').fill('user@example.com');
```

#### Implicit Waiting Without Assertion

```typescript
// Bad — count() resolves immediately; race condition if items load asynchronously
const count = await page.locator('.item').count();
expect(count).toBe(3);

// Good — web-first assertion retries until count matches
await expect(page.locator('.item')).toHaveCount(3);
```

---

### Test Independence

#### Tests That Share Mutable State

```typescript
// Bad — test 2 depends on data created by test 1; ordering dependency
test('creates item', async ({ page }) => {
  // creates 'Item A' via the UI
});
test('deletes item', async ({ page }) => {
  // fails if 'creates item' did not run first
  await page.getByText('Item A').getByRole('button', { name: 'Delete' }).click();
});

// Good — each test owns its preconditions
test('deletes an item', async ({ page }) => {
  await createItemViaAPI({ name: 'Item A' }); // API call for fast, independent setup
  await page.goto('/items');
  await page.getByText('Item A').getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByText('Item A')).toBeHidden();
});
```

#### Authentication Duplicated in Test Bodies

```typescript
// Bad — full login UI sequence before every test; slow and brittle if login UI changes
test.beforeEach(async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env.TEST_USER_EMAIL!);
  await page.getByLabel('Password').fill(process.env.TEST_USER_PASSWORD!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('/dashboard');
});

// Good — storageState restores session; login runs once in a setup project
// playwright.config.ts: use: { storageState: '.auth/user.json' }
test('views orders page', async ({ page }) => {
  await page.goto('/orders');
  await expect(page.getByText('Your orders')).toBeVisible();
});
```

#### `test.describe.serial` Without Justification

```typescript
// Bad — forces sequential execution across tests that could run in parallel
test.describe.serial('dashboard features', () => {
  test('loads widget', async ({ page }) => { ... });
  test('filters data', async ({ page }) => { ... }); // independent; doesn't need serial
});

// Good — only genuinely dependent tests serialised; justification comment required
test.describe.serial('multi-step import wizard', () => {
  // These tests must run in order: wizard state is persisted across steps
  test('step 1: upload file', async ({ page }) => { ... });
  test('step 2: map columns', async ({ page }) => { ... });
  test('step 3: confirm and import', async ({ page }) => { ... });
});
```

---

### Page Object Model Discipline

```typescript
// Bad — raw locator calls in test body; duplicated across test files; hard to maintain
test('adds item to cart', async ({ page }) => {
  await page.goto('/products');
  await page.locator('.product-card').first().locator('button[data-add-cart]').click();
  await expect(page.locator('#cart-count')).toHaveText('1');
});

// Good — page object owns selectors; test reads as a user story
test('adds item to cart', async ({ page }) => {
  const productsPage = new ProductsPage(page);
  await productsPage.goto();
  await productsPage.addFirstItemToCart();
  await expect(productsPage.cartCount).toHaveText('1');
});
```

---

### Network Mocking

#### Tests That Depend on Real APIs

```typescript
// Bad — test breaks on network issues, slow external APIs, or changing real data
test('shows order list', async ({ page }) => {
  await page.goto('/orders');
  await expect(page.getByText('Order #12345')).toBeVisible(); // depends on real DB data
});

// Good — deterministic data via route mock
test('shows fetched orders in a table', async ({ page }) => {
  await page.route('**/api/orders', route =>
    route.fulfill({ status: 200, body: JSON.stringify([{ id: 1, number: '#001' }]) })
  );
  await page.goto('/orders');
  await expect(page.getByText('#001')).toBeVisible();
});
```

#### Hanging Route Handlers

```typescript
// Bad — request never resolved if condition is not met; test hangs until timeout
await page.route('**/api/data', async (route) => {
  if (someCondition) {
    await route.fulfill({ status: 200, body: '{}' });
  }
  // else: request hangs
});

// Good — always resolve the request
await page.route('**/api/data', async (route) => {
  if (someCondition) {
    await route.fulfill({ status: 200, body: '{}' });
  } else {
    await route.continue();
  }
});
```

---

### Coverage Gaps to Flag

The most common missing coverage in Playwright suites:

- [ ] API 4xx/5xx — does the UI surface an appropriate error message? (use route mock)
- [ ] Empty state — what does the list/dashboard show with no data?
- [ ] Loading state — is a spinner or skeleton shown while data loads?
- [ ] Form validation — each invalid input triggers its specific inline error
- [ ] Unauthorised access — redirected to login or shown a 403 page
- [ ] Auth expiry — session timeout or token refresh handled gracefully

---

## Playwright Test Review Checklist

### Structure
- [ ] Test names describe scenario and expected outcome — a failing name explains itself
- [ ] `test.describe` groups related tests by feature or component
- [ ] Page Object Model used — no raw `page.locator()` / `page.getByRole()` calls in test bodies
- [ ] Fixtures (`test.extend`) used for shared setup — no copy-pasted `beforeEach` blocks

### Assertions
- [ ] All assertions use `expect(locator).*` — not `expect(await locator.isVisible()).toBe(true)`
- [ ] Assertions validate content, not just element existence
- [ ] No `page.waitForTimeout()` — every wait tied to an observable condition
- [ ] Every `expect(...)` call is awaited

### Locators
- [ ] No CSS class or nth-child selectors — `getByRole`, `getByLabel`, `getByTestId` used instead
- [ ] No XPath selectors (flag unless targeting a browser-native element with no ARIA role)
- [ ] Locators defined as POM class properties — not constructed inline in action methods

### Independence
- [ ] Tests do not share mutable state (DB records, localStorage, cookies)
- [ ] Each test owns its preconditions — no ordering dependencies
- [ ] `test.describe.serial` not used without a justification comment
- [ ] Authentication via `storageState` — no full login sequence in `beforeEach`

### Coverage
- [ ] Happy path tested
- [ ] API error states (4xx, 5xx) tested via route mocks — not just happy path
- [ ] Empty state tested
- [ ] Form validation error messages asserted with specific content

### Performance
- [ ] No `waitForTimeout` — every wait bound to an observable condition
- [ ] `fullyParallel: true` in config; tests do not force serial ordering unnecessarily
- [ ] `storageState` used to skip login overhead

---

## Resources

- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright Locators](https://playwright.dev/docs/locators)
- [Page Object Model](https://playwright.dev/docs/pom)
- [Web-First Assertions](https://playwright.dev/docs/test-assertions)
- [Authentication (storageState)](https://playwright.dev/docs/auth)
- [Network Mocking](https://playwright.dev/docs/mock)
- [Parallel Tests](https://playwright.dev/docs/test-parallel)
