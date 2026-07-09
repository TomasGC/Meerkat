# Claude Code Settings Guide

> **TL;DR**: Works out of the box. Customize only if needed.

---

## Overview: How Settings Work

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  settings.json (Team)          settings.local.json (You)       │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Model: Sonnet    │    +     │ Model: Opus      │    =       │
│  │ Plugins: [...20] │          │ Slack: enabled   │            │
│  │ AWS: team-profile│          │ AWS: my-profile  │            │
│  └──────────────────┘          └──────────────────┘            │
│         ↓                              ↓                        │
│    Everyone uses              Your overrides win               │
│                                                                 │
│  Final config = Team defaults + Your overrides                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Mental model**: Team settings = baseline, your overrides = delta.

---

## Settings vs Instructions (What's the Difference?)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  settings.json/local.json       CLAUDE.md/local.md             │
│  (Configuration)                (Instructions)                  │
│                                                                 │
│  WHAT Claude uses        vs     HOW Claude behaves             │
│  ─────────────────              ──────────────────             │
│  • Model (Opus/Sonnet)          • Language (EN/FR/ES)          │
│  • AWS profile                  • Response style               │
│  • Plugins enabled              • Tone (concise/detailed)      │
│  • Permissions                  • Custom shortcuts             │
│                                 • Commit conventions           │
│                                                                 │
│  System-level config            Behavioral config              │
│  This guide ↓                   See: claude-instructions.md ↑  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Quick decision**:
- Want **Opus model**? → `settings.local.json` (this guide)
- Want **French conversation**? → `CLAUDE.local.md` (see `docs/claude-instructions.md`)
- Want **both**? → Configure both files (see Combined Example below)

---

## Quick Start

### New Team Members

```
┌─────────────────────────────────────────┐
│                                         │
│   1. Clone repo                         │
│         ↓                               │
│   2. Open Claude Code                   │
│         ↓                               │
│   3. ✅ Done                            │
│                                         │
│   Zero configuration required.          │
│                                         │
└─────────────────────────────────────────┘
```

**Why it works**: `settings.json` is already configured with team standards (model, permissions, plugins).

---

## Do I Need Customization?

```
                    START HERE
                        │
                        ▼
        ┌───────────────────────────────┐
        │  Happy with Sonnet model?     │
        │  Happy with team plugins?     │
        │  Using standard AWS account?  │
        └───────────────┬───────────────┘
                        │
             ┌──────────┴──────────┐
             │                     │
            YES                   NO
             │                     │
             ▼                     ▼
    ┌─────────────────┐   ┌─────────────────┐
    │ You're all set! │   │ Create override │
    │ No action needed│   │ (see below)     │
    └─────────────────┘   └─────────────────┘
```

### ✅ You need customization if:

| Persona | Scenario | Impact |
|---------|----------|--------|
| 🧠 **Complex Reasoner** | Deep architecture decisions, system design | Switch to Opus |
| ⚡ **Speed Optimizer** | Quick edits, simple refactors | Switch to Haiku |
| ☁️ **Multi-Account User** | Personal AWS, testing environments | Custom AWS profile |
| 💬 **Integrations User** | Need Slack/GitLab/Jira integration | Enable specific plugins |

### ❌ You don't need customization if:

- ✅ New to the team
- ✅ Team defaults work fine
- ✅ Not sure what settings do

---

## Customization Guide

### By Use Case

#### 🧠 For AI Model Selection

**Decision tree**:
```
Task complexity?
    │
    ├─ Simple (formatting, docs, tests)
    │  └─→ Haiku (fast, efficient)
    │
    ├─ Standard (features, refactoring)
    │  └─→ Sonnet (balanced) ← Team default
    │
    └─ Complex (architecture, algorithms)
       └─→ Opus (deep reasoning)
```

**Implementation**:

```json
// ~/.claude/settings.local.json
{
  "model": "opus"
}
```

**Pro tip**: You can also specify exact versions for consistency:
```json
{
  "model": "eu.anthropic.claude-sonnet-4-6[1m]"
}
```

---

#### ☁️ For AWS Users

**Multi-account setup**:
```
     Corporate AWS              Personal AWS
     (team profile)            (your profile)
           │                          │
           ▼                          ▼
    settings.json           settings.local.json
    (aws-team)              (aws-personal)
                                     │
                                     ▼
                            Wins (override active)
```

**Implementation**:

```json
// ~/.claude/settings.local.json
{
  "awsAuthRefresh": "aws sso login --profile my-profile",
  "env": {
    "AWS_PROFILE": "my-profile",
    "AWS_REGION": "eu-west-1"
  }
}
```

