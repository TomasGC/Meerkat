#!/usr/bin/env python3
"""
Update a specific section in a markdown file (cross-platform).

Replaces: update-section-in-markdown.ps1

Finds and replaces a specific section in a markdown file while preserving
the rest of the document. Supports numbered sections, header-based sections,
and nested content.
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript


def update_section_in_markdown(
    file_path: Path,
    section: str,
    content: str,
    create_backup: bool = True
) -> dict:
    """
    Update a specific section in a markdown file.

    Args:
        file_path: Path to markdown file
        section: Section identifier (e.g., "## Architecture", "4. **Project**")
        content: New content for the section
        create_backup: Create backup before modifying

    Returns:
        Dict with update results

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If section not found
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read file content
    original_content = file_path.read_text(encoding="utf-8")

    # Create backup if requested
    backup_file = None
    if create_backup:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_file = file_path.with_suffix(f".backup.{timestamp}{file_path.suffix}")
        shutil.copy2(file_path, backup_file)

    # Find the section in the content
    section_escaped = re.escape(section)

    # Find section header level
    header_level_match = re.match(r"^(#{1,6})\s", section)
    numbered_match = re.match(r"^(\d+)\.", section)

    # Build the pattern to find section and its content
    if header_level_match:
        # Markdown header - match until next header of same or higher level
        level = len(header_level_match.group(1))
        # Match section header, then any content until next header with same or fewer #
        next_section_pattern = f"^#{{{1},{level}}}\\s"
    elif numbered_match:
        # Numbered section - match until next numbered section
        next_section_pattern = r"^\d+\.\s"
    else:
        # Generic - match until next markdown header or numbered section
        next_section_pattern = r"^(#{1,6}\s|\d+\.\s)"

    # Find start of section (include the line, not the newline after)
    section_match = re.search(rf"^{section_escaped}", original_content, re.MULTILINE)
    if not section_match:
        raise ValueError(f"Section not found: {section}")

    # Start position is at the beginning of the next line after section header
    start_pos = section_match.end()
    # Skip to next line if there's a newline immediately after
    if start_pos < len(original_content) and original_content[start_pos] == '\n':
        start_pos += 1

    # Find end of section (next section or end of file)
    rest_content = original_content[start_pos:]
    next_section_match = re.search(rf"{next_section_pattern}", rest_content, re.MULTILINE)

    if next_section_match:
        end_pos = start_pos + next_section_match.start()
    else:
        end_pos = len(original_content)

    # Build new content
    new_content = (
        original_content[:start_pos] +
        f"\n{content}\n" +
        original_content[end_pos:]
    )

    # Write updated content
    file_path.write_text(new_content, encoding="utf-8")

    # Calculate lines changed
    original_lines = len(original_content.split("\n"))
    new_lines = len(new_content.split("\n"))
    lines_changed = new_lines - original_lines

    result = {
        "file": str(file_path),
        "section": section,
        "updated": True,
        "backup": str(backup_file) if backup_file else None,
        "linesChanged": lines_changed
    }

    return result


class UpdateSectionInMarkdownScript(BaseCLIScript):
    """Update a specific section in a markdown file."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--file",
            required=True,
            help="Path to markdown file to update"
        )
        parser.add_argument(
            "--section",
            "-s",
            required=True,
            help="Section identifier (e.g., '## Architecture', '4. **Project**')"
        )
        parser.add_argument(
            "--content",
            "-c",
            required=True,
            help="New content for the section"
        )
        parser.add_argument(
            "--no-backup",
            action="store_true",
            help="Do not create backup before modifying"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute section update."""
        try:
            # Resolve path
            file_path = Path(args.file)

            # Update section
            result = update_section_in_markdown(
                file_path,
                args.section,
                args.content,
                create_backup=not args.no_backup
            )

            self.metrics.track("update_section_in_markdown", {
                "file": result["file"],
                "section": result["section"],
                "lines_changed": result["linesChanged"]
            })

            return {
                "success": True,
                **result
            }

        except FileNotFoundError as e:
            return {
                "success": False,
                "error": str(e)
            }
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            self.logger.error(f"Failed to update section: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = [
            f"Updated section in: {result['file']}",
            f"Section: {result['section']}",
            f"Lines changed: {result['linesChanged']}"
        ]

        if result.get("backup"):
            lines.append(f"Backup: {result['backup']}")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        change = f"+{result['linesChanged']}" if result['linesChanged'] > 0 else str(result['linesChanged'])
        return f"[OK] Updated {result['section']} ({change} lines)"


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(UpdateSectionInMarkdownScript)
