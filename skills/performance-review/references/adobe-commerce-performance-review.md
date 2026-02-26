# Adobe Commerce (Magento 2) Performance Best Practices

Applies to: Adobe Commerce / Magento 2 (AC 2.4.x)

> Covers Adobe Commerce / Magento 2 platform performance concerns only. PHP language performance patterns are covered in `php-performance-review.md`.

---

## Database Query Optimization

### Use Collections with Field Restrictions

```php
// Good — fetches only needed columns
$collection = $this->productCollectionFactory->create();
$collection->addFieldToSelect(['entity_id', 'sku', 'name', 'status']);
$collection->addFieldToFilter('status', Status::STATUS_ENABLED);

// Bad — SELECT * loads all EAV attributes, very expensive
$collection = $this->productCollectionFactory->create();
$collection->load();
```

### Avoid Per-Item `load()` Inside Loops

```php
// Bad — 1 query per order item (N+1)
foreach ($orderItems as $item) {
    $product = $this->productRepository->getById($item->getProductId());
    $this->process($product);
}

// Good — batch load with collection
$productIds = array_column($orderItems, 'product_id');
$collection = $this->productCollectionFactory->create();
$collection->addFieldToFilter('entity_id', ['in' => $productIds]);
$products = $collection->getItems(); // single query
```

### Use Repository API for Single-Record Access

```php
// Good — uses identity map / cache layer
$product = $this->productRepository->getById($id);

// Bad for repeated access — bypasses repository cache
$product = $this->productFactory->create()->load($id);
```

### Prefer `getSize()` for Count-Only Checks

```php
// Good — COUNT(*) at DB level, does not load records
if ($collection->getSize() > 0) { ... }

// Bad — loads all records just to count
if (count($collection->getItems()) > 0) { ... }
```

---

## Caching

### Use Cache Interface for Expensive Data

```php
use Magento\Framework\App\CacheInterface;
use Magento\Framework\Serialize\SerializerInterface;

class ConfigProvider
{
    private const CACHE_KEY = 'my_module_config';
    private const CACHE_TAG = 'my_module';
    private const CACHE_LIFETIME = 3600;

    public function __construct(
        private readonly CacheInterface $cache,
        private readonly SerializerInterface $serializer,
    ) {}

    public function getConfig(): array
    {
        $cached = $this->cache->load(self::CACHE_KEY);
        if ($cached) {
            return $this->serializer->unserialize($cached);
        }
        $data = $this->computeExpensiveConfig();
        $this->cache->save(
            $this->serializer->serialize($data),
            self::CACHE_KEY,
            [self::CACHE_TAG],
            self::CACHE_LIFETIME
        );
        return $data;
    }
}
```

### Full Page Cache (FPC) Compatibility

Blocks rendered inside FPC must not read session, cookies, or customer-specific data directly:

```php
// Bad — breaks FPC; customer data in a cacheable block
class MyBlock extends Template
{
    public function getCustomerName(): string
    {
        return $this->customerSession->getCustomerData()->getFirstname(); // FPC miss
    }
}

// Good — keep the block cacheable; load customer-specific data client-side via sections
class MyBlock extends Template
{
    public function getCacheLifetime(): ?int
    {
        return 86400;
    }
}
```

---

## Indexing

Trigger re-indexing correctly — never call `reindexAll()` in production request cycles:

```php
// Good — mark for partial reindex; indexer runs via cron
$this->indexer->invalidate();

// Bad — full synchronous reindex during a web request
$this->indexer->reindexAll(); // blocks the request for minutes
```

Configure indexers to **Update by Schedule** in production (Products, Categories, Price, Inventory).

---

## Message Queue for Heavy Operations

Move non-blocking work to queue consumers:

```php
// Good — publish to queue, return fast
class OrderService
{
    public function placeOrder(OrderInterface $order): void
    {
        $this->orderRepository->save($order);
        $this->publisher->publish('my.module.order.placed', $order->getEntityId());
    }
}

// Bad — heavy processing blocks the checkout response
class OrderService
{
    public function placeOrder(OrderInterface $order): void
    {
        $this->orderRepository->save($order);
        $this->sendConfirmationEmail($order);   // slow
        $this->updateErpSystem($order);         // very slow
        $this->generateInvoicePdf($order);      // very slow
    }
}
```

---

## Plugin (Interceptor) Performance

Around plugins impose the highest overhead — prefer before/after:

