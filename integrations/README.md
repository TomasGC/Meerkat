# Integration Profiles

One file per profile. Add your custom profiles here (gitignored).

## Structure

```
integrations/
├── .active                  # Current active profile name (gitignored)
├── default.json            # Committed (default GitHub profile)
├── work.local.json          # Gitignored (your private work setup)
├── company.local.json       # Gitignored (your private company setup)
└── README.md                # This file (committed)
```

## Profile Format

Each profile file is JSON:

```json
{
  "name": "Profile Description",
  "vcs": {
    "provider": "your-vcs-provider",
    "url": "https://...",
    "api_url": "https://..."
  },
  "ci": {
    "provider": "your-ci-provider"
  },
  "docs": {
    "provider": "your-docs-provider",
    "url": "https://..." 
  },
  "issues": {
    "provider": "your-issues-provider",
    "url": "https://...",
    "ticket_format": "regex pattern"
  }
}
```

## Usage

**Switch profile**:
```bash
python ~/.claude/scripts/cli/switch-profile.py azure
```

**List profiles**:
```bash
python ~/.claude/scripts/cli/switch-profile.py --list
```

## Git

- `default.json` → Committed (default)
- `*.json` (others) → Gitignored (your private configs)
- `.active` → Gitignored (your current choice)
