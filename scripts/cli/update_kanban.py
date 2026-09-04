#!/usr/bin/env python3
"""
Update .claude/contexts/kanban.md automatically with work from commits.

Replaces: update-kanban.ps1

Searches for existing issue entry in kanban.md and updates it, or creates
new entry if not found. Respects kanban.md format rules (singular/plural,
date updates, cumulative descriptions).
"""

import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.extract_issue import extract_issue
from cli.generate_comment import categorize_file, get_commit_files, get_commits_in_range
from cli.generate_kanban_entry import generate_descriptions
from cli.search_kanban import KanbanEntry, parse_kanban_file
from common.cli.base import BaseCLIScript
from common.utils import run_command


def find_kanban_file(start_path: Path = None) -> Path | None:
    """
    Search for .claude/contexts/kanban.md in current and parent directories.

    Args:
        start_path: Starting directory (defaults to current)

    Returns:
        Path to kanban.md or None if not found
    """
    search_path = start_path or Path.cwd()

    while search_path:
        kanban_path = search_path / ".claude" / "contexts" / "kanban.md"
        if kanban_path.exists():
            return kanban_path

        if search_path.parent == search_path:
            break
        search_path = search_path.parent

    return None


def get_commit_title(commit_hash: str) -> str:
    """Get commit message title."""
    returncode, stdout, stderr = run_command(
        ["git", "log", "-1", "--format=%s", commit_hash],
        timeout=5
    )

    if returncode != 0:
        return ""

    # Extract title after type: prefix (feat: title -> title)
    message = stdout.strip()
    if ":" in message:
        return message.split(":", 1)[1].strip()

    return message


def build_entry(
    issue_id: str,
    title: str,
    description: str,
    ref: str = None,
    commits: list[str] = None
) -> str:
    """
    Build KANBAN.md entry.

    Args:
        issue_id: Issue ID
        title: Entry title
        description: Description (bullet points)
        ref: Reference link
        commits: List of commit hashes

    Returns:
        Formatted entry
    """
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"{today} - [{issue_id}] {title}"]

    # Add description
    lines.append(description)

    # Add refs (singular/plural)
    if ref:
        refs = [r.strip() for r in ref.split(",")]
        if len(refs) == 1:
            lines.append(f"Ref: {refs[0]}")
        else:
            lines.append("Refs:")
            for r in refs:
                lines.append(f"- {r}")

    # Add commits (singular/plural)
    if commits:
        commits = [c.strip() for c in commits]
        if len(commits) == 1:
            lines.append(f"Commit: {commits[0]}")
        else:
            lines.append(f"Commits: {', '.join(commits)}")

    return "\n".join(lines)


