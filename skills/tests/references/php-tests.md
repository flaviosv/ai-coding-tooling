# PHP Testing Guide (8.2+, PHPUnit 10+)

Applies to: PHP 8.2+ projects using PHPUnit 10+. Framework-specific testing guides live in separate files.

---

## Setup

Install PHPUnit and configure:

```bash
composer require --dev phpunit/phpunit
```

`phpunit.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
         bootstrap="vendor/autoload.php"
         colors="true">
    <testsuites>
        <testsuite name="Unit">
            <directory>tests/Unit</directory>
        </testsuite>
        <testsuite name="Integration">
            <directory>tests/Integration</directory>
        </testsuite>
    </testsuites>
    <source>
        <include>
            <directory>src</directory>
        </include>
    </source>
</phpunit>
```

---

## Unit Tests

### Constructor Injection

```php
// tests/Unit/Service/InvoiceServiceTest.php
namespace Tests\Unit\Service;

use App\Service\InvoiceService;
use App\Repository\InvoiceRepositoryInterface;
use App\Model\Invoice;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;

class InvoiceServiceTest extends TestCase
{
    private InvoiceService $service;
    private InvoiceRepositoryInterface&MockObject $repository;

    protected function setUp(): void
    {
        $this->repository = $this->createMock(InvoiceRepositoryInterface::class);
        $this->service = new InvoiceService($this->repository);
    }

    public function testCreateSavesInvoice(): void
    {
        $this->repository->expects($this->once())->method('save');
        $this->service->create(['amount' => 1000, 'currency' => 'USD']);
    }

    public function testCreateThrowsWhenRepositoryFails(): void
    {
        $this->repository->method('save')
            ->willThrowException(new \RuntimeException('DB error'));

        $this->expectException(\RuntimeException::class);
        $this->service->create(['amount' => 1000, 'currency' => 'USD']);
    }
}
```

### Data Providers (PHPUnit 10+ Attribute Style)

```php
class EmailValidatorTest extends TestCase
{
    #[\PHPUnit\Framework\Attributes\DataProvider('provideValidEmails')]
    public function testValidEmailPasses(string $email): void
    {
        $validator = new EmailValidator();
        $this->assertTrue($validator->isValid($email));
    }

    #[\PHPUnit\Framework\Attributes\DataProvider('provideInvalidEmails')]
    public function testInvalidEmailFails(string $email): void
    {
        $validator = new EmailValidator();
        $this->assertFalse($validator->isValid($email));
    }

    public static function provideValidEmails(): array
    {
        return [
            'standard'       => ['user@example.com'],
            'subdomain'      => ['user@mail.example.com'],
            'plus-addressing'=> ['user+tag@example.com'],
        ];
    }

    public static function provideInvalidEmails(): array
    {
        return [
            'empty string' => [''],
            'no at sign'   => ['userexample.com'],
            'no domain'    => ['user@'],
        ];
    }
}
```

---

## Testing Readonly Classes (PHP 8.2+)

```php
readonly class Address
{
    public function __construct(
        public string $street,
        public string $city,
        public string $country,
    ) {}

    public function withCity(string $city): self
    {
        return new self($this->street, $city, $this->country);
    }
}

class AddressTest extends TestCase
{
    public function testWithCityReturnsNewInstance(): void
    {
        $original = new Address('Main St', 'London', 'GB');
        $updated  = $original->withCity('Manchester');

        $this->assertNotSame($original, $updated);
        $this->assertSame('London', $original->city);     // original unchanged
        $this->assertSame('Manchester', $updated->city);
    }

    public function testPropertiesAreImmutable(): void
    {
        $address = new Address('Main St', 'London', 'GB');
        $this->expectException(\Error::class);
        $address->city = 'Paris'; // readonly violation
    }
}
```

---

## Testing Enums (PHP 8.1+)

```php
enum Priority: int
{
    case Low    = 1;
    case Medium = 5;
    case High   = 10;

    public function label(): string
    {
        return match ($this) {
            Priority::Low    => 'Low Priority',
            Priority::Medium => 'Medium Priority',
            Priority::High   => 'High Priority',
        };
    }
}

class PriorityTest extends TestCase
{
    public function testFromValidValue(): void
    {
        $this->assertSame(Priority::High, Priority::from(10));
    }

    public function testFromInvalidValueThrows(): void
    {
        $this->expectException(\ValueError::class);
        Priority::from(99);
    }

    public function testTryFromReturnsNull(): void
    {
        $this->assertNull(Priority::tryFrom(99));
    }

    public function testLabelReturnsCorrectString(): void
    {
        $this->assertSame('High Priority', Priority::High->label());
    }
}
```

