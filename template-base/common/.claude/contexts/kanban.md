# KANBAN - [Project Name]

Track of work sessions and completed tasks linked to GitHub issues.

---



---

## Notes

- **One entry per issue** - Updated each time you work on it (not one entry per session)
- **Date** - Last update date
- **Title line**: `YYYY-MM-DD - [TICKET-ID] Title`
- **Description** - Bullet points describing work done (max 6 lines)
- **Tag/Tags** - Topic tags with # for grouping related work (singular if 1, plural if multiple)
- **Ref/Refs** - Documentation links (singular if 1, plural if multiple)
- **Commit/Commits** - Commit hashes (singular if 1, plural if multiple)
- **Format**:
  ```
  YYYY-MM-DD - [TICKET-ID] Title
  - Work description bullet point
  - Another bullet point
  tag: #balances (if single)
  tags: #balances #payments #Me2Me
  Ref: https://link (if single)
  Refs:
  - https://link1
  - https://link2
  Commit: abc123f (if single)
  Commits: abc123f, def456g
  ```
- **Language**: English only
- **Updated by**: `/update-context` skill automatically
- **All tasks tracked in GitHub** - This file is just a log
