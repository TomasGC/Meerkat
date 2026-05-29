#!/usr/bin/env python3
"""
Get comprehensive summary of current branch work.

Replaces: get-branch-summary.ps1

Analyzes current branch vs base branch (main/master/develop) to provide:
- List of commits on current branch
- Files changed (committed + uncommitted)
- Statistics (additions/deletions per commit)
- Summary for KANBAN.md documentation
"""

import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.models import BranchCommit, BranchSummary, FileChange, UncommittedChanges
from common.utils import run_command


def get_default_base_branch() -> str:
    """Detect default base branch from git configuration."""
    # Try to get default branch from remote HEAD
    returncode, stdout, stderr = run_command(["git", "remote"], timeout=5)
    if returncode == 0 and stdout.strip():
        remote = stdout.strip().split("\n")[0]

        returncode, stdout, stderr = run_command(
            ["git", "symbolic-ref", f"refs/remotes/{remote}/HEAD"],
            timeout=5
        )

        if returncode == 0 and stdout.strip():
            # Extract branch name from refs/remotes/origin/main
            parts = stdout.strip().split("/")
            if len(parts) > 0:
                return parts[-1]

    # Fallback: check which branch exists
    returncode, stdout, stderr = run_command(["git", "branch", "-r"], timeout=5)
    if returncode == 0:
        branches = stdout.strip()
        if "origin/main" in branches:
            return "main"
        if "origin/master" in branches:
            return "master"
        if "origin/develop" in branches:
            return "develop"

    return "main"  # Ultimate fallback


def get_current_branch() -> str:
    """Get current git branch name."""
    returncode, stdout, stderr = run_command(
        ["git", "branch", "--show-current"],
        timeout=5
    )

    if returncode != 0:
        raise RuntimeError("Not in a git repository or detached HEAD")

    branch = stdout.strip()
    if not branch:
        raise RuntimeError("Not on a branch (detached HEAD?)")

    return branch


def get_branch_commits(base_branch: str, current_branch: str) -> list[BranchCommit]:
    """Get commits on current branch not in base branch."""
    # Try with base_branch first, then with origin/base_branch
    range_spec = f"{base_branch}..{current_branch}"
    returncode, stdout, stderr = run_command(
        ["git", "log", "--format=%H", range_spec],
        timeout=10
    )

    if returncode != 0:
        # Try with origin/ prefix
        range_spec = f"origin/{base_branch}..{current_branch}"
        returncode, stdout, stderr = run_command(
            ["git", "log", "--format=%H", range_spec],
            timeout=10
        )

        if returncode != 0:
            return []

    commit_hashes = [h.strip() for h in stdout.strip().split("\n") if h.strip()]

    commits = []
    for hash in commit_hashes:
        # Get commit metadata
        returncode, stdout, stderr = run_command(
            ["git", "log", "-1", "--format=%s%n%an%n%ai", hash],
            timeout=5
        )

        if returncode != 0:
            continue

        lines = stdout.strip().split("\n")
        if len(lines) < 3:
            continue

        message = lines[0]
        author = lines[1]
        date = lines[2]
        short_hash = hash[:7]

        # Get file stats
        files, additions, deletions = get_commit_file_stats(hash)

        commit = BranchCommit(
            hash=hash,
            short_hash=short_hash,
            message=message,
            author=author,
            date=date,
            additions=additions,
            deletions=deletions,
            files_changed=len(files),
            files=files
        )

        commits.append(commit)

    return commits


def get_commit_file_stats(commit_hash: str) -> tuple[list[FileChange], int, int]:
    """Get file statistics for a commit."""
    returncode, stdout, stderr = run_command(
        ["git", "show", "--numstat", "--format=", commit_hash],
        timeout=10
    )

    if returncode != 0:
        return [], 0, 0

    files = []
    total_additions = 0
    total_deletions = 0

    for line in stdout.strip().split("\n"):
        if not line.strip():
            continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue

        added = parts[0]
        deleted = parts[1]
        file_path = parts[2]

        # Handle binary files (marked with "-")
        additions = 0 if added == "-" else int(added)
        deletions = 0 if deleted == "-" else int(deleted)

        files.append(FileChange(
            path=file_path,
            additions=additions,
            deletions=deletions
        ))

        total_additions += additions
        total_deletions += deletions

    return files, total_additions, total_deletions


