#!/usr/bin/env python3
"""
Extract git commit information (hash, message, author, date, files).

Replaces: get-commit-info.ps1

Retrieves commit metadata for one or more commits with configurable output formats.
"""

import csv
import io
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.models import GitCommitInfo
from common.utils import run_command


def get_commit_info(
    commit_hash: str = "HEAD",
    count: int = 1,
    include_files: bool = False
) -> list[GitCommitInfo]:
    """Get commit information from git log."""
    # Git log format: hash, short hash, message, author name, author email, date, relative date
    log_format = "%H%n%h%n%s%n%an%n%ae%n%ad%n%ar"

    returncode, stdout, stderr = run_command(
        ["git", "log", f"-{count}", f"--format={log_format}", "--date=iso", commit_hash],
        timeout=10
    )

    if returncode != 0:
        raise RuntimeError(f"Git log failed: {stderr}")

    commits = []
    lines = stdout.strip().split("\n")

    # Parse commits (7 lines per commit)
    for i in range(0, len(lines), 7):
        if i + 6 >= len(lines):
            break  # Incomplete commit block

        commit = GitCommitInfo(
            hash=lines[i].strip(),
            author=lines[i + 3].strip(),
            date=lines[i + 5].strip(),
            message=lines[i + 2].strip()
        )

        # Get file changes if requested
        if include_files:
            files, insertions, deletions = get_commit_files(lines[i].strip())
            commit.files_changed = files
            commit.insertions = insertions
            commit.deletions = deletions

        commits.append(commit)

    return commits


def get_commit_files(commit_hash: str) -> tuple[list[str], int, int]:
    """Get files changed in a commit with stats."""
    returncode, stdout, stderr = run_command(
        ["git", "show", "--pretty=", "--numstat", commit_hash],
        timeout=10
    )

    if returncode != 0:
        return [], 0, 0

    files = []
    total_insertions = 0
    total_deletions = 0

    for line in stdout.strip().split("\n"):
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) >= 3:
            insertions = parts[0]
            deletions = parts[1]
            file_path = parts[2]

            files.append(file_path)

            # Handle binary files (marked with "-")
            if insertions != "-":
                total_insertions += int(insertions)
            if deletions != "-":
                total_deletions += int(deletions)

    return files, total_insertions, total_deletions


def format_text_output(commits: list[GitCommitInfo], include_files: bool) -> str:
    """Format commits as human-readable text."""
    output = []

    for i, commit in enumerate(commits):
        if i > 0:
            output.append("")  # Blank line between commits

        output.append(f"Commit:  {commit.hash}")
        output.append(f"Author:  {commit.author}")
        output.append(f"Date:    {commit.date}")
        output.append(f"Message: {commit.message}")

        if include_files and commit.files_changed:
            output.append(f"Files:   {len(commit.files_changed)} changed, "
                         f"+{commit.insertions} insertions, -{commit.deletions} deletions")
            for file in commit.files_changed:
                output.append(f"  - {file}")

    return "\n".join(output)


def format_csv_output(commits: list[GitCommitInfo], include_files: bool) -> str:
    """Format commits as CSV."""
    output = io.StringIO()

    if include_files:
        fieldnames = ["hash", "author", "date", "message", "files", "insertions", "deletions"]
    else:
        fieldnames = ["hash", "author", "date", "message"]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for commit in commits:
        row = {
            "hash": commit.hash,
            "author": commit.author,
            "date": commit.date,
            "message": commit.message
        }

        if include_files:
            row["files"] = ";".join(commit.files_changed)
            row["insertions"] = commit.insertions
            row["deletions"] = commit.deletions

        writer.writerow(row)

    return output.getvalue()


class GetCommitInfoScript(BaseCLIScript):
    """Extract git commit information."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--hash",
            "-H",
            default="HEAD",
            help="Commit hash or reference (default: HEAD)"
        )
        parser.add_argument(
            "--count",
            "-c",
            type=int,
            default=1,
            help="Number of commits to retrieve (default: 1)"
        )
        parser.add_argument(
            "--include-files",
            action="store_true",
            help="Include files changed in each commit"
        )
        parser.add_argument(
            "--format-csv",
            action="store_true",
            help="Output as CSV (alternative to --format)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute commit info retrieval."""
        try:
            # Get commit information
            commits = get_commit_info(
                commit_hash=args.hash,
                count=args.count,
                include_files=args.include_files
            )

            if not commits:
                self.logger.warning("No commits found")
                return {
                    "success": False,
                    "error": "No commits found"
                }

            self.metrics.track("get_commit_info", {
                "count": len(commits),
                "include_files": args.include_files
            })

            return {
                "success": True,
                "commits": commits,
                "include_files": args.include_files,
                "format_csv": args.format_csv if hasattr(args, 'format_csv') else False
            }

        except Exception as e:
            self.logger.error(f"Failed to get commit info: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        return format_text_output(result["commits"], result["include_files"])

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        commits = result["commits"]
        if len(commits) == 1:
            c = commits[0]
            return f"{c.hash[:7]} - {c.message}"
        else:
            return f"{len(commits)} commits retrieved"

    def output(self, result: dict, format: str) -> None:
        """Override output to support CSV format."""
        if result.get("format_csv"):
            print(format_csv_output(result["commits"], result["include_files"]))
        else:
            super().output(result, format)


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(GetCommitInfoScript)
