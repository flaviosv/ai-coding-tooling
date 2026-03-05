# Adobe Commerce (Magento 2) Code Review Checklist

Supplements the generic `review-checklist.md` and `php-code-review.md` for projects using Adobe Commerce / Magento 2 (AC 2.4.x).

> Covers Adobe Commerce / Magento 2 platform concerns only. PHP language best practices are covered in `php-code-review.md`.

---

## Security

- [ ] No hardcoded credentials, API keys, or secrets — use `app/etc/env.php` or environment variables only
- [ ] User input escaped before output — use `$escaper->escapeHtml()`, `escapeUrl()`, `escapeJs()`, `escapeHtmlAttr()` in templates; never print raw user data
- [ ] No raw SQL string concatenation — use `$connection->select()` with bind parameters or resource model queries
- [ ] ACL resources defined in `etc/acl.xml` and enforced in Admin controllers via `_isAllowed()` — never omit this check
- [ ] Frontend controllers validate form keys with `validateFormKey()` to prevent CSRF attacks
- [ ] REST API endpoints declare proper `<resources>` in `etc/webapi.xml`; anonymous (`<resource ref="anonymous"/>`) used only where truly public
- [ ] Custom REST endpoints verify ownership of resources — any endpoint that returns customer-scoped data must confirm the requesting customer owns it (IDOR prevention)
- [ ] `setData()` called only with validated, explicit key-value pairs — never with raw user-supplied arrays (`$model->setData($request->getParams())` is forbidden)
- [ ] Sensitive data absent from logs, exception messages, API responses, and frontend output
- [ ] File uploads validated for MIME type, extension allowlist, size limit, and path traversal (no user-controlled path segments)
- [ ] Admin routes use `ScopeConfigInterface` for configuration reads — not direct `env.php` access in business logic
- [ ] `\Magento\Framework\Exception\*` typed exceptions thrown from service layer — never `\Exception` directly, which leaks stack traces

---

## Performance

- [ ] Collections use `addFieldToSelect()` with an explicit field list — never `addFieldToSelect('*')` which loads all EAV attributes
- [ ] Repository API preferred over direct `->load()` calls for single-entity access (repository uses identity-map caching)
- [ ] No N+1 query patterns: loops over collections must not call `->load()`, `->getById()`, or any repository method per iteration — batch with collection filters or `['in' => $ids]`
- [ ] Expensive, rarely-changing data cached via `\Magento\Framework\App\CacheInterface` with a module-specific cache tag
- [ ] Full Page Cache (FPC) compatibility maintained: cacheable blocks must not read session data, customer data, or cookies directly — use sections/private content
- [ ] `getCacheLifetime()` on blocks returns a positive integer when caching is intended — not `null` accidentally
- [ ] Heavy operations (email sending, ERP sync, PDF generation) offloaded to message queue consumers, not done inline in web requests
- [ ] EAV attribute loads restricted with `addAttributeToSelect(['attr1', 'attr2'])` — never with `'*'`
- [ ] Indexer `reindexAll()` never called during a web request — mark as `invalidate()` and let cron handle it
- [ ] GraphQL resolvers use batching (`BatchServiceContractResolverInterface`) or a request-scoped cache to avoid N+1 resolver calls

---

## Architecture & Design

Examples of correct DI wiring and plugin usage:

```xml
<!-- etc/di.xml — correct plugin declaration with sortOrder -->
<type name="Magento\Catalog\Api\ProductRepositoryInterface">
    <plugin name="myvendor_mymodule_product_repository_plugin"
            type="MyVendor\MyModule\Plugin\ProductRepositoryPlugin"
            sortOrder="10"/>
</type>
```

```php
// Good — constructor injection; no ObjectManager in business logic
class OrderProcessor
{
    public function __construct(
        private readonly OrderRepositoryInterface $orderRepository,
    ) {}
}

// Bad — ObjectManager in business logic
class OrderProcessor
{
    public function process(): void
    {
        $order = \Magento\Framework\App\ObjectManager::getInstance()
            ->create(OrderInterface::class); // forbidden outside factories/tests
    }
}
```