```php
// Bad — around plugin just to modify result
public function aroundGetName(ProductInterface $subject, callable $proceed): string
{
    return strtoupper($proceed());
}

// Good — after plugin is sufficient
public function afterGetName(ProductInterface $subject, string $result): string
{
    return strtoupper($result);
}
```

Use `disabled` in `di.xml` to turn off unused third-party plugins rather than leaving them active.

---

## EAV Attribute Loading

Load only the attributes you need:

```php
// Good — addAttributeToSelect with specific attributes
$collection->addAttributeToSelect(['name', 'price', 'special_price']);

// Bad — loads every EAV attribute for every entity
$collection->addAttributeToSelect('*');
```

Use flat tables (catalog flat product/category) when reading large product sets on the storefront. Note: flat table support is deprecated in Adobe Commerce 2.4.x and scheduled for removal. Prefer collection field restrictions and indexers instead.

---

## GraphQL Resolver Performance

### Use `BatchContainerInterface` to Avoid N+1 in Resolvers

Each GraphQL field resolver runs once per parent entity by default. Without batching, this causes N+1 queries:

```php
// Bad — 1 query per product in the result set
class CategoryResolver implements ResolverInterface
{
    public function resolve(Field $field, $context, ResolveInfo $info, array $value = null, array $args = null)
    {
        // Called once per product — N queries for N products
        return $this->categoryRepository->getById($value['category_id']);
    }
}

// Good — batch with BatchContainerInterface (AC 2.4.4+)
use Magento\GraphQl\Model\Query\ContextInterface;
use Magento\Framework\GraphQl\Query\Resolver\BatchServiceContractResolverInterface;
use Magento\Framework\GraphQl\Query\Resolver\BatchRequestItemInterface;

class CategoryBatchResolver implements BatchServiceContractResolverInterface
{
    public function getServiceContract(): array
    {
        return [CategoryBatchService::class, 'getCategories'];
    }
    // The batch service receives all IDs in one call — single query
}
```

For simpler cases, use a request-scoped in-memory cache keyed by entity ID:

```php
private array $cache = [];

public function resolve(...): array
{
    $id = $value['category_id'];
    if (!isset($this->cache[$id])) {
        $this->cache[$id] = $this->categoryRepository->getById($id);
    }
    return $this->cache[$id];
}
```

---

## HTTP & Infrastructure Performance

- Enable Varnish with the bundled VCL for full page caching in production.
- Use Redis for session storage and cache backend — not files.
- Enable OPcache with `opcache.validate_timestamps=0` in production.
- Use `bin/magento setup:static-content:deploy -f` with locale/theme targeting to minimize deploy size.

### Redis Tuning

Default Redis configuration is optimized for development. In production:

```bash
# redis.conf — recommended settings for AC cache backend
maxmemory 2gb
maxmemory-policy allkeys-lru   # evict least-recently-used keys when memory is full
save ""                        # disable RDB snapshots for pure cache use
```

```php
// app/etc/env.php — separate Redis instances for cache and sessions
'cache' => [
    'frontend' => [
        'default' => [
            'backend' => 'Magento\\Framework\\Cache\\Backend\\Redis',
            'backend_options' => [
                'server'   => '127.0.0.1',
                'port'     => '6379',
                'database' => '0',           // DB 0 for cache
                'compress_data' => '1',
            ],
        ],
    ],
],
'session' => [
    'save'    => 'redis',
    'redis'   => [
        'host'     => '127.0.0.1',
        'port'     => '6379',
        'database' => '2',                   // separate DB for sessions
    ],
],
```

Use separate Redis instances (or at least separate databases) for cache and sessions to prevent session data being evicted under memory pressure.

---

## Cron Job Optimization

```xml
<!-- etc/crontab.xml — heavy jobs in a separate cron group to avoid blocking the default group -->
<config>
    <group id="my_module_heavy">
        <job name="my_module_sync_products" instance="MyVendor\MyModule\Cron\SyncProducts" method="execute">
            <schedule>0 2 * * *</schedule>
        </job>
    </group>
</config>
```

Always check for a running lock before re-entering a long-running cron:

```php
public function execute(): void
{
    if ($this->lockManager->isLocked(self::LOCK_NAME)) {
        return; // previous run still active
    }
    $this->lockManager->lock(self::LOCK_NAME);
    try {
        $this->doWork();
    } finally {
        $this->lockManager->unlock(self::LOCK_NAME);
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
