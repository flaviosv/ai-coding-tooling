# Adobe Commerce (Magento 2) Testing Guide

Applies to: Adobe Commerce / Magento 2 projects using PHPUnit, Magento Integration Test Framework, and MFTF (AC 2.4.x).

> Covers Adobe Commerce / Magento 2 testing patterns only. PHP testing setup and patterns are covered in `php-tests.md`.

---

## Test Types Overview

| Type | Location | Framework | Purpose |
|---|---|---|---|
| Unit | `Test/Unit/` | PHPUnit | Isolated class logic with all dependencies mocked |
| Integration | `Test/Integration/` | Magento Integration Test Framework (PHPUnit) | Module interaction with real DI container and test DB |
| API Functional | `Test/Api/` | Magento Webapi Test Framework (PHPUnit) | REST and GraphQL endpoint contracts |
| MFTF | `Test/Mftf/` | MFTF (Codeception/XML) | End-to-end browser-level acceptance tests |

## Unit Tests

Unit tests live in `Test/Unit/` and extend `\PHPUnit\Framework\TestCase`. All dependencies are injected via constructor and mocked — no Magento bootstrap, no database, no DI container.

### Service Class with Constructor Injection

```php
// Test/Unit/Service/OrderProcessorTest.php
namespace MyVendor\MyModule\Test\Unit\Service;

use MyVendor\MyModule\Service\OrderProcessor;
use Magento\Sales\Api\OrderRepositoryInterface;
use Magento\Sales\Api\Data\OrderInterface;
use Magento\Framework\Exception\CouldNotSaveException;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;

class OrderProcessorTest extends TestCase
{
    private OrderProcessor $processor;
    private OrderRepositoryInterface&MockObject $orderRepository;

    protected function setUp(): void
    {
        $this->orderRepository = $this->createMock(OrderRepositoryInterface::class);
        $this->processor       = new OrderProcessor($this->orderRepository);
    }

    public function testProcessSavesOrder(): void
    {
        $order = $this->createMock(OrderInterface::class);
        $this->orderRepository->expects($this->once())->method('save')->with($order);
        $this->processor->process($order);
    }

    public function testProcessThrowsOnRepositoryFailure(): void
    {
        $order = $this->createMock(OrderInterface::class);
        $this->orderRepository->method('save')
            ->willThrowException(new CouldNotSaveException(__('Could not save order')));
        $this->expectException(CouldNotSaveException::class);
        $this->processor->process($order);
    }
}
```

### Testing Plugins (Interceptors)

Call the plugin method directly — do not go through the DI interceptor proxy:

```php
// Test/Unit/Plugin/ProductNamePluginTest.php
namespace MyVendor\MyModule\Test\Unit\Plugin;

use MyVendor\MyModule\Plugin\ProductNamePlugin;
use Magento\Catalog\Api\Data\ProductInterface;
use PHPUnit\Framework\TestCase;

class ProductNamePluginTest extends TestCase
{
    private ProductNamePlugin $plugin;

    protected function setUp(): void
    {
        $this->plugin = new ProductNamePlugin();
    }

    public function testAfterGetNameAppendsSaleTag(): void
    {
        $subject = $this->createMock(ProductInterface::class);
        $result  = $this->plugin->afterGetName($subject, 'Widget Pro');
        $this->assertStringContainsString('[SALE]', $result);
    }

    public function testAfterGetNameHandlesEmptyString(): void
    {
        $subject = $this->createMock(ProductInterface::class);
        $result  = $this->plugin->afterGetName($subject, '');
        $this->assertSame('', $result);
    }
}
```

### Testing Observers

Instantiate the observer directly with mocked dependencies — do not fire the real event dispatch:

```php
// Test/Unit/Observer/SetOrderStatusObserverTest.php
namespace MyVendor\MyModule\Test\Unit\Observer;

use MyVendor\MyModule\Observer\SetOrderStatusObserver;
use Magento\Framework\Event\Observer;
use Magento\Framework\Event;
use Magento\Sales\Api\Data\OrderInterface;
use PHPUnit\Framework\TestCase;

class SetOrderStatusObserverTest extends TestCase
{
    public function testExecuteSetsCustomStatus(): void
    {
        $order = $this->createMock(OrderInterface::class);
        $order->expects($this->once())->method('setStatus')->with('custom_status');
        $event = $this->createMock(Event::class);
        $event->method('getData')->with('order')->willReturn($order);
        $observerWrapper = $this->createMock(Observer::class);
        $observerWrapper->method('getEvent')->willReturn($event);
        $observer = new SetOrderStatusObserver();
        $observer->execute($observerWrapper);
    }
}
```

### Testing ViewModels

