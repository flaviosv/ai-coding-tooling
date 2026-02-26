# Adobe Commerce (Magento 2) Test Code Review Guide

Supplements `test-review-checklist.md` and `php-test-review-guide.md` for projects using Adobe Commerce / Magento 2 (PHPUnit, Magento Integration Test Framework).

> Covers Adobe Commerce / Magento 2 testing concerns only. PHP testing patterns are covered in `php-test-review-guide.md`.

---

## Unit Test Review Points

### ❌ Using ObjectManager in Unit Tests

```php
// Bad — real ObjectManager couples the test to the full DI container
class MyServiceTest extends \PHPUnit\Framework\TestCase
{
    public function testSomething(): void
    {
        $service = \Magento\Framework\App\ObjectManager::getInstance()
            ->create(MyService::class);
    }
}

// Good — inject mocks via constructor
class MyServiceTest extends \PHPUnit\Framework\TestCase
{
    private MyService $service;

    protected function setUp(): void
    {
        $this->repositoryMock = $this->createMock(ProductRepositoryInterface::class);
        $this->service = new MyService($this->repositoryMock);
    }
}
```

### ❌ Testing Concrete Models Instead of Service Contracts

```php
// Bad — tests implementation detail, not the contract
public function testGetProduct(): void
{
    $product = $this->createMock(\Magento\Catalog\Model\Product::class);
}

// Good — test against the interface
public function testGetProduct(): void
{
    $product = $this->createMock(\Magento\Catalog\Api\Data\ProductInterface::class);
}
```

### ❌ Not Resetting Registry State Between Tests

```php
// Bad — registry entry pollutes subsequent tests
class RegistryTest extends \PHPUnit\Framework\TestCase
{
    public function testFirst(): void
    {
        $this->registry->register('current_product', $product); // not cleaned up
    }
    // testSecond now has stale registry state
}

// Good — clean up in tearDown
protected function tearDown(): void
{
    $this->registry->unregister('current_product');
}
```

---

## Integration Test Review Points

### ❌ Missing `@magentoAppIsolation` on Tests That Modify Config

```php
// Bad — config changes leak into subsequent tests
class ConfigTest extends \Magento\TestFramework\TestCase\AbstractController
{
    public function testWithCustomConfig(): void
    {
        $this->scopeConfig->setValue('my/path/value', '1');
    }
}

// Good — isolate app state
/**
 * @magentoAppIsolation enabled
 */
class ConfigTest extends \Magento\TestFramework\TestCase\AbstractController
{
    public function testWithCustomConfig(): void
    {
        $this->scopeConfig->setValue('my/path/value', '1');
    }
}
```

### ❌ Missing `@magentoDataFixture` for Required Data

```php
// Bad — relies on pre-existing data in the test DB
public function testProductPage(): void
{
    $this->dispatch('/catalog/product/view/id/1'); // assumes product exists
    $this->assertResponseBodyContains('My Product');
}

// Good — declare the fixture
/**
 * @magentoDataFixture Magento/Catalog/_files/product_simple.php
 */
public function testProductPage(): void
{
    $product = $this->productRepository->get('simple');
    $this->dispatch('/catalog/product/view/id/' . $product->getId());
    $this->assertResponseBodyContains($product->getName());
}
```

### ❌ Using `setValue()` Instead of `@magentoConfigFixture`

```php
// Bad — bypasses proper config scoping and may leak state
public function testFeature(): void
{
    $this->scopeConfig->setValue('my_module/general/enabled', 1);
}

// Good — scoped and automatically rolled back
/**
 * @magentoConfigFixture current_store my_module/general/enabled 1
 */
public function testFeature(): void
{
    $this->assertTrue($this->config->isEnabled());
}
```

### ❌ Not Testing ACL / Authorization

```php
// Bad — only tests happy path
public function testAdminGridLoads(): void
{
    $this->dispatch('backend/my_module/grid/index');
    $this->assertResponseBodyContains('My Grid');
}

// Good — also test unauthorized access
public function testAdminGridRequiresAcl(): void
{
    $this->_objectManager->get(\Magento\Backend\Model\Auth\Session::class)
        ->setCurrentRole($this->getRoleWithoutPermission());
    $this->dispatch('backend/my_module/grid/index');
    $this->assertRedirect($this->stringContains('admin/noroute'));
}
```

---

## Plugin Test Review Points

```php
// Plugin tests call the plugin method directly — no need for DI proxy
class AfterGetNamePluginTest extends \PHPUnit\Framework\TestCase
{
    private AfterGetNamePlugin $plugin;

    protected function setUp(): void
    {
        $this->plugin = new AfterGetNamePlugin();
    }

    public function testAfterGetNameTransformsResult(): void
    {
        $subject = $this->createMock(ProductInterface::class);
        $result = $this->plugin->afterGetName($subject, 'my product');
        $this->assertSame('MY PRODUCT', $result);
    }

    public function testAfterGetNameHandlesEmptyString(): void
    {
        $subject = $this->createMock(ProductInterface::class);
        $result = $this->plugin->afterGetName($subject, '');
        $this->assertSame('', $result);
    }
}
```

