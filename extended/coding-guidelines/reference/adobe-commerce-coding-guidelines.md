# PHP + Adobe Commerce (Magento 2) Coding Style Guide

> Load this file together with `php-coding-guidelines.md`. Rules here are additive and Adobe Commerce-specific.

---

## Module Structure

- Follow the standard module layout: `Block/`, `Controller/`, `Model/`, `Plugin/`, `Observer/`, `Setup/`, `view/`, `etc/`
- Declare the module in `etc/module.xml` with a correct `<sequence>` listing all modules whose classes or tables this module depends on
- Register the module in `registration.php` at the module root using `ComponentRegistrar::register`
- Keep `etc/di.xml` as the single source of truth for dependency wiring — never use `ObjectManager` directly in business logic
- Place frontend assets under `view/frontend/`, adminhtml assets under `view/adminhtml/`, and shared assets under `view/base/`

```php
// registration.php
ComponentRegistrar::register(ComponentRegistrar::MODULE, 'MyVendor_MyModule', __DIR__);
```

## Naming Conventions

- Module namespace: `Vendor_ModuleName` (e.g., `Acme_Catalog`); PSR-4 root maps to `app/code/Acme/Catalog/`
- Block classes: place under `Block/`; suffix not mandatory but `Block` suffix is conventional for complex blocks
- Model classes: `Model/` for domain models; `Model/ResourceModel/` for resource models; `Model/ResourceModel/<Entity>/Collection` for collections
- Controllers: one action class per HTTP action in `Controller/<Area>/<ControllerName>/<ActionName>.php`; each implements `\Magento\Framework\App\ActionInterface`
- Plugins: suffix with `Plugin` (e.g., `ProductRepositoryPlugin`), placed in `Plugin/`
- Observers: suffix with `Observer` (e.g., `OrderSaveAfterObserver`), placed in `Observer/`; implement `\Magento\Framework\Event\ObserverInterface`
- ViewModels: suffix with `ViewModel` (e.g., `ProductInfoViewModel`); implement `\Magento\Framework\View\Element\Block\ArgumentInterface`
- Service contract interfaces: `Api/<EntityName>RepositoryInterface`, `Api/<EntityName>ManagementInterface`
- Data interfaces: `Api/Data/<EntityName>Interface`, `Api/Data/<EntityName>SearchResultsInterface`

## Dependency Injection

- Always inject dependencies through the constructor
- Never use `\Magento\Framework\App\ObjectManager::getInstance()` outside of factories, setup scripts, or test helpers
- Use virtual types in `di.xml` for parameter overrides instead of creating redundant subclasses:

```xml
<!-- etc/di.xml -->
<virtualType name="MyVendor\MyModule\Model\CustomLogger" type="Magento\Framework\Logger\Monolog">
    <arguments>
        <argument name="name" xsi:type="string">MyModule</argument>
    </arguments>
</virtualType>
```

- Prefer interfaces over concrete classes in constructor type hints
- Use factories (`XxxFactory`) for creating new object instances — never `new` for DI-managed classes:

```php
// Good
public function __construct(private readonly ProductInterfaceFactory $productFactory) {}
public function createProduct(): ProductInterface { return $this->productFactory->create(); }

// Bad — bypasses DI and plugins
public function createProduct(): ProductInterface { return new \Magento\Catalog\Model\Product(); }
```

- Use `Proxy` for heavy or circular dependencies — declare in `di.xml`, not in the constructor type hint:

```xml
<type name="MyVendor\MyModule\Model\HeavyConsumer">
    <arguments>
        <argument name="heavyService" xsi:type="object">MyVendor\MyModule\Model\HeavyService\Proxy</argument>
    </arguments>
</type>
```

## Service Contracts and APIs

- Expose module functionality through service contracts: interfaces in `Api/`, implementations in `Model/`
- Define data interfaces in `Api/Data/`; implement with `Model/Data/` using `ExtensibleDataObject` or `AbstractSimpleObject` as base
- Always use repository interfaces (`XxxRepositoryInterface`) for CRUD operations — not direct model `load()` calls
- Mark stable public APIs with the `@api` docblock annotation
- Use `SearchCriteria` and `SearchResultsInterface` for collection retrieval in repositories
- Build search criteria using `SearchCriteriaBuilder` injected as a constructor dependency — never instantiate it directly:

```php
$criteria = $this->searchCriteriaBuilder
    ->addFilter('status', 'active')
    ->addSortOrder($this->sortOrderBuilder->setField('created_at')->setDescendingDirection()->create())
    ->setPageSize(20)
    ->create();
$results = $this->repository->getList($criteria);
```

## Extension Attributes

