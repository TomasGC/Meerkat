# Claude Code Utility Scripts

PowerShell 7 cross-platform utility scripts for Claude Code skills and agents.

## 📋 Available Scripts

### 🎫 Ticket & Git Operations

#### `extract-issue.ps1`
Extract issue ID from git branch name or commit message.

**Usage**:
```powershell
# From current branch
./extract-issue.ps1
# → #123

# From specific branch
./extract-issue.ps1 -Branch "feature/#456"
# → #456

# From last commit message
./extract-issue.ps1 -FromCommit
# → #123
```

**Supported formats**: GitHub (`#123`), Azure DevOps (`#12345`)

---

#### `get-commit-info.ps1`
Extract git commit information (hash, message, author, date, files).

**Usage**:
```powershell
# Get HEAD commit info (JSON)
./get-commit-info.ps1

# Get specific commit
./get-commit-info.ps1 -Hash abc123f

# Get last 5 commits (text format)
./get-commit-info.ps1 -Count 5 -Format text

# Include changed files
./get-commit-info.ps1 -IncludeFiles

# CSV format for parsing
./get-commit-info.ps1 -Count 10 -Format csv
```

**Output formats**: `json` (default), `text`, `csv`

---

#### `format-commit-message.ps1`
Format and validate commit messages according to standard.

**Standard**: `TICKET-ID: type: description`

**Usage**:
```powershell
# Format new commit message
./format-commit-message.ps1 -Ticket #123 -Type feat -Message "add authentication"
# → #123: feat: add authentication

# Validate existing message
./format-commit-message.ps1 -Validate -Input "#123: feat: add auth"

# Validate and suggest corrections
./format-commit-message.ps1 -Validate -Input "added auth" -Suggest
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`, `perf`, `ci`, `build`

---

#### `get-branch-summary.ps1`
Get comprehensive summary of current branch work for documentation.

**Usage**:
```powershell
# Auto-detect base branch (JSON)
./get-branch-summary.ps1

# Quick summary for KANBAN.md
./get-branch-summary.ps1 -Format summary
# Branch: feature/#818_Initial_Commit (vs main)
# Commits: 1
# Changes: 100 files, +20917 -57 lines
#
# Commit hashes:
#   00c3ef5 - #818 - Initial commit.

# Compare with specific branch (text format)
./get-branch-summary.ps1 -BaseBranch develop -Format text

# Markdown output for documentation
./get-branch-summary.ps1 -Format markdown

# Exclude uncommitted changes
./get-branch-summary.ps1 -IncludeUncommitted $false
```

**Output formats**: `json` (default), `text`, `summary`, `markdown`

**Features**:
- Auto-detects base branch (main/master/develop)
- Lists all commits on current branch
- Shows file changes and statistics
- Includes uncommitted changes (staged/unstaged/untracked)
- Perfect for `/update-context` automation

---

### 🤖 Automation & Documentation

#### `analyze_work_patterns.py`
Intelligently analyze work patterns from git commits by examining file changes.

**Usage**:
```powershell
# Auto-detect from current branch
./analyze_work_patterns.py -Auto

# Analyze specific commits (JSON)
./analyze_work_patterns.py -Commits "abc123f,def456g"

# Quick summary
./analyze_work_patterns.py -Auto -Format summary
# Patterns: 10
# - testing: 16 files
# - scripts: 23 files
# - standards: 18 files
```

**Detects**:
- Tests (Pester, Jest, etc.)
- Scripts (PowerShell, Bash)
- Infrastructure (Docker, CI/CD)
- Standards & documentation
- Skills, templates, automation
- Code changes by technology

---

#### `generate_kanban_entry.py`
Generate professional KANBAN.md entry descriptions from commit analysis.

**Usage**:
```powershell
# Auto-generate from current branch
./generate_kanban_entry.py -Auto

# Generate from specific commits
./generate_kanban_entry.py -Commits "abc123f,def456g"

# Concise style
./generate_kanban_entry.py -Auto -Style concise -MaxBullets 5
```

**Output example**:
```
- Established complete Claude Code template infrastructure
- Implemented automation layer with 5 event-driven hooks
- Created 23 utility scripts with comprehensive test suite
- Defined coding standards across 15 technologies
```

---

#### `generate-github-comment.ps1`
Generate structured GitHub comment with technical details from commits.

**Usage**:
```powershell
# Generate and display
./generate-github-comment.ps1 -Auto

# Generate and copy to clipboard (Windows)
./generate-github-comment.ps1 -Auto | clip

# Generate and copy to clipboard (Linux/Mac)
./generate-github-comment.ps1 -Auto | xclip -selection clipboard
```

