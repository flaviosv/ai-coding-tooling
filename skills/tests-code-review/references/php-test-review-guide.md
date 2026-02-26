# PHP Test Code Review Guide (8.2+)

Supplements `test-review-checklist.md` for PHP 8.2+ projects using PHPUnit. Framework-specific test review guides live in separate files.

---

## Review Points

### ❌ Missing Return Types on Test Data Providers

```php
// Bad — no type on data provider return
public function provideValidEmails(): array
{
    return [['user@example.com'], ['admin@test.org']];
}

// Good — typed return and #[DataProvider] attribute (PHPUnit 10+)
#[\PHPUnit\Framework\Attributes\DataProvider('provideValidEmails')]
public function testValidEmailPasses(string $email): void { ... }

public static function provideValidEmails(): array
{
    return [
        'standard email' => ['user@example.com'],
        'admin email'    => ['admin@test.org'],
    ];
}
```

### ❌ Using `@annotation` Instead of Attributes (PHPUnit 10+)

```php
// Bad — deprecated docblock annotations
/**
 * @dataProvider provideEmails
 * @covers \MyApp\Validator::validate
 */
public function testValidate(string $email): void { ... }

// Good — PHP 8.x attributes
#[\PHPUnit\Framework\Attributes\DataProvider('provideEmails')]
#[\PHPUnit\Framework\Attributes\CoversMethod(\MyApp\Validator::class, 'validate')]
public function testValidate(string $email): void { ... }
```

### ❌ Asserting on Wrong Level of Abstraction

```php
// Bad — testing too many things at once
public function testUserCreation(): void
{
    $user = $this->service->create(['name' => 'Alice', 'email' => 'alice@example.com']);
    $this->assertNotNull($user->getId());
    $this->assertEquals('Alice', $user->getName());
    $this->assertEquals('alice@example.com', $user->getEmail());
    $this->assertNotNull($user->getCreatedAt());
    $this->assertDatabaseHas('users', ['email' => 'alice@example.com']); // integration concern
    $this->assertEmailSent('alice@example.com');                         // side effect concern
}

// Good — focused test per concern
public function testCreateReturnsUserWithAssignedId(): void
{
    $user = $this->service->create(['name' => 'Alice', 'email' => 'alice@example.com']);
    $this->assertNotNull($user->getId());
}

public function testCreateSendsWelcomeEmail(): void
{
    $this->mailerMock->expects($this->once())->method('send');
    $this->service->create(['name' => 'Alice', 'email' => 'alice@example.com']);
}
```

### ❌ Mocking the System Under Test

```php
// Bad — partial mock of the class being tested hides real behaviour
$service = $this->getMockBuilder(UserService::class)
    ->onlyMethods(['validateEmail'])
    ->getMock();
$service->method('validateEmail')->willReturn(true);
$service->create($data); // testing a mock, not the real class

// Good — mock only external dependencies
$repositoryMock = $this->createMock(UserRepositoryInterface::class);
$service = new UserService($repositoryMock);
$service->create($data);
```

### ❌ Tests with Hidden Order Dependency

```php
// Bad — testB depends on state set by testA
public function testA(): void
{
    $this->cache->set('key', 'value');
}

public function testB(): void
{
    $this->assertEquals('value', $this->cache->get('key')); // fails if testA runs first
}

// Good — each test sets up its own state
public function testCacheReturnsStoredValue(): void
{
    $this->cache->set('key', 'value');
    $this->assertEquals('value', $this->cache->get('key'));
}
```

### ❌ Not Testing Exception Messages / Codes

```php
// Bad — only checks the exception type
$this->expectException(\InvalidArgumentException::class);
$this->validator->validate('bad input');

// Good — verify the exception carries useful info
$this->expectException(\InvalidArgumentException::class);
$this->expectExceptionMessage('Email must not be empty');
$this->validator->validate('');
```

---

## Readonly Class Test Patterns (PHP 8.2+)

```php
readonly class Money
{
    public function __construct(
        public int $amount,
        public string $currency,
    ) {}
}

class MoneyTest extends \PHPUnit\Framework\TestCase
{
    public function testConstructorSetsFields(): void
    {
        $money = new Money(1000, 'USD');
        $this->assertSame(1000, $money->amount);
        $this->assertSame('USD', $money->currency);
    }

    public function testReadonlyPropertyCannotBeModified(): void
    {
        $money = new Money(1000, 'USD');
        $this->expectException(\Error::class);
        $money->amount = 2000; // readonly violation
    }
}
```

