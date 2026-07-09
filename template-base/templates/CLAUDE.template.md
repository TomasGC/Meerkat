# Project Instructions - {{PROJECT_NAME}}

**Purpose**: {{PROJECT_TYPE}} project instructions
**Last Updated**: {{DATE}}

@~/.claude/CLAUDE.md

---

## Hard Constraints (Non-Negotiable)

### Testing Requirements

**ALL TESTS MUST PASS** - No exceptions

After any code change:
1. Build (see `.claude/contexts/commands.md`)
2. Test (see `.claude/contexts/commands.md`)
3. **If any test fails → BLOCK COMMIT**

**Coverage requirement**: ≥ {{COVERAGE_THRESHOLD}}%

---

### Version Control Rules

#### Commit Format

**Format**: `#ISSUE: type: description`

**Examples**:
```
#42: feat: add user authentication
#42: fix: resolve null reference in UserService
#42: refactor: extract repository pattern
```

**Branch naming**:
- Features: `feature/#ISSUE-description`
- Bugfixes: `bugfix/#ISSUE-description`

---

### Code Quality Standards

**Mandatory rules** (see `.claude/rules/standards-*.md`):

{{CODE_QUALITY_RULES}}

### Language Conventions

{{CONVENTIONS}}

---

### Security Requirements

**Quality Gate** (ORCA + SonarQube + OWASP Top 10):
- ✅ No new vulnerabilities
- ✅ No new bugs
- ✅ Security rating ≥ A
- ✅ Coverage ≥ {{COVERAGE_THRESHOLD}}%
- ✅ Duplications < 3%
- ✅ **ALL tests passing**

**If ANY test fails** → **BLOCK COMMIT**

---

## Operational Guidelines

### Build & Test Workflow

**Commands**: see `.claude/contexts/commands.md`

**After any code change**:
1. Build must succeed
2. All tests must pass
3. Coverage threshold met

---

### Architecture Patterns

{{ARCHITECTURE_PATTERNS}}

**Design Patterns**:
{{DESIGN_PATTERNS_LIST}}

---

### Tech Stack

{{TECH_STACK_DETAILS}}

**Dependencies**:
{{DEPENDENCIES_LIST}}

---

## Communication Style

### Language

**Code/Documentation/Commits**: English (always)
**Conversation**: {{CONVERSATION_LANGUAGE}} (can be customized in `.claude/CLAUDE.local.md`)

---

### Decision Making

**When proposing solutions**:
1. Present 2-3 alternatives
2. List pros/cons for each
3. State recommendation with reasoning
4. Wait for user choice

**Before major changes**:
1. Analyze current code
2. Propose approach with trade-offs
3. Show impact (files affected, effort estimate)
4. Get approval before coding

---

## Project Structure

### Directory Layout

{{DIRECTORY_STRUCTURE}}

---

### Key Files

{{KEY_FILES_LIST}}

---

## References

### Available Skills

{{CUSTOM_SKILLS_LIST}}

---

### Coding Standards

Located in `.claude/rules/`:

{{RULES_FILES_LIST}}

---

### API Conventions

{{API_CONVENTIONS}}

---

### Database Migrations

{{DB_MIGRATIONS}}

---

**End of Project Instructions**
