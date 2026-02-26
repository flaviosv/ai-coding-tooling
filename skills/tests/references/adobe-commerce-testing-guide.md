# Adobe Commerce (Magento 2) Testing Guide

Applies to: Adobe Commerce / Magento 2 projects using PHPUnit, Magento Integration Test Framework, and MFTF (AC 2.4.x).

> Covers Adobe Commerce / Magento 2 testing patterns only. PHP testing setup and patterns are covered in `php-testing-guide.md`.

---

## Test Types Overview

| Type | Location | Purpose |
|---|---|---|
| Unit | `Test/Unit/` | Isolated class logic with mocked dependencies |
| Integration | `Test/Integration/` | Module interaction with real DI and DB |
| API Functional | `Test/Api/` | REST / GraphQL endpoint contracts |
| MFTF | `Test/Mftf/` | End-to-end browser-level acceptance tests |

---

## Unit Tests

### Service Class with Constructor Injection

```php
// Test/Unit/Service/OrderProcessorTest.php
namespace MyVendor\MyModule\Test\Unit\Service;

use MyVendor\MyModule\Service\OrderProcessor;
use Magento\Sales\Api\OrderRepositoryInterface;
use Magento\Sales\Api\Data\OrderInterface;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;

class OrderProcessorTest extends TestCase
{
    private OrderProcessor $processor;
    private OrderRepositoryInterface&MockObject $orderRepository;

    protected function setUp(): void
    {
        $this->orderRepository = $this->createMock(OrderRepositoryInterface::class);
        $this->processor = new OrderProcessor($this->orderRepository);
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
            ->willThrowException(new \Magento\Framework\Exception\CouldNotSaveException(__('error')));

        $this->expectException(\Magento\Framework\Exception\CouldNotSaveException::class);
        $this->processor->process($order);
    }
}
```

### Testing Plugins

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

    public function testAfterGetNameAppendsTag(): void
    {
        $subject = $this->createMock(ProductInterface::class);
        $result = $this->plugin->afterGetName($subject, 'Widget Pro');
        $this->assertStringContainsString('[SALE]', $result);
    }
}
```

### Testing Observers

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
    public function testExecuteSetsStatus(): void
    {
        $order = $this->createMock(OrderInterface::class);
        $order->expects($this->once())->method('setStatus')->with('custom_status');

        $event = $this->createMock(Event::class);
        $event->method('getData')->with('order')->willReturn($order);

        $observerMock = $this->createMock(Observer::class);
        $observerMock->method('getEvent')->willReturn($event);

        $observer = new SetOrderStatusObserver();
        $observer->execute($observerMock);
    }
}
```

---

## Integration Tests

### Area Code

Integration tests that bootstrap Magento may require an area code to be set before executing code that reads area-specific configuration or design settings:

```php
protected function setUp(): void
{
    parent::setUp();
    $this->appState = $this->_objectManager->get(\Magento\Framework\App\State::class);
    $this->appState->setAreaCode(\Magento\Framework\App\Area::AREA_FRONTEND);
}
```

Available area codes: `AREA_FRONTEND`, `AREA_ADMINHTML`, `AREA_CRONTAB`, `AREA_WEBAPI_REST`, `AREA_WEBAPI_SOAP`, `AREA_GRAPHQL`.

### Setup

Register the integration test suite in `dev/tests/integration/phpunit.xml`. Ensure the test DB is configured in `dev/tests/integration/etc/install-config-mysql.php`.

Run with:

```bash
cd dev/tests/integration
../../../vendor/bin/phpunit app/code/MyVendor/MyModule/Test/Integration/
```

### Data Fixtures

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
/** @var \Magento\Framework\Registry $registry */
$registry = \Magento\TestFramework\Helper\Bootstrap::getObjectManager()
    ->get(\Magento\Framework\Registry::class);

$registry->unregister('isSecureArea');
$registry->register('isSecureArea', true);

// create fixture data here ...

$registry->unregister('isSecureArea');
```

### Config Fixtures

```php
/**
 * @magentoConfigFixture current_store my_module/general/enabled 1
 * @magentoConfigFixture current_store my_module/general/api_key test_key_123
 */
