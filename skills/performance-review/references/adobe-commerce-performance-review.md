# Adobe Commerce (Magento 2) Performance Best Practices

Applies to: Adobe Commerce / Magento 2 (AC 2.4.x)

> Covers Adobe Commerce / Magento 2 platform performance concerns only. PHP language performance patterns are covered in `php-performance-review.md`.

---

## Database Query Optimization

### Use Collections with Field Restrictions

```php
// Good
$collection = $this->productCollectionFactory->create();
$collection->addFieldToSelect(['entity_id', 'sku', 'name', 'status']);
$collection->addFieldToFilter('status', Status::STATUS_ENABLED);

// Bad — SELECT * loads all EAV attributes across join tables
$collection = $this->productCollectionFactory->create();
$collection->load();
```

### Avoid Per-Item `load()` / Repository Calls Inside Loops

```php
// Bad — N+1
foreach ($orderItems as $item) {
    $product = $this->productRepository->getById($item->getProductId());
}

// Good — batch load with single collection query
$productIds = array_column($orderItems, 'product_id');
$collection = $this->productCollectionFactory->create();
$collection->addFieldToFilter('entity_id', ['in' => $productIds]);
$collection->addFieldToSelect(['entity_id', 'sku', 'name', 'price']);
$products = [];
foreach ($collection as $product) {
    $products[$product->getId()] = $product;
}
```

### Use Repository API for Single-Record Access

```php
// Good — uses repository identity-map; repeated calls for same ID are free
$product = $this->productRepository->getById($id);

// Bad — bypasses repository caching, always hits DB
$product = $this->productFactory->create()->load($id);
```

### Prefer `getSize()` for Count-Only Checks

```php
// Good — issues COUNT(*) at DB level
if ($collection->getSize() > 0) { ... }

// Bad — loads all records into memory to count
if (count($collection->getItems()) > 0) { ... }
```

### Use `SearchCriteriaBuilder` for Paginated Reads

```php
// Good
$criteria = $this->searchCriteriaBuilder
    ->addFilter('status', 'active')
    ->setPageSize(100)
    ->setCurrentPage(1)
    ->create();
$results = $this->repository->getList($criteria);
```

## EAV Attribute Loading

```php
// Good
$collection->addAttributeToSelect(['name', 'price', 'special_price', 'image']);

// Bad — joins every EAV attribute table
$collection->addAttributeToSelect('*');
```

Flat catalog tables (`catalog_product_flat_*`) deprecated in AC 2.4.x, scheduled for removal. Do not rely on flat tables; use collection field restrictions and ensure indexers run on schedule.

## Caching

### Use Cache Interface for Expensive Data

```php
class ConfigProvider
{
    private const CACHE_KEY   = 'my_module_config_v1';
    private const CACHE_TAG   = 'my_module';
    private const CACHE_TTL   = 3600;

    public function __construct(
        private readonly CacheInterface      $cache,
        private readonly SerializerInterface $serializer,
    ) {}

    public function getConfig(): array
    {
        $cached = $this->cache->load(self::CACHE_KEY);
        if ($cached !== false) {
            return $this->serializer->unserialize($cached);
        }
        $data = $this->computeExpensiveConfig();
        $this->cache->save(
            $this->serializer->serialize($data),
            self::CACHE_KEY,
            [self::CACHE_TAG],
            self::CACHE_TTL
        );
        return $data;
    }
}
```

### Full Page Cache (FPC) Compatibility

Blocks/ViewModels inside FPC MUST NOT read session, customer, or cookie data directly — causes cache miss for every visitor.

```php
// Bad — customer name in cacheable block forces cache miss per request
class MyBlock extends Template
{
    public function getCustomerName(): string
    {
        return $this->customerSession->getCustomerData()->getFirstname();
    }
}

// Good — block stays cacheable; load customer data client-side via sections API
class MyBlock extends Template
{
    public function getCacheLifetime(): ?int
    {
        return 86400;
    }
    // Customer name fetched via Alpine.js/RequireJS from /customer/section/load
}
```

### Block Identity for Granular Cache Invalidation

```php
class ProductListBlock extends Template implements IdentityInterface
{
    public function getIdentities(): array
    {
        return [\Magento\Catalog\Model\Product::CACHE_TAG, \Magento\Catalog\Model\Category::CACHE_TAG];
    }
}
```

## Indexing

Never call `reindexAll()` during a web or API request.

```php
// Good — mark invalid; cron picks up asynchronously
$this->indexer->invalidate();

// Bad — synchronous full reindex blocks web request
$this->indexer->reindexAll();
```

Configure indexers to **Update by Schedule** in production (Products, Categories, Price, Inventory) so mutations during import/mass-update do not block the request cycle.

## Message Queue for Heavy Operations

Move non-blocking work to queue consumers so web request returns immediately.