**Common profiles**:
- `aws-personal` - Your sandbox
- `aws-dev` - Development environment
- `aws-staging` - Pre-production testing

**Managing multiple profiles** (outside settings):
```bash
# List all profiles
aws configure list-profiles

# Switch profile temporarily
export AWS_PROFILE=my-profile

# Login to specific profile
aws sso login --profile my-profile
```

---

#### 🔌 For Plugin Management

**Plugin architecture**:
```
Team enables 20 plugins
    ├─ Core (always needed)
    ├─ Quality (code analysis)
    ├─ Language (LSP servers)
    └─ Integrations (GitHub, Slack, etc.)
              │
              ▼
    You override specific ones
    (enable Slack, disable CodeRabbit)
```

**Implementation**:

```json
// ~/.claude/settings.local.json
{
  "enabledPlugins": {
    "slack@claude-plugins-official": true,
    "coderabbit@claude-plugins-official": false
  }
}
```

**Available integrations**:
- `github` ✅ (enabled by default)
- `slack` ❌ (disabled, enable if needed)
- `gitlab` ❌ (disabled, enable if needed)
- `atlassian` ❌ (Jira/Confluence, disabled by default)

---

#### 🎯 Combined Configuration

**Real-world example 1** (Settings only):
```
Persona: Senior Engineer with personal AWS + Opus for architecture
```

```json
// ~/.claude/settings.local.json
{
  "model": "opus",
  "awsAuthRefresh": "aws sso login --profile personal",
  "env": {
    "AWS_PROFILE": "personal",
    "AWS_REGION": "eu-west-1"
  },
  "enabledPlugins": {
    "slack@claude-plugins-official": true
  }
}
```

---

**Real-world example 2** (Settings + Instructions):
```
Persona: French developer with Opus + personal AWS + concise responses
```

**Step 1**: Configure tools/model (settings)
```json
// ~/.claude/settings.local.json
{
  "model": "opus",
  "awsAuthRefresh": "aws sso login --profile personal-fr",
  "env": {
    "AWS_PROFILE": "personal-fr",
    "AWS_REGION": "eu-west-1"
  }
}
```

**Step 2**: Configure behavior (instructions)
```markdown
<!-- ~/.claude/CLAUDE.local.md -->
# Personal Claude Instructions

## Communication Preferences

**Conversation**: French
**Code/Docs/Commits**: English

## Response Format

**Default**: Concis et direct
```

**Result**: Opus model + French conversation + Personal AWS ✅

**See**: `docs/claude-instructions.md` for CLAUDE.local.md examples

---

**Apply changes**:
```bash
# 1. Save both files
vim ~/.claude/settings.local.json
vim ~/.claude/CLAUDE.local.md

# 2. Restart Claude Code
# All configs load at startup
```

---

## Troubleshooting

### Decision Tree

```
Settings not working?
    │
    ├─ Step 1: Did you restart?
    │     │
    │     ├─ No → Restart Claude Code
    │     └─ Yes → Continue
    │
    ├─ Step 2: Is file in correct location?
    │     │
    │     └─ Run: ls ~/.claude/settings.local.json
    │           │
    │           ├─ File not found → Wrong location
    │           └─ File exists → Continue
    │
    └─ Step 3: Is JSON valid?
          │
          └─ Run: cat ~/.claude/settings.local.json | jq .
                │
                ├─ Error → Fix JSON syntax
                └─ Success → Check settings content
```

### Common Issues

**1. Settings ignored (90% of cases)**
```
Problem: Changed settings but nothing happened
Solution: Restart Claude Code
Why: Settings load at startup, not live
```

**2. Permission denied**
```
Problem: Claude asks permission for allowed operations
Check: Operation in allowed list? (see Reference below)
Solution: Add to settings.json if team needs it
```

**3. Reset to defaults**
```bash
# Nuclear option: remove all overrides
rm ~/.claude/settings.local.json

# Restart Claude Code
# Back to team configuration
```

---

## Reference: Team Configuration

