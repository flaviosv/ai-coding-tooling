# PHP — coding-guidelines insights

Project-specific patterns and conventions.

---

1. Do NOT align `=` signs across consecutive variable assignments. Use a single space before `=` regardless of variable name length.

```php
// Good
$order = 1;
$x = 1;

// Bad
$order = 1;
$x     = 1;
```
