#!/usr/bin/env python3
"""
Format and validate commit messages according to standard.

Replaces: format-commit-message.ps1

Validates commit message format using active integration profile.
Example: #123: feat: add user authentication
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.integrations import get_issue_format

# Commit types
COMMIT_TYPES = ["feat", "fix", "refactor", "test", "docs", "chore", "style", "perf", "ci", "build"]


def _get_commit_pattern() -> str:
    """Build commit pattern from active profile's issue format."""
    issue_pattern = get_issue_format()
    # Build full pattern: <issue>: <type>: <message>
    return rf"^({issue_pattern}):\s+(feat|fix|refactor|test|docs|chore|style|perf|ci|build):\s+.{{3,}}"

COMMIT_TYPES = ["feat", "fix", "refactor", "test", "docs", "chore", "style", "perf", "ci", "build"]


@dataclass
class ValidationResult:
    """Commit message validation result."""
    valid: bool
    message: str
    errors: list[str]
    warnings: list[str]
    suggestion: Optional[str] = None


def validate_commit_message(
    message: str,
    suggest: bool = False
) -> ValidationResult:
    """Validate commit message format using active profile."""
    commit_pattern = _get_commit_pattern()
    issue_pattern = get_issue_format()

    is_valid = bool(re.match(commit_pattern, message))
    errors: list[str] = []
    warnings: list[str] = []

    if not is_valid:
        # Analyze what's wrong
        if not re.search(rf"^({issue_pattern}):", message):
            errors.append("Missing or invalid issue ID (check active integration profile format)")

        if not re.search(r":\s+(feat|fix|refactor|test|docs|chore|style|perf|ci|build):", message):
            errors.append("Missing or invalid type (should be one of: " + ", ".join(COMMIT_TYPES) + ")")

        if len(message) < 10:
            errors.append("Message too short (minimum 10 characters)")

    # Check description quality (always check, even if valid)
    if re.search(r":\s+[A-Z]", message):
        warnings.append("Description should start with lowercase (except proper nouns)")

    if message.endswith("."):
        warnings.append("Description should not end with period")

    if re.search(r"\b(added|fixed|refactored|updated)\b", message):
        warnings.append("Use imperative mood (add, fix, refactor, not added, fixed)")

    # Generate suggestion if requested
    suggestion = None
    if suggest and not is_valid:
        suggestion = generate_suggestion(message)

    return ValidationResult(
        valid=is_valid,
        message=message,
        errors=errors,
        warnings=warnings,
        suggestion=suggestion
    )


def generate_suggestion(message: str) -> Optional[str]:
    """Generate corrected commit message suggestion."""
    suggested_issue = None
    suggested_type = None
    suggested_message = message

    # Extract issue
    issue_match = re.search(r"([A-Z]+-\d+|#\d+)", message)
    if issue_match:
        suggested_issue = issue_match.group(1)
        suggested_message = re.sub(r"([A-Z]+-\d+|#\d+)[:\s]*", "", suggested_message)

    # Clean up message first
    suggested_message = suggested_message.strip()
    suggested_message = re.sub(r"^[:\s]+", "", suggested_message)
    suggested_message = re.sub(r"\.$", "", suggested_message)

    # Convert past tense to imperative BEFORE extracting type
    suggested_message = re.sub(r"\badded\b", "add", suggested_message)
    suggested_message = re.sub(r"\bfixed\b", "fix", suggested_message)
    suggested_message = re.sub(r"\brefactored\b", "refactor", suggested_message)
    suggested_message = re.sub(r"\bupdated\b", "update", suggested_message)
    suggested_message = re.sub(r"\bcreated\b", "create", suggested_message)

    # Extract type
    type_match = re.search(r"(feat|fix|refactor|test|docs|chore|style|perf|ci|build)", message)
    if type_match:
        suggested_type = type_match.group(1)
        suggested_message = re.sub(r"(feat|fix|refactor|test|docs|chore|style|perf|ci|build)[:\s]*", "", suggested_message, count=1)
    else:
        # Infer type from message
        if re.search(r"\b(add|implement|create)\b", suggested_message):
            suggested_type = "feat"
        elif re.search(r"\b(fix|resolve|correct)\b", suggested_message):
            suggested_type = "fix"
        elif re.search(r"\b(refactor|extract|reorganize)\b", suggested_message):
            suggested_type = "refactor"
        elif re.search(r"\b(test|spec)\b", suggested_message):
            suggested_type = "test"
        elif re.search(r"\b(doc|readme)\b", suggested_message):
            suggested_type = "docs"
        else:
            suggested_type = "chore"

    # Final cleanup
    suggested_message = suggested_message.strip()
    suggested_message = re.sub(r"^[:\s]+", "", suggested_message)

    if suggested_message:
        # Lowercase first letter
        suggested_message = suggested_message[0].lower() + suggested_message[1:]

    if suggested_issue and suggested_type and suggested_message:
        return f"{suggested_issue}: {suggested_type}: {suggested_message}"

    return None


