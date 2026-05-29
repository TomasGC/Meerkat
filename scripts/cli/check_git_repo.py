#!/usr/bin/env python3
"""
Check if directory is a git repository (cross-platform).

Verifies if a directory is a valid git repository and optionally
returns repository information (branch, remote, status).
"""

from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript, create_cli_script
from common.utils import run_command


class CheckGitRepoScript(BaseCLIScript):
    """Check if directory is a git repository."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--path",
            "-p",
            type=Path,
            default=Path("."),
            help="Path to check (default: current directory)"
        )
        parser.add_argument(
            "--info",
            "-i",
            action="store_true",
            help="Include detailed repository information"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute git repo check."""
        path = args.path.resolve()

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {args.path}")

        # Check if git repo
        result = {
            "isRepo": self._is_git_repo(path),
            "path": str(path)
        }

        if result["isRepo"] and args.info:
            result.update(self._get_repo_info(path))

        # Track metrics
        self.metrics.track("check_git_repo", {
            "is_repo": result["isRepo"],
            "include_info": args.info
        })

        return result

    def _is_git_repo(self, path: Path) -> bool:
        """Check if path is git repo."""
        returncode, _, _ = run_command(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            timeout=5
        )
        return returncode == 0

    def _get_repo_info(self, path: Path) -> dict:
        """Get detailed repo info."""
        info = {}

        # Current branch
        returncode, stdout, _ = run_command(
            ["git", "branch", "--show-current"],
            cwd=path,
            timeout=5
        )
        info["branch"] = stdout.strip() if returncode == 0 and stdout.strip() else None

        # Remote
        returncode, stdout, _ = run_command(
            ["git", "remote"],
            cwd=path,
            timeout=5
        )

        if returncode == 0 and stdout.strip():
            remote_name = stdout.strip().split("\n")[0]

            returncode, stdout, _ = run_command(
                ["git", "remote", "get-url", remote_name],
                cwd=path,
                timeout=5
            )

            if returncode == 0 and stdout.strip():
                info["hasRemote"] = True
                info["remote"] = remote_name
                info["remoteUrl"] = stdout.strip()
            else:
                info["hasRemote"] = False
        else:
            info["hasRemote"] = False

        # Status (uncommitted changes)
        returncode, stdout, _ = run_command(
            ["git", "status", "--porcelain"],
            cwd=path,
            timeout=5
        )

        if returncode == 0:
            info["hasUncommittedChanges"] = bool(stdout.strip())
            info["statusLines"] = len(stdout.strip().split("\n")) if stdout.strip() else 0
        else:
            info["hasUncommittedChanges"] = None

        return info

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        lines = [f"Path: {result['path']}"]

        if result['isRepo']:
            lines.append("Status: Git repository")

            if "branch" in result:
                lines.append(f"Branch: {result.get('branch', 'N/A')}")

            if "hasRemote" in result:
                if result['hasRemote']:
                    lines.append(f"Remote: {result.get('remote', 'N/A')}")
                    lines.append(f"URL: {result.get('remoteUrl', 'N/A')}")
                else:
                    lines.append("Remote: None")

            if "hasUncommittedChanges" in result:
                if result['hasUncommittedChanges']:
                    lines.append(f"Uncommitted: Yes ({result.get('statusLines', 0)} files)")
                else:
                    lines.append("Uncommitted: No")
        else:
            lines.append("Status: Not a git repository")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if result['isRepo']:
            branch = result.get('branch', 'unknown')
            return f"Git repo: {branch}"
        else:
            return "Not a git repo"


if __name__ == "__main__":
    create_cli_script(CheckGitRepoScript)
