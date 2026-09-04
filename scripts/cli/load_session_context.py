#!/usr/bin/env python3
"""
Load project context at session startup.

Replaces: load-session-context.ps1

Detects issue from git branch, loads KANBAN entry, displays info.
Used by /start-session skill to provide context at session start.
"""

import re
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.integrations import get_issue_format
from common.utils import run_command


def get_issue_from_branch(cwd: Optional[Path] = None) -> Optional[str]:
    """
    Extract issue ID from current git branch using active integration profile.

    Args:
        cwd: Current working directory

    Returns:
        Issue ID (format depends on active profile) or None
    """
    returncode, stdout, stderr = run_command(
        ["git", "branch", "--show-current"],
        cwd=cwd,
        timeout=5
    )

    if returncode != 0 or not stdout.strip():
        return None

    branch = stdout.strip()

    # Use issue format from active profile
    issue_pattern = get_issue_format()
    match = re.search(issue_pattern, branch)
    if match:
        return match.group(0)

    # Fallback: bare number after slash (e.g. feature/38-foo or bugfix/38-foo → #38)
    fallback = re.search(r"(?:^|/)#?(\d+)[-_]", branch)
    if fallback:
        return f"#{fallback.group(1)}"

    return None


def load_kanban_entry(issue_id: str, kanban_path: Path = None) -> Optional[str]:
    """
    Load KANBAN entry for issue.

    Args:
        issue_id: Issue ID (#123 or #12345)
        kanban_path: Path to kanban.md (default: .claude/contexts/kanban.md)

    Returns:
        KANBAN entry content or None
    """
    if kanban_path is None:
        kanban_path = Path(".claude/contexts/kanban.md")
        if not kanban_path.exists():
            return None

    try:
        content = kanban_path.read_text(encoding="utf-8")

        # Match entry for this issue up to next date or end of file
        pattern = rf"\[{re.escape(issue_id)}\].*?(?=\n\d{{4}}-\d{{2}}-\d{{2}}|\Z)"
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

        if match:
            return match.group(0).strip()

        return None

    except Exception:
        return None


def load_session_context(cwd: Optional[Path] = None) -> dict:
    """
    Load session context (branch, issue, KANBAN).

    Args:
        cwd: Current working directory

    Returns:
        Context dictionary
    """
    # Get current branch
    returncode, stdout, stderr = run_command(
        ["git", "branch", "--show-current"],
        cwd=cwd,
        timeout=5
    )

    branch = stdout.strip() if returncode == 0 else None

    # Get issue from branch
    issue_id = get_issue_from_branch(cwd)

    # Load KANBAN entry if issue found
    kanban_context = None
    if issue_id:
        kanban_context = load_kanban_entry(issue_id)

    return {
        "branch": branch,
        "issue": issue_id,
        "kanbanFound": kanban_context is not None,
        "kanbanContext": kanban_context
    }


class LoadSessionContextScript(BaseCLIScript):
    """Load project context at session startup."""

    def execute(self, args) -> dict[str, Any]:
        """Execute context loading."""
        try:
            # Load session context
            context = load_session_context()

            self.metrics.track("load_session_context", {
                "issue": context["issue"],
                "kanbanFound": context["kanbanFound"]
            })

            return {
                "success": True,
                **context
            }

        except Exception as e:
            self.logger.error(f"Failed to load session context: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as text for skill consumption."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = []

        if result["issue"]:
            lines.append("")
            lines.append("SESSION CONTEXT:")
            lines.append(f"- Branch: {result['branch']}")
            lines.append(f"- Issue: {result['issue']}")

            if result["kanbanFound"]:
                lines.append("- KANBAN: Found")
                lines.append("")
                lines.append(result["kanbanContext"])
            else:
                lines.append("- KANBAN: Not found (new issue?)")

            lines.append("")
            lines.append("<CLAUDE_INSTRUCTION>")
            lines.append("In your FIRST response, you MUST ask the user:")
            lines.append(f"Issue {result['issue']} detected. Do you want to read the issue for context? (yes/no)")
            lines.append("</CLAUDE_INSTRUCTION>")
        else:
            lines.append("No issue detected from branch.")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        if result["issue"]:
            status = "KANBAN found" if result["kanbanFound"] else "no KANBAN"
            return f"[OK] Issue {result['issue']} ({status})"

        return "[OK] No issue detected"


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(LoadSessionContextScript)
