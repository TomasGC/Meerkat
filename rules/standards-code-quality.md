---
paths:
  - "**/*.*"
---

# Company Code Quality Standards

Universal code quality principles applying to ALL programming languages.

---

## Core Principles

### DRY (Don't Repeat Yourself)
- ❌ No code duplication
- ✅ Extract common logic into reusable functions/methods
- ✅ Use inheritance or composition for shared behavior

### SOLID Principles
1. **Single Responsibility**: One class/function = one reason to change
2. **Open-Closed**: Open for extension, closed for modification
3. **Liskov Substitution**: Derived classes must be substitutable for base classes
4. **Interface Segregation**: Many specific interfaces > one general interface
5. **Dependency Inversion**: Depend on abstractions, not concretions

### KISS (Keep It Simple, Stupid)
- ✅ Prefer simple solutions over complex ones
- ❌ Avoid over-engineering
- ✅ Code should be self-explanatory

### YAGNI (You Aren't Gonna Need It)
- ❌ Don't add functionality until it's needed
- ✅ Focus on current requirements
- ❌ Avoid speculative generality

---

## Code Standards

### No Hardcoded Values
```csharp
// ❌ Bad - Hardcoded values
if (status == 3) { }
var url = "https://api.example.com";

// ✅ Good - Constants or configuration
if (status == PaymentStatus.Completed) { }
var url = _configuration["ApiUrl"];
```

### No Magic Numbers/Strings
```typescript
// ❌ Bad
if (user.age > 18) { }

// ✅ Good
const LEGAL_AGE = 18;
if (user.age > LEGAL_AGE) { }
```

### Strong Typing
```typescript
// ❌ Bad - Using any
function process(data: any): any { }

// ✅ Good - Proper types
function process(data: User): Result { }
```

```csharp
// ❌ Bad - Stringly-typed
void ProcessAction(string action) { }

// ✅ Good - Enum
void ProcessAction(PaymentAction action) { }
```

### No TODO/FIXME Comments
```csharp
// ❌ Bad - TODO in code
// TODO: Fix this later
public void ProcessPayment() { }

// ✅ Good - Create a tracked task (GITHUB, Azure DevOps)
// Task #1234: Implement error handling
public void ProcessPayment() { }
```

---

## File Organization

### One Class/Interface/Enum Per File
```
✅ Good:
- User.cs
- IUserRepository.cs
- UserRole.cs (enum)

❌ Bad:
- Models.cs (contains User, Order, Payment classes)
```

### Meaningful File Names
- ✅ File name matches primary class name
- ✅ Descriptive names (UserService.cs, AlertManager.ts)
- ❌ Generic names (Helper.cs, Utils.ts)

---

## Code Clarity

### Self-Documenting Code
```csharp
// ✅ Good - Clear naming
public decimal CalculateTotalWithTax(decimal amount, decimal taxRate)
{
    return amount * (1 + taxRate);
}

// ❌ Bad - Unclear naming
public decimal Calc(decimal a, decimal b)
{
    return a * (1 + b);
}
```

### Comments for WHY, Not WHAT
```csharp
// ❌ Bad - Explains WHAT (obvious from code)
// Increment counter by 1
counter++;

// ✅ Good - Explains WHY
// Retry count must be incremented before checking limit
// to avoid off-by-one error in circuit breaker logic
counter++;
```

---

## Error Handling

### Never Swallow Exceptions
```csharp
// ❌ Bad
try
{
    ProcessPayment();
}
catch { } // Silent failure

// ✅ Good
try
{
    ProcessPayment();
}
catch (Exception ex)
{
    _logger.LogError(ex, "Failed to process payment");
    throw; // or handle appropriately
}
```

### Specific Exception Types
```csharp
// ❌ Bad - Generic exception
throw new Exception("User not found");

// ✅ Good - Specific exception
throw new UserNotFoundException(userId);
```

---

## Performance Considerations

### Avoid Premature Optimization
- ✅ Write clear code first
- ✅ Measure performance before optimizing
- ❌ Don't sacrifice readability for micro-optimizations

### Be Aware of Common Issues
- ❌ N+1 queries in database access
- ❌ Unnecessary allocations in loops
- ❌ Blocking async calls (`.Result`, `.Wait()`)
- ❌ Not disposing IDisposable resources

---

## Consistency

### Follow Project Conventions
- ✅ Use existing patterns in the codebase
- ✅ Match naming conventions of the language/framework
- ✅ Follow team's established practices
- ❌ Don't introduce new patterns without team discussion

### Code Reviews
- ✅ All code must be reviewed before merge
- ✅ Address review comments promptly
- ✅ Learn from feedback

---

**These standards apply to all languages: C#, TypeScript, Go, Python, etc.**
