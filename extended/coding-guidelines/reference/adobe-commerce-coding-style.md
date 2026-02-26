# PHP + Adobe Commerce (Magento 2) Coding Style Guide

> Load this file together with `php-coding-style.md`. Rules here are additive and Adobe Commerce-specific.

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

## Plugins (Interceptors)

- Use plugins for cross-cutting concerns (logging, caching, authorization) — not for business logic
- Prefer `around` plugins only when you need to control whether the original method runs; use `before`/`after` otherwise
- Keep plugins thin — delegate to a dedicated service class for logic
- Avoid plugin chains that are hard to trace — prefer observers for event-driven scenarios

## Events and Observers

- Dispatch events at meaningful extension points using `\Magento\Framework\Event\ManagerInterface`
- Name events in lowercase with underscores: `vendor_module_entity_save_after`
- Keep observers stateless — they must implement `\Magento\Framework\Event\ObserverInterface`
- Do not perform heavy operations in observers — queue heavy work via message queues

## Layout and Templates

- Define layout handles in `view/<area>/layout/` XML files
- Use `<referenceBlock>` and `<referenceContainer>` to extend existing layouts — never override unless necessary
- Use ViewModels to pass data to templates — not Block methods that perform business logic
- Templates must be `.phtml` files with minimal PHP — no business logic in templates
- Escape all output with `$block->escapeHtml()`, `$block->escapeUrl()`, etc. — never print raw user input

## Data Management and Upgrades

- Use Declarative Schema (`etc/db_schema.xml`) for all schema changes — not `InstallSchema`/`UpgradeSchema`
- Use data patches (`Setup/Patch/Data/`) for data migrations — one patch per logical change
- Mark patches with `PatchVersionInterface` when order matters
- Never modify core database tables directly — use extension attributes or separate tables

## Caching

- Tag all custom cache entries with a module-specific cache tag for granular invalidation
- Implement `IdentityInterface` on blocks and ViewModels that have cacheable output
- Use `\Magento\Framework\Cache\FrontendInterface` for custom cache — not raw `Zend_Cache`

## Anti-Patterns to Avoid

- Do not use `ObjectManager` directly — use constructor injection or factories
- Do not override core templates by copying them — use layout XML to replace or extend
- Do not rewrite core classes with `<preference>` when a plugin achieves the same result
- Do not put business logic in Block classes — use ViewModels or Services
- Do not use `$_GET`, `$_POST`, or `$_SESSION` directly — use request/session abstractions
- Do not perform database queries in templates or Block `toHtml` methods
- Do not skip ACL checks in admin controllers — always implement `_isAllowed()`
