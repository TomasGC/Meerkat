## TypeScript Conventions

### Naming

```typescript
// Classes and Interfaces: PascalCase
class UserService { }
interface UserRepository { }

// Variables and Functions: camelCase
const userId = "123";
function getUserById(id: string) { }

// Constants: UPPER_SNAKE_CASE
const MAX_RETRY_COUNT = 3;

// Type Aliases: PascalCase
type UserId = string;
```

### Type Safety

```typescript
// ✅ Good - Strong typing
interface CreateUserRequest {
  email: string;
  name: string;
  age: number;
}

async function createUser(req: CreateUserRequest): Promise<User> {
  // Implementation
}

// ❌ Bad - Using any
async function createUser(req: any): Promise<any> {
  // Implementation
}
```

---