def format_commit_message(issue_id: str, commit_type: str, message: str) -> str:
    """Format commit message according to standard."""
    # Clean message
    message = message.strip()
    message = re.sub(r"\.$", "", message)

    # Lowercase first letter (unless proper noun)
    if message and not message[0].isupper() or (message and len(message) > 1 and message[1].isupper()):
        message = message[0].lower() + message[1:]

    return f"{issue_id}: {commit_type}: {message}"


class FormatCommitMessageScript(BaseCLIScript):
    """Format and validate commit messages according to standard."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--message",
            "-m",
            required=True,
            help="Commit message to validate or format"
        )
        parser.add_argument(
            "--validate",
            "-v",
            action="store_true",
            help="Validate message format (default mode)"
        )
        parser.add_argument(
            "--suggest",
            "-s",
            action="store_true",
            help="Generate correction suggestions for invalid messages"
        )
        parser.add_argument(
            "--issue",
            "-t",
            help="Issue ID for formatting mode (e.g., #123)"
        )
        parser.add_argument(
            "--type",
            choices=COMMIT_TYPES,
            help="Commit type for formatting mode"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute commit message validation or formatting."""
        try:
            # Validate mode (default)
            if args.validate or not (args.issue and args.type):
                result = validate_commit_message(args.message, args.suggest)

                self.metrics.track("format_commit_message", {
                    "mode": "validate",
                    "valid": result.valid
                })

                return {
                    "success": True,
                    "mode": "validate",
                    "valid": result.valid,
                    "message": result.message,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "suggestion": result.suggestion
                }

            # Format mode
            else:
                formatted = format_commit_message(args.issue, args.type, args.message)

                # Validate the formatted message
                validation = validate_commit_message(formatted)

                self.metrics.track("format_commit_message", {
                    "mode": "format",
                    "valid": validation.valid
                })

                return {
                    "success": True,
                    "mode": "format",
                    "original": args.message,
                    "formatted": formatted,
                    "valid": validation.valid
                }

        except Exception as e:
            self.logger.error(f"Failed to process commit message: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        if result["mode"] == "validate":
            lines = []

            if result["valid"]:
                lines.append("[OK] Valid commit message")
            else:
                lines.append("[FAIL] Invalid commit message")

            if result["errors"]:
                lines.append("")
                lines.append("Errors:")
                for error in result["errors"]:
                    lines.append(f"  [X] {error}")

            if result["warnings"]:
                lines.append("")
                lines.append("Warnings:")
                for warning in result["warnings"]:
                    lines.append(f"  [!] {warning}")

            if result["suggestion"]:
                lines.append("")
                lines.append(f"Suggestion: {result['suggestion']}")

            return "\n".join(lines)

        else:  # format mode
            lines = [
                f"Original: {result['original']}",
                f"Formatted: {result['formatted']}",
                f"Valid: {'Yes' if result['valid'] else 'No'}"
            ]
            return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        if result["mode"] == "validate":
            status = "[OK]" if result["valid"] else "[FAIL]"
            details = f"{len(result['errors'])} errors, {len(result['warnings'])} warnings"
            return f"{status} {details}"
        else:
            return result["formatted"]


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(FormatCommitMessageScript)
