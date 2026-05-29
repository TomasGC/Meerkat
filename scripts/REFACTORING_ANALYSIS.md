# 🔍 Code Review: SOLID/KISS/YAGNI/DRY/DDD/TDD Analysis

**Date**: 2026-05-02
**Scope**: 29 Python CLI scripts + common/ infrastructure
**Goal**: Extract reusable patterns into "Claude framework"

---

## 📊 Current State

### Scripts Analyzed
- **Total CLI scripts**: 29
- **Common infrastructure modules**: 6
  - `common/logger.py` - Logging infrastructure
  - `common/utils.py` - Utility functions  
  - `common/formatters.py` - JSON/text formatting
  - `common/models.py` - Data models (20+ dataclasses)
  - `common/validators.py` - Validation logic
  - `common/__init__.py` - Package init

### Test Coverage
- **Total tests**: 596 (595 passing, 1 skipped)
- **Coverage**: 100% test pass rate

---

## 🎯 SOLID Principles Analysis

### ✅ Single Responsibility Principle (SRP)

**Good**:
- Each CLI script has a single focused purpose
- `common/` modules have clear separation:
  - `logger.py` → Only logging
  - `formatters.py` → Only formatting
  - `validators.py` → Only validation
  - `models.py` → Only data structures

**Issues**:
- ⚠️ Some CLI scripts have `format_text()`, `format_summary()` functions inline
- ⚠️ Validation logic sometimes duplicated in CLI scripts (should delegate to `validators.py`)

**Recommendations**:
1. Extract all formatting functions to `common/formatters.py`
2. Move validation logic from CLI scripts to `common/validators.py`

---

### ⚠️ Open-Closed Principle (OCP)

**Issues**:
- ❌ **No base classes for CLI scripts** - Each script reimplements:
  - `main()` function with argparse
  - Error handling pattern (try/except + sys.exit(1))
  - Logging initialization (`logger, metrics = get_defaults()`)
  - Output formatting (JSON/text/summary)

**Violation Example**:
```python
# EVERY script does this:
def main() -> int:
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--format", choices=["json", "text", "summary"])
    args = parser.parse_args()
    
    try:
        # Script logic
        if args.format == "json":
            print(format_json(result))
        elif args.format == "text":
            print(format_text(result))
        else:
            print(format_summary(result))
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**This pattern repeated in 29/29 scripts** - massive DRY violation!

**Recommendations**:
1. Create `BaseCLIScript` abstract base class
2. Extract common argument patterns (--format, --path, --recursive)
3. Provide template methods for:
   - `setup_parser()` - Add script-specific arguments
   - `execute()` - Script logic
   - `format_result()` - Custom formatting

---

### ⚠️ Liskov Substitution Principle (LSP)

**Status**: Not applicable yet (no inheritance hierarchy)

**Recommendations**:
- Once `BaseCLIScript` exists, ensure all subclasses are substitutable
- Validators should follow consistent interface

---

### ⚠️ Interface Segregation Principle (ISP)

**Good**:
- `common/formatters.py` provides specific functions (`format_json`, `format_text`)
- `common/validators.py` has focused validation functions

**Issues**:
- ⚠️ No explicit interfaces (protocols) defined
- ⚠️ Validators mix different concerns (YAML frontmatter + skill structure + script syntax)

**Recommendations**:
1. Define protocols (typing.Protocol) for:
   - `Validator` interface
   - `Formatter` interface
   - `CLIScript` interface
2. Split `validators.py` into smaller modules:
   - `validators/yaml_validator.py`
   - `validators/skill_validator.py`
   - `validators/script_validator.py`

---

### ❌ Dependency Inversion Principle (DIP)

**Issues**:
- ❌ CLI scripts directly import concrete implementations
- ❌ No dependency injection
- ❌ Hard to test with mocks (no abstractions)

**Example**:
```python
# Direct dependency on concrete logger
from common.logger import get_defaults
logger, metrics = get_defaults(module_name=__name__)

