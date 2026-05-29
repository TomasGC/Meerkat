#!/usr/bin/env python3
"""
Validate markdown files for format compliance (cross-platform).

Validates KANBAN.md, ARCHITECTURE.md, and CLAUDE.md for format compliance,
language requirements, and structure standards.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript, create_cli_script


class ValidateMarkdownScript(BaseCLIScript):
    """Validate markdown files."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--file",
            type=Path,
            required=True,
            help="Path to markdown file"
        )
        parser.add_argument(
            "--type",
            "-t",
            choices=["auto", "kanban", "architecture", "claude", "generic"],
            default="auto",
            help="Validation type (default: auto-detect)"
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat warnings as errors"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute markdown validation."""
        file_path = args.file.resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {args.file}")

        # Detect or use specified type
        if args.type == "auto":
            validation_type = self._detect_type(file_path)
        else:
            validation_type = args.type

        # Validate
        errors, warnings, info = self._validate(file_path, validation_type)

        # Apply strict mode
        if args.strict and warnings:
            errors.extend(warnings)
            warnings = []

        # Track metrics
        self.metrics.track("validate_markdown", {
            "type": validation_type,
            "valid": len(errors) == 0
        })

        return {
            "file": str(file_path),
            "type": validation_type,
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "summary": {
                "errorCount": len(errors),
                "warningCount": len(warnings),
                "infoCount": len(info)
            }
        }

    def _detect_type(self, file_path: Path) -> str:
        """Detect validation type from filename."""
        name = file_path.name.upper()
        if "KANBAN" in name:
            return "kanban"
        elif "ARCHITECTURE" in name:
            return "architecture"
        elif "CLAUDE" in name:
            return "claude"
        else:
            return "generic"

    def _validate(self, file_path: Path, validation_type: str) -> tuple[list, list, list]:
        """Validate markdown file."""
        errors = []
        warnings = []
        info = []

        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            errors.append(f"Failed to read file: {e}")
            return errors, warnings, info

        # Common checks
        self._check_encoding(content, errors, warnings, info)
        self._check_structure(content, errors, warnings, info)

        # Type-specific checks
        if validation_type == "kanban":
            self._check_kanban(content, errors, warnings, info)
        elif validation_type == "architecture":
            self._check_architecture(content, errors, warnings, info)
        elif validation_type == "claude":
            self._check_claude(content, errors, warnings, info)

        return errors, warnings, info

    def _check_encoding(self, content: str, errors: list, warnings: list, info: list):
        """Check file encoding."""
        # Check for non-ASCII characters
        if all(ord(c) < 128 for c in content):
            info.append("File is pure ASCII")
        else:
            info.append("File contains UTF-8 characters")

    def _check_structure(self, content: str, errors: list, warnings: list, info: list):
        """Check markdown structure."""
        lines = content.splitlines()

        # Check for headings
        headings = [l for l in lines if l.startswith('#')]
        if not headings:
            warnings.append("No markdown headings found")
        else:
            info.append(f"Found {len(headings)} headings")

        # Check for empty file
        if not content.strip():
            errors.append("File is empty")

    def _check_kanban(self, content: str, errors: list, warnings: list, info: list):
        """Check KANBAN.md specific requirements."""
        info.append("Validating KANBAN.md format...")

        # Check for required sections
        required_sections = ["TODO", "IN PROGRESS", "DONE"]
        for section in required_sections:
            if section not in content:
                warnings.append(f"Missing recommended section: {section}")

        # Check for date format
        if not re.search(r"\d{4}-\d{2}-\d{2}", content):
            warnings.append("No dates found (YYYY-MM-DD format recommended)")

    def _check_architecture(self, content: str, errors: list, warnings: list, info: list):
        """Check ARCHITECTURE.md specific requirements."""
        info.append("Validating ARCHITECTURE.md format...")

        # Check for architecture keywords
        keywords = ["architecture", "component", "module", "layer", "design"]
        found_keywords = sum(1 for k in keywords if k.lower() in content.lower())

        if found_keywords == 0:
            warnings.append("No architecture-related keywords found")
        else:
            info.append(f"Found {found_keywords} architecture keywords")

    def _check_claude(self, content: str, errors: list, warnings: list, info: list):
        """Check CLAUDE.md specific requirements."""
        info.append("Validating CLAUDE.md format...")

        # Check for English content
        if not re.search(r'[a-zA-Z]', content):
            warnings.append("No English text detected")

        # Check for common Claude.md sections
        common_sections = ["Purpose", "Instructions", "Rules", "Guidelines"]
        found_sections = sum(1 for s in common_sections if s in content)

        if found_sections == 0:
            warnings.append("No common CLAUDE.md sections found")
        else:
            info.append(f"Found {found_sections} common sections")

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        lines = [
            f"Markdown Validation: {result['file']}",
            f"Type: {result['type']}",
            ""
        ]

        if result['errors']:
            lines.append("ERRORS:")
            for error in result['errors']:
                lines.append(f"  [ERROR] {error}")
            lines.append("")

        if result['warnings']:
            lines.append("WARNINGS:")
            for warning in result['warnings']:
                lines.append(f"  [WARN] {warning}")
            lines.append("")

        if result['info']:
            lines.append("INFO:")
            for info_msg in result['info']:
                lines.append(f"  [INFO] {info_msg}")
            lines.append("")

        status = "[OK]" if result['valid'] else "[FAIL]"
        lines.append(f"{status} Validation {'passed' if result['valid'] else 'failed'}")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        status = "OK" if result['valid'] else "FAIL"
        file_name = Path(result['file']).name
        return (f"[{status}] {file_name} ({result['type']}) - "
                f"{result['summary']['errorCount']} errors, "
                f"{result['summary']['warningCount']} warnings")


if __name__ == "__main__":
    create_cli_script(ValidateMarkdownScript)
