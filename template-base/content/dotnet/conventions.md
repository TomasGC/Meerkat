## C# / .NET Conventions

### Naming

```csharp
// Classes, interfaces, enums, methods, properties: PascalCase
public class UserRepository { }
public interface IUserRepository { }
public enum UserRole { Admin, User }
public void GetUserById(int id) { }
public string FirstName { get; set; }

// Private fields: _camelCase
private readonly IUserRepository _repository;
private string _connectionString;

// Local variables, parameters: camelCase
var userId = 42;
void ProcessOrder(int orderId) { }

// Constants: PascalCase
public const int MaxRetryCount = 3;
```

### Async/Await

```csharp
// ✅ Good - Async suffix, return Task
public async Task<User> GetUserByIdAsync(int id)
{
    return await _repository.FindByIdAsync(id);
}

// ✅ Good - ConfigureAwait(false) in libraries
var user = await _repository.FindByIdAsync(id).ConfigureAwait(false);

// ❌ Bad - Blocking async calls
var user = _repository.FindByIdAsync(id).Result;
```

### Null Safety

```csharp
// Enable nullable reference types (in .csproj)
// <Nullable>enable</Nullable>

// ✅ Good - Null-conditional and coalescing
var name = user?.Name ?? "Unknown";

// ✅ Good - Guard clauses
public void Process(User user)
{
    ArgumentNullException.ThrowIfNull(user);
    // ...
}
```

### Immutability

```csharp
// ✅ Good - Record types for immutable data
public record User(int Id, string Name, string Email);

// ✅ Good - Init-only setters
public class Order
{
    public int Id { get; init; }
    public string Status { get; init; } = "Pending";
}
```

### LINQ

```csharp
// ✅ Good - Method syntax, avoid multiple enumerations
var activeUsers = users
    .Where(u => u.IsActive)
    .OrderBy(u => u.Name)
    .Select(u => new UserDto(u.Id, u.Name))
    .ToList();

// ❌ Bad - Multiple ToList() calls
var filtered = users.Where(u => u.IsActive).ToList();
var sorted = filtered.OrderBy(u => u.Name).ToList();
```

### Dependency Injection

```csharp
// ✅ Good - Constructor injection, readonly fields
public class OrderService
{
    private readonly IOrderRepository _repository;
    private readonly ILogger<OrderService> _logger;

    public OrderService(IOrderRepository repository, ILogger<OrderService> logger)
    {
        _repository = repository;
        _logger = logger;
    }
}
```

### Error Handling

```csharp
// ✅ Good - Specific exception types, structured logging
try
{
    await _repository.SaveAsync(order);
}
catch (DbUpdateConcurrencyException ex)
{
    _logger.LogWarning(ex, "Concurrency conflict for order {OrderId}", order.Id);
    throw new ConflictException($"Order {order.Id} was modified by another process");
}
```

### Testing

```csharp
[Fact]
public async Task CreateOrder_ShouldReturnCreatedOrder_WhenValid()
{
    // Arrange
    var request = new CreateOrderRequest { CustomerId = 1, Items = [] };
    _repositoryMock.Setup(r => r.SaveAsync(It.IsAny<Order>())).ReturnsAsync(new Order { Id = 1 });

    // Act
    var result = await _service.CreateOrderAsync(request);

    // Assert
    result.Id.Should().Be(1);
    _repositoryMock.Verify(r => r.SaveAsync(It.IsAny<Order>()), Times.Once);
}
```

---
