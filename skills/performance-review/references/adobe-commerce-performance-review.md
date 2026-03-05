# Adobe Commerce (Magento 2) Performance Best Practices

Applies to: Adobe Commerce / Magento 2 (AC 2.4.x)

> Covers Adobe Commerce / Magento 2 platform performance concerns only. PHP language performance patterns are covered in `php-performance-review.md`.

---

## Database Query Optimization

### Use Collections with Field Restrictions

```php
// Good — fetches only needed columns; one query at the DB level
$collection = $this->productCollectionFactory->create();
$collection->addFieldToSelect(['entity_id', 'sku', 'name', 'status']);
$collection->addFieldToFilter('status', Status::STATUS_ENABLED);

// Bad — SELECT * loads all EAV attributes across many join tables; extremely expensive
$collection = $this->productCollectionFactory->create();
$collection->load();
```

### Avoid Per-Item `load()` / Repository Calls Inside Loops

```php
// Bad — 1 repository call per order item (classic N+1)
foreach ($orderItems as $item) {
    $product = $this->productRepository->getById($item->getProductId());
    $this->process($product);
}

// Good — batch load with a single collection query
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
// Good — uses the repository's identity-map layer; repeated calls for the same ID are free
$product = $this->productRepository->getById($id);

// Bad for repeated access — bypasses repository caching, always hits the DB
$product = $this->productFactory->create()->load($id);
```

### Prefer `getSize()` for Count-Only Checks

```php
// Good — issues COUNT(*) at the DB level; does not load any records
if ($collection->getSize() > 0) { ... }

// Bad — loads all records into memory just to count them
if (count($collection->getItems()) > 0) { ... }
```

### Use `SearchCriteriaBuilder` for Paginated Reads

```php
// Good — page size prevents unbounded result sets
$criteria = $this->searchCriteriaBuilder
    ->addFilter('status', 'active')
    ->setPageSize(100)
    ->setCurrentPage(1)
    ->create();
$results = $this->repository->getList($criteria);
```

---

## EAV Attribute Loading

```php
// Good — load only the attributes you will actually use
$collection->addAttributeToSelect(['name', 'price', 'special_price', 'image']);

// Bad — joins every EAV attribute table; multiplies query count and memory
$collection->addAttributeToSelect('*');
```

Note: Flat catalog tables (`catalog_product_flat_*`) were deprecated in Adobe Commerce 2.4.x and are scheduled for removal. Do not rely on flat table enablement as a performance strategy; use collection field restrictions and ensure indexers run on schedule instead.

---

## Caching

### Use Cache Interface for Expensive Data

```php
use Magento\Framework\App\CacheInterface;
use Magento\Framework\Serialize\SerializerInterface;

class ConfigProvider
{
    private const CACHE_KEY   = 'my_module_config_v1';
    private const CACHE_TAG   = 'my_module';
    private const CACHE_TTL   = 3600; // seconds

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

Blocks and ViewModels rendered inside FPC must never read session, customer, or cookie data directly — doing so causes a cache miss for every visitor:

```php
// Bad — customer name in a cacheable block forces a cache miss for every request
class MyBlock extends Template
{
    public function getCustomerName(): string
    {
        // customerSession read invalidates FPC for this block
        return $this->customerSession->getCustomerData()->getFirstname();
    }
}

// Good — keep the block cacheable; load customer-specific data client-side via sections API
class MyBlock extends Template
{
    public function getCacheLifetime(): ?int
    {
        return 86400; // positive value = cacheable
    }

    // Customer name is fetched by Alpine.js / RequireJS from /customer/section/load
}
```

### Block Identity for Granular Cache Invalidation

```php
use Magento\Framework\DataObject\IdentityInterface;

class ProductListBlock extends Template implements IdentityInterface
{
    public function getIdentities(): array
    {
        // Invalidate only when these specific cache tags are cleaned
        return [\Magento\Catalog\Model\Product::CACHE_TAG, \Magento\Catalog\Model\Category::CACHE_TAG];
    }
}
```

---

## Indexing

Trigger re-indexing correctly — never call `reindexAll()` during a web or API request:

```php
// Good — mark the indexer as invalid; cron picks it up asynchronously
$this->indexer->invalidate();

// Bad — synchronous full reindex blocks the web request for minutes in any non-trivial catalog
$this->indexer->reindexAll();
```

Configure indexers to **Update by Schedule** in production (Products, Categories, Price, Inventory) so mutations during import or mass-update do not block the request cycle.

---

## Message Queue for Heavy Operations

Move non-blocking work to queue consumers so the web request returns immediately:

```php
// Good — publish a lightweight message and return fast
class OrderService
{
    public function placeOrder(OrderInterface $order): void
    {
        $this->orderRepository->save($order);
        // Publisher sends only the entity ID — not the full object
        $this->publisher->publish('my_module.order.placed', (string) $order->getEntityId());
    }
}

