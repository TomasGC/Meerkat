# Claude Code Utility Scripts - Tests

Comprehensive test suite for all utility scripts using Pester (PowerShell testing framework).

## 🧪 Test Coverage

### Utility Scripts

| Script | Test File | Status |
|--------|-----------|--------|
| `read-yaml-frontmatter.ps1` | `read-yaml-frontmatter.Tests.ps1` | ✅ |
| `categorize-documentation.ps1` | `categorize-documentation.Tests.ps1` | ✅ |
| `analyze-dependencies.ps1` | `analyze-dependencies.Tests.ps1` | ✅ |
| `list-files-by-extension.ps1` | `list-files-by-extension.Tests.ps1` | ✅ |
| `find-git-repos.ps1` | `find-git-repos.Tests.ps1` | ✅ |
| `update-section-in-markdown.ps1` | `update-section-in-markdown.Tests.ps1` | ✅ |

### Automation Scripts

| Script | Test File | Status |
|--------|-----------|--------|
| `analyze_work_patterns.py` | `test_analyze_work_patterns.py` | ✅ |
| `generate_kanban_entry.py` | `test_generate_kanban_entry.py` | ✅ |
| `generate-github-comment.ps1` | `generate-github-comment.Tests.ps1` | ✅ |
| `update-kanban.ps1` | `update-kanban.Tests.ps1` | ✅ |

**Total**: 10 scripts tested with comprehensive coverage

## 📋 Test Structure

```
tests/
├── fixtures/                           # Test data
│   ├── sample-skill.md                 # Simple YAML frontmatter
│   ├── sample-multiline.md             # Multiline YAML
│   ├── sample-package.json             # Node.js project
│   ├── sample-requirements.txt         # Python project
│   ├── sample-cargo.toml               # Rust project
│   ├── sample-readme.md                # FUNCTIONAL doc
│   ├── sample-architecture.md          # TECHNICAL doc
│   └── sample-local.md                 # PERSONAL doc
├── read-yaml-frontmatter.Tests.ps1
├── categorize-documentation.Tests.ps1
├── analyze-dependencies.Tests.ps1
├── list-files-by-extension.Tests.ps1
├── find-git-repos.Tests.ps1
├── update-section-in-markdown.Tests.ps1
├── test_analyze_work_patterns.py
├── test_generate_kanban_entry.py
├── generate-github-comment.Tests.ps1
├── update-kanban.Tests.ps1
├── run-all-tests.ps1                   # Test runner
└── README.md                           # This file
```

## 🚀 Running Tests

### Prerequisites

- **PowerShell 7+**
- **Pester 5+** (auto-installed by run-all-tests.ps1 if missing)
- **Git** (for git-related tests)

### Run All Tests

```powershell
cd ~/.claude/scripts/tests
./run-all-tests.ps1
```

### Run Specific Test File

```powershell
./run-all-tests.ps1 -TestFile "read-yaml-frontmatter.Tests.ps1"
```

### Run with Detailed Output

```powershell
./run-all-tests.ps1 -Detailed
```

### Run with Pester Directly

```powershell
# All tests
Invoke-Pester

# Specific test
Invoke-Pester -Path "read-yaml-frontmatter.Tests.ps1"

# With coverage
Invoke-Pester -CodeCoverage "../*.ps1"
```

## 📊 Test Categories

### 1. **Unit Tests** (normal cases)
- Valid inputs
- Expected outputs
- Format conversions

### 2. **Edge Case Tests**
- Multiline strings
- Arrays and nested objects
- Empty values
- Special characters

### 3. **Error Handling Tests**
- File not found
- Invalid format
- Missing frontmatter
- Unsupported file types

### 4. **Integration Tests**
- Multiple files
- Real-world scenarios
- End-to-end workflows

## 🎯 Test Examples

### read-yaml-frontmatter.Tests.ps1
- ✅ Parses simple frontmatter
- ✅ Handles multiline strings with pipe `|`
- ✅ Parses arrays `[item1, item2]`
- ✅ Outputs JSON/YAML/text formats
- ✅ Fails gracefully on errors

### categorize-documentation.Tests.ps1
- ✅ Categorizes README.md as FUNCTIONAL
- ✅ Categorizes ARCHITECTURE.md as TECHNICAL
- ✅ Categorizes *.local.md as PERSONAL
- ✅ Handles multiple files
- ✅ Outputs different formats

### analyze-dependencies.Tests.ps1
- ✅ Detects Node.js/Python/Rust projects
- ✅ Identifies frameworks (React, FastAPI, actix-web)
- ✅ Extracts dependencies with versions
- ✅ Extracts scripts from package.json
- ✅ Respects TopN parameter
- ✅ Handles unsupported files

### list-files-by-extension.Tests.ps1
- ✅ Finds files with extensions
- ✅ Searches recursively
- ✅ Excludes node_modules by default
- ✅ Respects custom exclusions
- ✅ Includes file metadata

### find-git-repos.Tests.ps1
- ✅ Finds git repositories
- ✅ Excludes non-git directories
- ✅ Includes repo metadata (branch, remote)
- ✅ Respects MaxDepth parameter

### update-section-in-markdown.Tests.ps1
- ✅ Updates sections successfully
- ✅ Preserves other sections
- ✅ Handles numbered sections
- ✅ Creates backups
- ✅ Fails when section not found

## 🔧 Adding New Tests

1. **Create test file**: `<script-name>.Tests.ps1`
2. **Add BeforeAll/AfterAll** for setup/cleanup
3. **Use Describe/Context/It** structure
4. **Add fixtures** in `fixtures/` if needed
5. **Run tests** to verify

### Template

```powershell
#!/usr/bin/env pwsh
#Requires -Version 7.0

BeforeAll {
    $scriptPath = Join-Path $PSScriptRoot ".." "my-script.ps1"
}

Describe "my-script.ps1" {
    Context "Basic functionality" {
        It "Does what it should" {
            $result = & $scriptPath -Param "value"
            $result | Should -Be "expected"
        }
    }
}
```

## 📚 Resources

- [Pester Documentation](https://pester.dev/docs/quick-start)
- [PowerShell Testing Best Practices](https://pester.dev/docs/usage/assertions)
- [Should Assertions](https://pester.dev/docs/commands/Should)

## 🎉 Benefits

- ✅ **Confidence in refactoring** - Change scripts without breaking existing behavior
- ✅ **Catch regressions early** - Tests run before committing
- ✅ **Documentation** - Tests show how scripts are meant to be used
- ✅ **Quality assurance** - Ensures scripts work across edge cases
- ✅ **CI/CD integration** - Can be run in pipelines

## 🚨 Known Limitations

- Tests create temporary files/directories during execution
- Git-related tests require git to be installed
- Some tests may be slower on Windows due to file system operations
- Pester 5+ required (older versions not supported)

---

**Last updated**: 2026-03-15
