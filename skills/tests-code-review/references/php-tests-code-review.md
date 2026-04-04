# PHP Test Code Review Reference (PHP 8.2–8.5, PHPUnit 11–12)

Supplements `test-review-checklist.md` for PHP 8.2–8.5 projects using PHPUnit 11 or 12. Framework-specific test review guides live in separate files.

> **PHPUnit note:** PHPUnit 10 is EOL (ended Feb 2025). Reviews should flag deprecated PHPUnit 10 patterns still present in test suites targeting PHPUnit 11/12.

---

## General PHP Test Review Patterns

### Review Points

#### ❌ Missing Return Types on Test Data Providers

```php
// Bad — no return type, no named keys
public function provideValidEmails(): array
{
    return [['user@example.com'], ['admin@test.org']];
}

// Good — typed return, named datasets, #[DataProvider] attribute
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

#### ❌ Using `@annotation` Instead of Attributes (PHPUnit 10+)

```php
// Bad — deprecated docblock annotations; removed or erroring in PHPUnit 11+
/** @dataProvider provideEmails */
public function testValidate(string $email): void { ... }

// Good — PHP 8.x native attributes
#[\PHPUnit\Framework\Attributes\DataProvider('provideEmails')]
#[\PHPUnit\Framework\Attributes\CoversMethod(\MyApp\Validator::class, 'validate')]
public function testValidate(string $email): void { ... }
```

#### ❌ Using `createMock()` When `createStub()` Is Appropriate (PHPUnit 11+)

`createMock()` is a strict mock that implicitly verifies call expectations. `createStub()` is a pure stub — it returns configured values with no verification. Using `createMock()` without expectations misleads readers about test intent.

```php
// Bad — createMock() with no expectation
$logger = $this->createMock(LoggerInterface::class);
$service = new OrderService($logger);
$service->processOrder($order);

// Good — createStub() makes intent explicit
$logger = $this->createStub(LoggerInterface::class);
$service = new OrderService($logger);
$service->processOrder($order);

// Good — createMock() only when asserting interaction IS the behaviour under test
$logger = $this->createMock(LoggerInterface::class);
$logger->expects($this->once())
    ->method('error')
    ->with($this->stringContains('payment failed'));
$service = new OrderService($logger);
$service->processOrder($failingOrder);
```

#### ❌ Unaddressed Deprecation Failures in Test Output (PHPUnit 11+)

PHPUnit 11+ treats `E_DEPRECATED` and `E_USER_DEPRECATED` as test failures by default. A suite that "passes" while emitting deprecation warnings gives false confidence — those deprecations will become fatal errors in a future PHP version.

```php
// Bad — passes under PHPUnit 10 but fails under 11+
public function testUserService(): void
{
    $result = (new UserService())->createUser($data);
    $this->assertNotNull($result->getId());
}

// Good — explicitly expect the deprecation while migration is in progress
public function testUserService(): void
{
    $this->expectUserDeprecationMessage('UserService::createUser() is deprecated, use createFromDto()');
    $result = (new UserService())->createUser($data);
    $this->assertNotNull($result->getId());
}
```

#### ❌ Broad `#[IgnoreDeprecations]` on Entire Test Class

Apply `#[IgnoreDeprecations]` at the method level with a documented justification. Class-level suppression silently swallows new deprecations as they appear.

```php
// Bad — blanket suppression; new deprecations pass undetected
#[\PHPUnit\Framework\Attributes\IgnoreDeprecations]
class UserServiceTest extends TestCase { }

// Good — method-level with reason and tracking reference
#[\PHPUnit\Framework\Attributes\IgnoreDeprecations]
public function testCompatibilityWithLegacyAdapter(): void
{
    // Suppressed: LegacyAdapter emits E_USER_DEPRECATED — tracked in #456, planned for Q3 removal
    $result = (new Service())->processViaLegacyAdapter();
    $this->assertNotNull($result);
}
```

#### ❌ Asserting on Wrong Level of Abstraction

```php
// Bad — one test covers too many concerns
public function testUserCreation(): void
{
    $user = $this->service->create(['name' => 'Alice', 'email' => 'alice@example.com']);
    $this->assertNotNull($user->getId());
    $this->assertEquals('Alice', $user->getName());
    $this->assertDatabaseHas('users', ['email' => 'alice@example.com']);
    $this->assertEmailSent('alice@example.com');
}

// Good — focused, one concern per test
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

#### ❌ Mocking the System Under Test

```php
// Bad — partial mock hides real behaviour
$service = $this->getMockBuilder(UserService::class)
    ->onlyMethods(['validateEmail'])->getMock();
$service->method('validateEmail')->willReturn(true);
$service->create($data);

// Good — mock only external dependencies
$repositoryMock = $this->createMock(UserRepositoryInterface::class);
$service        = new UserService($repositoryMock);
$service->create($data);
```

`getMockBuilder(...)->onlyMethods(...)` on the **system under test** is a red flag — always flag it.

#### ❌ Tests with Hidden Order Dependency

```php
// Bad — testB depends on state set by testA; fails when run in isolation
public function testA(): void { $this->cache->set('key', 'value'); }
public function testB(): void { $this->assertEquals('value', $this->cache->get('key')); }