- Use extension attributes (`etc/extension_attributes.xml`) to add data to existing entities — never modify core `Api/Data` interfaces directly
- Load extension attributes in an `afterGet`/`afterGetList` plugin on the repository; save them in a `beforeSave` plugin:

```php
// Plugin/ProductRepositoryPlugin.php
public function afterGet(ProductRepositoryInterface $subject, ProductInterface $product): ProductInterface
{
    $extensionAttributes = $product->getExtensionAttributes() ?? $this->productExtensionFactory->create();
    $extensionAttributes->setMyCustomData($this->myRepository->getByProductId((int) $product->getId()));
    $product->setExtensionAttributes($extensionAttributes);
    return $product;
}
```

- Always null-check extension attributes and create via the generated factory if null

## Plugins (Interceptors)

- Use plugins for cross-cutting concerns (logging, caching, authorization) — not for core business logic
- Prefer `before` and `after` plugins. Use `around` only when the original method call must be conditionally skipped or wrapped in try/catch. An `around` plugin that always calls `$proceed()` adds overhead for no benefit:

```php
// Bad — around plugin just to modify result; always calls $proceed()
public function aroundGetName(ProductInterface $subject, callable $proceed): string
{
    return strtoupper($proceed());
}

// Good — after plugin achieves same result at lower cost
public function afterGetName(ProductInterface $subject, string $result): string
{
    return strtoupper($result);
}
```

- Keep plugin classes thin — delegate logic to a dedicated service class; plugins are wiring, not implementation
- Plugins intercept public methods only. Do not target protected or private methods — the plugin will be silently ignored, creating an invisible bug. If the target behaviour is in a non-public method, dispatch a custom event or refactor the method to public

## Events and Observers

- Dispatch events at meaningful extension points using `\Magento\Framework\Event\ManagerInterface::dispatch()`
- Name events in lowercase with underscores: `vendor_module_entity_save_after`
- Keep observers stateless — no mutable instance properties that persist across requests
- Do not perform heavy operations in observers — queue heavy work via message queues

```php
// Model/Service/OrderService.php
public function placeOrder(OrderInterface $order): void
{
    $this->orderRepository->save($order);
    $this->eventManager->dispatch('myvendor_mymodule_order_placed', ['order' => $order]);
}
```

## Message Queues

- Define topics in `etc/communication.xml` and bindings in `etc/queue_topology.xml` and `etc/queue_publisher.xml`
- Define consumers in `etc/queue_consumer.xml`
- Publish via `\Magento\Framework\MessageQueue\PublisherInterface` — never call consumers directly
- Keep message payloads small — pass entity IDs, not serialized full objects
- Implement idempotent consumers — messages may be delivered more than once

```php
// Consumer/OrderPlacedConsumer.php — safe to call multiple times for the same orderId
public function process(string $orderId): void
{
    if ($this->isAlreadyProcessed((int) $orderId)) { return; }
    $order = $this->orderRepository->get((int) $orderId);
    $this->doWork($order);
    $this->markAsProcessed((int) $orderId);
}
```

## GraphQL APIs

- Define schema types and resolvers in `etc/schema.graphqls`
- Place resolver classes in `Model/Resolver/` and register them in `etc/schema.graphqls`
- Delegate all business logic from resolvers to service classes — resolvers are thin wiring:

```php
// Model/Resolver/ProductExtendedData.php
public function resolve(Field $field, mixed $context, ResolveInfo $info, array $value = null, array $args = null): mixed
{
    return $this->productDataService->getExtendedData((int) $value['model']->getId());
}
```

- Use `\Magento\GraphQl\Model\Query\ContextInterface` for customer and store context — never access session directly in resolvers
- Return scalar values or arrays from resolvers; let the GraphQL framework handle serialization

## Layout and Templates

- Define layout handles in `view/<area>/layout/` XML files
- Use `<referenceBlock>` and `<referenceContainer>` to extend existing layouts — avoid `<block>` overrides that replace core blocks
- **Prefer ViewModels over Block subclasses for all template data access.** Create a new Block subclass only when overriding rendering infrastructure (e.g., custom `toHtml()` logic). Data retrieval, formatting, and any logic consumed by a template belongs in a ViewModel — not in a Block method. If you find yourself adding a `getFoo()` method to a Block, extract it to a ViewModel instead.
- Use ViewModels to pass data to templates — not Block methods that perform business logic:

```xml
<!-- view/frontend/layout/catalog_product_view.xml -->
<referenceBlock name="product.info.main">
    <arguments>
        <argument name="view_model" xsi:type="object">MyVendor\MyModule\ViewModel\ProductInfoViewModel</argument>
    </arguments>
</referenceBlock>
```