```php
// Test/Unit/ViewModel/ProductInfoViewModelTest.php
namespace MyVendor\MyModule\Test\Unit\ViewModel;

use MyVendor\MyModule\ViewModel\ProductInfoViewModel;
use Magento\Catalog\Api\ProductRepositoryInterface;
use Magento\Catalog\Api\Data\ProductInterface;
use PHPUnit\Framework\TestCase;

class ProductInfoViewModelTest extends TestCase
{
    public function testGetProductNameReturnsName(): void
    {
        $product = $this->createMock(ProductInterface::class);
        $product->method('getName')->willReturn('My Product');
        $repository = $this->createMock(ProductRepositoryInterface::class);
        $repository->method('getById')->with(42)->willReturn($product);
        $viewModel = new ProductInfoViewModel($repository);
        $this->assertSame('My Product', $viewModel->getProductName(42));
    }
}
```

## Integration Tests

Integration tests live in `Test/Integration/` and extend one of the Magento test case base classes. They bootstrap the full Magento application with a dedicated test database configured in `dev/tests/integration/etc/install-config-mysql.php`.

### Running Integration Tests

```bash
cd dev/tests/integration
../../../vendor/bin/phpunit --configuration phpunit.xml \
    ../../../app/code/MyVendor/MyModule/Test/Integration/
```

### Setting the Area Code

Tests that exercise area-specific code (design, configuration, templates) MUST set the area code:

```php
protected function setUp(): void
{
    parent::setUp(); // always call parent first in integration tests
    $this->appState = $this->_objectManager->get(\Magento\Framework\App\State::class);
    $this->appState->setAreaCode(\Magento\Framework\App\Area::AREA_FRONTEND);
}
```

Available constants: `AREA_FRONTEND`, `AREA_ADMINHTML`, `AREA_CRONTAB`, `AREA_WEBAPI_REST`, `AREA_WEBAPI_SOAP`, `AREA_GRAPHQL`.

### Data Fixtures — Legacy File Style

```php
/**
 * @magentoDataFixture Magento/Catalog/_files/product_simple.php
 * @magentoDataFixture MyVendor_MyModule::Test/Integration/_files/custom_attribute.php
 */
public function testProductHasCustomAttribute(): void
{
    $product = $this->productRepository->get('simple');
    $this->assertNotNull($product->getCustomAttribute('my_attribute'));
}
```

Custom fixture file (`Test/Integration/_files/custom_attribute.php`):

```php
<?php
$registry = \Magento\TestFramework\Helper\Bootstrap::getObjectManager()
    ->get(\Magento\Framework\Registry::class);
$registry->unregister('isSecureArea');
$registry->register('isSecureArea', true);
// create fixture data here (attribute EAV record, custom table rows, etc.) ...
$registry->unregister('isSecureArea');
```

### Data Fixtures — PHP Attribute Style (AC 2.4.5+)

More composable and type-safe than legacy DocBlock file fixtures (which are deprecated):

```php
use Magento\TestFramework\Fixture\DataFixture;
use Magento\Catalog\Test\Fixture\Product as ProductFixture;
use Magento\Quote\Test\Fixture\GuestCart as GuestCartFixture;
use Magento\Quote\Test\Fixture\AddProductToCart as AddProductToCartFixture;

class QuoteTest extends \PHPUnit\Framework\TestCase
{
    #[
        DataFixture(ProductFixture::class, as: 'p'),
        DataFixture(GuestCartFixture::class, as: 'cart'),
        DataFixture(AddProductToCartFixture::class, [
            'cart_id'    => '$cart.id$',
            'product_id' => '$p.id$',
            'qty'        => 2,
        ]),
    ]
    public function testCollectTotals(): void
    {
        $cart = $this->fixtures->get('cart');
        $this->assertNotNull($cart->getId());
    }
}
```

### Config Fixtures

```php
/**
 * @magentoConfigFixture current_store my_module/general/enabled 1
 * @magentoConfigFixture current_store my_module/general/api_key test_key_placeholder
 */
public function testFeatureEnabledByConfig(): void
{
    $this->assertTrue($this->config->isEnabled());
}
```

Config values set via `@magentoConfigFixture` are automatically restored after each test — use this instead of `scopeConfig->setValue()`.

### App Isolation

```php
/**
 * @magentoAppIsolation enabled
 */
class SomeConfigMutatingTest extends \Magento\TestFramework\TestCase\AbstractController
{
    // Full application state (DI, config, registry) is reset before and after this class
}
```

## Testing Admin Controllers

```php
namespace MyVendor\MyModule\Test\Integration\Controller\Adminhtml;

use Magento\TestFramework\TestCase\AbstractBackendController;

class GridTest extends AbstractBackendController
{
    protected $resource = 'MyVendor_MyModule::manage';
    protected $uri      = 'backend/my_module/grid/index';

    public function testAclAllowsAccess(): void
    {
        $this->dispatch($this->uri);
        $this->assertNotSame(403, $this->getResponse()->getHttpResponseCode());
    }

    public function testAclDeniesUnauthorizedAccess(): void
    {
        $this->_objectManager->get(\Magento\Backend\Model\Auth\Session::class)
            ->setCurrentRole($this->_noAccessRole);
        $this->dispatch($this->uri);
        $this->assertSame(403, $this->getResponse()->getHttpResponseCode());
    }
}
```

