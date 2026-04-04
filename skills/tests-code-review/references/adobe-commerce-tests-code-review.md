# Adobe Commerce (Magento 2) Test Code Review Guide

Supplements `test-review-checklist.md` and `php-tests-code-review.md` for projects using Adobe Commerce / Magento 2 (PHPUnit, Magento Integration Test Framework, MFTF).

> Covers Adobe Commerce / Magento 2 testing concerns only. PHP testing patterns are covered in `php-tests-code-review.md`.

---

## Unit Test Review Points

### Prefer ViewModel Tests Over Block Tests for Data Logic

Unit tests that test data-retrieval methods on a Block class are a code smell — that logic should live in a ViewModel. Flag as a quality finding and recommend extracting to a ViewModel.

```php
// Bad — testing data retrieval on a Block; Block should not own this logic
class MyBlockTest extends \PHPUnit\Framework\TestCase
{
    public function testGetProductName(): void
    {
        $productRepository = $this->createMock(ProductRepositoryInterface::class);
        $block = new MyBlock(..., $productRepository);
        $this->assertSame('Widget', $block->getProductName(42));
    }
}

// Good — data logic lives in a ViewModel; Block test only covers rendering decisions
class ProductInfoViewModelTest extends \PHPUnit\Framework\TestCase
{
    public function testGetProductName(): void
    {
        $product = $this->createMock(ProductInterface::class);
        $product->method('getName')->willReturn('Widget');
        $repository = $this->createMock(ProductRepositoryInterface::class);
        $repository->method('getById')->with(42)->willReturn($product);
        $viewModel = new ProductInfoViewModel($repository);
        $this->assertSame('Widget', $viewModel->getProductName(42));
    }
}
```

### ObjectManager Must Not Appear in Unit Tests

```php
// Bad — ObjectManager couples test to full DI container
class MyServiceTest extends \PHPUnit\Framework\TestCase
{
    public function testSomething(): void
    {
        $service = \Magento\Framework\App\ObjectManager::getInstance()
            ->create(MyService::class);
    }
}

// Good — inject mocks via constructor; no Magento bootstrap needed
class MyServiceTest extends \PHPUnit\Framework\TestCase
{
    private MyService $service;
    private ProductRepositoryInterface&MockObject $repositoryMock;

    protected function setUp(): void
    {
        $this->repositoryMock = $this->createMock(ProductRepositoryInterface::class);
        $this->service        = new MyService($this->repositoryMock);
    }
}
```

### Mock Service Contract Interfaces, Not Concrete Models

```php
// Bad — mocks implementation detail, not contract; breaks on internal refactors
public function testGetProduct(): void
{
    $product = $this->createMock(\Magento\Catalog\Model\Product::class);
}

// Good — mock the interface; valid even if Adobe changes implementation
public function testGetProduct(): void
{
    $product = $this->createMock(\Magento\Catalog\Api\Data\ProductInterface::class);
}
```

### Registry State Must Be Cleaned Up Between Tests

```php
// Bad — registry entry leaks into subsequent tests
class RegistryTest extends \PHPUnit\Framework\TestCase
{
    public function testFirst(): void
    {
        $this->registry->register('current_product', $this->productMock);
    }
}

// Good — always unregister in tearDown
protected function tearDown(): void
{
    parent::tearDown();
    $this->registry->unregister('current_product');
}
```

### Plugin Tests Call the Method Directly

Plugin tests MUST call the plugin's before/after/around method directly — not via the DI interceptor proxy. Testing through the proxy bootstraps the full container and ceases to be a unit test.

```php
class AfterGetNamePluginTest extends \PHPUnit\Framework\TestCase
{
    private AfterGetNamePlugin $plugin;

    protected function setUp(): void
    {
        $this->plugin = new AfterGetNamePlugin();
    }

    public function testAfterGetNameTransformsToUppercase(): void
    {
        $subject = $this->createMock(ProductInterface::class);
        $this->assertSame('MY PRODUCT', $this->plugin->afterGetName($subject, 'my product'));
    }

    public function testAfterGetNameHandlesEmptyString(): void
    {
        $subject = $this->createMock(ProductInterface::class);
        $this->assertSame('', $this->plugin->afterGetName($subject, ''));
    }
}
```

### Observer Tests Do Not Fire the Real Event Dispatch

