#!/usr/bin/env python3
"""
Extract issue ID from git branch name or commit message.

Uses the active integration profile to extract issue IDs.
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


def extract_issue_from_text(text: str) -> Optional[str]:
    r"""
    Extract issue ID from text using active integration profile.

    Uses issue_format regex from active profile (e.g., r"#(\d+)" for GitHub).
    """
    issue_pattern = get_issue_format()

    match = re.search(issue_pattern, text)
    if match:
        # Return the full match (includes # for GitHub format)
        return match.group(0)

    return None


def get_current_branch() -> str:
    """Get current git branch name."""
    returncode, stdout, stderr = run_command(
        ["git", "branch", "--show-current"],
        timeout=5
    )

    if returncode != 0:
        raise RuntimeError("Not a git repository")

    return stdout.strip()


def get_last_commit_message() -> str:
    """Get last commit message."""
    returncode, stdout, stderr = run_command(
        ["git", "log", "-1", "--pretty=%B"],
        timeout=5
    )

    if returncode != 0:
        raise RuntimeError("Not a git repository or no commits")

    return stdout.strip()


def extract_issue(branch: Optional[str] = None, from_commit: bool = False) -> Optional[str]:
    """Extract issue ID from git branch or commit."""
    # Get source text
    if from_commit:
        text = get_last_commit_message()
    else:
        if branch is None:
            text = get_current_branch()
        else:
            text = branch

    # Extract issue ID
    issue_id = extract_issue_from_text(text)

    return issue_id


class ExtractTicketScript(BaseCLIScript):
    """Extract issue ID from git branch name or commit message."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--branch",
            "-b",
            help="Git branch name to extract from (optional)"
        )
        group.add_argument(
            "--from-commit",
            "-c",
            action="store_true",
            help="Extract from commit message instead"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute issue extraction."""
        try:
            # Extract issue ID
            issue_id = extract_issue(
                branch=args.branch,
                from_commit=args.from_commit
            )

            if issue_id:
                self.metrics.track("extract_issue", {
                    "issue_id": issue_id,
                    "source": "commit" if args.from_commit else "branch"
                })

                return {
                    "success": True,
                    "issue_id": issue_id,
                    "source": "commit" if args.from_commit else "branch"
                }
            else:
                self.logger.debug("No issue ID found")
                return {
                    "success": False,
                    "issue_id": None
                }

        except Exception as e:
            self.logger.error(f"Failed to extract issue: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            if "error" in result:
                return f"Error: {result['error']}"
            else:
                return "No issue ID found"

        return f"Issue ID: {result['issue_id']} (source: {result['source']})"

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            if "error" in result:
                return f"[ERROR] {result['error']}"
            else:
                return "No issue ID found"

        return result['issue_id']


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(ExtractTicketScript)