public function testFeatureEnabledByConfig(): void
{
    $this->assertTrue($this->config->isEnabled());
}
```

### App Isolation

```php
/**
 * @magentoAppIsolation enabled
 */
class SomeConfigMutatingTest extends \Magento\TestFramework\TestCase\AbstractController
{
    // App state is reset before and after this test class
}
```

---

## Testing Admin Controllers

```php
namespace MyVendor\MyModule\Test\Integration\Controller\Adminhtml;

use Magento\TestFramework\TestCase\AbstractBackendController;

class GridTest extends AbstractBackendController
{
    protected $resource = 'MyVendor_MyModule::manage';
    protected $uri = 'backend/my_module/grid/index';

    public function testAclHasAccess(): void
    {
        $this->dispatch($this->uri);
        $this->assertNotSame(403, $this->getResponse()->getHttpResponseCode());
    }

    public function testAclNoAccess(): void
    {
        $this->_objectManager->get(\Magento\Backend\Model\Auth\Session::class)
            ->setCurrentRole($this->_noAccessRole);
        $this->dispatch($this->uri);
        $this->assertSame(403, $this->getResponse()->getHttpResponseCode());
    }
}
```

---

## Testing REST API (Webapi Functional Tests)

```php
// Test/Api/ProductApiTest.php
namespace MyVendor\MyModule\Test\Api;

use Magento\TestFramework\TestCase\WebapiAbstract;

class ProductApiTest extends WebapiAbstract
{
    private const RESOURCE_PATH = '/V1/products';

    /**
     * @magentoApiDataFixture Magento/Catalog/_files/product_simple.php
     */
    public function testGetProduct(): void
    {
        $serviceInfo = [
            'rest' => [
                'resourcePath' => self::RESOURCE_PATH . '/simple',
                'httpMethod'   => \Magento\Framework\Webapi\Rest\Request::HTTP_METHOD_GET,
            ],
        ];
        $response = $this->_webApiCall($serviceInfo);
        $this->assertEquals('simple', $response['sku']);
    }
}
```

---

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
    public function testProductQuery(): void
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

    public function testUnauthorizedQueryReturnsError(): void
    {
        $query = <<<QUERY
        {
            customer {
                email
            }
        }
        QUERY;

        $this->expectException(\Magento\Framework\Exception\AuthorizationException::class);
        $this->graphQlQuery($query);
    }
}
```

---

## MFTF (Magento Functional Testing Framework)

MFTF tests live in `Test/Mftf/` and use XML-based test definitions:

```xml
<!-- Test/Mftf/Test/MyModuleFeatureTest.xml -->
<tests xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:noNamespaceSchemaLocation="urn:magento:mftf:Test/etc/testSchema.xsd">
    <test name="MyModuleFeatureTest">
        <annotations>
            <features value="MyModule"/>
            <stories value="Feature works on storefront"/>
            <title value="Customer can use my feature"/>
            <severity value="CRITICAL"/>
            <group value="my_module"/>
        </annotations>
        <before>
            <createData entity="SimpleProduct" stepKey="createProduct"/>
        </before>
        <after>
            <deleteData createDataKey="createProduct" stepKey="deleteProduct"/>
        </after>
        <amOnPage url="{{StorefrontHomePage.url}}" stepKey="goToHome"/>
        <waitForPageLoad stepKey="waitForHome"/>
    </test>
</tests>
```

Run MFTF:

```bash
vendor/bin/mftf run:test MyModuleFeatureTest
vendor/bin/mftf run:group my_module
```

---

## Resources

- [Magento 2 Unit Testing Guide](https://developer.adobe.com/commerce/testing/guide/unit/)
- [Magento 2 Integration Testing Guide](https://developer.adobe.com/commerce/testing/guide/integration/)
- [MFTF Documentation](https://developer.adobe.com/commerce/testing/functional-testing-framework/)
- [Magento Webapi Testing](https://developer.adobe.com/commerce/testing/guide/web-api/)
- [PHPUnit Documentation](https://docs.phpunit.de/)
- [Magento Test Fixtures Reference](https://developer.adobe.com/commerce/testing/guide/integration/attributes/)