```php
// Bad — fires event bus; slow and non-isolated
public function testObserverBehaviour(): void
{
    $this->eventManager->dispatch('sales_order_save_after', ['order' => $this->orderMock]);
}

// Good — instantiate observer directly with mocked dependencies
class SendEmailOnOrderPlacedTest extends \PHPUnit\Framework\TestCase
{
    public function testExecuteSendsEmail(): void
    {
        $emailSenderMock = $this->createMock(EmailSenderInterface::class);
        $emailSenderMock->expects($this->once())->method('send');
        $observer    = new SendEmailOnOrderPlaced($emailSenderMock);
        $orderMock   = $this->createMock(OrderInterface::class);
        $eventMock   = $this->createMock(\Magento\Framework\Event::class);
        $eventMock->method('getData')->with('order')->willReturn($orderMock);
        $wrapperMock = $this->createMock(\Magento\Framework\Event\Observer::class);
        $wrapperMock->method('getEvent')->willReturn($eventMock);
        $observer->execute($wrapperMock);
    }
}
```

## Integration Test Review Points

### `parent::setUp()` Must Be Called First

Adobe Commerce integration base classes (`AbstractController`, `AbstractBackendController`, `AbstractModule`) perform critical bootstrapping in `setUp()`. Omitting `parent::setUp()` silently breaks fixture loading and the `_objectManager` reference.

```php
// Bad — _objectManager is null; fixtures never load; test passes vacuously
class MyIntegrationTest extends \Magento\TestFramework\TestCase\AbstractController
{
    protected function setUp(): void
    {
        $this->service = $this->_objectManager->get(MyService::class);
    }
}

// Good — parent::setUp() always runs first; parent::tearDown() always runs last
class MyIntegrationTest extends \Magento\TestFramework\TestCase\AbstractController
{
    protected function setUp(): void
    {
        parent::setUp();
        $this->service = $this->_objectManager->get(MyService::class);
    }

    protected function tearDown(): void
    {
        $this->registry->unregister('my_fixture_key');
        parent::tearDown();
    }
}
```

### Missing `@magentoDataFixture` Causes Implicit Data Dependencies

```php
// Bad — relies on pre-existing data; test is environment-dependent
public function testProductPage(): void
{
    $this->dispatch('/catalog/product/view/id/1');
    $this->assertResponseBodyContains('My Product');
}

// Good — declare the fixture; test is self-contained and reproducible
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

### Use `@magentoConfigFixture` Instead of `setValue()`

```php
// Bad — scopeConfig->setValue() bypasses proper scoping; may leak state
public function testFeatureEnabled(): void
{
    $this->scopeConfig->setValue('my_module/general/enabled', 1);
    $this->assertTrue($this->config->isEnabled());
}

// Good — automatically scoped and rolled back after each test
/**
 * @magentoConfigFixture current_store my_module/general/enabled 1
 */
public function testFeatureEnabled(): void
{
    $this->assertTrue($this->config->isEnabled());
}
```

### Missing `@magentoAppIsolation` on Config-Mutating Tests

```php
// Bad — config mutations persist into subsequent test classes
class ConfigMutatingTest extends \Magento\TestFramework\TestCase\AbstractController
{
    public function testWithCustomConfig(): void
    {
        $this->scopeConfig->setValue('my/path', 'custom_value');
    }
}

// Good — full application state reset between test classes
/**
 * @magentoAppIsolation enabled
 */
class ConfigMutatingTest extends \Magento\TestFramework\TestCase\AbstractController
{
    public function testWithCustomConfig(): void
    {
        $this->scopeConfig->setValue('my/path', 'custom_value');
    }
}
```

### Admin Controllers Must Test Both Authorized and Unauthorized Access

```php
// Bad — only happy path; ACL enforcement untested
public function testAdminGridLoads(): void
{
    $this->dispatch('backend/my_module/grid/index');
    $this->assertResponseBodyContains('My Grid');
}

// Good — pair every access test with an unauthorized-access test
public function testAdminGridDeniesUnauthorizedUser(): void
{
    $this->_objectManager->get(\Magento\Backend\Model\Auth\Session::class)
        ->setCurrentRole($this->getRoleWithoutPermission());
    $this->dispatch('backend/my_module/grid/index');
    $this->assertRedirect($this->stringContains('admin/noroute'));
}
```

### Prefer PHP Attribute Fixtures Over Legacy File Fixtures (AC 2.4.5+)

```php
// Deprecated — legacy file-based fixture
/**
 * @magentoDataFixture Magento/Catalog/_files/product_simple.php
 */
