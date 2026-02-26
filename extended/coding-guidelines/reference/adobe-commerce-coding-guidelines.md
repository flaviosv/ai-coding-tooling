# PHP + Adobe Commerce (Magento 2) Coding Style Guide

> Load this file together with `php-coding-guidelines.md`. Rules here are additive and Adobe Commerce-specific.

## Module Structure

- Follow the standard module layout: `Block/`, `Controller/`, `Model/`, `Plugin/`, `Observer/`, `Setup/`, `view/`
- Declare the module in `etc/module.xml` with a proper `sequence` for dependencies
- Register the module in `registration.php` at the module root
- Keep `etc/di.xml` the single source of truth for dependency injection wiring — never use `ObjectManager` directly in business logic
- Place frontend assets under `view/frontend/`, adminhtml under `view/adminhtml/`, shared under `view/base/`

## Naming Conventions

- Module namespace: `Vendor_ModuleName` (e.g., `Acme_Catalog`)
- Block classes: suffix with `Block` or place under `Block/` namespace
- Model classes: place under `Model/`; resource models under `Model/ResourceModel/`; collections under `Model/ResourceModel/<Entity>/Collection`
- Controllers: one action class per HTTP action; suffix with the action name (`IndexAction`, `SaveAction`)
- Plugins: suffix with `Plugin` (`ProductRepositoryPlugin`)
- Observers: suffix with `Observer` (`OrderSaveAfterObserver`)
- ViewModels: suffix with `ViewModel`; implement `\Magento\Framework\View\Element\Block\ArgumentInterface`

## Dependency Injection

- Always inject dependencies through the constructor
- Never use `\Magento\Framework\App\ObjectManager::getInstance()` outside of factories, tests, or setup scripts
- Use virtual types in `di.xml` for parameter overrides instead of creating new classes
- Prefer interfaces over concrete classes in constructor type hints
- Use factories (`XxxFactory`) for creating new model instances — never `new`

## Service Contracts and APIs

- Expose module functionality through service contracts (`Api/` interfaces + `Model/` implementations)
- Define data interfaces in `Api/Data/`; implement with `Model/Data/`
- Always use repository interfaces (`XxxRepositoryInterface`) for CRUD — not direct model loading
- Mark public APIs with `@api` docblock annotation
- Use `SearchCriteria` and `SearchResultsInterface` for collection retrieval in repositories
- Build search criteria using `\Magento\Framework\Api\SearchCriteriaBuilder` injected as a constructor dependency — never instantiate it directly:
  ```php
  $criteria = $this->searchCriteriaBuilder
      ->addFilter('status', 'active')
      ->addSortOrder($this->sortOrderBuilder->setField('created_at')->setDescendingDirection()->create())
      ->setPageSize(20)
      ->create();
  $results = $this->repository->getList($criteria);
  ```

## Extension Attributes

- Use extension attributes (defined in `etc/extension_attributes.xml`) to add data to existing entities — never modify core `Api/Data` interfaces
- Load and save extension attributes explicitly in repository plugins: read in an `afterGet`/`afterGetList` plugin, save in a `beforeSave` plugin
- Access extension attributes via `getExtensionAttributes()` — always null-check and create via the generated factory if null

## Plugins (Interceptors)

- Use plugins for cross-cutting concerns (logging, caching, authorization) — not for business logic
- Use `before` and `after` plugins as the default. Only use `around` when you need to conditionally skip the original method call or wrap it in a try/catch. Never write an `around` plugin that always calls `$proceed()` without conditional logic — it adds overhead and complicates debugging with no benefit.
- Keep plugins thin — delegate to a dedicated service class for logic
- Avoid plugin chains that are hard to trace — prefer observers for event-driven scenarios
- Plugins only intercept public methods. Do not attempt to write plugins for protected or private methods — they will not be invoked and will not produce an error, making the bug hard to detect. If you need to intercept behavior in a non-public method, raise a custom event or refactor the method to public.

## Events and Observers

- Dispatch events at meaningful extension points using `\Magento\Framework\Event\ManagerInterface`
- Name events in lowercase with underscores: `vendor_module_entity_save_after`
- Keep observers stateless — they must implement `\Magento\Framework\Event\ObserverInterface`
- Do not perform heavy operations in observers — queue heavy work via message queues

## Message Queues

- Define topics in `etc/communication.xml` and consumers in `etc/queue_consumer.xml`
- Define queue bindings in `etc/queue_topology.xml` and `etc/queue_publisher.xml`
- Publish messages via `\Magento\Framework\MessageQueue\PublisherInterface` — never call consumers directly
- Keep message payloads small — pass entity IDs, not full objects
- Implement idempotent consumers — messages may be delivered more than once

## GraphQL APIs

- Define resolvers in `Model/Resolver/` and register them in `etc/schema.graphqls`
- Never perform business logic directly in resolvers — delegate to service classes
- Use `\Magento\GraphQl\Model\Query\ContextInterface` for customer/store context — never use session directly in resolvers
- Return scalar types from resolvers; let the GraphQL layer handle serialization

## Layout and Templates

- Define layout handles in `view/<area>/layout/` XML files
- Use `<referenceBlock>` and `<referenceContainer>` to extend existing layouts — never override unless necessary
- Use ViewModels to pass data to templates — not Block methods that perform business logic
- Templates must be `.phtml` files with minimal PHP — no business logic in templates
- Escape all output with `$block->escapeHtml()`, `$block->escapeUrl()`, etc. — never print raw user input

## Data Management and Upgrades

- Use Declarative Schema (`etc/db_schema.xml`) for all schema changes — not `InstallSchema`/`UpgradeSchema`
- After modifying `db_schema.xml`, regenerate the schema whitelist: `bin/magento setup:db-declaration:generate-whitelist --module-name=Vendor_Module`
- Use data patches (`Setup/Patch/Data/`) for data migrations — one patch per logical change
- Mark patches with `PatchVersionInterface` when order matters
- Never modify core database tables directly — use extension attributes or separate tables

## Caching

- Tag all custom cache entries with a module-specific cache tag for granular invalidation
- Implement `IdentityInterface` on blocks and ViewModels that have cacheable output
- Use `\Magento\Framework\Cache\FrontendInterface` for custom cache — not raw `Zend_Cache`

## Security and ACL

- Define ACL resources in `etc/acl.xml` for every admin action
- Implement `_isAllowed()` in admin controllers returning the ACL resource identifier
- For programmatic authorization checks in services, inject `\Magento\Framework\AuthorizationInterface` and call `$this->authorization->isAllowed('Vendor_Module::resource')`

## Anti-Patterns to Avoid

- Do not use `ObjectManager` directly — use constructor injection or factories
- Do not override core templates by copying them — use layout XML to replace or extend
- Do not rewrite core classes with `<preference>` when a plugin achieves the same result
- Do not put business logic in Block classes — use ViewModels or Services
- Do not use `$_GET`, `$_POST`, or `$_SESSION` directly — use request/session abstractions
- Do not perform database queries in templates or Block `toHtml` methods
- Do not skip ACL checks in admin controllers — always implement `_isAllowed()`