---

## Testing Fibers (PHP 8.1+)

```php
class FiberTest extends TestCase
{
    public function testFiberSuspendsAndResumes(): void
    {
        $fiber = new \Fiber(function (): string {
            $input = \Fiber::suspend('waiting');
            return "got: $input";
        });

        $suspended = $fiber->start();
        $this->assertSame('waiting', $suspended);

        $result = $fiber->resume('hello');
        $this->assertTrue($fiber->isTerminated());
        $this->assertSame('got: hello', $fiber->getReturn());
    }
}
```

---

## Testing with Property Hooks (PHP 8.4+)

```php
class Temperature
{
    public float $celsius {
        set (float $value) {
            if ($value < -273.15) {
                throw new \InvalidArgumentException('Below absolute zero');
            }
            $this->celsius = $value;
        }
    }
}

class TemperatureTest extends TestCase
{
    public function testValidTemperatureSet(): void
    {
        $t = new Temperature();
        $t->celsius = 20.0;
        $this->assertSame(20.0, $t->celsius);
    }

    public function testBelowAbsoluteZeroThrows(): void
    {
        $t = new Temperature();
        $this->expectException(\InvalidArgumentException::class);
        $this->expectExceptionMessage('Below absolute zero');
        $t->celsius = -300.0;
    }
}
```

---

## Exception Testing

```php
public function testThrowsWithCorrectMessage(): void
{
    $this->expectException(\InvalidArgumentException::class);
    $this->expectExceptionMessage('Email must not be empty');
    $this->expectExceptionCode(422);

    (new EmailValidator())->validate('');
}
```

---

## setUp vs setUpBeforeClass

- `setUp()` — runs before **each** test method. Use for per-test mocks and fresh objects.
- `setUpBeforeClass()` — runs **once** per class, before any test runs. Use only for truly shared, expensive, read-only resources (e.g. a static in-memory fixture, a one-time DB schema creation).

```php
class InvoiceServiceTest extends TestCase
{
    // Per-test setup — new mock for every test
    protected function setUp(): void
    {
        $this->repository = $this->createMock(InvoiceRepositoryInterface::class);
        $this->service = new InvoiceService($this->repository);
    }

    // Once per class — use sparingly, only for read-only shared state
    public static function setUpBeforeClass(): void
    {
        parent::setUpBeforeClass();
        // e.g. load a large static fixture file once
    }
}
```

Avoid `setUpBeforeClass()` for mutable objects — shared state causes test-order coupling.

---

## Mocking Final Classes

PHPUnit cannot mock `final` classes by default. Use one of:

1. **`dg/bypass-finals`** (most common) — patches the classloader to remove `final` during tests:

```bash
composer require --dev dg/bypass-finals
```

```php
// bootstrap.php (or phpunit.xml bootstrap)
\DG\BypassFinals::enable();
```

2. **Wrapper / interface** — preferred when you own the code. Introduce an interface and mock the interface instead of the final class.

---

## Integration Tests with Real Database

```php
// tests/Integration/Repository/InvoiceRepositoryTest.php
namespace Tests\Integration\Repository;

use App\Repository\InvoiceRepository;
use PHPUnit\Framework\TestCase;

class InvoiceRepositoryTest extends TestCase
{
    private \PDO $pdo;
    private InvoiceRepository $repository;

    protected function setUp(): void
    {
        $this->pdo = new \PDO(
            'mysql:host=' . getenv('TEST_DB_HOST') . ';dbname=' . getenv('TEST_DB_NAME'),
            getenv('TEST_DB_USER'),
            getenv('TEST_DB_PASS'),
            [\PDO::ATTR_ERRMODE => \PDO::ERRMODE_EXCEPTION]
        );
        $this->pdo->beginTransaction(); // each test runs in its own transaction
        $this->repository = new InvoiceRepository($this->pdo);
    }

    protected function tearDown(): void
    {
        $this->pdo->rollBack(); // always rolls back — leaves DB clean
    }

    public function testSaveAndFindById(): void
    {
        $id = $this->repository->save(['amount' => 1000, 'currency' => 'USD']);
        $invoice = $this->repository->findById($id);
        $this->assertSame(1000, $invoice['amount']);
    }
}
```