public function testProductExists(): void { ... }

// Current — PHP 8 attribute fixture (AC 2.4.5+); composable and type-safe
use Magento\TestFramework\Fixture\DataFixture;
use Magento\Catalog\Test\Fixture\Product as ProductFixture;

#[DataFixture(ProductFixture::class, ['sku' => 'test-sku'], 'p')]
public function testProductExists(): void
{
    // $this->fixtures->get('p') gives the created product
}
```

Flag legacy file fixtures in new tests as a quality finding (P2) and recommend migration.

## GraphQL Test Review Points

### Authorization Must Be Tested, Not Just the Happy Path

```php
// Bad — only tests authenticated success; authorization failures untested
public function testProductQuery(): void
{
    $response = $this->graphQlQuery('{ products(filter:{sku:{eq:"simple"}}){ items{ sku } } }');
    $this->assertNotEmpty($response['products']['items']);
}

// Good — assert unauthenticated customer endpoints reject requests
public function testCustomerQueryRequiresAuthentication(): void
{
    $this->expectException(\Magento\Framework\Exception\AuthorizationException::class);
    $this->graphQlQuery('{ customer { email } }');
}

// Good — authenticated requests succeed
public function testCustomerQuerySucceedsWithValidToken(): void
{
    $token    = $this->getCustomerToken('customer@example.com', '$ecret123');
    $response = $this->graphQlQuery(
        '{ customer { email } }',
        [],
        '',
        ['Authorization' => 'Bearer ' . $token]
    );
    $this->assertEquals('customer@example.com', $response['customer']['email']);
}
```

## MFTF Test Review Points

When reviewing MFTF XML test files:

- [ ] `<annotations>` block present with all required fields: `<features>`, `<stories>`, `<title>`, `<description>`, `<severity>`, `<group>`
- [ ] `<before>` and `<after>` blocks are symmetric: every `createData` has a corresponding `deleteData` in `<after>`
- [ ] No hard-coded entity IDs or hard-coded URLs — use `createData` and page/section objects
- [ ] `<severity>` reflects actual business impact: `CRITICAL` for checkout/payment/authentication, `MAJOR` for primary user journeys, `AVERAGE` for standard feature paths, `MINOR` for cosmetic or low-risk paths
- [ ] Test assigned to a module group (`<group value="my_module"/>`) for targeted CI runs
- [ ] Section selectors defined in `Section` XML objects — not inline CSS strings in test body
- [ ] Page URLs referenced via `Page` XML objects — not hardcoded strings

## Comprehensive Checklist for Adobe Commerce Tests

### Unit Tests
- [ ] All dependencies mocked via constructor — no `ObjectManager::getInstance()` in unit tests
- [ ] Service contract interfaces mocked — not concrete model classes (`Model\Product` vs `Api\Data\ProductInterface`)
- [ ] Plugin tests call the plugin method directly — not via the interceptor proxy
- [ ] Observer tests instantiate the observer directly with mocked dependencies — no event dispatch
- [ ] `tearDown()` unregisters any registry entries set during tests
- [ ] Repository mocks cover both success and failure paths (`CouldNotSaveException`, `NoSuchEntityException`)

### Integration Tests
- [ ] `parent::setUp()` called first in `setUp()`; `parent::tearDown()` called last in `tearDown()`
- [ ] `@magentoDataFixture` (or PHP attribute `#[DataFixture]`) declared for all data requirements
- [ ] `@magentoConfigFixture` used for scoped config — not `setValue()`
- [ ] `@magentoAppIsolation enabled` on classes that modify config or global registry state
- [ ] Both authorized and unauthorized paths tested for Admin controller routes
- [ ] Area code set explicitly when testing area-scoped behaviour
- [ ] New tests use PHP attribute-style fixtures (AC 2.4.5+) rather than legacy file fixtures

### GraphQL Tests
- [ ] Unauthenticated access tested for all customer-scoped queries and mutations
- [ ] Token-authenticated requests tested for customer endpoints
- [ ] Store-scoped headers tested where resolver behaviour varies by store

### MFTF Tests
- [ ] `<before>`/`<after>` cleanup is complete — no orphaned fixture data
- [ ] No hard-coded entity IDs, product SKUs, or URLs — all resolved via fixtures and page objects
- [ ] Severity annotation accurately reflects business risk
- [ ] Group annotation present for targeted test runs