```php
// view/frontend/templates/product/info.phtml
$viewModel = $block->getData('view_model');
echo $block->escapeHtml($viewModel->getProductBadge());
```

- Templates must be `.phtml` files with minimal PHP — no business logic, no repository calls in templates
- Escape all output: `$block->escapeHtml()`, `$block->escapeUrl()`, `$block->escapeJs()`, `$block->escapeHtmlAttr()`; never print raw user input

## Data Management and Upgrades

- Use Declarative Schema (`etc/db_schema.xml`) for all schema changes — `InstallSchema` and `UpgradeSchema` classes are deprecated
- After modifying `db_schema.xml`, regenerate the schema whitelist: `bin/magento setup:db-declaration:generate-whitelist --module-name=Vendor_Module`
- Use data patches (`Setup/Patch/Data/`) for data migrations — one patch class per logical change, implementing `DataPatchInterface`:

```php
// Setup/Patch/Data/AddCustomAttribute.php
class AddCustomAttribute implements DataPatchInterface
{
    public function apply(): void
    {
        $this->eavSetup->addAttribute(\Magento\Catalog\Model\Product::ENTITY, 'my_attribute', [
            'type' => 'varchar', 'label' => 'My Attribute', 'input' => 'text',
            'required' => false, 'global' => ScopedAttributeInterface::SCOPE_GLOBAL,
        ]);
    }
    public static function getDependencies(): array { return []; }
    public function getAliases(): array { return []; }
}
```

- Never modify core database tables directly — use extension attributes or separate module tables

## Caching

- Tag all custom cache entries with a module-specific cache tag for granular invalidation
- Implement `IdentityInterface` on blocks and ViewModels that have cacheable output:

```php
class ProductBadgeBlock extends Template implements IdentityInterface
{
    public function getIdentities(): array
    {
        return [\Magento\Catalog\Model\Product::CACHE_TAG . '_' . $this->getProductId()];
    }
}
```

- Use `\Magento\Framework\App\CacheInterface` for custom cache — not raw Zend_Cache
- Use `\Magento\Framework\Cache\FrontendInterface` for frontend-level cache operations

## Security and ACL

- Define ACL resources in `etc/acl.xml` for every admin-facing action
- Implement `_isAllowed()` in all admin controllers returning the ACL resource identifier string:

```php
protected function _isAllowed(): bool
{
    return $this->_authorization->isAllowed('MyVendor_MyModule::manage');
}
```

- For programmatic authorization checks in service classes, inject `\Magento\Framework\AuthorizationInterface`:

```php
public function performSensitiveAction(): void
{
    if (!$this->authorization->isAllowed('MyVendor_MyModule::sensitive_action')) {
        throw new AuthorizationException(__('Access denied.'));
    }
}
```

## LESS / CSS

- **Never use `darken()`, `lighten()`, or similar LESS color functions** — Magento's LESS compiler (`less.php`) does not reliably resolve them, especially inside BEM `&:hover` blocks or when variables originate from the compilation context rather than a local `@import`. Calculate the final hex value manually instead (e.g. `darken(#ffffff, 10%)` = `#e6e6e6`).
- Do not add `@import (reference)` for Magento lib variables (`_lib.less`, `_responsive.less`) inside module `_extend.less` files — lib variables are injected by Magento's compilation pipeline automatically. Manual `lib::css` path imports cause compiler errors.
- Use `.less` files in `view/frontend/web/css/source/` for storefront overrides and `view/adminhtml/web/css/source/` for admin overrides.

## Anti-Patterns to Avoid

- **ObjectManager direct use** — use constructor injection or factories; `ObjectManager::getInstance()` in business logic is a P0 finding
- **Core template override by copy** — use layout XML to `<referenceBlock>` and extend; never copy a core `.phtml` template to override it
- **`<preference>` rewrite when a plugin suffices** — preferences replace the entire class and break other extensions; plugins compose safely
- **Business logic in Block classes** — extract to ViewModels or service classes; blocks are responsible for rendering only
- **Raw superglobals** — never use `$_GET`, `$_POST`, or `$_SESSION` directly; use `\Magento\Framework\App\RequestInterface` and session abstractions
- **Database queries in templates** — all data access in template scope must go through ViewModels pre-fetched by the block; no repository calls in `.phtml`
- **Skipping ACL in admin controllers** — `_isAllowed()` is not optional; every admin action that is missing it is a security vulnerability
- **`reindexAll()` in web requests** — synchronous full reindex during a page request can block for minutes; mark as `invalidate()` and let cron schedule it
- **`around` plugins that always call `$proceed()`** — adds two stack frames and one closure allocation per call with no behavioural benefit; use `after` instead