## Testing REST API (Webapi Functional Tests)

```php
// Test/Api/ProductApiTest.php
namespace MyVendor\MyModule\Test\Api;

use Magento\TestFramework\TestCase\WebapiAbstract;
use Magento\Framework\Webapi\Rest\Request;

class ProductApiTest extends WebapiAbstract
{
    private const RESOURCE_PATH = '/V1/products';

    /**
     * @magentoApiDataFixture Magento/Catalog/_files/product_simple.php
     */
    public function testGetProductReturnsSku(): void
    {
        $serviceInfo = [
            'rest' => [
                'resourcePath' => self::RESOURCE_PATH . '/simple',
                'httpMethod'   => Request::HTTP_METHOD_GET,
            ],
        ];
        $response = $this->_webApiCall($serviceInfo);
        $this->assertEquals('simple', $response['sku']);
    }

    public function testUnauthorizedAccessReturnsError(): void
    {
        $serviceInfo = [
            'rest' => [
                'resourcePath' => '/V1/customers/me',
                'httpMethod'   => Request::HTTP_METHOD_GET,
                'token'        => 'invalid_token',
            ],
        ];
        $this->expectException(\Exception::class);
        $this->_webApiCall($serviceInfo);
    }
}
```

## Testing GraphQL (Webapi Functional Tests)

```php
// Test/Api/GraphQl/ProductGraphQlTest.php
namespace MyVendor\MyModule\Test\Api\GraphQl;

use Magento\TestFramework\TestCase\GraphQlAbstract;

class ProductGraphQlTest extends GraphQlAbstract
{
    /**
     * @magentoApiDataFixture Magento/Catalog/_files/product_simple.php
     */
    public function testProductQueryReturnsSku(): void
    {
        $query = <<<QUERY
        {
            products(filter: { sku: { eq: "simple" } }) {
                items {
                    sku
                    name
                }
            }
        }
        QUERY;
        $response = $this->graphQlQuery($query);
        $this->assertNotEmpty($response['products']['items']);
        $this->assertEquals('simple', $response['products']['items'][0]['sku']);
    }

    public function testCustomerQueryRequiresAuthentication(): void
    {
        $this->expectException(\Magento\Framework\Exception\AuthorizationException::class);
        $this->graphQlQuery('{ customer { email } }');
    }

    public function testCustomerQuerySucceedsWithToken(): void
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
}
```

## MFTF (Magento Functional Testing Framework)

MFTF tests live in `Test/Mftf/` and use XML-based test definitions interpreted by Codeception.

### Test Definition

```xml
<!-- Test/Mftf/Test/MyModuleFeatureTest.xml -->
<tests xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:noNamespaceSchemaLocation="urn:magento:mftf:Test/etc/testSchema.xsd">
    <test name="MyModuleFeatureTest">
        <annotations>
            <features value="MyModule"/>
            <stories value="Feature works on storefront"/>
            <title value="Customer can use my feature"/>
            <description value="Verifies the feature is visible and functional for a logged-in customer"/>
            <severity value="CRITICAL"/>
            <group value="my_module"/>
        </annotations>
        <before>
            <createData entity="SimpleProduct" stepKey="createProduct"/>
            <createData entity="Customer" stepKey="createCustomer"/>
        </before>
        <after>
            <deleteData createDataKey="createProduct" stepKey="deleteProduct"/>
            <deleteData createDataKey="createCustomer" stepKey="deleteCustomer"/>
        </after>
        <amOnPage url="{{StorefrontHomePage.url}}" stepKey="goToHome"/>
        <waitForPageLoad stepKey="waitForHome"/>
        <!-- additional steps -->
    </test>
</tests>
```

### Running MFTF Tests

```bash
vendor/bin/mftf run:test MyModuleFeatureTest
vendor/bin/mftf run:group my_module
vendor/bin/mftf generate:tests
```

### MFTF Page and Section Objects

```xml
<!-- Test/Mftf/Page/MyModulePage.xml -->
<pages xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:noNamespaceSchemaLocation="urn:magento:mftf:Page/etc/PageObject.xsd">
    <page name="MyModulePage" url="/my-module/feature" area="storefront">
        <section name="MyModuleSection"/>
    </page>
</pages>
```

```xml
<!-- Test/Mftf/Section/MyModuleSection.xml -->
<sections xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:noNamespaceSchemaLocation="urn:magento:mftf:Page/etc/SectionObject.xsd">
    <section name="MyModuleSection">
        <element name="featureButton" type="button" selector="#my-module-feature-btn"/>
        <element name="resultMessage" type="text" selector=".my-module-result"/>
    </section>
</sections>
```

## Test Configuration

Register custom integration tests in `dev/tests/integration/phpunit.xml`:

```xml
<!-- dev/tests/integration/phpunit.xml (excerpt) -->
<testsuites>
    <testsuite name="My Module Integration Tests">
        <directory suffix="Test.php">
            ../../../app/code/MyVendor/MyModule/Test/Integration
        </directory>
    </testsuite>
</testsuites>
```