def get_uncommitted_changes() -> UncommittedChanges:
    """Get uncommitted changes in working directory."""
    changes = UncommittedChanges()

    # Staged files
    returncode, stdout, stderr = run_command(
        ["git", "diff", "--cached", "--name-status"],
        timeout=5
    )

    if returncode == 0:
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue

            parts = line.split("\t", 1)
            if len(parts) == 2:
                status, path = parts
                changes.staged.append(FileChange(
                    path=path,
                    status=status,
                    additions=0,
                    deletions=0
                ))

    # Unstaged files
    returncode, stdout, stderr = run_command(
        ["git", "diff", "--name-status"],
        timeout=5
    )

    if returncode == 0:
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue

            parts = line.split("\t", 1)
            if len(parts) == 2:
                status, path = parts
                changes.unstaged.append(FileChange(
                    path=path,
                    status=status,
                    additions=0,
                    deletions=0
                ))

    # Untracked files
    returncode, stdout, stderr = run_command(
        ["git", "ls-files", "--others", "--exclude-standard"],
        timeout=5
    )

    if returncode == 0:
        for line in stdout.strip().split("\n"):
            if line.strip():
                changes.untracked.append(FileChange(
                    path=line.strip(),
                    status="?",
                    additions=0,
                    deletions=0
                ))

    return changes


def format_text_summary(summary: BranchSummary) -> str:
    """Format summary as human-readable text."""
    lines = [
        "Branch Summary",
        "=" * 50,
        "",
        f"Current branch: {summary.current_branch}",
        f"Base branch:    {summary.base_branch}",
        "",
        f"Commits: {summary.commits_count}",
        f"Files changed: {summary.unique_files_changed} unique files",
        f"Lines: +{summary.total_additions} -{summary.total_deletions}",
        ""
    ]

    if summary.commits:
        lines.append("Commits on this branch:")
        lines.append("-" * 50)
        for commit in summary.commits:
            lines.append(f"{commit.short_hash} - {commit.message}")
            lines.append(f"  Author: {commit.author}")
            lines.append(f"  Date: {commit.date}")
            lines.append(f"  Stats: +{commit.additions} -{commit.deletions} ({commit.files_changed} files)")
            lines.append("")

    if summary.has_uncommitted_changes:
        lines.append("Uncommitted changes:")
        lines.append("-" * 50)
        if summary.uncommitted.staged:
            lines.append(f"Staged ({len(summary.uncommitted.staged)}):")
            for file in summary.uncommitted.staged:
                lines.append(f"  {file.status} {file.path}")

        if summary.uncommitted.unstaged:
            lines.append(f"Unstaged ({len(summary.uncommitted.unstaged)}):")
            for file in summary.uncommitted.unstaged:
                lines.append(f"  {file.status} {file.path}")

        if summary.uncommitted.untracked:
            lines.append(f"Untracked ({len(summary.uncommitted.untracked)}):")
            for file in summary.uncommitted.untracked:
                lines.append(f"  ? {file.path}")

    return "\n".join(lines)


def format_brief_summary(summary: BranchSummary) -> str:
    """Format as brief summary."""
    return f"{summary.commits_count} commits, {summary.unique_files_changed} files changed (+{summary.total_additions} -{summary.total_deletions})"


