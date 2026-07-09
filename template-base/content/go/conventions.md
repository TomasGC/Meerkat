## Go Conventions

### Naming

- **Packages**: Lowercase, single word (`user`, `order`, not `userService`)
- **Files**: Lowercase with underscores (`user_repository.go`)
- **Types**: PascalCase (`UserRepository`)
- **Functions/Methods**: PascalCase for exported, camelCase for private
- **Variables**: camelCase (`userID`, `orderTotal`)
- **Constants**: PascalCase or UPPER_CASE

### Code Organization

```go
// Package declaration
package user

// Imports (grouped: stdlib, external, internal)
import (
    "context"
    "fmt"

    "github.com/gin-gonic/gin"

    "myproject/internal/domain"
)

// Constants
const (
    DefaultPageSize = 20
    MaxPageSize = 100
)

// Types
type Repository interface {
    Create(ctx context.Context, user *domain.User) error
    GetByID(ctx context.Context, id string) (*domain.User, error)
}

// Functions
func New(db *sql.DB) Repository {
    return &repository{db: db}
}
```

### Error Handling

```go
// ✅ Good - Return errors, wrap with context
func (s *Service) CreateUser(ctx context.Context, req *CreateUserRequest) error {
    user, err := s.repo.GetByEmail(ctx, req.Email)
    if err != nil {
        return fmt.Errorf("failed to check existing user: %w", err)
    }
    if user != nil {
        return ErrUserAlreadyExists
    }
    // ...
}

// ❌ Bad - Panic for recoverable errors
func (s *Service) CreateUser(ctx context.Context, req *CreateUserRequest) error {
    user, err := s.repo.GetByEmail(ctx, req.Email)
    if err != nil {
        panic(err) // Don't do this
    }
    // ...
}
```

### Testing

```go
func TestUserService_Create(t *testing.T) {
    // Arrange
    ctrl := gomock.NewController(t)
    defer ctrl.Finish()

    repo := mock.NewMockRepository(ctrl)
    service := NewService(repo)

    // Act
    err := service.CreateUser(context.Background(), &CreateUserRequest{
        Email: "test@example.com",
        Name: "Test User",
    })

    // Assert
    assert.NoError(t, err)
    repo.AssertExpectations(t)
}
```

---
