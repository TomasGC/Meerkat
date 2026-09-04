#!/usr/bin/env python3
"""
Search KANBAN.md for entries by issue, tag, or date.

Replaces: search-kanban.ps1

Flexible search tool for KANBAN.md entries with multiple search criteria
and output formats (JSON, text, summary).
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript


@dataclass
class KanbanEntry:
    """KANBAN.md entry."""
    date: str
    issue_id: str
    title: str
    description: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    raw: str = ""


def parse_kanban_file(file_path: Path) -> list[KanbanEntry]:
    """
    Parse KANBAN.md file into structured entries.

    Args:
        file_path: Path to KANBAN.md

    Returns:
        List of KanbanEntry objects
    """
    if not file_path.exists():
        raise FileNotFoundError(f"KANBAN.md not found at: {file_path}")

    content = file_path.read_text(encoding="utf-8")

    # Split into sections by --- markers
    sections = re.split(r"(?m)^---$", content)

    if len(sections) < 3:
        # No entries yet
        return []

    # Entries section is between first two ---
    entries_section = sections[1].strip()

    # Split entries by date pattern (YYYY-MM-DD)
    entries = []
    lines = entries_section.split("\n")
    current_entry = []

    for line in lines:
        # New entry starts with date pattern
        if re.match(r"^\d{4}-\d{2}-\d{2}\s+-\s+\[([A-Z]+-\d+|#\d+)\]", line):
            if current_entry:
                entries.append("\n".join(current_entry))
                current_entry = []
            current_entry.append(line)
        elif current_entry:
            current_entry.append(line)

    # Add last entry
    if current_entry:
        entries.append("\n".join(current_entry))

    # Parse entries into structured objects
    parsed_entries = []
    for entry in entries:
        # Extract header: YYYY-MM-DD - [ISSUE] Title
        match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+-\s+\[([A-Z]+-\d+|#\d+)\]\s+(.+)", entry, re.MULTILINE)
        if not match:
            continue

        date = match.group(1)
        issue_id = match.group(2)
        title = match.group(3).strip()

        # Extract tags
        tags = []
        tag_match = re.search(r"(?m)^tags?:\s+(.+)$", entry)
        if tag_match:
            tag_line = tag_match.group(1)
            tags = [t.lstrip("#") for t in re.findall(r"#\w+", tag_line)]

        # Extract refs
        refs = []
        refs_match = re.search(r"(?ms)^Refs?:(.+?)(?=^[A-Z]|^Commit|$)", entry)
        if refs_match:
            refs_section = refs_match.group(1)
            refs = re.findall(r"https?://[^\s]+", refs_section)
        else:
            ref_match = re.search(r"Ref:\s+(https?://[^\s]+)", entry)
            if ref_match:
                refs = [ref_match.group(1)]

        # Extract commits
        commits = []
        commit_match = re.search(r"Commits?:\s+(.+)", entry)
        if commit_match:
            commits = [c.strip() for c in commit_match.group(1).split(",")]

        # Extract description (bullet points)
        description = []
        for line in entry.split("\n"):
            if re.match(r"^\s*-\s+", line):
                description.append(line.strip())

        parsed_entry = KanbanEntry(
            date=date,
            issue_id=issue_id,
            title=title,
            description=description,
            tags=tags,
            refs=refs,
            commits=commits,
            raw=entry
        )

        parsed_entries.append(parsed_entry)

    return parsed_entries


def filter_entries(
    entries: list[KanbanEntry],
    issue_id: str = None,
    tag: str = None,
    date: str = None,
    date_from: str = None,
    date_to: str = None
) -> list[KanbanEntry]:
    """
    Filter entries based on search criteria.

    Args:
        entries: List of KanbanEntry objects
        issue_id: Issue ID to filter by
        tag: Tag to filter by
        date: Specific date to filter by
        date_from: Start date for range
        date_to: End date for range

    Returns:
        Filtered list of entries
    """
    results = entries

    if issue_id:
        results = [e for e in results if e.issue_id == issue_id]

    if tag:
        results = [e for e in results if tag in e.tags]

    if date:
        results = [e for e in results if e.date == date]

    if date_from and date_to:
        results = [e for e in results if date_from <= e.date <= date_to]
    elif date_from:
        results = [e for e in results if e.date >= date_from]
    elif date_to:
        results = [e for e in results if e.date <= date_to]

    return results


class SearchKanbanScript(BaseCLIScript):
    """Search KANBAN.md for entries by issue, tag, or date."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--issue",
            "-t",
            help="Ticket ID to search (e.g., #123)"
        )
        parser.add_argument(
            "--tag",
            "-T",
            help="Tag to search (without # prefix)"
        )
        parser.add_argument(
            "--date",
            "-d",
            help="Date to search (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--date-from",
            help="Start date for date range search"
        )
        parser.add_argument(
            "--date-to",
            help="End date for date range search"
        )
        parser.add_argument(
            "--path",
            "-p",
            default=".claude/contexts/kanban.md",
            help="Path to kanban.md (default: .claude/contexts/kanban.md)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute KANBAN search."""
        try:
            # Parse kanban.md
            file_path = Path(args.path)
            entries = parse_kanban_file(file_path)

            if not entries:
                return {
                    "success": True,
                    "entries": [],
                    "count": 0
                }

            # Filter entries
            results = filter_entries(
                entries,
                issue_id=args.issue_id,
                tag=args.tag,
                date=args.date,
                date_from=args.date_from,
                date_to=args.date_to
            )

            self.metrics.track("search_kanban", {
                "results": len(results),
                "criteria": {
                    "issue": args.issue_id is not None,
                    "tag": args.tag is not None,
                    "date": args.date is not None or args.date_from is not None or args.date_to is not None
                }
            })

            return {
                "success": True,
                "count": len(results),
                "entries": [
                    {
                        "date": e.date,
                        "issue": e.issue_id,
                        "title": e.title,
                        "description": e.description,
                        "tags": e.tags,
                        "refs": e.refs,
                        "commits": e.commits
                    }
                    for e in results
                ]
            }

        except FileNotFoundError as e:
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            self.logger.error(f"Failed to search KANBAN.md: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        if not result["entries"]:
            return "No entries found"

        lines = []
        for entry in result["entries"]:
            lines.append(f"{entry['date']} - [{entry['issue']}] {entry['title']}")
            for desc in entry['description']:
                lines.append(f"  {desc}")
            if entry['tags']:
                lines.append(f"  Tags: {', '.join(entry['tags'])}")
            if entry['commits']:
                lines.append(f"  Commits: {', '.join(entry['commits'])}")
            lines.append("")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        if not result["entries"]:
            return "[OK] No entries found"

        lines = [f"[OK] Found {result['count']} entries"]
        for entry in result["entries"]:
            lines.append(f"[{entry['issue']}] {entry['title']} ({entry['date']})")

        return "\n".join(lines)


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(SearchKanbanScript)