### Model Comparison

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Haiku          Sonnet          Opus                           │
│  ────────────────────────────────────────────────              │
│  Speed: ⚡⚡⚡    Speed: ⚡⚡       Speed: ⚡                      │
│  Reason: ⭐      Reason: ⭐⭐⭐    Reason: ⭐⭐⭐⭐⭐              │
│  Cost: $         Cost: $$        Cost: $$$                     │
│                                                                │
│  Use for:        Use for:        Use for:                     │
│  • Formatting    • Features      • Architecture               │
│  • Docs          • Refactoring   • Algorithms                 │
│  • Tests         • Code review   • System design              │
│                  ↑ Team default                               │
└────────────────────────────────────────────────────────────────┘
```

### Permissions Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Auto-approved ✅          Requires approval ⚠️                 │
│  ─────────────────────────────────────────────                 │
│  • Read files              • Delete files                      │
│  • Search code             • Move files                        │
│  • Run tests               • Git commit                        │
│  • Build project           • Git push                          │
│  • View git history        • Destructive ops                   │
│  • Edit .claude/ files                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Why this matters**: Fast feedback loop for safe operations, gate for risky ones.

### Plugin Categories

```
Core Workflow (6)
├─ superpowers - Enhanced capabilities
├─ frontend-design - Component creation
├─ feature-dev - Feature workflow
├─ pr-review-toolkit - PR automation
├─ claude-md-management - Config maintenance
└─ ralph-loop - Continuous execution

Code Quality (5)
├─ code-simplifier - Quality improvements
├─ coderabbit - AI code review
├─ qodo-skills - Standards enforcement
├─ security-guidance - Security checks
└─ semgrep - Static analysis

Language Support (3)
├─ typescript-lsp - TypeScript
├─ csharp-lsp - C#
└─ gopls-lsp - Go

Integrations (4)
├─ github ✅ (enabled)
├─ slack ❌ (disabled by default)
├─ gitlab ❌ (disabled by default)
└─ atlassian ❌ (disabled by default)

Development Tools (4)
├─ context7 - Documentation search
├─ skill-creator - Skill development
├─ plugin-dev - Plugin development
└─ explanatory-output-style - Educational mode
```

**Full details**: See `~/.claude/settings.json`

---

## FAQ

**Q: Will my overrides be committed to git?**  
A: No. `*.local.*` files are gitignored.

**Q: How do I see active settings?**  
A: `settings.json` (team) + `settings.local.json` (yours) = active config

**Q: Team changed settings, do mine break?**  
A: No. Your overrides still apply. Team changes affect non-overridden settings only.

**Q: How do I update team settings?**  
A: Discuss with team → Update `settings.json` → Commit → Team pulls → Restart

**Q: Can I switch models per task?**  
A: Not via settings (startup only). Use model selector in UI for per-task switching.

---

## Architecture Notes (Advanced)

### Merge Strategy

```javascript
// Simplified merge logic
const activeConfig = {
  ...loadTeamSettings(),      // settings.json
  ...loadPersonalSettings()   // settings.local.json (if exists)
}

// Personal overrides win
// Missing keys in personal → use team defaults
```

### File Discovery

```
Startup sequence:
1. Load ~/.claude/settings.json (required)
2. Check ~/.claude/settings.local.json (optional)
3. Merge (local overrides team)
4. Validate schema
5. Apply configuration
```

### Best Practices

✅ **Do**:
- Override only what you need
- Document why you override (comments in JSON)
- Test changes in safe environment first
- Keep team informed of common overrides

❌ **Don't**:
- Copy entire settings.json to settings.local.json
- Override permissions without team discussion
- Commit settings.local.json
- Override critical security settings

---

## Quick Reference

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  What to configure         Where                               │
│  ──────────────────────────────────────────────────────────    │
│  Model (Opus/Sonnet)   →   settings.local.json (this file)    │
│  AWS profile           →   settings.local.json (this file)    │
│  Plugins               →   settings.local.json (this file)    │
│  Permissions           →   settings.json (team, discuss first)│
│                                                                │
│  Language preference   →   CLAUDE.local.md (see other guide)  │
│  Response style        →   CLAUDE.local.md (see other guide)  │
│  Custom shortcuts      →   CLAUDE.local.md (see other guide)  │
│  Commit conventions    →   CLAUDE.local.md (see other guide)  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Two config systems**:
- **Settings** (this file): WHAT Claude uses (tools, models, permissions)
- **Instructions** (`docs/claude-instructions.md`): HOW Claude behaves (language, tone)

---

## Related Documentation

- **Instructions Guide**: `docs/claude-instructions.md` - Configure language, tone, shortcuts
- **Integration Profiles**: `docs/integrations.md` - VCS, CI, docs, issues provider configuration
- **Rules Overview**: `~/.claude/rules/standards-*.md` - Team coding standards
- **Contexts System**: `~/.claude/contexts/*.md` - Project context files

---

## Need Help?

1. ✅ Check this guide (you're here)
2. 💬 Ask in team chat
3. 📚 [Claude Code Documentation](https://docs.anthropic.com/claude-code)
4. 🐛 [Report Issues](https://github.com/anthropics/claude-code/issues)

**Remember**: 90% of users never create `settings.local.json`. Start simple, customize when you have a clear need.
