# PHP — code-review insights

Cross-project PHP style preferences — defer to the repo's formatter config or `CONVENTIONS.md` when they differ.

---

1. Flag aligned `=` signs across consecutive variable assignments. Each assignment must use a single space before `=`, regardless of variable name length.

```php
// Good
$order = 1;
$x = 1;

// Bad
$order = 1;
$x     = 1;
```