# Direct dependency on concrete formatter
from common.formatters import format_json
print(format_json(result))
```

**Recommendations**:
1. Define abstractions (protocols):
   ```python
   class Logger(Protocol):
       def info(self, msg: str) -> None: ...
       def error(self, msg: str) -> None: ...
   
   class Formatter(Protocol):
       def format(self, data: dict) -> str: ...
   ```

2. Inject dependencies via constructor/factory:
   ```python
   class MyScript(BaseCLIScript):
       def __init__(
           self,
           logger: Logger,
           formatter: Formatter
       ):
           self.logger = logger
           self.formatter = formatter
   ```

---

## 🔥 DRY Violations (Critical)

### 1. ❌ argparse Boilerplate (29/29 scripts)

**Pattern repeated everywhere**:
```python
parser = argparse.ArgumentParser(
    description="...",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""Examples: ..."""
)
parser.add_argument("--format", choices=["json", "text", "summary"], default="json")
parser.add_argument("--path", "-p", default=".", help="...")
args = parser.parse_args()
```

**Solution**: Extract to `BaseCLIScript`

---

### 2. ❌ main() Pattern (29/29 scripts)

**Pattern repeated everywhere**:
```python
def main() -> int:
    try:
        # Script logic
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**Solution**: Extract to `BaseCLIScript.run()`

---

### 3. ❌ Output Formatting Logic (29/29 scripts)

**Pattern repeated everywhere**:
```python
if args.format == "json":
    print(format_json(result))
elif args.format == "text":
    print(format_text(result))
else:  # summary
    print(format_summary(result))
```

**Solution**: Extract to `BaseCLIScript.output()`

---

### 4. ❌ Logging Initialization (29/29 scripts)

**Pattern repeated everywhere**:
```python
from common.logger import get_defaults
logger, metrics = get_defaults(module_name=__name__)
```

**Solution**: Auto-initialize in `BaseCLIScript.__init__()`

---

### 5. ⚠️ Validation Logic Duplication

**Example**: Cross-platform validation checks repeated across scripts
- Hardcoded path detection logic in `validate_cross_platform.py`
- Similar pattern in `safe_read_context.py` (file existence checks)

**Solution**: Centralize in `common/validators/`

---

### 6. ⚠️ File Reading Patterns

**Pattern repeated**:
```python
def read_file_safely(file_path: Path) -> dict:
    if not file_path.exists():
        return {"exists": False, "path": str(file_path)}
    
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = len(content.splitlines())
        return {
            "exists": True,
            "path": str(file_path),
            "content": content,
            "lines": lines
        }
    except Exception as e:
        return {
            "exists": True,
            "path": str(file_path),
            "error": str(e)
        }
```

**This exact pattern in multiple scripts**:
- `safe_read_context.py`
- Potentially others

**Solution**: Extract to `common/file_utils.py` → `read_file_safe()`

---

## 💡 KISS Violations

### ⚠️ Over-complicated Patterns

**Example from `validate_cross_platform.py`**:
- 7 separate check functions (`check_hardcoded_paths`, `check_path_api_usage`, etc.)
- Each mutates lists passed as parameters (errors, warnings, info)
- Hard to test in isolation

**Improvement**:
```python
# Current (complex)
def check_hardcoded_paths(content: str, errors: list, warnings: list) -> None:
    if re.search(r'C:\\', content):
        errors.append("Hardcoded Windows path")
    # Mutates external lists

# Better (simple)
@dataclass
class CheckResult:
    errors: list[str]
    warnings: list[str]

def check_hardcoded_paths(content: str) -> CheckResult:
    errors = []
    warnings = []
    if re.search(r'C:\\', content):
        errors.append("Hardcoded Windows path")
    return CheckResult(errors=errors, warnings=warnings)
```

---

## ✅ YAGNI Compliance

**Good**:
- No speculative features detected
- Scripts focus on current requirements
- No "future-proofing" complexity

**No violations found** ✅

---

## 🏗️ DDD (Domain-Driven Design) Analysis

### Current Domain Models

**Good** (`common/models.py`):
- Clear domain entities:
  - `SkillInfo`, `AgentInfo`, `ScriptInfo`
  - `ValidationResult`, `TestCoverageResult`
  - `GitCommitInfo`, `GitHubTicket`, `KanbanEntry`
  - `CIFailure`, `BranchSummary`

**Issues**:
- ⚠️ Domain logic scattered across CLI scripts
- ⚠️ No domain services layer
- ⚠️ CLI scripts directly manipulate domain models

### Recommended Domain Structure

```
common/
├── domain/
│   ├── models/
│   │   ├── validation.py       # ValidationResult, etc.
│   │   ├── git.py              # GitCommitInfo, BranchSummary
│   │   ├── ci.py               # CIFailure
│   │   ├── components.py       # SkillInfo, AgentInfo, ScriptInfo
│   │   └── project.py          # GitHubTicket, KanbanEntry
│   ├── services/
│   │   ├── validation_service.py
│   │   ├── git_service.py
│   │   ├── ci_service.py
│   │   └── project_service.py
│   └── repositories/
│       ├── file_repository.py
│       └── git_repository.py
```

---

## 🧪 TDD Compliance

### Current State

**Good**:
- **596 tests** with 100% pass rate
- Tests use pytest framework
- Tests follow AAA pattern (Arrange-Act-Assert)
- Fixtures used for test data (`tmp_path`)

**Test Coverage by Module**:
```
tests/
├── test_analyze_ci_failure.py
├── test_analyze_dependencies.py
├── test_categorize_documentation.py
├── test_check_git_repo.py
├── test_check_test_coverage.py
├── test_extract_issue.py
├── test_format_commit_message.py
├── test_generate_github_comment.py
├── test_generate_kanban_entry.py
├── test_generate_test_scaffold.py
├── test_infer_name.py
├── test_load_session_context.py
├── test_read_yaml_frontmatter.py
├── test_run_all_validations.py
├── test_safe_read_context.py
├── test_update_kanban.py
├── test_validate_cross_platform.py
├── test_validate_markdown.py
├── test_validate_script_syntax.py
└── test_validate_skill_structure.py
```

**Issues**:
- ⚠️ No tests for `common/formatters.py`
- ⚠️ No tests for `common/utils.py`
- ⚠️ No tests for `common/logger.py`
- ⚠️ Missing integration tests for CLI workflows

**Recommendations**:
1. Add unit tests for `common/` modules (target: 100% coverage)
2. Add integration tests for end-to-end CLI workflows
3. When refactoring to `BaseCLIScript`, write tests FIRST (TDD)

---

## 🚀 Proposed "Claude Framework" Architecture

### 1. Base CLI Infrastructure

```
common/
├── cli/
│   ├── __init__.py
│   ├── base.py                 # BaseCLIScript (abstract base)
│   ├── arguments.py            # Common argument patterns
│   └── output.py               # Output formatting strategies
```

**`base.py` (new)**:
```python
#!/usr/bin/env python3
"""Base class for all CLI scripts."""

from abc import ABC, abstractmethod
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path
from typing import Any

from ..formatters import format_json
from ..logger import get_defaults
from ..models import OutputFormat


class BaseCLIScript(ABC):
    """Abstract base class for all CLI scripts.
    
    Provides:
    - Automatic argparse setup
    - Logging initialization
    - Error handling
    - Output formatting (JSON/text/summary)
    - Exit code handling
    
    Subclasses must implement:
    - execute() - Main script logic
    """
    
    def __init__(self):
        """Initialize logging and metrics."""
        self.logger, self.metrics = get_defaults(module_name=self.__class__.__module__)
    
    def setup_parser(self, parser: ArgumentParser) -> None:
        """
        Add script-specific arguments to parser.
        
        Override this method to add custom arguments.
        Default arguments (--format, --path, etc.) are added automatically.
        
        Args:
            parser: ArgumentParser instance
        """
        pass
    
    @abstractmethod
    def execute(self, args) -> dict[str, Any]:
        """
        Execute script logic.
        
        Args:
            args: Parsed command-line arguments
        
        Returns:
            dict: Result dictionary (will be formatted according to --format)
        
        Raises:
            Exception: Any error during execution
        """
        pass
    
    def format_text(self, result: dict) -> str:
        """
        Format result as human-readable text.
        
        Override this method for custom text formatting.
        Default: pretty-printed JSON.
        
        Args:
            result: Result dictionary from execute()
        
        Returns:
            Formatted string
        """
        return format_json(result)
    
    def format_summary(self, result: dict) -> str:
        """
        Format result as brief summary.
        
        Override this method for custom summary formatting.
        Default: Same as format_text().
        
        Args:
            result: Result dictionary from execute()
        
        Returns:
            Summary string (should be 1-3 lines)
        """
        return self.format_text(result)
    
    def create_parser(self) -> ArgumentParser:
        """
        Create argument parser with common arguments.
        
        Returns:
            ArgumentParser with default arguments
        """
        parser = ArgumentParser(
            description=self.__doc__ or "CLI script",
            formatter_class=RawDescriptionHelpFormatter
        )
        
        # Common arguments
        parser.add_argument(
            "--format",
            "-f",
            choices=["json", "text", "summary"],
            default="json",
            help="Output format (default: json)"
        )
        
        # Allow subclass to add custom arguments
        self.setup_parser(parser)
        
        return parser
    
    def output(self, result: dict, format: str) -> None:
        """
        Output result in requested format.
        
        Args:
            result: Result dictionary
            format: Output format (json/text/summary)
        """
        if format == "json":
            print(format_json(result))
        elif format == "text":
            print(self.format_text(result))
        else:  # summary
            print(self.format_summary(result))
    
    def run(self, args: list[str] | None = None) -> int:
        """
        Main entry point - handles full execution lifecycle.
        
        - Parses arguments
        - Calls execute()
        - Handles errors
        - Formats output
        - Returns exit code
        
        Args:
            args: Command-line arguments (None = sys.argv)
        
        Returns:
            Exit code (0 = success, 1 = error)
        """
        try:
            parser = self.create_parser()
            parsed_args = parser.parse_args(args)
            
            # Execute script logic
            result = self.execute(parsed_args)
            
            # Output result
            self.output(result, parsed_args.format)
            
            # Track success metric
            self.metrics.track(
                f"{self.__class__.__name__}.success",
                {"format": parsed_args.format}
            )
            
            return 0
            
        except KeyboardInterrupt:
            self.logger.warning("Interrupted by user")
            return 130
        
        except Exception as e:
            self.logger.error(f"Error: {e}", exc_info=True)
            self.metrics.track(
                f"{self.__class__.__name__}.error",
                {"error_type": type(e).__name__}
            )
            return 1


def create_cli_script(script_class: type[BaseCLIScript]) -> None:
    """
    Create and run CLI script.
    
    Usage:
        if __name__ == "__main__":
            create_cli_script(MyScript)
    
    Args:
        script_class: Subclass of BaseCLIScript
    """
    import sys
    script = script_class()
    sys.exit(script.run())
```

**Example Migration** (`check_test_coverage.py`):

**Before** (78 lines of boilerplate):
```python
def main() -> int:
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--path", ...)
    parser.add_argument("--recursive", ...)
    parser.add_argument("--format", ...)
    args = parser.parse_args()
    
    try:
        # 50 lines of logic
        if args.format == "json":
            print(format_json(result))
        elif args.format == "text":
            print(format_text(result))
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**After** (20 lines, focused on logic):
```python
class CheckTestCoverageScript(BaseCLIScript):
    """Check test coverage for Python and PowerShell scripts."""
    
    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--path", "-p", type=Path, default=Path("."),
            help="Path to directory"
        )
        parser.add_argument(
            "--recursive", "-r", action="store_true",
            help="Search subdirectories"
        )
    
    def execute(self, args) -> dict:
        """Execute coverage check."""
        # 50 lines of PURE LOGIC (no boilerplate)
        return analyze_coverage(args.path, args.recursive)
    
    def format_text(self, result) -> str:
        """Format as human-readable report."""
        return format_coverage_report(result)
    
    def format_summary(self, result) -> str:
        """Format as one-line summary."""
        return f"Coverage: {result['coverage_percent']:.1f}%"


if __name__ == "__main__":
    create_cli_script(CheckTestCoverageScript)
```

**Benefits**:
- ✅ 78 lines → 20 lines (73% reduction)
- ✅ Focus on WHAT, not HOW
- ✅ Consistent error handling
- ✅ Automatic logging and metrics
- ✅ Easy to test (inject mocks in `execute()`)

---

### 2. Domain Layer

```
common/
├── domain/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── validation.py       # ValidationResult, CheckResult
│   │   ├── git.py              # GitCommitInfo, BranchSummary
│   │   ├── ci.py               # CIFailure
│   │   ├── components.py       # SkillInfo, AgentInfo, ScriptInfo
│   │   └── project.py          # GitHubTicket, KanbanEntry
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── validation_service.py  # Validation orchestration
│   │   ├── git_service.py         # Git operations
│   │   ├── ci_service.py          # CI/CD analysis
│   │   └── project_service.py     # Project context (KANBAN, etc.)
│   │
│   └── repositories/
│       ├── __init__.py
│       ├── file_repository.py     # File I/O
│       └── git_repository.py      # Git operations
```

**Example** (`validation_service.py`):
```python
#!/usr/bin/env python3
"""Validation domain service."""

from pathlib import Path
from typing import Protocol

from ..models.validation import ValidationResult


class Validator(Protocol):
    """Validator interface."""
    
    def validate(self, target: Path) -> ValidationResult:
        """Validate target."""
        ...


class ValidationService:
    """Orchestrates validation workflows."""
    
    def __init__(
        self,
        validators: list[Validator],
        logger: Logger
    ):
        self.validators = validators
        self.logger = logger
    
    def validate_all(self, target: Path) -> list[ValidationResult]:
        """Run all validators on target."""
        results = []
        for validator in self.validators:
            try:
                result = validator.validate(target)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Validator {validator} failed: {e}")
        
        return results
    
    def is_valid(self, target: Path) -> bool:
        """Check if all validations pass."""
        results = self.validate_all(target)
        return all(r.success for r in results)
```

---

### 3. Validators Refactoring

```
common/
├── validators/
│   ├── __init__.py
│   ├── base.py                 # BaseValidator (abstract)
│   ├── yaml_validator.py       # YAML frontmatter validation
│   ├── skill_validator.py      # SKILL.md structure validation
│   ├── agent_validator.py      # AGENT.md structure validation
│   ├── script_validator.py     # Script syntax validation
│   └── cross_platform_validator.py  # Cross-platform checks
```

**Example** (`base.py`):
```python
#!/usr/bin/env python3
"""Base validator interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from ..domain.models.validation import ValidationResult


class BaseValidator(ABC):
    """Abstract base class for all validators."""
    
    @abstractmethod
    def validate(self, target: Path) -> ValidationResult:
        """
        Validate target.
        
        Args:
            target: File or directory to validate
        
        Returns:
            ValidationResult with errors/warnings/info
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Validator name for reporting."""
        pass
```

---

### 4. File Utilities

```
common/
├── file_utils.py               # File I/O helpers
```

**`file_utils.py` (new)**:
```python
#!/usr/bin/env python3
"""File I/O utilities."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileReadResult:
    """Result of safe file read operation."""
    exists: bool
    path: str
    content: Optional[str] = None
    lines: int = 0
    error: Optional[str] = None


def read_file_safe(file_path: Path, encoding: str = "utf-8") -> FileReadResult:
    """
    Read file with graceful error handling.
    
    Args:
        file_path: Path to file
        encoding: File encoding (default: utf-8)
    
    Returns:
        FileReadResult with content or error
    
    Examples:
        >>> result = read_file_safe(Path("test.txt"))
        >>> if result.exists and result.content:
        ...     print(result.content)
    """
    if not file_path.exists():
        return FileReadResult(exists=False, path=str(file_path))
    
    try:
        content = file_path.read_text(encoding=encoding)
        lines = len(content.splitlines())
        
        return FileReadResult(
            exists=True,
            path=str(file_path),
            content=content,
            lines=lines
        )
    
    except Exception as e:
        return FileReadResult(
            exists=True,
            path=str(file_path),
            error=str(e)
        )


def read_files_safe(
    file_paths: list[Path],
    encoding: str = "utf-8"
) -> list[FileReadResult]:
    """
    Read multiple files with graceful error handling.
    
    Args:
        file_paths: List of file paths
        encoding: File encoding
    
    Returns:
        List of FileReadResult
    """
    return [read_file_safe(p, encoding) for p in file_paths]
```

---

## 📋 Refactoring Roadmap

### Phase 1: Foundation (Week 1)

1. ✅ Create `common/cli/base.py` with `BaseCLIScript`
2. ✅ Create `common/cli/arguments.py` for common arguments
3. ✅ Create `common/file_utils.py` with `read_file_safe()`
4. ✅ Write tests for all new base classes (TDD approach)

**Test Plan**:
```python
# tests/common/cli/test_base.py
def test_base_cli_script_execute():
    """Test BaseCLIScript execution lifecycle."""
    pass

def test_base_cli_script_error_handling():
    """Test error handling and exit codes."""
    pass

def test_base_cli_script_output_formatting():
    """Test output formatting (JSON/text/summary)."""
    pass
```

### Phase 2: Migrate 3 Pilot Scripts (Week 1)

**Choose simple scripts first**:
1. `check_test_coverage.py` → `CheckTestCoverageScript(BaseCLIScript)`
2. `validate_script_syntax.py` → `ValidateScriptSyntaxScript(BaseCLIScript)`
3. `infer_name.py` → `InferNameScript(BaseCLIScript)`

**Why these 3?**:
- Simple logic (no complex dependencies)
- Already have good test coverage
- Representative of common patterns

**Process**:
1. Write tests for new class-based version (TDD)
2. Migrate script to use `BaseCLIScript`
3. Run tests (all must pass)
4. Verify manual testing still works
5. Compare before/after line count

**Success Criteria**:
- ✅ All 596 tests still passing
- ✅ Manual CLI usage unchanged
- ✅ Code reduction ≥ 50% per script
- ✅ No functionality lost

### Phase 3: Domain Layer Refactoring (Week 2)

1. ✅ Reorganize `common/models.py` into `common/domain/models/`
2. ✅ Create `common/domain/services/validation_service.py`
3. ✅ Create `common/validators/` with split validators
4. ✅ Update imports in existing scripts

**Preserve Backward Compatibility**:
```python
# common/models.py (keep for backward compatibility)
# Re-export from new locations
from .domain.models.validation import ValidationResult
from .domain.models.git import GitCommitInfo
# ... etc
```

### Phase 4: Migrate Remaining Scripts (Week 2-3)

**Batch migration**:
- Analyze script groups (validation, git, CI, etc.)
- Migrate in groups of 5-7 scripts per batch
- Run full test suite after each batch

**Order** (simplest to most complex):
1. Validation scripts (5 scripts)
2. Git-related scripts (4 scripts)
3. Project management scripts (6 scripts)
4. CI/CD analysis scripts (4 scripts)
5. Complex multi-step scripts (5 scripts)

### Phase 5: Cleanup & Documentation (Week 3)

1. ✅ Remove legacy code (old `main()` functions)
2. ✅ Update docstrings
3. ✅ Create migration guide (`MIGRATION.md`)
4. ✅ Update `README.md` with framework architecture
5. ✅ Create usage examples for `BaseCLIScript`

---

## 📈 Expected Impact

### Code Reduction

**Current**:
- Average script size: ~300 lines
- Boilerplate per script: ~80 lines (27%)

**After refactoring**:
- Average script size: ~150 lines (50% reduction)
- Boilerplate per script: ~5 lines (inheritance only)
- **Total reduction**: ~4,350 lines across 29 scripts

### Maintainability

**Before**:
- Changing error handling → Update 29 files
- Adding new output format → Update 29 files
- Fixing logging issue → Update 29 files

**After**:
- Changing error handling → Update 1 file (`BaseCLIScript`)
- Adding new output format → Update 1 file (`BaseCLIScript`)
- Fixing logging issue → Update 1 file (`BaseCLIScript`)

### Testability

**Before**:
- Hard to test CLI scripts (full integration tests only)
- Mocking difficult (tight coupling)

**After**:
- Easy unit tests (`execute()` method is pure logic)
- Easy mocking (inject dependencies)
- Faster test execution (no full CLI setup)

### Extensibility

**Before**:
- Adding new script → Copy/paste boilerplate from existing
- Inconsistent argument patterns
- Easy to forget error handling

**After**:
- Adding new script → Inherit from `BaseCLIScript`
- Consistent argument patterns (enforced by base class)
- Error handling automatic (no way to forget)

---

## ✅ Success Metrics

1. **Code Reduction**: ≥ 40% reduction in total lines of code
2. **Test Coverage**: Maintain 100% test pass rate (596+ tests)
3. **DRY Score**: Zero repeated patterns in CLI scripts
4. **SOLID Compliance**: 100% compliance with all 5 principles
5. **Performance**: No degradation in script execution time
6. **Backward Compatibility**: 100% of existing CLI usage still works

---

## 🎯 Quick Wins (Immediate Action)

### 1. Extract `read_file_safe()` (1 hour)

**Files affected**: 2 (safe_read_context.py, potentially others)

**Impact**: DRY improvement, reusable utility

**Implementation**:
```python
# common/file_utils.py (create)
def read_file_safe(file_path: Path) -> FileReadResult:
    # Implementation from REFACTORING_ANALYSIS.md
    pass

# tests/common/test_file_utils.py (create)
def test_read_file_safe_existing_file():
    pass

def test_read_file_safe_missing_file():
    pass

def test_read_file_safe_permission_error():
    pass
```

### 2. Create `BaseCLIScript` Prototype (4 hours)

**Implementation** (see code above in section "Proposed Claude Framework Architecture")

**Test first** (TDD):
```python
# tests/common/cli/test_base.py
class MockScript(BaseCLIScript):
    """Mock script for testing."""
    
    def execute(self, args) -> dict:
        return {"result": "success", "value": 42}
    
    def format_summary(self, result) -> str:
        return f"Result: {result['value']}"

def test_mock_script_run_success():
    script = MockScript()
    exit_code = script.run(["--format", "json"])
    assert exit_code == 0

def test_mock_script_run_error():
    # Test error handling
    pass
```

### 3. Migrate 1 Pilot Script (2 hours)

**Choose**: `check_test_coverage.py` (simple, well-tested)

**Steps**:
1. Copy existing tests
2. Create `CheckTestCoverageScript(BaseCLIScript)`
3. Migrate logic to `execute()` method
4. Run tests (all must pass)
5. Verify manual CLI usage

**Before/After comparison**:
- Lines: 300 → 150 (50% reduction)
- Boilerplate: 80 lines → 5 lines (94% reduction)
- Functionality: 100% preserved

---

## 🚦 Risks & Mitigation

### Risk 1: Breaking Existing Tests

**Mitigation**:
- Migrate one script at a time
- Run full test suite after each migration
- Keep old code until tests pass
- Maintain backward-compatible imports

### Risk 2: Performance Degradation

**Mitigation**:
- Benchmark before/after
- Profile execution time
- Optimize hot paths if needed
- Accept ≤5% slowdown for better architecture

### Risk 3: Over-Engineering

**Mitigation**:
- Follow YAGNI principle
- Only extract patterns that exist ≥3 times
- Defer complex abstractions until proven need
- Get user feedback after Phase 2

---

## 📝 Next Steps

1. **Get user approval** for refactoring approach
2. **Start with quick win #1**: Extract `read_file_safe()` (1 hour)
3. **Implement quick win #2**: Create `BaseCLIScript` prototype (4 hours)
4. **Test quick win #3**: Migrate 1 pilot script (2 hours)
5. **Review results** and adjust approach if needed
6. **Continue with Phase 2** (migrate 3 pilot scripts)

**Estimated time to complete**:
- Phase 1 (Foundation): 7 hours
- Phase 2 (3 pilots): 6 hours
- Phase 3 (Domain layer): 8 hours
- Phase 4 (Remaining scripts): 20 hours
- Phase 5 (Cleanup): 5 hours
- **Total**: ~46 hours (≈ 1.5 weeks full-time)

---

**🎯 PRIMARY GOAL: Transform 29 scattered CLI scripts into a cohesive, maintainable, testable framework while maintaining 100% functionality and 100% test pass rate.**