```php
// Good
class OrderService
{
    public function placeOrder(OrderInterface $order): void
    {
        $this->orderRepository->save($order);
        $this->publisher->publish('my_module.order.placed', (string) $order->getEntityId());
    }
}

// Bad — heavy processing blocks checkout response
class OrderService
{
    public function placeOrder(OrderInterface $order): void
    {
        $this->orderRepository->save($order);
        $this->sendConfirmationEmail($order);  // slow — external SMTP
        $this->updateErpSystem($order);        // slow — external HTTP
        $this->generateInvoicePdf($order);     // slow — PDF rendering
    }
}
```

Queue consumer definition (`etc/queue_consumer.xml`):

```xml
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework-message-queue:etc/consumer.xsd">
    <consumer name="myModuleOrderConsumer"
              queue="my_module.order.placed"
              handler="MyVendor\MyModule\Consumer\OrderPlacedConsumer::process"
              connection="db"
              maxMessages="100"/>
</config>
```

Consumers MUST be idempotent — broker may deliver a message more than once.

## Plugin (Interceptor) Performance

Around plugins have highest overhead. Prefer before/after.

```php
// Bad — around plugin only to modify return value
public function aroundGetName(ProductInterface $subject, callable $proceed): string
{
    return strtoupper($proceed());
}

// Good — after plugin is sufficient, costs less
public function afterGetName(ProductInterface $subject, string $result): string
{
    return strtoupper($result);
}
```

Disable unused third-party plugins in `di.xml`:

```xml
<type name="Magento\Catalog\Model\Product">
    <plugin name="unused_third_party_plugin" disabled="true"/>
</type>
```

## GraphQL Resolver Performance

### Batching to Avoid N+1 Resolver Calls

```php
// Bad — one DB call per product in response set
class CategoryResolver implements ResolverInterface
{
    public function resolve(Field $field, $context, ResolveInfo $info, array $value = null, array $args = null): mixed
    {
        return $this->categoryRepository->getById($value['category_id']);
    }
}

// Good — request-scoped in-memory cache
class CategoryResolver implements ResolverInterface
{
    private array $categoryCache = [];

    public function resolve(Field $field, $context, ResolveInfo $info, array $value = null, array $args = null): mixed
    {
        $id = $value['category_id'];
        if (!isset($this->categoryCache[$id])) {
            $this->categoryCache[$id] = $this->categoryRepository->getById($id);
        }
        return $this->categoryCache[$id];
    }
}

// Best — BatchServiceContractResolverInterface (AC 2.4.4+)
class CategoryBatchResolver implements BatchServiceContractResolverInterface
{
    public function getServiceContract(): array
    {
        return [CategoryBatchService::class, 'getCategories'];
    }

    public function convertToMassGet(BatchRequestItemInterface $request): mixed
    {
        return $request->getValue()['category_id'];
    }

    public function convertFromMassGet(BatchRequestItemInterface $request, mixed $result): mixed
    {
        return $result;
    }
}
```

## HTTP & Infrastructure Performance

- Enable Varnish with AC-bundled VCL for FPC in production.
- Use Redis for session store and cache backend — not default file backends.
- Enable OPcache with `opcache.validate_timestamps=0` and `opcache.revalidate_freq=0` in production.
- Deploy static content with locale/theme targeting: `bin/magento setup:static-content:deploy -f en_US --theme Magento/luma`.

### Redis Configuration

Use separate Redis instances (or separate logical databases) for cache and sessions to prevent session eviction under memory pressure.

```php
// app/etc/env.php
'cache' => [
    'frontend' => [
        'default' => [
            'backend' => 'Magento\\Framework\\Cache\\Backend\\Redis',
            'backend_options' => [
                'server'        => '127.0.0.1',
                'port'          => '6379',
                'database'      => '0',
                'compress_data' => '1',
            ],
        ],
    ],
],
'session' => [
    'save'  => 'redis',
    'redis' => [
        'host'     => '127.0.0.1',
        'port'     => '6379',
        'database' => '2',
    ],
],
```

```
# redis.conf — production cache instance
maxmemory 2gb
maxmemory-policy allkeys-lru
save ""
```

## Cron Job Optimization

Place heavy cron jobs in a dedicated group to prevent blocking the `default` group.

```xml
<!-- etc/crontab.xml -->
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Cron:etc/crontab.xsd">
    <group id="my_module_heavy">
        <job name="my_module_sync_products"
             instance="MyVendor\MyModule\Cron\SyncProducts"
             method="execute">
            <schedule>0 2 * * *</schedule>
        </job>
    </group>
</config>
```

Use `LockManagerInterface` to prevent overlapping executions of long-running cron jobs.

```php
class SyncProducts
{
    private const LOCK_NAME = 'my_module_sync_products';
    private const LOCK_TTL  = 3600;

    public function __construct(
        private readonly LockManagerInterface $lockManager,
    ) {}

    public function execute(): void
    {
        if ($this->lockManager->isLocked(self::LOCK_NAME)) {
            return;
        }
        $this->lockManager->lock(self::LOCK_NAME, self::LOCK_TTL);
        try {
            $this->doWork();
        } finally {
            $this->lockManager->unlock(self::LOCK_NAME);
        }
    }
}
```
