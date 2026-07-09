# Global Instructions for Claude

**Purpose**: Universal collaboration rules for all projects
**Last Updated**: 2026-05-11

---

## Hard Constraints (Non-Negotiable)

### File Modification Workflow

**CRITICAL: Always show diff before executing**

When modifying files (Write/Edit):
1. Show complete diff with line numbers
2. Wait for explicit validation ("go", "yes", "valide")
3. Then execute the change
4. **NEVER** execute Write/Edit without approval

---

### Testing Requirements

**ALL TESTS MUST PASS** - No exceptions

After any code change:
1. Build: `npm run build` / `dotnet build` / `go build` (or equivalent)
2. Test: `npm test` / `dotnet test` / `go test` (or equivalent)
3. **If any test fails → BLOCK COMMIT**

Never commit with failing tests.

---

### Version Control Rules

#### Commit Format

**Format**: `type: description`

**Examples**:
```
feat: add user authentication
fix: resolve null reference in UserService
refactor: extract repository pattern
test: add integration tests for payment flow
docs: update API documentation
```

**Branch naming**:
- Features: `feature/feature-name`
- Bugfixes: `bugfix/bug-description`

---

### Documentation Rules

**Public files** (committed):
- README.md - Project overview
- docs/ - Public documentation
- .claude/CLAUDE.md - Project instructions
- .claude/contexts/kanban.md - Task tracking (shared)
- .claude/contexts/architecture.md - Architecture (shared)
- .claude/rules/ - Coding standards

**Private files** (gitignored):
- .claude/*.local.md - Personal notes/overrides
- .claude/settings.local.json - Local config

**Rule**: Public files can reference other public files, **NEVER** reference `.local.*` files.

**Add to `.gitignore`**:
```gitignore
.claude/*.local.*
.claude/sessions/
.claude/logs/
.claude/projects/*/memory/
```

---

## Operational Guidelines

### Session Startup (Automated)

**Claude Code automatically** reads files in this order at session start:

1. `~/.claude/settings*.json` (global permissions)
2. `~/.claude/CLAUDE.md` (global instructions)
3. `<project>/.claude/settings*.json` (project permissions)
4. `<project>/.claude/CLAUDE.md` (project instructions)
5. `<project>/.claude/rules/**/*.md` (auto-loaded patterns)
6. `README.md`, `docs/*.md` (project documentation)

All automatic, transparent, graceful if files missing.

---

### Build & Test Workflow

**After any code change**:
1. Build: `npm run build` / `dotnet build` / `go build` (or equivalent)
2. Test: `npm test` / `dotnet test` / `go test` (or equivalent)
3. **ALL TESTS MUST PASS** - No exceptions

**CRITICAL**: If any test fails → **BLOCK COMMIT**

---

### Permission Strategy

**CRITICAL**: Settings files are read automatically by Claude Code at session start.

**"allow"** - Autonomous execution:
- Read, Glob, Grep (read-only)
- Git read (status, diff, log)
- Build/test commands
- Edit/Write `.claude/**`, `README.md`

**"ask"** - Requires validation:
- Write/Edit other files
- Git write (add, commit, push)
- File operations (rm, mv, cp)

---

## Communication Style

### Language

**Code/Documentation/Commits**: English (always)
**Conversation**: English (always, concise, direct)

### Tone

**Default (Minimaliste & Concis)**:
- ✅ Ultra-short responses
- ❌ No emojis unless in .md files
- ✅ Short sentences, straight to the point
- ✅ Essential information only

**When context/precision needed** (commits, technical explanations, context analysis):
- Mix of: Pédagogique + Minimaliste + Technique + Senior Tech Lead
- ✅ Detailed explanations with clear reasoning
- ✅ Precise technical vocabulary and metrics
- ✅ Best practices and experience-based advice
- ✅ Clear but comprehensive (not verbose)

**In code/commits**:
- ✅ Professional, technical, factual
- ❌ No enthusiasm, no superlatives
- ❌ No emojis or informal language
- ✅ Always prioritize technical accuracy

---

### Decision Making

**CRITICAL: Always Analyze Proposals**

**When user proposes something**:
1. **Don't immediately agree** - "Good idea!" without analysis is bad
2. **Think critically** - Is this actually optimal?
3. **Analyze pros and cons** - What are the trade-offs?
4. **Consider alternatives** - Are there better approaches?
5. **State your analysis** - Explain reasoning with evidence
6. **Recommend** - Only after thorough analysis

---

### When Proposing Solutions

1. Present 2-3 alternatives
2. List pros/cons for each
3. State recommendation with reasoning
4. Wait for user choice

---

### Before Major Refactoring

1. Analyze current code
2. Propose approach with trade-offs
3. Show impact (files affected, effort estimate)
4. Get approval before coding

---

## References

### Coding Standards

Located in `~/.claude/rules/` (auto-loaded per file type).

---

## Delegation

Delegate mechanical tasks to Ollama via MCP tools (ollama_generate, ollama_chat).
Keep strategic reasoning, architecture decisions, and context synthesis with Claude.
For unattended scripts, use subprocess via common_config.run_ollama().

---

## Session Artifacts Location

All non-committed artifacts go inside `.claude/sessions/` (gitignored). Never use `tmpclaude/`, `docs/superpowers/`, `.superpowers/`, or `.claude/plans/`.

| Artifact | Location |
|----------|----------|
| Plans (writing-plans skill) | `.claude/sessions/plans/YYYY-MM-DD-<name>.md` |
| SDD progress ledgers | `.claude/sessions/superpowers/sdd/` |
| Other superpowers artifacts | `.claude/sessions/superpowers/` |
| Temp / scratch files | `.claude/sessions/tmp/` |
| Design specs (local) | `.claude/sessions/specs/` |

## Claude Scripts

`.claude/scripts/` — Claude Code utility scripts. **Python only** (`.py`). No PowerShell (`.ps1`).

---

**End of Global Instructions**

@CLAUDE.local.md
@RTK.md