- [ ] Module follows standard Magento 2 directory structure: `registration.php`, `etc/module.xml`, correct PSR-4 namespace
- [ ] Dependency Injection used exclusively — `ObjectManager::getInstance()` never appears in business logic, controllers, or blocks (only acceptable in factories, setup scripts, and test helpers)
- [ ] New required constructor parameters not added to existing public classes — breaking change for third-party extensions; use optional parameters with defaults or create a new class
- [ ] `Proxy` used only for heavy or circular dependencies — not applied indiscriminately as a performance hack
- [ ] Service contracts defined: interfaces in `Api/`, data objects in `Api/Data/`, implementations in `Model/` — modules never depend on concrete model classes across boundaries
- [ ] Public interfaces in `Api/` annotated with `@api` to signal stability
- [ ] Plugins (`etc/di.xml` interceptors) used instead of class rewrites (`<preference>`) wherever possible
- [ ] `around` plugins used only when the original method call must be conditionally skipped or wrapped in try/catch — never when `before`/`after` suffices
- [ ] Events dispatched at meaningful extension points; observers registered in `etc/events.xml`; no circular event chains
- [ ] No circular module dependencies — `sequence` in `etc/module.xml` declares load order, not feature dependencies
- [ ] Declarative Schema (`etc/db_schema.xml`) used for all schema changes — `InstallSchema`/`UpgradeSchema` classes are a red flag
- [ ] Data migrations in `Setup/Patch/Data/` classes implementing `DataPatchInterface` — not in `UpgradeData`
- [ ] UI Components and layout XML follow convention; no inline PHP logic in `.phtml` templates; business logic lives in ViewModels or service classes
- [ ] `<sequence>` declarations in `etc/module.xml` are accurate — missing sequences cause random load-order failures
- [ ] Extension attributes (`etc/extension_attributes.xml`) used to add data to existing core entities — never modifying core `Api/Data` interfaces

---

## Code Quality

- [ ] Observers are stateless — implement `ObserverInterface`, carry no mutable instance state that persists across requests
- [ ] Block classes contain only presentation logic — no business logic, no repository calls; use ViewModels for data retrieval
- [ ] ViewModels implement `ArgumentInterface`, injected via layout XML `<arguments>` — not instantiated with `ObjectManager` in templates
- [ ] Factories (`XxxFactory`) used to create new model instances — never `new ModelClass()` for classes managed by the DI container
- [ ] Virtual types in `di.xml` used for parameter overrides instead of creating redundant subclasses
- [ ] Store-scoped configuration read via `ScopeConfigInterface::getValue($path, ScopeInterface::SCOPE_STORE)` — not hardcoded defaults
- [ ] `SearchCriteria` built via `SearchCriteriaBuilder` injected as a constructor dependency — never instantiated with `new`
- [ ] Repository `getList()` returns `SearchResultsInterface` — not a raw collection or array
- [ ] `__()` translation function used for all user-visible strings — no hardcoded English text in PHP or templates
- [ ] Layout handle scope correct — module-specific layouts use module-specific handles, not `default.xml`

---

## Adobe Commerce Best Practices

- [ ] `di.xml` plugins have a clear `sortOrder` to avoid conflicts with other plugins on the same method
- [ ] Cron schedule defined in `etc/crontab.xml`; heavy cron jobs placed in a dedicated cron group to avoid blocking the `default` group
- [ ] Message queue consumer defined in `etc/queue_consumer.xml` with a correct connection type (`db` or `amqp`)
- [ ] Admin grids use `etc/ui_component/` XML listings — no legacy `adminhtml/widget/grid` block rewrites
- [ ] Customer and sales data accessed through service contracts — not through raw collection or model `load()` calls
- [ ] GraphQL resolvers implement `ResolverInterface`, delegate business logic to service classes, and use `ContextInterface` for customer/store context — never session
- [ ] For projects using the Hyva theme: Knockout.js / RequireJS-based UI Components flagged as incompatible; Alpine.js / web components are the Hyva-native approach
- [ ] `bin/magento setup:db-declaration:generate-whitelist --module-name=Vendor_Module` run after every `db_schema.xml` change
- [ ] Message payloads in queues contain only entity IDs — not serialized full objects, which bloat the queue and break on schema changes
- [ ] Plugins intercept only public methods — no plugin targeting protected or private methods (they are silently ignored, creating an invisible bug)

---

## Documentation

- [ ] Public interfaces and service contract methods have complete PHPDoc blocks (`@param`, `@return`, `@throws`)
- [ ] `@api` annotation present on stable public interfaces in `Api/`
- [ ] Complex business logic has inline comments explaining the "why", not the "what"
- [ ] `README.md` or module `docs/` updated if the public API or module configuration changes

---

## Resources

- [Adobe Commerce Developer Documentation](https://developer.adobe.com/commerce/docs/)
- [Magento 2 Coding Standards](https://developer.adobe.com/commerce/php/coding-standards/)
- [Service Contracts](https://developer.adobe.com/commerce/php/development/components/service-contracts/)
- [Plugins (Interceptors)](https://developer.adobe.com/commerce/php/development/components/plugins/)
- [Declarative Schema](https://developer.adobe.com/commerce/php/development/components/declarative-schema/)
- [Dependency Injection](https://developer.adobe.com/commerce/php/development/components/dependency-injection/)
- [Extension Attributes](https://developer.adobe.com/commerce/php/development/components/add-attributes/)
- [Adobe Commerce Security Best Practices](https://experienceleague.adobe.com/docs/commerce-operations/security-and-compliance/overview.html)
- [Message Queues](https://developer.adobe.com/commerce/php/development/components/message-queues/)
