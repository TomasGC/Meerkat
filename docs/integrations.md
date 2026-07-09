# Integration Profiles Guide

> **TL;DR**: Default is GitHub (zero config). Custom profiles let you switch between work/personal accounts or add future providers (GitLab, Azure DevOps, etc.).

---

## Why This Matters to You

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Without Profiles          With Profiles                        │
│  ────────────────           ─────────────                       │
│  Hardcoded GitHub    →      Switch instantly                    │
│  One environment     →      Multiple environments               │
│  Change code         →      Change config only                  │
│                                                                 │
│  Problem:                   Solution:                           │
│  Work + Personal GitHub     Profile per context                 │
│  → Manual URL changes       → Automatic switching               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Golden rule**: Default works for 90%. Profiles = flexibility for multi-account or future extensibility.

---

## Do You Need This?

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  👤 Single Account           🏢 Multi-Account                  │
│  ──────────────              ─────────────                     │
│  Problem: None               Problem:                          │
│  Just GitHub personal        Work GitHub + Personal GitHub     │
│                              → Need to switch contexts         │
│                                                                │
│  Solution: Skip this         Solution: Create profiles         │
│  Default works perfectly     • work.json (team repos)          │
│                              • personal.json (side projects)   │
│                                                                │
│  Time to setup: 0 min        Time to setup: 3 min              │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  🔮 Future-Proof                                               │
│  ────────────────                                              │
│  Problem:                                                      │
│  Might migrate to GitLab/Azure DevOps later                   │
│  Want architecture ready                                       │
│                                                                │
│  Solution: Profile system extensible                           │
│  • Add gitlab.json when needed                                │
│  • Scripts auto-adapt                                          │
│  • No code changes required                                    │
│                                                                │
│  Time to setup: 0 min (architecture ready)                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Not you?** → Skip this guide. Default GitHub works perfectly.

---

## Quick Start

### Default (Zero Config)

```
Already done ✅
    ↓
default.json (GitHub) is active
    ↓
No action needed
```

---

### Multi-Account Setup

**Scenario**: Work repos + Personal repos (both GitHub, different orgs)

```bash
# 1. Create work profile
cat > ~/.claude/integrations/work.json << 'EOF'
{
  "name": "Work GitHub",
  "vcs": { "provider": "github", "url": "https://github.com" },
  "ci": { "provider": "github-actions" },
  "docs": { "provider": "github-wiki" },
  "issues": { "provider": "github", "issue_format": "#(\\d+)" }
}
EOF

# 2. Create personal profile
cat > ~/.claude/integrations/personal.json << 'EOF'
{
  "name": "Personal GitHub",
  "vcs": { "provider": "github", "url": "https://github.com" },
  "ci": { "provider": "github-actions" },
  "docs": { "provider": "github-pages" },
  "issues": { "provider": "github", "issue_format": "#(\\d+)" }
}
EOF

# 3. Manual switch (option A)
python ~/.claude/scripts/cli/switch-profile.py work
python ~/.claude/scripts/cli/switch-profile.py personal

# OR 4. Auto-switch by directory (option B)
cat > ~/.claude/integrations/path-mappings.local.json << 'EOF'
{
  "mappings": [
    { "path": "C:/dev/work", "profile": "work" },
    { "path": "C:/dev/personal", "profile": "personal" }
  ]
}
EOF
```

**Result**: Scripts auto-use correct profile based on context ✅

---

## How It Works

### Priority Flow

```
Script calls load_integrations()
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Check path mappings?             │
│    (path-mappings.local.json)       │
│         │                            │
│    Match found? ──┐                  │
│         │         │                  │
│        Yes       No                  │
│         │         │                  │
│         │         ▼                  │
│         │   ┌─────────────────────┐ │
│         │   │ 2. Check .active?   │ │
│         │   │                     │ │
│         │   │  Found? ──┐         │ │
│         │   │    │       │         │ │
│         │   │   Yes     No         │ │
│         │   │    │       │         │ │
│         │   │    │       ▼         │ │
│         │   │    │   ┌─────────┐   │ │
│         │   │    │   │ 3. Use  │   │ │
│         │   │    │   │ default │   │ │
│         │   │    │   └─────────┘   │ │
│         │   │    │       │         │ │
│         │   └────┴───────┘         │ │
│         └──────────┐                │ │
│                    ▼                │ │
└─────────────────────────────────────┘ │
                     │                  │
                     ▼                  │
        Load {profile}.json             │
                     │                  │
                     ▼                  │
              Return config             │
```

**Priority**: Path-based > Manual (.active) > Default (GitHub)

---

### File Structure

```
~/.claude/integrations/
│
├── .active ❌                      # Current profile (gitignored)
├── .gitignore ✅                   # Ignores *.json except default
│
├── default.json ✅                 # GitHub (committed, everyone)
│
├── work.json ❌                    # Your work profile (gitignored)
├── personal.json ❌                # Your personal profile (gitignored)
│
└── path-mappings.local.json ❌     # Auto-switch rules (gitignored)

✅ = Committed (team)
❌ = Gitignored (personal)
```

---

## Profile Format Reference

```json
{
  "name": "Profile Name",
  "vcs": {
    "provider": "github",              // github, gitlab, bitbucket, etc.
    "url": "https://github.com",
    "api_url": "https://api.github.com"
  },
  "ci": {
    "provider": "github-actions"       // github-actions, gitlab-ci, etc.
  },
  "docs": {
    "provider": "github-pages"         // github-pages, confluence, etc.
  },
  "issues": {
    "provider": "github",              // github, jira, linear, etc.
    "issue_format": "#(\\d+)"          // #123 (GitHub), PROJ-456 (JIRA)
  }
}
```

