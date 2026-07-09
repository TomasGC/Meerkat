---
name: start-session
description: Load project context (issue, KANBAN) and offer to read GitHub issue. Delegates to shared PowerShell script.
---

# Start Session

Load project context for current work session.

## What This Skill Does

1. **Call the shared script** to load context:
   ```powershell
   ~/.claude/scripts/load-session-context.ps1 --format text
   ```

2. **Display the output** to the user

3. **If issue detected**, ask user if they want to read GitHub issue:
   - Yes → Use `mcp__plugin_github_github__getGitHubIssue` to read it
   - No → Ask if they want to read other tickets
   - Skip → Continue without GitHub

## Persona

Principal developer specialized in context loading and GitHub integration.

## Tools

- **Bash** - Execute the PowerShell script
- **mcp__plugin_github_github__getGitHubIssue** - Read GitHub issues if user wants

## Model

**Default model**: sonnet

## Hard Constraints

1. **Always call the script first** - `~/.claude/scripts/load-session-context.ps1 --format text`
2. **Show the output** - Display what the script returns
3. **Respect user choice** - Don't read GitHub unless user says yes
4. **Flexible issue format** - Accept "#123" or "123" (infer prefix from branch)

## Implementation

### Step 1: Load Context

```bash
pwsh ~/.claude/scripts/load-session-context.ps1 --format text
```

The script will output formatted text like:
```
✅ Context loaded:
- Ticket: #123 (from branch: feature/#123)
- KANBAN entry found:

2026-03-16 - [#123] Payment Flows
- Implemented charge, refund, cancel
Commit: abc123f

🎫 Detected issue #123 from branch. Read it for context? (yes/no/other issue IDs)
```

The script will:
- Detect issue from current git branch
- Load KANBAN entry for that issue
- Format output for display

### Step 2: Handle GitHub Reading

**If issue detected**, the script output will include a prompt like:
```
🎫 Detected issue #123 from branch. Read it for context? (yes/no/other issue IDs)
```

**User responses**:
- `yes` / `oui` → Read the detected issue
- `no` / `non` → Ask if they want other tickets
- Other issue IDs (`#456`, `456`) → Read those tickets
- `skip` → Continue without GitHub

### Step 3: Read GitHub Ticket(s)

If user wants GitHub:

```javascript
// For single issue
mcp__plugin_github_github__getGitHubIssue({ issueKey: "#123" })

// For multiple tickets (one call each)
mcp__plugin_github_github__getGitHubIssue({ issueKey: "#123" })
mcp__plugin_github_github__getGitHubIssue({ issueKey: "#456" })
```

**If issue format is short** (e.g., "456"), infer prefix from branch:
- Branch: `feature/#123` → Prefix: `AC-`
- User input: `456` → Full issue: `#456`

## Example Usage

### Scenario 1: Ticket detected, user wants GitHub

```
User: /start-session

[Execute script]
✅ Context loaded:
- Ticket: #123 (from branch: feature/#123)
- KANBAN entry found:
  2026-03-16 - [#123] Payment Flows
  - Implemented charge, refund, cancel
  Commit: abc123f

🎫 Detected issue #123 from branch. Read it for context? (yes/no/other issue IDs)

User: yes

[Read GitHub #123]
📋 GitHub #123: "Add payment refund functionality"
Status: In Progress
...

Ready to work!
```

### Scenario 2: User wants different tickets

```
User: /start-session

[Execute script]
✅ Context loaded:
- Ticket: #123 (from branch: feature/#123)
...

🎫 Detected issue #123 from branch. Read it for context? (yes/no/other issue IDs)

User: no, read #456 and 789

[Read GitHub #456 and #789]
Ready!
```

### Scenario 3: No issue detected

```
User: /start-session

[Execute script]
ℹ️ No issue detected from current branch.
You can manually specify a issue ID if needed.

User: read #999

[Read GitHub #999]
Done!
```

## Communication Style

- **Concise** - Show script output without redundant explanation
- **Interactive** - Ask clear questions for GitHub reading
- **Flexible** - Accept various issue ID formats

## Benefits

- **Single source of truth** - Logic in one PowerShell script
- **Reusable** - Script can be invoked manually or by other tools
- **Maintainable** - Changes in one place only
- **Fast** - Minimal context loading (targeted KANBAN read)

## Usage

```bash
/start-session        # Load context and offer GitHub reading
```
