## Python 3.12+ Conventions

### Naming

```python
# Modules and packages: snake_case
import user_repository
from data_access import db_client

# Classes: PascalCase
class UserRepository: ...
class DatabaseConfig: ...

# Functions and variables: snake_case
def get_user_by_id(user_id: int) -> User: ...
max_retry_count = 3

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT_SEC = 30

# Private: _prefix
def _internal_helper() -> None: ...
_cache: dict[str, User] = {}
```

### Type Hints (mandatory)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

# ✅ Good - Type hints everywhere
def process_users(users: list[User], limit: int = 100) -> list[UserDto]:
    ...

# ✅ Good - Dataclasses for data models
@dataclass
class User:
    id: int
    name: str
    email: str
    tags: list[str] = field(default_factory=list)

# ✅ Good - Type aliases (Python 3.12)
type UserId = int
type UserMap = dict[UserId, User]

# ❌ Bad - No type hints
def process(data, limit):
    ...
```

### Paths

```python
# ✅ Good - pathlib.Path always
from pathlib import Path

config_path = Path(__file__).parent / "config.json"
output_dir = Path("output")
output_dir.mkdir(parents=True, exist_ok=True)

# ❌ Bad - os.path
import os
config_path = os.path.join(os.path.dirname(__file__), "config.json")
```

### Error Handling

```python
# ✅ Good - Specific exceptions, contextual messages
class UserNotFoundError(Exception):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"User {user_id} not found")
        self.user_id = user_id

try:
    user = repository.get_by_id(user_id)
except UserNotFoundError:
    logger.warning("User not found: %d", user_id)
    raise
except Exception:
    logger.exception("Unexpected error fetching user %d", user_id)
    raise

# ❌ Bad - Bare except, swallowed errors
try:
    user = repository.get_by_id(user_id)
except:
    pass
```

### CLI Scripts

```python
#!/usr/bin/env python3
"""Script description."""

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("input", type=Path, help="Input file")
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        process(args.input, args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Testing (pytest)

```python
import pytest
from pathlib import Path


@pytest.fixture
def sample_user() -> User:
    return User(id=1, name="John", email="john@example.com")


def test_get_user_returns_user(sample_user: User, tmp_path: Path) -> None:
    # Arrange
    repo = UserRepository(tmp_path / "db.json")
    repo.save(sample_user)

    # Act
    result = repo.get_by_id(1)

    # Assert
    assert result == sample_user


def test_get_user_raises_when_not_found(tmp_path: Path) -> None:
    repo = UserRepository(tmp_path / "db.json")
    with pytest.raises(UserNotFoundError, match="User 999 not found"):
        repo.get_by_id(999)
```

---