**Sections**:
- Work Completed (summary)
- Implementation Details (by category)
- Files Modified (grouped)
- Statistics
- Commits list

---

#### `update-kanban.ps1`
Automatically update KANBAN.md with work from commits.

**Usage**:
```powershell
# Auto-detect everything (issue, commits, description)
./update-kanban.ps1

# Specify issue and commits
./update-kanban.ps1 -Ticket #123 -Commits "abc123f,def456g"

# Custom description
./update-kanban.ps1 -Ticket #123 -Description "- Custom work description"
```

**Features**:
- Searches for existing issue entry and updates (or creates new)
- Auto-detects issue ID from branch name
- Auto-generates description from commits
- Merges with existing descriptions (cumulative)
- Handles singular/plural (Commit/Commits, Ref/Refs)
- Creates automatic backup before updating

---

### 📂 Project Detection

#### `detect-project-type.ps1`
Auto-detect project type and return build/test commands.

**Usage**:
```powershell
# Detect current directory (JSON)
./detect-project-type.ps1
# → {"type":"go","technology":"Go","build":"go build","test":"go test ./..."}

# Detect specific path (text format)
./detect-project-type.ps1 -Path /path/to/project -Format text
# Type: go
# Technology: Go
# Build: go build
# Test: go test ./...

# Environment variables format
./detect-project-type.ps1 -Format env
# PROJECT_TYPE=go
# BUILD_COMMAND=go build
# TEST_COMMAND=go test ./...
```

**Supported types**: `go`, `node`, `vuejs`, `cypress`, `dotnet`, `cshtml`, `python`, `rust`, `unknown`

**Output formats**: `json` (default), `text`, `env`

---

#### `check-git-repo.ps1`
Check if directory is a git repository.

**Usage**:
```powershell
# Check current directory (JSON)
./check-git-repo.ps1

# Simple boolean output
./check-git-repo.ps1 -Format bool
# true

# Detailed info
./check-git-repo.ps1 -Info
# Branch, remote, commit count, changes status

# Check specific directory
./check-git-repo.ps1 -Path C:\path\to\dir
```

**Output formats**: `json` (default), `text`, `bool`

---

### 📝 KANBAN & Documentation

#### `search-kanban.ps1`
Search KANBAN.md for entries by issue, tag, or date.

**Usage**:
```powershell
# Find by issue
./search-kanban.ps1 -Ticket #123

# Find by tag
./search-kanban.ps1 -Tag payments

# Find by date
./search-kanban.ps1 -Date 2026-03-15

# Find by date range
./search-kanban.ps1 -DateFrom 2026-03-01 -DateTo 2026-03-15

# Custom KANBAN path + text format
./search-kanban.ps1 -Ticket #123 -Path /path/to/KANBAN.md -Format text

# Summary output
./search-kanban.ps1 -Tag payments -Format summary
```

**Output formats**: `json` (default), `text`, `summary`

---

#### `safe-read-context.ps1`
Read Claude context files with graceful error handling.

**Usage**:
```powershell
# Read KANBAN.md (JSON)
./safe-read-context.ps1 -Kanban

# Read ARCHITECTURE.md (text)
./safe-read-context.ps1 -Architecture -Format text

# Read all rules
./safe-read-context.ps1 -Rules

# Read everything
./safe-read-context.ps1 -All -Format text

# Custom path
./safe-read-context.ps1 -All -Path /path/to/project
```

**Output formats**: `json` (default), `text`

---

#### `validate-markdown.ps1`
Validate markdown files for format compliance.

**Usage**:
```powershell
# Validate KANBAN.md (auto-detect type)
./validate-markdown.ps1 -File .claude/contexts/kanban.md

# Validate ARCHITECTURE.md (explicit type)
./validate-markdown.ps1 -File .claude/contexts/architecture.md -Type architecture

# Strict validation (warnings = errors)
./validate-markdown.ps1 -File .claude/CLAUDE.md -Strict

# Summary output
./validate-markdown.ps1 -File .claude/contexts/kanban.md -Format summary
```

**Validation types**: `auto`, `kanban`, `architecture`, `claude`

**Checks**:
- Language (English only)
- Format compliance (dates, issue IDs, sections)
- Forbidden markers (TODO, PLACEHOLDER)
- Line endings (CRLF vs LF)
- Type-specific rules (Mermaid diagrams, required sections, etc.)

**Output formats**: `json` (default), `text`, `summary`

---

#### `list-files-by-extension.ps1`
List files by extension with smart exclusions.

