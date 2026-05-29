#!/usr/bin/env python3
"""
Safely read Claude context files with graceful fallback (cross-platform).

Replaces: safe-read-context.ps1

Reads .claude/ context files (KANBAN.md, ARCHITECTURE.md, rules/) with
graceful error handling. Returns structured JSON output or plain text.
"""

import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.file_utils import read_file_safe


def read_kanban(claude_dir: Path) -> Optional[dict]:
    """
    Read KANBAN.md file.

    Args:
        claude_dir: Path to .claude directory

    Returns:
        Dictionary with KANBAN info
    """
    kanban_file = claude_dir / "KANBAN.md"
    result = read_file_safe(kanban_file)

    # Convert FileReadResult to dict for backward compatibility
    return {
        "exists": result.exists,
        "path": result.path,
        "content": result.content,
        "lines": result.lines,
        **({"error": result.error} if result.error else {})
    }


def read_architecture(claude_dir: Path) -> Optional[dict]:
    """
    Read ARCHITECTURE.md file.

    Args:
        claude_dir: Path to .claude directory

    Returns:
        Dictionary with ARCHITECTURE info
    """
    arch_file = claude_dir / "ARCHITECTURE.md"
    result = read_file_safe(arch_file)

    # Convert FileReadResult to dict for backward compatibility
    return {
        "exists": result.exists,
        "path": result.path,
        "content": result.content,
        "lines": result.lines,
        **({"error": result.error} if result.error else {})
    }


def read_rules(claude_dir: Path) -> list[dict]:
    """
    Read all rules/**/*.md files.

    Args:
        claude_dir: Path to .claude directory

    Returns:
        List of dictionaries with rule file info
    """
    rules_dir = claude_dir / "rules"
    results = []

    if not rules_dir.exists():
        return results

    try:
        # Find all .md files recursively
        for rule_file in rules_dir.rglob("*.md"):
            result = read_file_safe(rule_file)

            # Convert FileReadResult to dict with name field
            rule_dict = {
                "exists": result.exists,
                "path": result.path,
                "name": rule_file.name,
            }

            if result.content is not None:
                rule_dict["content"] = result.content
                rule_dict["lines"] = result.lines

            if result.error:
                rule_dict["error"] = result.error

            results.append(rule_dict)

    except Exception:
        # Rules directory exists but can't read
        pass

    return results


def safe_read_context(
    path: Path,
    read_kanban_flag: bool = False,
    read_architecture_flag: bool = False,
    read_rules_flag: bool = False,
    read_all: bool = False
) -> dict:
    """
    Safely read Claude context files.

    Args:
        path: Base path to .claude directory
        read_kanban_flag: Read KANBAN.md
        read_architecture_flag: Read ARCHITECTURE.md
        read_rules_flag: Read rules files
        read_all: Read all context files

    Returns:
        Dictionary with results

    Raises:
        FileNotFoundError: If .claude directory doesn't exist
    """
    # Resolve .claude directory
    claude_dir = path / ".claude"

    if not claude_dir.exists():
        raise FileNotFoundError(f"No .claude directory found at: {path}")

    # Initialize results
    results = {
        "kanban": None,
        "architecture": None,
        "rules": []
    }

    # Read KANBAN.md
    if read_all or read_kanban_flag:
        results["kanban"] = read_kanban(claude_dir)

    # Read ARCHITECTURE.md
    if read_all or read_architecture_flag:
        results["architecture"] = read_architecture(claude_dir)

    # Read rules/**/*.md
    if read_all or read_rules_flag:
        results["rules"] = read_rules(claude_dir)

    return results


class SafeReadContextScript(BaseCLIScript):
    """Safely read Claude context files."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--kanban",
            action="store_true",
            help="Read .claude/KANBAN.md"
        )
        parser.add_argument(
            "--architecture",
            action="store_true",
            help="Read .claude/ARCHITECTURE.md"
        )
        parser.add_argument(
            "--rules",
            action="store_true",
            help="Read all .claude/rules/**/*.md files"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Read all context files (KANBAN, ARCHITECTURE, and rules)"
        )
        parser.add_argument(
            "--path",
            "-p",
            default=".",
            help="Base path to .claude directory (default: current directory)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute context reading."""
        try:
            path = Path(args.path).resolve()

            # Read context
            results = safe_read_context(
                path=path,
                read_kanban_flag=args.kanban,
                read_architecture_flag=args.architecture,
                read_rules_flag=args.rules,
                read_all=args.all
            )

            self.metrics.track("safe_read_context", {
                "kanban": results["kanban"] is not None,
                "architecture": results["architecture"] is not None,
                "rules_count": len(results["rules"])
            })

            return {
                "success": True,
                **results
            }

        except FileNotFoundError as e:
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            self.logger.error(f"Failed to read context: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = []

        # KANBAN.md
        if result["kanban"]:
            kanban = result["kanban"]
            if kanban["exists"]:
                lines.append("=== KANBAN.md ===")
                if "error" in kanban:
                    lines.append(f"ERROR: {kanban['error']}")
                else:
                    lines.append(f"{kanban['lines']} lines")
                    lines.append("")
                    lines.append(kanban["content"])
                lines.append("")
            else:
                lines.append("KANBAN.md not found")
                lines.append("")

        # ARCHITECTURE.md
        if result["architecture"]:
            arch = result["architecture"]
            if arch["exists"]:
                lines.append("=== ARCHITECTURE.md ===")
                if "error" in arch:
                    lines.append(f"ERROR: {arch['error']}")
                else:
                    lines.append(f"{arch['lines']} lines")
                    lines.append("")
                    lines.append(arch["content"])
                lines.append("")
            else:
                lines.append("ARCHITECTURE.md not found")
                lines.append("")

        # Rules
        if result["rules"]:
            lines.append(f"=== RULES ({len(result['rules'])} files) ===")
            for rule in result["rules"]:
                lines.append(f"--- {rule['name']} ---")
                if "error" in rule:
                    lines.append(f"ERROR: {rule['error']}")
                else:
                    lines.append(f"{rule['lines']} lines")
                    lines.append("")
                    lines.append(rule["content"])
                lines.append("")
        elif result["kanban"] or result["architecture"]:
            # Only show if other sections were requested
            lines.append("No rules found")
            lines.append("")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        parts = []
        if result["kanban"]:
            parts.append("KANBAN")
        if result["architecture"]:
            parts.append("ARCHITECTURE")
        if result["rules"]:
            parts.append(f"{len(result['rules'])} rules")

        return f"[OK] Read: {', '.join(parts)}" if parts else "[OK] No context files requested"


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(SafeReadContextScript)
