# Adobe Commerce (Magento 2) Code Review Checklist

Supplements the generic `review-checklist.md` and `php-review-checklist.md` for projects using Adobe Commerce / Magento 2 (AC 2.4.x).

> Covers Adobe Commerce / Magento 2 platform concerns only. PHP language best practices are covered in `php-review-checklist.md`.

---

## Security

- [ ] No hardcoded credentials, API keys, or secrets — use `app/etc/env.php` or environment variables
- [ ] User input escaped before output — use `$escaper->escapeHtml()`, `escapeUrl()`, `escapeJs()` in templates
- [ ] No raw SQL string concatenation — use `$connection->select()` or resource model queries with bind parameters
- [ ] ACL resources defined in `etc/acl.xml` and enforced on Admin controllers (`_isAllowed()`)
- [ ] Frontend controllers validate form keys (`validateFormKey()`) to prevent CSRF
- [ ] REST API endpoints have proper `<resources>` configured in `etc/webapi.xml`
- [ ] Custom REST endpoints verify ownership of resources — IDOR risk if any customer can access another's data
- [ ] `setData()` called only with validated, explicit data — not with raw user-supplied arrays
- [ ] Sensitive data not exposed in logs, error messages, or API responses
- [ ] File uploads validated for type, size, and path traversal

---

## Performance

- [ ] Collections use `addFieldToSelect()` with specific fields — avoid loading full objects when not needed
- [ ] Repository API preferred over direct collection loading for service layer calls
- [ ] No N+1 query patterns in loops over collections — use `join()` or `addAttributeToFilter()` upfront
- [ ] Caching used for expensive, rarely changing data (`\Magento\Framework\App\CacheInterface`)
- [ ] Full Page Cache (FPC) compatibility maintained: no session/cookie reads in cacheable blocks
- [ ] Block `getCacheLifetime()` configured correctly — not returning `null` unintentionally
- [ ] Heavy operations offloaded to cron jobs or message queue consumers
- [ ] EAV attribute loads batched where possible — avoid per-entity `load()` calls in loops

---

## Architecture & Design

- [ ] Module follows Magento 2 file structure: `registration.php`, `etc/module.xml`, proper namespace
- [ ] Dependency Injection used exclusively — no `ObjectManager::getInstance()` outside factories/proxies/tests
- [ ] New constructor parameters are optional with defaults (or added in a new class) — adding required parameters breaks third-party extensions
- [ ] `Proxy` injection used for heavy or circular dependencies — not for every dependency
- [ ] Service contracts defined (interfaces in `Api/`) and implemented — no direct model dependencies across modules
- [ ] Public interfaces in `Api/` directory have the `@api` annotation to signal stability
- [ ] Plugins (`etc/di.xml` interceptors) used instead of class rewrites/overrides where possible
- [ ] Events used for cross-module communication — observer registered in `etc/events.xml`
- [ ] No circular module dependencies
- [ ] Declarative schema (`etc/db_schema.xml`) used for all table changes — no `InstallSchema`/`UpgradeSchema`
- [ ] Data patches (`Setup/Patch/Data/`) used for data migrations — not `UpgradeData`
- [ ] UI Components and layout XML follow convention — no inline PHP in `.phtml` templates
- [ ] `etc/module.xml` sequence declarations correct for dependency ordering

---

## Adobe Commerce Best Practices

- [ ] `etc/di.xml` preferences and plugins have correct `sortOrder` to avoid conflicts
- [ ] Around plugins used only when before/after is insufficient — they are expensive interceptors
- [ ] Cron schedule defined in `etc/crontab.xml` and cron groups configured correctly
- [ ] Message queue consumers defined in `etc/queue_consumer.xml` with correct connection
- [ ] Admin grids use `etc/ui_component/` XML — no legacy grid block rewrites
- [ ] Customer and sales data access goes through service contracts — not raw model loads
- [ ] `\Magento\Framework\Exception\*` types thrown from service layer (not generic `\Exception`)
- [ ] GraphQL resolvers implement `ResolverInterface` and handle authorization via context
- [ ] Layout handles used correctly — no `default.xml` pollution for module-specific layouts
- [ ] Store-scoped configuration read via `ScopeConfigInterface` — not directly from `env.php`
- [ ] For projects using Hyva theme (Tailwind/Alpine.js): UI components built with Knockout.js/RequireJS are flagged as incompatible with the Hyva frontend

---

## Documentation

- [ ] Public interfaces and service contract methods have PHPDoc blocks
- [ ] Complex business logic has inline comments explaining the "why"
- [ ] `README.md` or module `docs/` updated if public API changes

---

## Resources

- [Adobe Commerce Developer Documentation](https://developer.adobe.com/commerce/docs/)
- [Magento 2 Coding Standards](https://developer.adobe.com/commerce/php/coding-standards/)
- [Service Contracts](https://developer.adobe.com/commerce/php/development/components/service-contracts/)
- [Plugins (Interceptors)](https://developer.adobe.com/commerce/php/development/components/plugins/)
- [Declarative Schema](https://developer.adobe.com/commerce/php/development/components/declarative-schema/)
- [Dependency Injection](https://developer.adobe.com/commerce/php/development/components/dependency-injection/)
- [Adobe Commerce Security Best Practices](https://experienceleague.adobe.com/docs/commerce-operations/security-and-compliance/overview.html)