**Usage**:
```powershell
# Find all markdown and text files
./list-files-by-extension.ps1 -Extensions ".md",".txt"

# Find C# files excluding build directories (text format)
./list-files-by-extension.ps1 -Extensions ".cs" -Exclude "bin/","obj/" -Format text

# Find Go files in specific path (list format)
./list-files-by-extension.ps1 -Path "C:\projects" -Extensions ".go" -Format list
```

**Default exclusions**: `node_modules/`, `vendor/`, `bin/`, `obj/`, `dist/`, `build/`, `.git/`, etc.

**Output formats**: `json` (default), `text`, `list`

---

#### `categorize-documentation.ps1`
Categorize documentation files into FUNCTIONAL, TECHNICAL, and PERSONAL.

**Usage**:
```powershell
# Categorize specific files
./categorize-documentation.ps1 -Files "README.md","docs/api.md","CLAUDE.local.md"

# Categorize all markdown files (text format)
Get-ChildItem *.md | ./categorize-documentation.ps1 -Format text

# Get summary only
./categorize-documentation.ps1 -Files "*.md" -Format summary
```

**Categories**:
- **FUNCTIONAL**: User-facing docs (README, user-guide, specs)
- **TECHNICAL**: Developer docs (ARCHITECTURE, API, design)
- **PERSONAL**: Local overrides (`*.local.md`)

**Output formats**: `json` (default), `text`, `summary`

---

#### `find-git-repos.ps1`
Find all git repositories in a directory tree.

**Usage**:
```powershell
# Find all git repos in current directory
./find-git-repos.ps1

# Find in specific path (list format)
./find-git-repos.ps1 -Path "C:\dev\projects" -Format list

# Search only 2 levels deep
./find-git-repos.ps1 -MaxDepth 2 -Format text
```

**Output includes**: repo path, current branch, remote info

**Output formats**: `json` (default), `text`, `list`

---

#### `read-yaml-frontmatter.ps1`
Extract and parse YAML frontmatter from markdown files.

**Usage**:
```powershell
# Extract frontmatter from skill file
./read-yaml-frontmatter.ps1 -File "SKILL.md"

# Extract and display as text
./read-yaml-frontmatter.ps1 -File "agent.md" -Format text

# Get original YAML format
./read-yaml-frontmatter.ps1 -File "hook.md" -Format yaml
```

**Supported**: Skills, agents with `---` delimited frontmatter

**Output formats**: `json` (default), `yaml`, `text`

---

#### `update-section-in-markdown.ps1`
Update a specific section in a markdown file.

**Usage**:
```powershell
# Update section 4 in CLAUDE.md
./update-section-in-markdown.ps1 -File "CLAUDE.md" -Section "4. **Project Documentation**" -Content "..."

# Update Installation section without backup
./update-section-in-markdown.ps1 -File "README.md" -Section "## Installation" -Content "..." -Backup $false
```

**Features**: Auto-backup, preserves surrounding sections, regex-based replacement

**Default**: Creates backup with timestamp

---

#### `analyze-dependencies.ps1`
Analyze project dependencies from package files.

**Usage**:
```powershell
# Analyze Node.js project
./analyze-dependencies.ps1 -File "package.json"

# Analyze Python project, show top 5 dependencies
./analyze-dependencies.ps1 -File "requirements.txt" -TopN 5 -Format text

# Analyze Rust project, summary only
./analyze-dependencies.ps1 -File "Cargo.toml" -Format summary
```

**Supported files**: `package.json`, `requirements.txt`, `Cargo.toml`, `go.mod`, `pom.xml`

**Output includes**: language, framework, dependencies, scripts

**Output formats**: `json` (default), `text`, `summary`

---

### 📊 Script for Scripts

#### `resume-project-common.ps1`
Common logic for `resume-<project>` PowerShell functions.

**Usage**: Called by `load-claude-projects.ps1` dynamically generated functions.

**Internal use only** - not meant to be called directly.

---

## 🔧 Integration with Skills

These scripts are declared in the `## Tools` section of relevant skills:

| Script | Used by Skills |
|--------|----------------|
| `extract-issue.ps1` | start-session, update-context |
| `detect-project-type.ps1` | project-setup, create-project-template |
| `safe-read-context.ps1` | start-session |
| `get-commit-info.ps1` | update-context, analyze-commit, analyze-feature |
| `search-kanban.ps1` | start-session, analyze-feature |
| `validate-markdown.ps1` | update-context, project-setup |
| `format-commit-message.ps1` | update-context |
| `check-git-repo.ps1` | All git-dependent skills |
| `list-files-by-extension.ps1` | index-documentation, analyze-code, create-project-template |
| `categorize-documentation.ps1` | index-documentation |
| `find-git-repos.ps1` | (utility script, multi-repo discovery) |
| `read-yaml-frontmatter.ps1` | skill-setup, agent-setup |
| `update-section-in-markdown.ps1` | index-documentation, project-setup |
| `analyze-dependencies.ps1` | create-project-template, detect-project-type |

