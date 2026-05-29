#!/usr/bin/env python3
"""
Find all git repositories in a directory tree (cross-platform).

Replaces: find-git-repos.ps1

Recursively searches for .git directories and returns the parent
directories as git repository paths. Useful for multi-repo operations.
"""

import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.utils import run_command


def find_git_repos(root_path: Path, max_depth: int = 5) -> list[dict]:
    """Find all git repositories in directory tree."""
    repos = []

    # Find .git directories
    def search_dir(path: Path, current_depth: int) -> None:
        """Recursively search for .git directories."""
        if max_depth != -1 and current_depth > max_depth:
            return

        try:
            for item in path.iterdir():
                if not item.is_dir():
                    continue

                # Check if this is a .git directory
                if item.name == ".git":
                    # Parent directory is the repository root
                    repo_path = item.parent

                    # Get repository info
                    repo_info = get_repo_info(repo_path)
                    repos.append(repo_info)
                    continue  # Don't recurse into .git

                # Recurse into subdirectories
                try:
                    search_dir(item, current_depth + 1)
                except (PermissionError, OSError):
                    # Skip directories we can't access
                    pass
        except (PermissionError, OSError):
            # Skip directories we can't access
            pass

    search_dir(root_path, 0)

    # Sort by path
    repos.sort(key=lambda r: r["path"])

    return repos


def get_repo_info(repo_path: Path) -> dict:
    """Get information about a git repository."""
    info = {
        "path": str(repo_path),
        "name": repo_path.name,
        "branch": None,
        "hasRemote": False,
        "remote": None,
        "remoteUrl": None
    }

    # Get current branch
    returncode, stdout, stderr = run_command(
        ["git", "branch", "--show-current"],
        cwd=repo_path,
        timeout=5
    )
    if returncode == 0 and stdout.strip():
        info["branch"] = stdout.strip()

    # Get remote info
    returncode, stdout, stderr = run_command(
        ["git", "remote"],
        cwd=repo_path,
        timeout=5
    )
    if returncode == 0 and stdout.strip():
        remote_name = stdout.strip().split("\n")[0]

        # Verify remote has URL
        returncode, stdout, stderr = run_command(
            ["git", "remote", "get-url", remote_name],
            cwd=repo_path,
            timeout=5
        )
        if returncode == 0 and stdout.strip():
            info["hasRemote"] = True
            info["remote"] = remote_name
            info["remoteUrl"] = stdout.strip()

    return info


def format_list(repos: list[dict]) -> str:
    """Format results as simple list of paths."""
    return "\n".join(repo["path"] for repo in repos)


class FindGitReposScript(BaseCLIScript):
    """Find all git repositories in a directory tree."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--path",
            "-p",
            default=".",
            help="Root path to search (defaults to current directory)"
        )
        parser.add_argument(
            "--max-depth",
            "-d",
            type=int,
            default=5,
            help="Maximum depth to search (default: 5, unlimited: -1)"
        )
        parser.add_argument(
            "--format-list",
            action="store_true",
            help="Output as simple list of paths (alternative to --format)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute git repository search."""
        try:
            # Resolve path
            root_path = Path(args.path).resolve()

            if not root_path.exists():
                self.logger.error(f"Path does not exist: {root_path}")
                return {
                    "success": False,
                    "error": f"Path does not exist: {root_path}"
                }

            if not root_path.is_dir():
                self.logger.error(f"Path is not a directory: {root_path}")
                return {
                    "success": False,
                    "error": f"Path is not a directory: {root_path}"
                }

            # Find repositories
            repos = find_git_repos(root_path, args.max_depth)

            self.metrics.track("find_git_repos", {
                "count": len(repos),
                "max_depth": args.max_depth
            })

            return {
                "success": True,
                "searchPath": str(root_path),
                "maxDepth": args.max_depth,
                "count": len(repos),
                "repositories": repos,
                "format_list": args.format_list if hasattr(args, 'format_list') else False
            }

        except Exception as e:
            self.logger.error(f"Failed to find git repositories: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = [f"Found {result['count']} git repositories in {result['searchPath']}", ""]

        for repo in result["repositories"]:
            lines.append(f"Repository: {repo['name']}")
            lines.append(f"  Path: {repo['path']}")
            lines.append(f"  Branch: {repo['branch']}")

            if repo["hasRemote"]:
                lines.append(f"  Remote: {repo['remote']} ({repo['remoteUrl']})")
            else:
                lines.append("  Remote: None")

            lines.append("")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return f"Found {result['count']} git repositories (max depth: {result['maxDepth']})"

    def output(self, result: dict, format: str) -> None:
        """Override output to support list format."""
        if result.get("format_list"):
            print(format_list(result["repositories"]))
        else:
            super().output(result, format)


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(FindGitReposScript)
