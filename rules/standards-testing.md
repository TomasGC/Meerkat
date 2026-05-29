---
paths:
  - "**/*test*.*"
  - "**/tests/**"
  - "**/*spec*.*"
  - "**/*.test.*"
  - "**/*.spec.*"
---

# Company Testing Standards

Testing requirements and best practices for all projects.

---

## Coverage Requirements

### Minimum Coverage
- **Overall**: 80% code coverage minimum
- **Critical paths**: 100% coverage required
  - Authentication/Authorization
  - Payment processing
  - Financial calculations
  - Security-sensitive operations
  - Data validation
- **New code**: Must include tests (no exceptions)

### Coverage Metrics
```bash
# .NET
dotnet test /p:CollectCoverage=true /p:CoverageReportFormat=cobertura

# Node.js
npm run test:coverage

# Go
go test ./... -coverprofile=coverage.out
go tool cover -html=coverage.out
```

---

## Test Types Required

### 1. Unit Tests
**Purpose**: Test individual functions/methods in isolation

**Coverage**: All business logic, services, utilities

```csharp
// Example - C#
[Fact]
public void CalculateTax_WithValidAmount_ReturnsCorrectTax()
{
    // Arrange
    var calculator = new TaxCalculator();
    var amount = 100m;

    // Act
    var tax = calculator.CalculateTax(amount, 0.20m);

    // Assert
    tax.Should().Be(20m);
}
```

### 2. Integration Tests
**Purpose**: Test interactions between components

**Coverage**:
- API endpoints with real HTTP requests
- Database operations with test database
- External service integrations (mocked)

```csharp
// Example - Integration test
[Fact]
public async Task CreateUser_WithValidData_ReturnsCreatedUser()
{
    // Arrange
    var client = _factory.CreateClient();
    var request = new CreateUserRequest { Email = "test@example.com" };

    // Act
    var response = await client.PostAsJsonAsync("/api/users", request);

    // Assert
    response.StatusCode.Should().Be(HttpStatusCode.Created);
}
```

### 3. E2E Tests
**Purpose**: Test complete user workflows

**Coverage**: Critical user journeys

```typescript
// Example - Cypress
it('should complete checkout process', () => {
  cy.visit('/products');
  cy.get('[data-testid="add-to-cart"]').first().click();
  cy.get('[data-testid="checkout-button"]').click();
  cy.get('[data-testid="payment-form"]').should('be.visible');
  // ... complete flow
});
```

---

## Test Structure

### AAA Pattern (Arrange-Act-Assert)
```csharp
// ✅ Good - Clear structure
[Fact]
public void ProcessPayment_WithInsufficientFunds_ThrowsException()
{
    // Arrange
    var account = new Account { Balance = 10 };
    var payment = new Payment { Amount = 100 };

    // Act
    Action act = () => account.ProcessPayment(payment);

    // Assert
    act.Should().Throw<InsufficientFundsException>();
}

// ❌ Bad - No clear structure
[Fact]
public void Test1()
{
    var account = new Account { Balance = 10 };
    Action act = () => account.ProcessPayment(new Payment { Amount = 100 });
    act.Should().Throw<InsufficientFundsException>();
}
```

### Test Naming
```csharp
// ✅ Good - Descriptive names
MethodName_StateUnderTest_ExpectedBehavior

CreateUser_WithDuplicateEmail_ThrowsException()
GetUser_WithValidId_ReturnsUser()
DeleteUser_WithInvalidId_ReturnsNotFound()

// ❌ Bad - Unclear names
Test1()
TestCreateUser()
UserTest()
```

---

## Test Independence

