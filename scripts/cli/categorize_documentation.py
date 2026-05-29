#!/usr/bin/env python3
"""
Categorize documentation files into FUNCTIONAL, TECHNICAL, and PERSONAL.

Replaces: categorize-documentation.ps1

Analyzes documentation files and categorizes them based on filename,
location, and content patterns. Used for organizing project documentation
in CLAUDE.md section 4.
"""

import re
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript

# Categorization patterns
FUNCTIONAL_PATTERNS = [
    "readme",
    "changelog",
    "contributing",
    "user-guide",
    "getting-started",
    "requirements",
    "specifications",
    "spec",
    "faq",
    "pull_request_template",
    "pr_template",
    "issue_template"
]

TECHNICAL_PATTERNS = [
    "architecture",
    r"claude\.md",
    r"kanban\.md",
    "api",
    "design",
    "implementation",
    "technical",
    "deployment",
    "database",
    "schema",
    "testing",
    "setup",
    "install",
    "config",
    "development"
]

TECHNICAL_PATHS = ["docs/", ".claude/", "documentation/", "dev/"]


def categorize_file(file_path: str) -> dict:
    """Categorize a single documentation file."""
    path_obj = Path(file_path)
    file_name = path_obj.name
    file_name_lower = file_name.lower()
    file_path_lower = file_path.lower()

    # PERSONAL category (always *.local.md or *-local.md)
    if re.search(r"[.-]local\.(md|txt)$", file_name_lower):
        return {
            "path": file_path,
            "name": file_name,
            "category": "PERSONAL",
            "reason": "Local override file (not committed)"
        }

    # FUNCTIONAL category indicators
    for pattern in FUNCTIONAL_PATTERNS:
        if re.search(pattern, file_name_lower):
            return {
                "path": file_path,
                "name": file_name,
                "category": "FUNCTIONAL",
                "reason": "User-facing documentation"
            }

    # TECHNICAL category indicators
    for pattern in TECHNICAL_PATTERNS:
        if re.search(pattern, file_name_lower):
            return {
                "path": file_path,
                "name": file_name,
                "category": "TECHNICAL",
                "reason": "Technical documentation for developers"
            }

    # Check path for technical indicators
    for tech_path in TECHNICAL_PATHS:
        if tech_path in file_path_lower:
            return {
                "path": file_path,
                "name": file_name,
                "category": "TECHNICAL",
                "reason": "Technical documentation for developers"
            }

    # Default to TECHNICAL if in docs/ or .claude/
    if re.search(r"(docs/|\.claude/)", file_path_lower):
        return {
            "path": file_path,
            "name": file_name,
            "category": "TECHNICAL",
            "reason": "Documentation file in technical directory"
        }

    # Fallback to FUNCTIONAL for root-level docs
    return {
        "path": file_path,
        "name": file_name,
        "category": "FUNCTIONAL",
        "reason": "Root-level documentation"
    }


def categorize_documentation(files: list[str]) -> dict:
    """Categorize multiple documentation files."""
    functional = []
    technical = []
    personal = []

    for file_path in files:
        categorization = categorize_file(file_path)

        if categorization["category"] == "FUNCTIONAL":
            functional.append(categorization)
        elif categorization["category"] == "TECHNICAL":
            technical.append(categorization)
        elif categorization["category"] == "PERSONAL":
            personal.append(categorization)

    result = {
        "total": len(files),
        "functional": functional,
        "technical": technical,
        "personal": personal,
        "summary": {
            "functionalCount": len(functional),
            "technicalCount": len(technical),
            "personalCount": len(personal)
        }
    }

    return result


class CategorizeDocumentationScript(BaseCLIScript):
    """Categorize documentation files into FUNCTIONAL, TECHNICAL, and PERSONAL."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--files",
            nargs="+",
            required=True,
            help="File paths to categorize"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute documentation categorization."""
        try:
            # Categorize documentation
            result = categorize_documentation(args.files)

            self.metrics.track("categorize_documentation", {
                "total": result["total"],
                "functional": result["summary"]["functionalCount"],
                "technical": result["summary"]["technicalCount"],
                "personal": result["summary"]["personalCount"]
            })

            return {
                "success": True,
                **result
            }

        except Exception as e:
            self.logger.error(f"Failed to categorize documentation: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = [
            "Documentation Categorization Results",
            "=====================================",
            "",
            f"Total files: {result['total']}",
            ""
        ]

        lines.append(f"FUNCTIONAL ({len(result['functional'])} files):")
        for item in result["functional"]:
            lines.append(f"  - {item['name']} [{item['reason']}]")
        lines.append("")

        lines.append(f"TECHNICAL ({len(result['technical'])} files):")
        for item in result["technical"]:
            lines.append(f"  - {item['name']} [{item['reason']}]")
        lines.append("")

        lines.append(f"PERSONAL ({len(result['personal'])} files):")
        for item in result["personal"]:
            lines.append(f"  - {item['name']} [{item['reason']}]")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return (f"Categorized {result['total']} files: "
                f"FUNCTIONAL={result['summary']['functionalCount']}, "
                f"TECHNICAL={result['summary']['technicalCount']}, "
                f"PERSONAL={result['summary']['personalCount']}")


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(CategorizeDocumentationScript)
