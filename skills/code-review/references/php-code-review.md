# PHP — code-review insights

Project-specific patterns and conventions.

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