---

## Enum Test Patterns (PHP 8.1+)

```php
enum Status: string
{
    case Active   = 'active';
    case Inactive = 'inactive';
}

class StatusTest extends \PHPUnit\Framework\TestCase
{
    public function testFromValidValue(): void
    {
        $status = Status::from('active');
        $this->assertSame(Status::Active, $status);
    }

    public function testFromInvalidValueThrows(): void
    {
        $this->expectException(\ValueError::class);
        Status::from('unknown');
    }

    public function testTryFromReturnsNullOnInvalidValue(): void
    {
        $this->assertNull(Status::tryFrom('unknown'));
    }
}
```

---

## Partial Mocking Anti-Pattern

```php
// Bad — getMockBuilder with onlyMethods on the class under test hides real behaviour
$service = $this->getMockBuilder(UserService::class)
    ->onlyMethods(['sendEmail'])
    ->getMock();
$service->method('sendEmail')->willReturn(true);
$service->register($data); // testing a partial mock, not the real class

// Good — extract email sending behind an interface; mock that instead
$mailerMock = $this->createMock(MailerInterface::class);
$mailerMock->expects($this->once())->method('send');
$service = new UserService($mailerMock);
$service->register($data);
```

Reviewing `getMockBuilder(...)->onlyMethods(...)` on the **system under test** is a red flag.

---

## Mutation Testing Awareness

When reviewing tests for completeness, ask:
- Do the assertions actually fail if the logic is broken? High line coverage with trivial assertions (e.g. `$this->assertTrue(true)`) is meaningless.
- Consider recommending `infection/infection` if coverage is high but confidence is low.

```bash
# Run mutation testing and check MSI score
vendor/bin/infection --min-msi=80
```

---

## Checklist for PHP Tests

- [ ] `#[DataProvider]` attribute used — not deprecated `@dataProvider` docblock (PHPUnit 10+)
- [ ] Data provider methods are `static` and return named datasets
- [ ] Only external dependencies are mocked — not the class under test
- [ ] `getMockBuilder()->onlyMethods()` not used on the class under test (partial mock anti-pattern)
- [ ] Tests are independent — no shared mutable state between test methods
- [ ] Each test asserts one logical concern
- [ ] Exception message and/or code verified with `expectExceptionMessage()` / `expectExceptionCode()`
- [ ] `tearDown()` resets any static/global state mutated in tests
- [ ] `readonly` classes tested for immutability enforcement
- [ ] Enum `from()` and `tryFrom()` both covered for backed enums
- [ ] Fibers tested by driving the fiber manually through suspend/resume cycles
- [ ] `#[\NoDiscard]` return values are captured and asserted — not silently ignored
- [ ] `array_first()` / `array_last()` used in test assertions — not `reset()` / `end()`

---

## PHP 8.5 Test Review Points

### ❌ Not Asserting on `#[\NoDiscard]` Return Values

```php
// Bad — silently discards a return value marked #[\NoDiscard]
// This will emit a warning at runtime
$validator->validate($input); // return value not captured

// Good — capture or explicitly acknowledge the result
$result = $validator->validate($input);
$this->assertTrue($result->isValid());
```

### ❌ Using `reset()` / `end()` Instead of `array_first()` / `array_last()`

```php
// Bad — mutates internal array pointer, subtle in test assertions
$first = reset($items);

// Good — PHP 8.5+: side-effect free
$first = array_first($items);
```

---

## Resources

- [PHPUnit Documentation](https://docs.phpunit.de/)
- [PHPUnit 10 Migration Guide](https://phpunit.de/announcements/phpunit-10.html)
- [PHP 8.2 readonly classes](https://www.php.net/releases/8.2/en.php)
- [PHP 8.5 Release Notes](https://www.php.net/releases/8.5/en.php)
- [PHP Enums](https://www.php.net/manual/en/language.enumerations.php)
- [PHP Fibers](https://www.php.net/manual/en/language.fibers.php)