def update_existing_entry(
    existing: KanbanEntry,
    new_description: str,
    new_commits: list[str]
) -> str:
    """
    Update existing KANBAN entry.

    Args:
        existing: Existing KanbanEntry
        new_description: New description to add
        new_commits: New commits to add

    Returns:
        Updated entry text
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Update title line with new date
    title_line = f"{today} - [{existing.issue_id}] {existing.title}"

    # Merge descriptions (deduplicate)
    new_desc_lines = [l for l in new_description.split("\n") if l.startswith("-")]
    all_desc = list(dict.fromkeys(existing.description + new_desc_lines))  # Deduplicate preserving order

    # Merge commits (deduplicate)
    all_commits = list(dict.fromkeys(existing.commits + new_commits))

    lines = [title_line]
    lines.extend(all_desc)

    # Add refs if exist
    if existing.refs:
        if len(existing.refs) == 1:
            lines.append(f"Ref: {existing.refs[0]}")
        else:
            lines.append("Refs:")
            for ref in existing.refs:
                lines.append(f"- {ref}")

    # Add commits (singular/plural)
    if all_commits:
        if len(all_commits) == 1:
            lines.append(f"Commit: {all_commits[0]}")
        else:
            lines.append(f"Commits: {', '.join(all_commits)}")

    return "\n".join(lines)


def insert_entry_at_top(content: str, entry: str) -> str:
    """Insert entry at top of entries section."""
    # Find first --- marker
    match = re.search(r"(.*?---\s*\n)", content, re.DOTALL)
    if match:
        header = match.group(1)
        rest = content[match.end():]
        return f"{header}\n{entry}\n\n---{rest}"
    else:
        # No --- found, just prepend
        return f"{entry}\n\n{content}"


class UpdateKanbanScript(BaseCLIScript):
    """Update KANBAN.md automatically with work from commits."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--issue",
            "-t",
            default="",
            help="Ticket ID (auto-detects from branch if not provided)"
        )
        parser.add_argument(
            "--commits",
            "-c",
            default="",
            help="Comma-separated commit hashes (auto-detects if not provided)"
        )
        parser.add_argument(
            "--description",
            "-d",
            default="",
            help="Manual description (auto-generates if not provided)"
        )
        parser.add_argument(
            "--ref",
            "-r",
            default="",
            help="Reference link (issue, docs, etc.)"
        )
        parser.add_argument(
            "--kanban-file",
            "-k",
            default="",
            help="Path to kanban.md (auto-detects .claude/contexts/kanban.md if not provided)"
        )
        parser.add_argument(
            "--no-backup",
            action="store_true",
            help="Skip backup creation"
        )
        parser.add_argument(
            "--auto",
            "-a",
            action="store_true",
            help="Auto-detect issue and commits"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute KANBAN update."""
        try:
            # Auto-detect issue if not provided
            if not args.issue:
                issue_id = extract_issue()
                if not issue_id:
                    return {
                        "success": False,
                        "error": "Could not detect issue ID. Please provide --issue parameter."
                    }
                self.logger.debug(f"Detected issue: {issue_id}")
            else:
                issue_id = args.issue

            # Auto-detect commits if not provided
            if not args.commits and args.auto:
                # Get commits from current branch
                returncode, stdout, stderr = run_command(["git", "branch", "--show-current"], timeout=5)
                if returncode == 0:
                    current_branch = stdout.strip()
                    # Get base branch (simplified)
                    commits = get_commits_in_range("main", current_branch)
                    if not commits:
                        commits = get_commits_in_range("master", current_branch)
                    if commits:
                        commit_hashes = [c[:7] for c in commits]
                        self.logger.debug(f"Detected commits: {', '.join(commit_hashes)}")
                    else:
                        commit_hashes = []
                else:
                    commit_hashes = []
            elif args.commits:
                commit_hashes = [c.strip() for c in args.commits.split(",")]
            else:
                commit_hashes = []

            # Auto-generate description if not provided
            if not args.description:
                if commit_hashes:
                    # Analyze commit files and generate description
                    all_files = []
                    for commit in commit_hashes:
                        files = get_commit_files(commit)
                        all_files.extend(files)

                    categories = defaultdict(int)
                    for file in all_files:
                        category = categorize_file(file)
                        categories[category] += 1

                    descriptions = generate_descriptions(categories, "professional")
                    description = "\n".join(descriptions)
                else:
                    description = "- Work completed"

                self.logger.debug("Generated description from commits")
            else:
                description = args.description

            # Find KANBAN.md
            if args.kanban_file:
                kanban_file = Path(args.kanban_file)
            else:
                kanban_file = find_kanban_file()
                if not kanban_file:
                    return {
                        "success": False,
                        "error": ".claude/contexts/kanban.md not found in current directory or parent directories"
                    }

            if not kanban_file.exists():
                return {
                    "success": False,
                    "error": f"kanban.md not found at: {kanban_file}"
                }

            self.logger.debug(f"Using KANBAN file: {kanban_file}")

            # Create backup
            backup_file = None
            if not args.no_backup:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_file = kanban_file.with_suffix(f".backup-{timestamp}.md")
                shutil.copy2(kanban_file, backup_file)
                self.logger.debug(f"Backup created: {backup_file}")

            # Parse KANBAN.md
            entries = parse_kanban_file(kanban_file)

            # Search for existing entry
            existing = next((e for e in entries if e.issue_id == issue_id), None)

            # Read content for manipulation
            content = kanban_file.read_text(encoding="utf-8")

            if existing:
                self.logger.debug(f"Found existing entry for {issue_id} - updating")

                # Update existing entry
                updated_entry = update_existing_entry(existing, description, commit_hashes)

                # Replace in content
                new_content = content.replace(existing.raw, updated_entry)

                # Save
                kanban_file.write_text(new_content, encoding="utf-8")

                action = "updated"
            else:
                self.logger.debug(f"No existing entry for {issue_id} - creating new")

                # Get title from first commit
                if commit_hashes:
                    title = get_commit_title(commit_hashes[0])
                    if not title:
                        title = issue_id
                else:
                    title = issue_id

                # Build new entry
                new_entry = build_entry(issue_id, title, description, args.ref, commit_hashes)

                # Insert at top
                new_content = insert_entry_at_top(content, new_entry)

                # Save
                kanban_file.write_text(new_content, encoding="utf-8")

                action = "created"

            self.metrics.track("update_kanban", {
                "issue": issue_id,
                "commits": len(commit_hashes),
                "action": action
            })

            return {
                "success": True,
                "issue": issue_id,
                "action": action,
                "commits": len(commit_hashes),
                "kanban_file": str(kanban_file),
                "backup": str(backup_file) if backup_file else None
            }

        except Exception as e:
            self.logger.error(f"Failed to update KANBAN.md: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        action = "Updated" if result["action"] == "updated" else "Created"
        lines = [
            f"{action} entry for [{result['issue']}]",
            f"Commits: {result['commits']}",
            f"KANBAN: {result['kanban_file']}"
        ]

        if result.get("backup"):
            lines.append(f"Backup: {result['backup']}")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        action = "Updated" if result["action"] == "updated" else "Created"
        return f"[OK] {action} [{result['issue']}] ({result['commits']} commits)"


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(UpdateKanbanScript)