---

## Observer / Event Test Review Points

```php
// Test observer logic directly — not by firing the real event dispatch
class SendEmailOnOrderPlacedTest extends \PHPUnit\Framework\TestCase
{
    public function testExecuteSendsEmail(): void
    {
        $emailSenderMock = $this->createMock(EmailSenderInterface::class);
        $emailSenderMock->expects($this->once())->method('send');

        $observer = new SendEmailOnOrderPlaced($emailSenderMock);

        $orderMock = $this->createMock(OrderInterface::class);
        $eventMock = $this->createMock(\Magento\Framework\Event::class);
        $eventMock->method('getData')->with('order')->willReturn($orderMock);
        $observerMock = $this->createMock(\Magento\Framework\Event\Observer::class);
        $observerMock->method('getEvent')->willReturn($eventMock);

        $observer->execute($observerMock);
    }
}
```

---

## `parent::setUp()` / `parent::tearDown()` Review

### ❌ Missing `parent::setUp()` in Integration Tests

Adobe Commerce integration test base classes (e.g. `AbstractController`, `AbstractBackendController`) perform critical bootstrapping in `setUp()`. Failing to call `parent::setUp()` silently breaks the test environment:

```php
// Bad — Bootstrap state not initialized; fixtures may not load correctly
class MyIntegrationTest extends \Magento\TestFramework\TestCase\AbstractController
{
    protected function setUp(): void
    {
        // Missing: parent::setUp()
        $this->service = $this->_objectManager->get(MyService::class);
    }
}

// Good
class MyIntegrationTest extends \Magento\TestFramework\TestCase\AbstractController
{
    protected function setUp(): void
    {
        parent::setUp(); // always first in integration test setUp
        $this->service = $this->_objectManager->get(MyService::class);
    }

    protected function tearDown(): void
    {
        parent::tearDown(); // always last in tearDown
        $this->registry->unregister('my_fixture_key');
    }
}
```

---

## GraphQL Test Review Points

### ❌ Not Testing GraphQL Authorization

GraphQL endpoints must be tested for unauthenticated and unauthorized access — not just happy path:

```php
// Bad — only tests authenticated success case
public function testProductQuery(): void
{
    $response = $this->graphQlQuery($query);
    $this->assertNotEmpty($response['products']['items']);
}

// Good — also test unauthorized customer endpoint
public function testCustomerQueryRequiresAuth(): void
{
    $this->expectException(\Magento\Framework\Exception\AuthorizationException::class);
    $this->graphQlQuery('{ customer { email } }');
}

// Good — test with customer token
public function testCustomerQueryWithToken(): void
{
    $token = $this->getCustomerToken('customer@example.com', 'password');
    $response = $this->graphQlQuery(
        '{ customer { email } }',
        [],
        '',
        ['Authorization' => 'Bearer ' . $token]
    );
    $this->assertEquals('customer@example.com', $response['customer']['email']);
}
```

---

## MFTF Test Review Points

When reviewing MFTF test XML files:
- [ ] `<annotations>` block present with `<features>`, `<stories>`, `<title>`, `<severity>`, `<group>`
- [ ] `<before>` and `<after>` blocks clean up created data (`deleteData` for every `createData`)
- [ ] Test does not rely on hard-coded product IDs or pre-existing data — uses `createData`
- [ ] `<severity>` reflects actual business impact: CRITICAL for checkout/payment paths, AVERAGE for standard features
- [ ] Test is assigned to a module group with `<group value="my_module"/>` — enables targeted runs

---

## Checklist for Adobe Commerce Tests

- [ ] Unit tests inject mocks via constructor — no `ObjectManager::getInstance()`
- [ ] Service contract interfaces mocked — not concrete model classes
- [ ] `@magentoDataFixture` declared for all integration tests requiring data
- [ ] `@magentoAppIsolation enabled` used when tests modify config or global registry
- [ ] `@magentoConfigFixture` used for scoped config — not `setValue()`
- [ ] Both authorized and unauthorized paths tested for Admin controllers
- [ ] Plugin tests call the plugin method directly, not through the DI proxy
- [ ] Observer tests instantiate the observer directly with mocked dependencies
- [ ] `tearDown()` unregisters any registry entries set during tests
- [ ] Repository mocks cover both success and `CouldNotSaveException` / `NoSuchEntityException` paths
- [ ] `parent::setUp()` called first in integration test `setUp()`; `parent::tearDown()` called last in `tearDown()`
- [ ] GraphQL tests cover unauthenticated and token-authenticated paths
- [ ] MFTF tests have `<before>`/`<after>` cleanup and no hard-coded entity IDs

---

## Resources

- [Magento 2 Unit Testing](https://developer.adobe.com/commerce/testing/guide/unit/)
- [Magento 2 Integration Testing](https://developer.adobe.com/commerce/testing/guide/integration/)
- [MFTF Documentation](https://developer.adobe.com/commerce/testing/functional-testing-framework/)
- [PHPUnit Documentation](https://docs.phpunit.de/)
- [Magento Test Fixtures](https://developer.adobe.com/commerce/testing/guide/integration/attributes/)