def format_markdown_summary(summary: BranchSummary) -> str:
    """Format summary as markdown."""
    lines = [
        f"# Branch Summary: {summary.current_branch}",
        "",
        f"**Base branch:** {summary.base_branch}",
        "",
        "## Statistics",
        "",
        f"- Commits: {summary.commits_count}",
        f"- Files changed: {summary.unique_files_changed}",
        f"- Lines: +{summary.total_additions} -{summary.total_deletions}",
        ""
    ]

    if summary.commits:
        lines.append("## Commits")
        lines.append("")
        for commit in summary.commits:
            lines.append(f"### {commit.short_hash} - {commit.message}")
            lines.append("")
            lines.append(f"- **Author:** {commit.author}")
            lines.append(f"- **Date:** {commit.date}")
            lines.append(f"- **Stats:** +{commit.additions} -{commit.deletions} ({commit.files_changed} files)")
            lines.append("")

    if summary.has_uncommitted_changes:
        lines.append("## Uncommitted Changes")
        lines.append("")
        if summary.uncommitted.staged:
            lines.append(f"### Staged ({len(summary.uncommitted.staged)})")
            lines.append("")
            for file in summary.uncommitted.staged:
                lines.append(f"- `{file.status}` {file.path}")
            lines.append("")

        if summary.uncommitted.unstaged:
            lines.append(f"### Unstaged ({len(summary.uncommitted.unstaged)})")
            lines.append("")
            for file in summary.uncommitted.unstaged:
                lines.append(f"- `{file.status}` {file.path}")
            lines.append("")

        if summary.uncommitted.untracked:
            lines.append(f"### Untracked ({len(summary.uncommitted.untracked)})")
            lines.append("")
            for file in summary.uncommitted.untracked:
                lines.append(f"- `?` {file.path}")
            lines.append("")

    return "\n".join(lines)


class GetBranchSummaryScript(BaseCLIScript):
    """Get comprehensive summary of current branch work."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--base-branch",
            "-b",
            default="",
            help="Base branch to compare against (auto-detects if not specified)"
        )
        parser.add_argument(
            "--no-uncommitted",
            action="store_true",
            help="Exclude uncommitted changes from analysis"
        )
        parser.add_argument(
            "--format-markdown",
            action="store_true",
            help="Output as markdown (alternative to --format)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute branch summary analysis."""
        try:
            # Get current branch
            current_branch = get_current_branch()

            # Determine base branch
            base_branch = args.base_branch if args.base_branch else get_default_base_branch()

            # Get commits on current branch
            commits = get_branch_commits(base_branch, current_branch)

            # Calculate totals
            total_additions = sum(c.additions for c in commits)
            total_deletions = sum(c.deletions for c in commits)

            # Get unique files
            all_files = set()
            for commit in commits:
                for file in commit.files:
                    all_files.add(file.path)

            # Get uncommitted changes
            uncommitted = UncommittedChanges() if args.no_uncommitted else get_uncommitted_changes()

            has_uncommitted = (
                len(uncommitted.staged) +
                len(uncommitted.unstaged) +
                len(uncommitted.untracked)
            ) > 0

            # Build summary
            summary = BranchSummary(
                current_branch=current_branch,
                base_branch=base_branch,
                commits_count=len(commits),
                commits=commits,
                total_additions=total_additions,
                total_deletions=total_deletions,
                unique_files_changed=len(all_files),
                uncommitted=uncommitted,
                has_uncommitted_changes=has_uncommitted
            )

            self.metrics.track("get_branch_summary", {
                "commits": len(commits),
                "has_uncommitted": has_uncommitted
            })

            return {
                "success": True,
                "summary": summary,
                "format_markdown": args.format_markdown if hasattr(args, 'format_markdown') else False
            }

        except Exception as e:
            self.logger.error(f"Failed to get branch summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        return format_text_summary(result["summary"])

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return format_brief_summary(result["summary"])

    def output(self, result: dict, format: str) -> None:
        """Override output to support markdown format."""
        if result.get("format_markdown"):
            print(format_markdown_summary(result["summary"]))
        else:
            super().output(result, format)


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(GetBranchSummaryScript)