---

## 🎯 Benefits

**Token Optimization**:
- ✅ Eliminates 50-100 lines of repeated bash/grep/awk logic per skill
- ✅ Reduces context size by ~30% for git-heavy operations
- ✅ Faster execution with compiled PowerShell vs interpreted bash

**Consistency**:
- ✅ Unified validation logic across all skills
- ✅ Standardized output formats (JSON, text, CSV)
- ✅ Centralized error handling

**Maintainability**:
- ✅ Fix once, benefit everywhere
- ✅ Easy to test in isolation
- ✅ Cross-platform (Windows, Linux, macOS)

**Reusability**:
- ✅ Can be called from skills, agents
- ✅ Can be invoked manually for debugging
- ✅ Can be integrated into CI/CD pipelines

---

## 🧪 Testing Scripts

All scripts support `--help` for usage information:

```powershell
./extract-issue.ps1 -?
./get-commit-info.ps1 -?
./search-kanban.ps1 -?
```

Test in current repository:

```powershell
# Test issue extraction
./extract-issue.ps1

# Test project detection
./detect-project-type.ps1

# Test git repo check
./check-git-repo.ps1 -Info

# Test commit info
./get-commit-info.ps1 -Count 5 -Format text

# Test KANBAN search (if KANBAN.md exists)
./search-kanban.ps1 -DateFrom 2026-03-01 -Format summary
```

---

## 🧪 Testing

All utility scripts are tested with **Pester** (PowerShell testing framework).

### Running Tests

```powershell
cd scripts/tests

# Run all tests
./run-all-tests.ps1

# Run specific test file
./run-all-tests.ps1 -TestFile "get-branch-summary.Tests.ps1"

# Detailed output
./run-all-tests.ps1 -Detailed
```

### Test Coverage

- ✅ 54 tests across 6 script files
- ✅ 100% passing (unit + integration + edge cases)
- ✅ Test fixtures in `tests/fixtures/`
- ✅ Auto-installs Pester if missing

**Tested scripts**:
- `read-yaml-frontmatter.ps1`
- `categorize-documentation.ps1`
- `analyze-dependencies.ps1`
- `list-files-by-extension.ps1`
- `find-git-repos.ps1`
- `update-section-in-markdown.ps1`

See `scripts/tests/README.md` for full test documentation.

---

## 📝 Requirements

- **PowerShell 7+** (cross-platform)
- **Git** (for git-related scripts)
- **Pester** (auto-installed by test runner)
- **Executable permissions** (`chmod +x *.ps1` on Linux/Mac)

All scripts include:
- ✅ Shebang `#!/usr/bin/env pwsh`
- ✅ PowerShell 7 requirement `#Requires -Version 7.0`
- ✅ Comprehensive help documentation
- ✅ Error handling with meaningful messages
- ✅ Multiple output formats
- ✅ Cross-platform compatibility

---

## 🔄 Updates

Last updated: 2026-03-16

**Recent additions**:
- **Automation suite** - 4 new scripts for complete `/update-context` automation:
  - `analyze_work_patterns.py` - Intelligent commit analysis by file patterns
  - `generate_kanban_entry.py` - Auto-generate KANBAN.md descriptions
  - `generate-github-comment.ps1` - Structured GitHub comments with technical details
  - `update-kanban.ps1` - Automatic KANBAN.md updates (search/update/create)
- `get-branch-summary.ps1` - Branch work summary for documentation automation
- `list-files-by-extension.ps1` - Smart file discovery with exclusions
- `categorize-documentation.ps1` - Documentation organization
- `find-git-repos.ps1` - Multi-repo discovery
- `read-yaml-frontmatter.ps1` - YAML frontmatter parsing
- `update-section-in-markdown.ps1` - Markdown section updates
- `analyze-dependencies.ps1` - Package file analysis
- **Pester test suite** - 54 tests for 6 scripts (100% passing)

---

## 📚 Resources

- PowerShell 7 docs: https://learn.microsoft.com/powershell/
- Git docs: https://git-scm.com/docs
- KANBAN format: See `.claude/contexts/kanban.md` template
- Commit format: See `~/.claude/CLAUDE.md` global instructions