// Bad — heavy processing blocks checkout response; degrades conversion rate
class OrderService
{
    public function placeOrder(OrderInterface $order): void
    {
        $this->orderRepository->save($order);
        $this->sendConfirmationEmail($order);  // slow — external SMTP call
        $this->updateErpSystem($order);        // very slow — external HTTP call
        $this->generateInvoicePdf($order);     // very slow — PDF rendering
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

Keep consumers idempotent — the message broker may deliver a message more than once.

---

## Plugin (Interceptor) Performance

Around plugins impose the highest overhead of the three plugin types. Prefer before/after:

```php
// Bad — around plugin used only to modify the return value; always calls $proceed()
public function aroundGetName(ProductInterface $subject, callable $proceed): string
{
    return strtoupper($proceed());
}

// Good — after plugin is sufficient and costs less
public function afterGetName(ProductInterface $subject, string $result): string
{
    return strtoupper($result);
}
```

Use `disabled` in `di.xml` to turn off unused third-party plugins:

```xml
<type name="Magento\Catalog\Model\Product">
    <plugin name="unused_third_party_plugin" disabled="true"/>
</type>
```

---

## GraphQL Resolver Performance

### Batching to Avoid N+1 Resolver Calls

Each GraphQL field resolver is called once per parent entity by default. Without batching this causes N+1 queries:

```php
// Bad — one DB call per product in the response set
class CategoryResolver implements ResolverInterface
{
    public function resolve(Field $field, $context, ResolveInfo $info, array $value = null, array $args = null): mixed
    {
        // Called N times for N products — N queries
        return $this->categoryRepository->getById($value['category_id']);
    }
}

// Good — simple request-scoped in-memory cache (sufficient for most cases)
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

// Best for large result sets — BatchServiceContractResolverInterface (AC 2.4.4+)
use Magento\Framework\GraphQl\Query\Resolver\BatchServiceContractResolverInterface;

class CategoryBatchResolver implements BatchServiceContractResolverInterface
{
    public function getServiceContract(): array
    {
        // The batch service method receives ALL requested IDs in a single call
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

---

## HTTP & Infrastructure Performance

- Enable Varnish with the Adobe Commerce-bundled VCL for full page caching in production.
- Use Redis for both the session store and the cache backend — not the default file backends.
- Enable OPcache with `opcache.validate_timestamps=0` and `opcache.revalidate_freq=0` in production to eliminate stat calls on every request.
- Deploy static content with locale/theme targeting to minimize deploy size: `bin/magento setup:static-content:deploy -f en_US --theme Magento/luma`.

### Redis Configuration

Use separate Redis instances (or at least separate logical databases) for cache and sessions to prevent session data being evicted under memory pressure:

```php
// app/etc/env.php
'cache' => [
    'frontend' => [
        'default' => [
            'backend' => 'Magento\\Framework\\Cache\\Backend\\Redis',
            'backend_options' => [
                'server'        => '127.0.0.1',
                'port'          => '6379',
                'database'      => '0',       // DB 0 for cache
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
        'database' => '2',                    // separate DB for sessions
    ],
],
```

```
# redis.conf — production cache instance
maxmemory 2gb
maxmemory-policy allkeys-lru   # evict LRU keys when full
save ""                        # disable RDB snapshots for a pure cache instance
```

---

## Cron Job Optimization

Place heavy cron jobs in a dedicated group to prevent them from blocking the `default` group:

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

Use `LockManagerInterface` to prevent overlapping executions of long-running cron jobs:

```php
use Magento\Framework\Lock\LockManagerInterface;

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
            return; // previous run still active — skip this cycle
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

---

## Resources

- [Adobe Commerce Performance Best Practices](https://experienceleague.adobe.com/docs/commerce-operations/performance-best-practices/overview.html)
- [Magento 2 Indexing](https://developer.adobe.com/commerce/php/development/components/indexing/)
- [Magento 2 Caching](https://developer.adobe.com/commerce/php/development/cache/partial/)
- [Message Queues](https://developer.adobe.com/commerce/php/development/components/message-queues/)
- [Full Page Caching](https://developer.adobe.com/commerce/php/development/cache/page/public-content/)
- [Redis Configuration](https://experienceleague.adobe.com/docs/commerce-operations/configuration-guide/cache/redis/redis-session.html)
- [GraphQL Batch Resolvers](https://developer.adobe.com/commerce/webapi/graphql/develop/resolvers/)