// Good — each test sets up its own state
public function testCacheReturnsStoredValue(): void
{
    $this->cache->set('key', 'value');
    $this->assertEquals('value', $this->cache->get('key'));
}
```

#### ❌ Not Testing Exception Messages or Codes

```php
// Bad — only checks exception type
$this->expectException(\InvalidArgumentException::class);
$this->validator->validate('bad input');

// Good — verify diagnostic information
$this->expectException(\InvalidArgumentException::class);
$this->expectExceptionMessage('Email must not be empty');
$this->validator->validate('');
```

#### ❌ Not Using `#[TestWith]` for Simple Inline Data (PHPUnit 11+)

`#[TestWith]` is cleaner for small, self-contained invariant cases (2–5 entries). Use `#[DataProvider]` for dynamically generated data, named datasets that need clear failure labels, or more than ~5 cases.

```php
// Bad — separate provider for 3 trivial cases
#[\PHPUnit\Framework\Attributes\DataProvider('provideSums')]
public function testAdd(int $a, int $b, int $expected): void
{
    $this->assertSame($expected, $a + $b);
}
public static function provideSums(): array
{
    return [[0, 0, 0], [1, 0, 1], [1, 1, 2]];
}

// Good — inline for small invariant cases
#[\PHPUnit\Framework\Attributes\TestWith([0, 0, 0])]
#[\PHPUnit\Framework\Attributes\TestWith([1, 0, 1])]
#[\PHPUnit\Framework\Attributes\TestWith([1, 1, 2])]
public function testAdd(int $a, int $b, int $expected): void
{
    $this->assertSame($expected, $a + $b);
}
```

### Readonly Class Test Patterns (PHP 8.2+)

```php
readonly class Money
{
    public function __construct(
        public int    $amount,
        public string $currency,
    ) {}
}

class MoneyTest extends TestCase
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
        $money->amount = 2000;
    }
}
```

### Enum Test Patterns (PHP 8.1+)

```php
enum Status: string
{
    case Active   = 'active';
    case Inactive = 'inactive';
}

class StatusTest extends TestCase
{
    public function testFromValidValue(): void
    {
        $this->assertSame(Status::Active, Status::from('active'));
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

### Partial Mocking Anti-Pattern

```php
// Bad — onlyMethods() on the class under test
$service = $this->getMockBuilder(UserService::class)
    ->onlyMethods(['sendEmail'])->getMock();
$service->method('sendEmail')->willReturn(true);
$service->register($data);

// Good — extract behind an interface; mock that instead
$mailerMock = $this->createMock(MailerInterface::class);
$mailerMock->expects($this->once())->method('send');
$service = new UserService($mailerMock);
$service->register($data);
```

### Mutation Testing Awareness

When reviewing tests for completeness, ask: Do assertions actually fail if the logic is broken? High coverage with trivial or missing assertions is meaningless. Consider recommending `infection/infection` when line coverage is high but confidence in the suite is low.

```bash
vendor/bin/infection --min-msi=80
```

### Checklist for PHP Tests

- [ ] `#[DataProvider]` attribute used — not deprecated `@dataProvider` docblock (PHPUnit 10+)
- [ ] Data provider methods are `static` and return named datasets
- [ ] `createStub()` used for pure stubs — `createMock()` reserved for interaction-assertion tests (PHPUnit 11+)
- [ ] No `createMock()` without a corresponding `expects()` call — use `createStub()` instead
- [ ] `getMockBuilder()->onlyMethods()` not used on the class under test (partial mock anti-pattern)
- [ ] Tests are independent — no shared mutable state between test methods
- [ ] Each test asserts one logical concern
- [ ] Exception message and/or code verified with `expectExceptionMessage()` / `expectExceptionCode()`
- [ ] `tearDown()` resets any static/global state mutated in tests
- [ ] `readonly` classes tested for immutability enforcement (PHP 8.2+)
- [ ] Enum `from()` and `tryFrom()` both covered for backed enums (PHP 8.1+)
- [ ] Deprecation-emitting code handled with `expectUserDeprecationMessage()` or scoped `#[IgnoreDeprecations]` (PHPUnit 11+)
- [ ] `#[IgnoreDeprecations]` applied at method level only — not blanket on the entire class
- [ ] `#[\NoDiscard]` return values captured and asserted — not silently ignored (PHP 8.5+)
- [ ] `array_first()` / `array_last()` used in test assertions — not `reset()` / `end()` (PHP 8.5+)
- [ ] `#[TestWith]` used for 2–5 simple inline cases — `#[DataProvider]` for larger/named/generated sets (PHPUnit 11+)
- [ ] `createMockForIntersectionOfInterfaces()` used for intersection type dependencies — not complex workarounds (PHPUnit 11+)

## PHP 8.5 Test Review Points

#### ❌ Not Asserting on `#[\NoDiscard]` Return Values

```php
// Bad — silently discards a #[\NoDiscard] return value
$validator->validate($input);

// Good — capture and assert
$result = $validator->validate($input);
$this->assertTrue($result->isValid());
```

#### ❌ Using `reset()` / `end()` Instead of `array_first()` / `array_last()`

```php
// Bad — reset()/end() mutate internal array pointer
$first = reset($items);

// Good — PHP 8.5+: side-effect free
$first = array_first($items);
```