### Each Test Should Be Independent
```csharp
// ✅ Good - Independent tests
public class UserServiceTests : IDisposable
{
    private readonly DbContext _context;

    public UserServiceTests()
    {
        _context = CreateInMemoryDatabase();
    }

    [Fact]
    public void Test1() { }

    [Fact]
    public void Test2() { }

    public void Dispose()
    {
        _context.Dispose();
    }
}

// ❌ Bad - Tests depend on each other
private static User _sharedUser; // Shared state

[Fact]
public void Test1_CreateUser()
{
    _sharedUser = CreateUser(); // Sets state
}

[Fact]
public void Test2_UpdateUser()
{
    UpdateUser(_sharedUser); // Depends on Test1
}
```

---

## Test Data

### Use Test Builders/Factories
```csharp
// ✅ Good - Reusable test data
public class UserBuilder
{
    private string _email = "test@example.com";
    private string _name = "Test User";

    public UserBuilder WithEmail(string email)
    {
        _email = email;
        return this;
    }

    public User Build() => new User { Email = _email, Name = _name };
}

// Usage
var user = new UserBuilder()
    .WithEmail("specific@example.com")
    .Build();
```

### Use Realistic Test Data
```csharp
// ✅ Good - Realistic data
var email = "john.doe@company.com";
var amount = 99.99m;

// ❌ Bad - Unrealistic data
var email = "test@test.com";
var amount = 1m;
```

---

## Mocking Guidelines

### Prefer InMemory Over Mocks When Possible
```csharp
// ✅ Good - InMemory database
var options = new DbContextOptionsBuilder<AppDbContext>()
    .UseInMemoryDatabase("TestDb")
    .Options;
var context = new AppDbContext(options);

// ⚠️ OK - Mock when InMemory not available
var mockRepo = new Mock<IUserRepository>();
mockRepo.Setup(r => r.GetByIdAsync(1)).ReturnsAsync(user);
```

### Don't Over-Mock
```csharp
// ❌ Bad - Mocking too much
var mockLogger = new Mock<ILogger>();
var mockConfig = new Mock<IConfiguration>();
var mockMapper = new Mock<IMapper>();
// ... 10 more mocks

// ✅ Good - Use real lightweight objects
var logger = NullLogger.Instance;
var config = new ConfigurationBuilder().Build();
```

---

## Flaky Tests

### Avoid Non-Deterministic Tests
```csharp
// ❌ Bad - Time-dependent
[Fact]
public void Test()
{
    var now = DateTime.Now;
    Thread.Sleep(1000);
    Assert.True(DateTime.Now > now); // Can fail
}

// ✅ Good - Deterministic
[Fact]
public void Test()
{
    var clock = new TestClock(DateTime.Parse("2024-01-01"));
    var result = service.Process(clock.Now);
    Assert.NotNull(result);
}
```

### Avoid Race Conditions
```csharp
// ❌ Bad - Race condition
[Fact]
public async Task Test()
{
    var task1 = ProcessAsync();
    var task2 = ProcessAsync();
    // Race condition - order not guaranteed
}

// ✅ Good - Deterministic execution
[Fact]
public async Task Test()
{
    await ProcessAsync();
    await ProcessAsync();
}
```

---

## Performance Tests

### For High-Traffic Endpoints
```csharp
[Fact]
public async Task GetUsers_ShouldCompleteUnder200ms()
{
    // Arrange
    var stopwatch = Stopwatch.StartNew();

    // Act
    await _service.GetUsersAsync();

    // Assert
    stopwatch.ElapsedMilliseconds.Should().BeLessThan(200);
}
```

---

## Test Documentation

### Document Complex Test Scenarios
```csharp
/// <summary>
/// Tests the circuit breaker pattern when the payment gateway
/// returns 5 consecutive failures. The circuit should open and
/// subsequent requests should fail fast without calling the gateway.
/// </summary>
[Fact]
public async Task ProcessPayment_WithCircuitBreakerOpen_FailsFast()
{
    // Test implementation
}
```

---

## CI/CD Integration

### Tests Must Pass Before Merge
- ✅ All tests run automatically on PR
- ✅ No merge if tests fail
- ✅ Coverage reports generated and checked
- ❌ No bypassing test failures

---

**Testing is not optional. Every feature must have tests.**
