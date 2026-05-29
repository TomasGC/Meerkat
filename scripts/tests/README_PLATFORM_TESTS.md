# Platform-Specific Tests Guide

This document explains how to write platform-specific tests using pytest markers.

## Available Markers

- `@pytest.mark.unix` - Test runs only on Unix-like systems (Linux, macOS)
- `@pytest.mark.windows` - Test runs only on Windows
- `@pytest.mark.linux` - Test runs only on Linux
- `@pytest.mark.macos` - Test runs only on macOS
- `@pytest.mark.requires_shellcheck` - Test requires shellcheck binary
- `@pytest.mark.slow` - Test takes more than 1 second
- `@pytest.mark.integration` - Integration test (not unit test)

## Usage Examples

### Unix-only Test

```python
import pytest

@pytest.mark.unix
def test_bash_validation(tmp_path):
    """Test Bash syntax validation (Unix only)."""
    script = tmp_path / "script.sh"
    script.write_text("#!/usr/bin/env bash\necho 'Hello'")
    
    result = validate_bash(script)
    assert result.valid
```

### Windows-only Test

```python
import pytest

@pytest.mark.windows
def test_powershell_validation(tmp_path):
    """Test PowerShell syntax validation (Windows only)."""
    script = tmp_path / "script.ps1"
    script.write_text("Write-Host 'Hello'")
    
    result = validate_powershell(script)
    assert result.valid
```

### Multiple Markers

```python
import pytest

@pytest.mark.unix
@pytest.mark.slow
@pytest.mark.requires_shellcheck
def test_comprehensive_bash_lint(tmp_path):
    """Full Bash linting with shellcheck (Unix only, slow)."""
    # ... test implementation
```

## Running Platform-Specific Tests

### Run all tests (auto-skips based on platform)
```bash
pytest tests/
```

### Run only Unix tests
```bash
pytest -m unix tests/
```

### Run only Windows tests
```bash
pytest -m windows tests/
```

### Skip slow tests
```bash
pytest -m "not slow" tests/
```

### Run integration tests only
```bash
pytest -m integration tests/
```

## How It Works

The `tests/conftest.py` file contains a `pytest_runtest_setup` hook that:

1. Checks for platform markers on each test
2. Auto-skips tests that don't match the current platform
3. Provides clear skip messages (e.g., "Test requires Unix-like system")

This approach is **cleaner than manual `skipif`** because:
- ✅ Centralized skip logic in `conftest.py`
- ✅ No need for `sys.platform` checks in every test
- ✅ Clear, consistent skip messages
- ✅ Easy to add new platform markers
- ✅ Tests are self-documenting with markers

## When to Use Platform Markers

Use platform markers when:

- ✅ Test validates platform-specific tooling (shellcheck, pwsh)
- ✅ Test uses platform-specific paths or conventions
- ✅ Test requires platform-specific binaries
- ✅ Test behavior differs significantly by platform

Don't use markers when:

- ❌ Code should be cross-platform (write portable tests instead)
- ❌ Test can be abstracted with mocks
- ❌ Platform differences are minor (handle in test logic)

## Example: Converting Old Skip Pattern

### Before (manual skipif)
```python
import sys
import pytest

@pytest.mark.skipif(sys.platform == "win32", reason="Bash validation requires Unix")
def test_bash_validation(tmp_path):
    """Test Bash validation."""
    # ... test code
```

### After (marker-based)
```python
import pytest

@pytest.mark.unix
def test_bash_validation(tmp_path):
    """Test Bash validation (Unix only)."""
    # ... test code
```

**Benefits**: Cleaner, more declarative, centralized skip logic.

## Adding New Platform Markers

To add a new marker:

1. Add it to `pytest.ini`:
```ini
markers =
    mymarker: Description of when to use this marker
```

2. Add skip logic to `tests/conftest.py`:
```python
def pytest_runtest_setup(item):
    if "mymarker" in item.keywords:
        # Custom skip logic
        if some_condition:
            pytest.skip("Custom skip message")
```

3. Use it in tests:
```python
@pytest.mark.mymarker
def test_something():
    pass
```

## CI/CD Considerations

In CI pipelines, tests auto-skip based on runner platform:

- **GitHub Actions Windows runner** → Unix tests skipped
- **GitHub Actions Linux runner** → Windows tests skipped
- **GitLab CI Linux runner** → Windows tests skipped

This ensures clean CI runs without platform-specific failures.
