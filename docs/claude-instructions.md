# Claude Instructions Guide

> **TL;DR**: CLAUDE.md = team rules (committed). CLAUDE.local.md = your style (gitignored). 90% of users never need customization.

---

## Why This Matters to You

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  CLAUDE.md                         CLAUDE.local.md              │
│  (Team rules)                      (Your style)                 │
│                                                                 │
│  ┌───────────────────┐            ┌───────────────────┐        │
│  │ WHAT to do        │      +     │ HOW to say it     │   =    │
│  │                   │            │                   │        │
│  │ • Tests must pass │            │ • Talk in French  │        │
│  │ • Show diffs      │            │ • Be concise      │        │
│  │ • Git format      │            │ • No AI refs      │        │
│  └───────────────────┘            └───────────────────┘        │
│          ↓                                 ↓                    │
│    Affects quality             Affects communication           │
│    (don't override)            (safe to customize)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Golden rule**: Override **style** (how Claude talks), not **substance** (what Claude does).

---

## Do You Need This?

### 3 Common Personas

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  🌍 Non-English Speaker          ⚡ Minimalist                 │
│  ───────────────────────         ──────────────                │
│  Problem:                        Problem:                      │
│  Thinking in French/Spanish      Too much explanation          │
│  but coding in English           Just want the code            │
│                                                                │
│  Solution:                       Solution:                     │
│  Language override               Response style override       │
│  • Convo: Your language          • Ultra-concise mode          │
│  • Code: English                 • Code blocks only            │
│                                                                │
│  Time to setup: 2 min            Time to setup: 1 min          │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  🎯 Power User                                                 │
│  ──────────────                                                │
│  Problem:                                                      │
│  Typing same commands repeatedly                              │
│  Want custom workflows                                         │
│                                                                │
│  Solution:                                                     │
│  Custom shortcuts + conventions                                │
│  • "context" = reload all files                               │
│  • "go" = validate and execute                                │
│  • Personal commit rules                                       │
│                                                                │
│  Time to setup: 5 min                                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Not you?** → Skip this guide. Team defaults work great.

---

## Quick Wins (2 Minutes)

**Choose your flavor**:

```bash
# 1. Language only (Non-English speakers)
cat > ~/.claude/CLAUDE.local.md << 'EOF'
# Personal Claude Instructions

## Communication Preferences

**Conversation**: [French/Spanish/German/etc.]
**Code/Docs/Commits**: English
EOF

# 2. Response style only (Minimalists)
cat > ~/.claude/CLAUDE.local.md << 'EOF'
# Personal Claude Instructions

## Response Format

**Default**: Ultra-concise
- One sentence max
- Code only
- No explanations unless asked
EOF

# 3. Both (Language + Style)
cat > ~/.claude/CLAUDE.local.md << 'EOF'
# Personal Claude Instructions

## Communication Preferences

**Conversation**: [Your language]
**Code/Docs/Commits**: English

## Response Format

**Default**: [Concis/Conciso/Kurz]
- Short responses
- Code only
- No explanations unless asked
EOF
```

**Apply changes**: Restart session or say `"relis CLAUDE.local.md"`

---

## Use Cases by Persona

### 🌍 Non-English Speaker

**Why it matters**:
```
Native language → Faster comprehension → Better decisions
     ↓
English code → Team collaboration → No friction
```

**Configuration**:

```markdown
# Personal Claude Instructions

## Communication Preferences

**Conversation**: [French/Spanish/German/Portuguese/Italian/Japanese/Korean]
**Code/Docs/Commits**: English (always)
```

**Copy-paste template** → Replace `[Your language]` → Done ✅

---

### ⚡ Minimalist

**Response spectrum**:
```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Verbose          Balanced          Minimal                  │
│  ────────────────────────────────────────────                │
│  Paragraphs       Mixed             1-2 sentences            │
│  Explanations     Reasoning         Code only                │
│  Examples         Some context      Zero fluff               │
│                   ↑                 ↑                        │
│                   Team default      You want this            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Configuration**:

```markdown
# Personal Claude Instructions

## Response Format

**Default (ultra-concise)**:
- ✅ 1-2 sentences max
- ✅ Code blocks only
- ✅ No explanations unless asked
- ❌ No verbose reasoning

**Exception**: When I say "explain", "why", or "how"
```

**Trigger words**: `explain`, `why`, `how does this work` → activates detailed mode

---

### 🎯 Power User

**Workflow optimization**:
```
Before:                          After:
"Read KANBAN, ARCHITECTURE,  →   "context"
CLAUDE.md, and all rules"        (1 word, same result)

"Show me git status,         →   "status"
current branch, and          
last 3 commits"                   (1 word, full status)

"Validate the diff and       →   "go"
execute the changes"              (1 word, executes)
```

**Configuration**:

```markdown
# Personal Claude Instructions

## Communication Preferences

**Conversation**: [Your language]
**Code/Docs/Commits**: English

## Custom Shortcuts

**"context"** = Re-read all context files:
- `.claude/contexts/kanban.md`
- `.claude/contexts/architecture.md`
- `.claude/CLAUDE.md`
- `.claude/rules/**/*.md`

**"go"** = Validate changes and execute immediately

**"status"** = Full project status:
- Git status + branch
- Last 3 commits
- Pending tasks from KANBAN

## Personal Conventions

**Commit messages**:
- ❌ No AI tool references
- ❌ No stats (+XX lines)
- ❌ No emoji
- ✅ Business value only

Good: `#123: feat: add caching for faster page loads`
Bad: `#123: feat: add caching (+150 lines) 🎉 (Co-Authored-By: Claude)`
```

---

## When to Use Global vs Project-Specific

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    START: Need customization                    │
│                              │                                  │
│                    ┌─────────┴─────────┐                        │
│                    │                   │                        │
│              Same for ALL         Different per                 │
│              projects?            project?                       │
│                    │                   │                        │
│                    ▼                   ▼                        │
│                                                                 │
│     ~/.claude/CLAUDE.local.md    <project>/.claude/            │
│            (Global)               CLAUDE.local.md               │
│                                   (Project-specific)            │
│     Use for:                      Use for:                      │
│     • Language preference         • Legacy project has          │
│     • Response style                different conventions       │
│     • Personal shortcuts          • Client project needs        │
│                                     specific tone               │
│                                   • Experimental project        │
│                                     uses different workflow     │
│                                                                 │
│     Applies: Everywhere           Applies: This project only   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Example scenario**:

```bash
# Global: French for all projects
~/.claude/CLAUDE.local.md
→ Conversation: French

# But: Legacy project has English comments everywhere
~/projects/legacy/.claude/CLAUDE.local.md
→ Conversation: English (overrides global for this project)
```

---

## File Structure & Load Sequence

```
Session Startup
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Load Team Configuration                                      │
│                                                                 │
│    CLAUDE.md ✅ ──────┬─→ @contexts/kanban.md ✅                │
│                       ├─→ @contexts/architecture.md ✅          │
│                       ├─→ @contexts/commands.md ✅              │
│                       └─→ @contexts/conventions.md ✅           │
│                                └─→ @conventions.local.md ❌     │
│                                    (if exists)                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Load Personal Configuration                                  │
│                                                                 │
│    CLAUDE.local.md ❌ ─┬─→ @contexts/kanban.local.md ❌         │
│                        ├─→ @contexts/architecture.local.md ❌   │
│                        └─→ @contexts/commands.local.md ❌       │
│                            (all optional)                       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Merge Strategy                                               │
│                                                                 │
│    Team rules (CLAUDE.md)        Personal style (local)        │
│           ↓                              ↓                      │
│    WHAT Claude does         +    HOW Claude talks              │
│           ↓                              ↓                      │
│    Base behavior                 Overrides win                 │
│                                                                 │
│    Result: Team consistency + Your preferences                 │
└─────────────────────────────────────────────────────────────────┘

Legend:
  ✅ = Committed (team, always loaded)
  ❌ = Gitignored (personal, optional)
```

**Directory tree**:

```
~/.claude/
│
├─ CLAUDE.md ✅                  # Team rules (WHAT to do)
├─ CLAUDE.local.md ❌            # Your style (HOW to say it)
│
├─ contexts/
│   ├─ kanban.md ✅              # Work history (team)
│   ├─ kanban.local.md ❌        # Your notes (optional)
│   │
│   ├─ architecture.md ✅        # System design (team)
│   ├─ architecture.local.md ❌  # Your research (optional)
│   │
│   ├─ commands.md ✅            # Scripts/commands (team)
│   ├─ commands.local.md ❌      # Your aliases (optional)
│   │
│   ├─ conventions.md ✅         # Standards (team)
│   └─ conventions.local.md ❌   # Your commit preferences (auto-created)
│
├─ rules/ ✅                     # Coding standards (team)
│   └─ standards-*.md ✅         # DRY, SOLID, security, testing, etc.
│
└─ docs/ ✅                      # User guides (team)
    ├─ settings.md ✅            # Models, AWS, plugins config
    └─ claude-instructions.md ✅ # This guide
```

---

## What's in CLAUDE.md (Reference)

<details>
<summary><strong>Click to expand: Team rules you shouldn't override</strong></summary>

### Hard Constraints

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  File Modification: Show diff → Wait approval → Execute     │
│  Testing: ALL TESTS MUST PASS before commit                 │
│  Git Format: "type: description"                            │
│  Documentation: Public (.md) vs Private (.local.*)          │
│                                                              │
│  Why: Team quality, safety, collaboration standards         │
│  Override? NO (affects everyone)                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Operational Guidelines

**See**: `docs/settings.md` for details on:
- Session startup (auto-loading)
- Build & test workflows
- Permission strategy (allow vs ask)

### Communication Style (Safe to Override)

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Language: Code/Docs (English), Conversation (Customizable) │
│  Decision Making: Analyze → Alternatives → Wait choice      │
│  Proposals: 2-3 options with pros/cons                      │
│                                                              │
│  Why: Consistent collaboration                              │
│  Override? YES in CLAUDE.local.md (language, tone, format)  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

</details>

---

## Examples Comparison

| Persona | Language | Style | Shortcuts | Length | Setup Time |
|---------|----------|-------|-----------|--------|------------|
| **Minimalist** | English | Code only | None | 5 lines | 30 sec |
| **French Dev** | French convo<br>English code | Concise | None | 8 lines | 1 min |
| **Power User** | French convo<br>English code | Minimalist | context, go, build | 20 lines | 3 min |
| **Spanish Dev** | Spanish convo<br>English code | Detailed | None | 15 lines | 2 min |

**Copy templates from**: See "Quick Wins" section above for ready-to-use configs

---

## Troubleshooting

### Quick Fixes

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Problem              Solution                 Time             │
│  ─────────────────────────────────────────────────────          │
│  Language not         Say: "parle en français" Instant          │
│  applying             → switches immediately                    │
│                       Then restart for permanent                │
│                                                                 │
│  Changes not visible  Say: "relis CLAUDE.local.md" Instant     │
│                       → reloads preferences                     │
│                                                                 │
│  Too complex,         rm ~/.claude/CLAUDE.local.md 10 sec      │
│  start over           → back to team defaults                  │
│                                                                 │
│  File location wrong  Must be:                   Check path    │
│                       ~/.claude/CLAUDE.local.md                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Still stuck?** Check `docs/settings.md` for related configuration issues.

---

## What NOT to Override

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  ❌ Don't override              ✅ Safe to override            │
│  ──────────────────             ───────────────                │
│  • Testing requirements         • Conversation language        │
│  • Git workflows                • Response format              │
│  • Code quality standards       • Personal shortcuts           │
│  • Permission strategies        • Tone preferences             │
│  • Architecture principles      • Custom conventions           │
│                                   (non-conflicting)            │
│  Why? Breaks team               Why? Personal only             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Test**: If it affects other team members → don't override.

---

## FAQ

**Q: Does this file get committed?**  
A: No. `.local.*` = gitignored automatically.

**Q: Will team CLAUDE.md changes break my overrides?**  
A: No. Your overrides still apply. Team changes only affect non-overridden sections.

**Q: Can I switch languages mid-session?**  
A: Yes. Say "parle en français" or "speak English" anytime.

**Q: How do I reset to team defaults?**  
A: `rm ~/.claude/CLAUDE.local.md` then restart session.

**Q: Can I have different settings per project?**  
A: Yes. `<project>/.claude/CLAUDE.local.md` overrides `~/.claude/CLAUDE.local.md`.

**Q: Where are model/AWS/plugin settings?**  
A: See `docs/settings.md` - different file, different purpose.

---

## Quick Reference

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  What to customize         Where                               │
│  ──────────────────────────────────────────────────            │
│  Language preference   →   CLAUDE.local.md                     │
│  Response style        →   CLAUDE.local.md                     │
│  Custom shortcuts      →   CLAUDE.local.md                     │
│  Commit conventions    →   contexts/conventions.local.md       │
│                                                                │
│  Model (Opus/Sonnet)   →   settings.local.json (see settings.md) │
│  AWS profile           →   settings.local.json (see settings.md) │
│  Plugins               →   settings.local.json (see settings.md) │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Two config systems**:
- **Instructions** (this file): HOW Claude communicates
- **Settings** (`docs/settings.md`): WHAT Claude uses (models, tools, permissions)

---

## Related Documentation

- **Settings Guide**: `docs/settings.md` - Configure models, AWS, plugins, permissions
- **Coding Standards**: `~/.claude/rules/standards-*.md` - Team coding conventions
- **Contexts System**: Auto-loaded files with team/personal split (see File Structure above)

---

**Remember**: 90% of users never customize. Team defaults work great. Start minimal (language + style), expand only when you have clear needs.