Skip integration tests when the environment is unavailable:

```php
protected function setUp(): void
{
    if (!getenv('TEST_DB_HOST')) {
        $this->markTestSkipped('Integration DB not configured');
    }
    // ...
}
```

---

## Mutation Testing

[infection/infection](https://infection.github.io/) runs your test suite against mutated code to find assertions that pass even when logic is broken:

```bash
composer require --dev infection/infection
vendor/bin/infection --min-msi=80 --min-covered-msi=90
```

Key metrics:
- **MSI** (Mutation Score Indicator) — percentage of mutants killed by tests.
- **Covered MSI** — MSI restricted to code your tests actually execute.

A high line coverage with a low MSI score reveals tests that execute code without meaningfully asserting on it.

---

## Test Organization

```
tests/
├── Unit/
│   ├── Service/
│   ├── Model/
│   └── Validator/
├── Integration/
│   ├── Repository/
│   └── Api/
└── bootstrap.php
```

- Unit tests: pure logic, no I/O, no DB, all dependencies mocked.
- Integration tests: real DB, real filesystem — use test doubles only for external services.

---

## Running Tests

```bash
# All tests
vendor/bin/phpunit

# Specific suite
vendor/bin/phpunit --testsuite Unit

# Specific file
vendor/bin/phpunit tests/Unit/Service/InvoiceServiceTest.php

# With coverage (requires Xdebug or PCOV)
XDEBUG_MODE=coverage vendor/bin/phpunit --coverage-html coverage/
```

---

## PHP 8.5 Testing Patterns

### Testing Pipe Operator Chains

```php
// Pipe chains are just composed functions — test the chain's output directly
class SlugifierTest extends TestCase
{
    public function testSlugify(): void
    {
        $slugify = fn(string $s): string => $s
            |> trim(...)
            |> strtolower(...)
            |> (fn($s) => str_replace(' ', '-', $s));

        $this->assertSame('hello-world', $slugify('  Hello World  '));
    }
}
```

### Testing Clone-With (PHP 8.5+)

```php
readonly class Order
{
    public function __construct(
        public string $id,
        public string $status,
    ) {}
}

class CloneWithTest extends TestCase
{
    public function testCloneWithChangesStatus(): void
    {
        $original = new Order('ord-1', 'pending');
        $updated  = clone($original, ['status' => 'shipped']);

        $this->assertSame('pending', $original->status); // original unchanged
        $this->assertSame('shipped', $updated->status);
        $this->assertSame('ord-1', $updated->id);         // other fields preserved
    }
}
```

### Testing #[\NoDiscard] Methods

```php
#[\NoDiscard('Result must be checked')]
public function validate(string $input): ValidationResult { ... }

// Test that the method's return value is used meaningfully
class ValidatorTest extends TestCase
{
    public function testValidReturnsSuccessResult(): void
    {
        $result = (new Validator())->validate('valid@example.com');
        $this->assertTrue($result->isValid());
    }

    public function testInvalidReturnsFailureResult(): void
    {
        $result = (new Validator())->validate('');
        $this->assertFalse($result->isValid());
        $this->assertNotEmpty($result->errors());
    }
}
```

### Testing URI Parsing (PHP 8.5+)

```php
use Uri\Rfc3986\Uri;

class UriParserTest extends TestCase
{
    public function testExtractsHost(): void
    {
        $uri = new Uri('https://example.com/path?q=1');
        $this->assertSame('example.com', $uri->getHost());
    }

    public function testInvalidUriThrows(): void
    {
        $this->expectException(\Uri\InvalidUriException::class);
        new Uri('not a uri');
    }
}
```

---

## Resources

- [PHPUnit Documentation](https://docs.phpunit.de/)
- [PHPUnit 10 Migration Guide](https://phpunit.de/announcements/phpunit-10.html)
- [PHP 8.2 Release Notes](https://www.php.net/releases/8.2/en.php)
- [PHP 8.4 Property Hooks](https://www.php.net/releases/8.4/en.php)
- [PHP 8.5 Release Notes](https://www.php.net/releases/8.5/en.php)
- [PHP Enums](https://www.php.net/manual/en/language.enumerations.php)
- [PHP Fibers](https://www.php.net/manual/en/language.fibers.php)