**Future extensibility**: Architecture supports GitLab, Azure DevOps, etc. (not yet implemented).

---

## Commands

| Command | Result |
|---------|--------|
| `switch-profile.py` | Show current profile |
| `switch-profile.py --list` | List all profiles |
| `switch-profile.py work` | Switch to work profile |
| `switch-profile.py --format json` | JSON output |

**See**: `~/.claude/contexts/commands.md` for full commands reference

---

## Troubleshooting

### Profile not switching?

```bash
# Check active profile
cat ~/.claude/integrations/.active

# If wrong: Switch manually
python ~/.claude/scripts/cli/switch-profile.py work
```

---

### Path-based auto-switch not working?

```bash
# Check mappings exist
cat ~/.claude/integrations/path-mappings.local.json

# Check current directory matches
pwd  # Should start with one of the mapped paths
```

---

### Reset to default

```bash
rm ~/.claude/integrations/.active
# Now uses default.json (GitHub)
```

---

## Examples by Scenario

### Scenario 1: Work + Personal (Manual Switch)

```bash
# Morning: Work on company project
cd ~/work/company-repo
python ~/.claude/scripts/cli/switch-profile.py work

# Evening: Personal side project
cd ~/personal/my-app
python ~/.claude/scripts/cli/switch-profile.py personal
```

---

### Scenario 2: Work + Personal (Auto-Switch)

```bash
# One-time setup
cat > ~/.claude/integrations/path-mappings.local.json << 'EOF'
{
  "mappings": [
    { "path": "/home/user/work", "profile": "work" },
    { "path": "/home/user/personal", "profile": "personal" }
  ]
}
EOF

# Then: Just cd anywhere
cd ~/work/company-repo      # Auto-uses "work"
cd ~/personal/my-app        # Auto-uses "personal"
```

---

### Scenario 3: Future GitLab Migration

```bash
# Company migrates to GitLab (future)
cat > ~/.claude/integrations/gitlab.json << 'EOF'
{
  "name": "GitLab",
  "vcs": { "provider": "gitlab", "url": "https://gitlab.com" },
  "ci": { "provider": "gitlab-ci" },
  "docs": { "provider": "gitlab-wiki" },
  "issues": { "provider": "gitlab", "issue_format": "#(\\d+)" }
}
EOF

python ~/.claude/scripts/cli/switch-profile.py gitlab
# Scripts adapt automatically (when GitLab support is implemented)
```

---

## Advanced: Programmatic Usage

<details>
<summary><strong>Click to expand: Python API for scripts</strong></summary>

### Load Current Profile

```python
from common.integrations import load_integrations

config = load_integrations()

print(config.vcs_provider)      # github
print(config.ci_provider)       # github-actions
print(config.issue_format)      # #(\d+)
```

### Shortcut Functions

```python
from common.integrations import (
    get_vcs_provider,
    get_issues_provider,
    get_issue_format
)

vcs = get_vcs_provider()        # "github"
issues = get_issues_provider()  # "github"
pattern = get_issue_format()    # "#(\d+)"
```

**Full API**: See `~/.claude/scripts/common/integrations.py`

</details>

---

## FAQ

**Q: Do I need to create profiles?**  
A: No. Default (GitHub) works for 90% of users.

**Q: What's the difference between work and personal profiles?**  
A: Just naming. Both can use GitHub but help mentally separate contexts.

**Q: Can I have different issue formats?**  
A: Yes. JIRA (`PROJ-123`), GitHub (`#123`), etc. Customize via `issue_format`.

**Q: Will my profiles be committed?**  
A: No. `*.json` (except `default.json`) are gitignored.

**Q: Can I use multiple providers simultaneously?**  
A: No. One active profile at a time. Switch as needed.

**Q: What providers are supported now?**  
A: GitHub only. Architecture ready for GitLab, Azure DevOps, etc.

**Q: How do path mappings work with nested directories?**  
A: Uses longest matching prefix. `/home/user/work/project1` matches `/home/user/work`.

---

## Quick Reference

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  File                              Purpose                     │
│  ──────────────────────────────────────────────────            │
│  default.json ✅                   Team default (GitHub)       │
│  work.json ❌                      Your work profile           │
│  personal.json ❌                  Your personal profile       │
│  path-mappings.local.json ❌       Auto-switch rules           │
│  .active ❌                        Current profile name        │
│                                                                │
│  Profile Fields                    Values                      │
│  ──────────────────────────────────────────────────            │
│  vcs.provider                      github, gitlab, etc.        │
│  ci.provider                       github-actions, etc.        │
│  docs.provider                     github-pages, etc.          │
│  issues.provider                   github, jira, etc.          │
│  issues.issue_format               #(\d+), PROJ-(\d+), etc.   │
│                                                                │
│  ✅ = Committed    ❌ = Gitignored                             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- **Settings Guide**: `docs/settings.md` - Models, AWS, plugins configuration
- **Instructions Guide**: `docs/claude-instructions.md` - Language, tone, shortcuts
- **Commands Reference**: `~/.claude/contexts/commands.md` - All script commands

---

**Remember**: 90% of users never create custom profiles. GitHub default works perfectly. Profiles = flexibility for multi-account or future providers.
