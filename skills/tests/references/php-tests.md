# PHP Testing Guide (PHP 8.2–8.5, PHPUnit 11–12)

Applies to: PHP 8.2–8.5 projects using PHPUnit 11 or 12. Framework-specific testing guides live in separate files.

---

> **PHPUnit versions:** PHPUnit 10 is EOL (ended Feb 2025). PHPUnit 11 requires PHP 8.2+ and is the minimum floor. PHPUnit 12 (Feb 2025) is the recommended version for new projects.

## General PHP Testing Patterns

### Setup

Install PHPUnit:

```bash
composer require --dev phpunit/phpunit:^12
```

`phpunit.xml` (PHPUnit 12):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
         bootstrap="vendor/autoload.php"
         colors="true"
         failOnDeprecation="true"
         failOnPhpunitDeprecation="true">
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
    <coverage>
        <report>
            <html outputDirectory="coverage/html"/>
            <text outputFile="php://stdout"/>
        </report>
    </coverage>
</phpunit>
```

Key PHPUnit 12 config attributes:
- `failOnDeprecation="true"` — treat `E_DEPRECATED` / `E_USER_DEPRECATED` as test failures (default in PHPUnit 11+)
- `failOnPhpunitDeprecation="true"` — treat internal PHPUnit deprecations as failures (surfaces migration issues early)

### Unit Tests

#### Constructor Injection

```php
// tests/Unit/Service/InvoiceServiceTest.php
namespace Tests\Unit\Service;
use App\Service\InvoiceService;
use App\Repository\InvoiceRepositoryInterface;
class InvoiceServiceTest extends TestCase
{
    private InvoiceService $service;
    private InvoiceRepositoryInterface&MockObject $repository;
    protected function setUp(): void
    {
        $this->repository = $this->createMock(InvoiceRepositoryInterface::class);
        $this->service    = new InvoiceService($this->repository);
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

### Test Doubles: Stubs vs Mocks (PHPUnit 11+)

PHPUnit 11 formalized the distinction between stubs and mocks. Use the right tool:

```php
// createStub() — pure stub: configures return values only, NO expectations on call count/args.
// Use when you only need a dependency to return something; you are NOT testing the interaction.
$stub = $this->createStub(LoggerInterface::class);
$stub->method('info')->willReturn(null);
$service = new OrderService($stub);
$service->process($order); // logging is a side-effect here; we are not asserting on it

// createMock() — strict mock: verifies that the expected call happens exactly as specified.
// Use when the interaction with the dependency IS what you are testing.
$mock = $this->createMock(MailerInterface::class);
$mock->expects($this->once())
    ->method('send')
    ->with($this->equalTo('user@example.com'));
$service = new RegistrationService($mock);
$service->register(['email' => 'user@example.com']); // asserts send() was called exactly once
```

#### Intersection Type Mocks

```php
// When the type hint is an intersection (UserRepositoryInterface&CacheableInterface),
// use createMockForIntersectionOfInterfaces()
$mock = $this->createMockForIntersectionOfInterfaces([
    UserRepositoryInterface::class,
    CacheableInterface::class,
]);
$mock->method('findById')->willReturn($user);
$mock->method('isCached')->willReturn(true);
```

### Data Providers

#### Named Data Provider Method (PHPUnit 10+)

```php
class EmailValidatorTest extends TestCase
{
    #[\PHPUnit\Framework\Attributes\DataProvider('provideValidEmails')]
    public function testValidEmailPasses(string $email): void
    {
        $this->assertTrue((new EmailValidator())->isValid($email));
    }
    #[\PHPUnit\Framework\Attributes\DataProvider('provideInvalidEmails')]
    public function testInvalidEmailFails(string $email): void
    {
        $this->assertFalse((new EmailValidator())->isValid($email));
    }
    public static function provideValidEmails(): array
    {
        return [
            'standard'        => ['user@example.com'],
            'subdomain'       => ['user@mail.example.com'],
            'plus-addressing' => ['user+tag@example.com'],
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

#### Inline Data with #[TestWith] (PHPUnit 11+)

For 2–5 simple cases where a separate provider method adds unnecessary overhead:

```php
use PHPUnit\Framework\Attributes\TestWith;
class MathTest extends TestCase
{
    #[TestWith([0, 0, 0])]
    #[TestWith([1, 0, 1])]
    #[TestWith([1, 1, 2])]
    #[TestWith([2, 3, 5])]
    public function testAdd(int $a, int $b, int $expected): void
    {
        $this->assertSame($expected, $a + $b);
    }
}
```

Use `#[DataProvider]` for large, named, or dynamically generated datasets. Use `#[TestWith]` for small, invariant inline cases.

### Testing Deprecated Code (PHPUnit 11+)

PHPUnit 11+ fails tests that emit `E_DEPRECATED` or `E_USER_DEPRECATED` by default. Three approaches:

#### 1. Expect the deprecation (preferred — explicitly documents the intent)

```php
public function testLegacyMethodEmitsDeprecation(): void
{
    $this->expectUserDeprecationMessage('Use newMethod() instead');
    (new LegacyService())->oldMethod();
}
```

#### 2. Suppress deprecations for a specific test (acceptable with justification)

```php
use PHPUnit\Framework\Attributes\IgnoreDeprecations;
#[IgnoreDeprecations]
public function testServiceWithLegacyAdapter(): void
{
    // Suppressed: ThirdPartyAdapter emits a deprecation — tracked in #456, migration planned Q3
    $result = (new Service())->processViaLegacyAdapter();
    $this->assertNotNull($result);
}
```

#### 3. Suppress for an entire class (use sparingly, document why)

```php
use PHPUnit\Framework\Attributes\IgnoreDeprecations;
#[IgnoreDeprecations]
class LegacyAdapterTest extends TestCase
{
    // All tests in this class suppress E_DEPRECATED failures
    // Reason: LegacyAdapter wraps a deprecated library pending replacement in v3.0
}
```

### Conditional Skipping by Version (PHPUnit 11+)

```php
use PHPUnit\Framework\Attributes\RequiresPhp;
use PHPUnit\Framework\Attributes\RequiresPhpunit;
class ArrayHelpersTest extends TestCase
{
    #[RequiresPhp('>= 8.5')]
    public function testArrayFirstReturnsFirstElement(): void
    {
        $this->assertSame(1, array_first([1, 2, 3]));
    }
    #[RequiresPhpunit('^12')]
    public function testFeatureRequiringPhpUnit12(): void
    {
        // This test is skipped on PHPUnit 11
    }
}
```

### Disabling the Error Handler (PHPUnit 12)

When testing code that sets its own error handler, use `#[WithoutErrorHandler]` to prevent PHPUnit's error handler from intercepting errors first:

```php
use PHPUnit\Framework\Attributes\WithoutErrorHandler;
class CustomErrorHandlerTest extends TestCase
{
    #[WithoutErrorHandler]
    public function testCustomHandlerReceivesTriggerError(): void
    {
        $received = null;
        set_error_handler(function (int $errno, string $errstr) use (&$received): bool {
            $received = $errstr;
            return true;
        });
        trigger_error('test error', E_USER_WARNING);
        restore_error_handler();
        $this->assertSame('test error', $received);
    }
}
```

### Testing Readonly Classes (PHP 8.2+)

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

### Testing Enums (PHP 8.1+)

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

### Testing Typed Class Constants (PHP 8.3+)

```php
class Config
{
    const int    MAX_RETRIES     = 3;
    const string DEFAULT_LOCALE  = 'en_GB';
}
class ConfigTest extends TestCase
{
    public function testMaxRetriesIsThree(): void
    {
        $this->assertSame(3, Config::MAX_RETRIES);
    }
    public function testDefaultLocaleIsEnGb(): void
    {
        $this->assertSame('en_GB', Config::DEFAULT_LOCALE);
    }
}
```

### Testing Property Hooks (PHP 8.4+)

```php
class Temperature
{
    public float $celsius {
        set(float $value) {
            if ($value < -273.15) {
                throw new \InvalidArgumentException('Below absolute zero');
            }
            $this->celsius = $value;
        }
    }
    // Virtual property — no backing field; computed on read
    public float $fahrenheit {
        get => $this->celsius * 9 / 5 + 32;
    }
}
class TemperatureTest extends TestCase
{
    public function testValidTemperatureSet(): void
    {
        $t = new Temperature();
        $t->celsius = 100.0;
        $this->assertSame(100.0, $t->celsius);
        $this->assertSame(212.0, $t->fahrenheit); // virtual property
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

### Testing Fibers (PHP 8.1+)

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
        $fiber->resume('hello');
        $this->assertTrue($fiber->isTerminated());
        $this->assertSame('got: hello', $fiber->getReturn());
    }
}
```

### Exception Testing

```php
public function testThrowsWithCorrectMessage(): void
{
    $this->expectException(\InvalidArgumentException::class);
    $this->expectExceptionMessage('Email must not be empty');
    $this->expectExceptionCode(422);
    (new EmailValidator())->validate('');
}
```

### setUp vs setUpBeforeClass

- `setUp()` — runs before **each** test method. Use for per-test mocks and fresh objects.
- `setUpBeforeClass()` — runs **once** per class. Use only for truly shared, expensive, read-only resources.

```php
class InvoiceServiceTest extends TestCase
{
    protected function setUp(): void
    {
        // Fresh mock for every test — no cross-test contamination
        $this->repository = $this->createMock(InvoiceRepositoryInterface::class);
        $this->service    = new InvoiceService($this->repository);
    }
    public static function setUpBeforeClass(): void
    {
        parent::setUpBeforeClass();
        // e.g. load a large static read-only fixture file once
    }
}
```

Avoid `setUpBeforeClass()` for mutable objects — shared state causes test-order coupling.

### Mocking Final Classes

PHPUnit cannot mock `final` classes by default. Two options:

1. **`dg/bypass-finals`** — patches the classloader to remove `final` during tests:

```bash
composer require --dev dg/bypass-finals
```

```php
// bootstrap.php (referenced in phpunit.xml)
\DG\BypassFinals::enable();
```

2. **Wrapper / interface** (preferred when you own the code) — introduce an interface and mock that instead of the final class.

### Integration Tests with Real Database

```php
// tests/Integration/Repository/InvoiceRepositoryTest.php
namespace Tests\Integration\Repository;
use App\Repository\InvoiceRepository;
class InvoiceRepositoryTest extends TestCase
{
    private \PDO $pdo;
    private InvoiceRepository $repository;
    protected function setUp(): void
    {
        if (!getenv('TEST_DB_HOST')) {
            $this->markTestSkipped('Integration DB not configured');
        }
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
        $id      = $this->repository->save(['amount' => 1000, 'currency' => 'USD']);
        $invoice = $this->repository->findById($id);
        $this->assertSame(1000, $invoice['amount']);
    }
}
```

### Mutation Testing

[infection/infection](https://infection.github.io/) runs your test suite against mutated code to reveal assertions that pass even when logic is broken:

```bash
composer require --dev infection/infection
vendor/bin/infection --min-msi=80 --min-covered-msi=90
```

- **MSI** (Mutation Score Indicator) — percentage of mutants killed by tests.
- **Covered MSI** — MSI restricted to code your tests actually execute.

High line coverage with low MSI reveals tests that execute code without meaningfully asserting on it.

### Test Organization

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

- **Unit tests**: pure logic, no I/O, no DB, all external dependencies stubbed/mocked.
- **Integration tests**: real DB, real filesystem — stub only external services.

### Running Tests

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

## PHP 8.5 Testing Patterns

### Testing Pipe Operator Chains

```php
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

### Testing #[\NoDiscard] Methods (PHP 8.5+)

```php
class ValidatorTest extends TestCase
{
    public function testValidReturnsSuccessResult(): void
    {
        // Capture the return value — discarding it would emit a notice at runtime
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
