#!/usr/bin/env python3
"""
Validate skill/agent structure for compliance with template standards.

Replaces: validate-skill-structure.ps1

Validates SKILL.md or agent.md files for:
- YAML frontmatter (name, description)
- Required sections (7 for skills, similar for agents)
- No placeholders ([TODO], [PLACEHOLDER], [TBD])
- Valid markdown format
- English content only
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript


@dataclass
class StructureValidationResult:
    """Structure validation result."""
    file: str
    type: str  # skill or agent
    valid: bool
    errors: list[str]
    warnings: list[str]
    info: list[str]

    @property
    def error_count(self) -> int:
        """Number of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Number of warnings."""
        return len(self.warnings)

    @property
    def info_count(self) -> int:
        """Number of info messages."""
        return len(self.info)


def detect_type(file_path: Path) -> str:
    """Detect type from filename."""
    filename = file_path.name

    if filename == "SKILL.md":
        return "skill"
    elif "agent" in str(file_path).lower():
        return "agent"
    else:
        return "skill"  # Default


def validate_yaml_frontmatter(
    content: str,
    errors: list[str],
    warnings: list[str],
    info: list[str]
) -> None:
    """Validate YAML frontmatter."""
    # Match YAML frontmatter
    yaml_match = re.search(r"^---\s*\n(.+?)\n---", content, re.DOTALL | re.MULTILINE)

    if not yaml_match:
        errors.append("Missing YAML frontmatter (should start with ---)")
        return

    yaml_content = yaml_match.group(1)
    info.append("Found YAML frontmatter")

    # Check required fields
    if not re.search(r"name:\s*\S+", yaml_content):
        errors.append("YAML frontmatter missing 'name' field")
    else:
        # Validate name format (lowercase-with-dashes)
        name_match = re.search(r"name:\s*([^\s]+)", yaml_content)
        if name_match:
            name = name_match.group(1)
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                errors.append(f"Name '{name}' invalid (should be lowercase-with-dashes)")

    if not re.search(r"description:\s*", yaml_content):
        errors.append("YAML frontmatter missing 'description' field")
    else:
        # Check if description contains trigger phrases
        desc_match = re.search(r"description:\s*(.+?)(?:\n|$)", yaml_content, re.DOTALL)
        if desc_match:
            description = desc_match.group(1)
            if not re.search(r"(?i)(when|use|trigger|invoke)", description):
                warnings.append("Description should include trigger phrases (when/use/trigger)")


def validate_common_issues(
    content: str,
    errors: list[str],
    warnings: list[str]
) -> None:
    """Validate common issues (placeholders, non-English, markdown)."""
    # Check for placeholders
    if re.search(r"\[TODO\]|\[PLACEHOLDER\]|\[TBD\]", content):
        errors.append("Contains TODO/PLACEHOLDER/TBD markers (must have real content)")

    # Check for non-English content (French accents)
    if re.search(r"[àâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ]", content):
        errors.append("Non-English characters detected (French accents)")

    # Check for broken markdown
    if re.search(r"##[^#\s]", content):
        warnings.append("Malformed heading (missing space after ##)")


def validate_skill_sections(
    content: str,
    errors: list[str],
    warnings: list[str]
) -> None:
    """Validate skill-specific sections."""
    # Required sections for skills (7 mandatory)
    required_sections = [
        "Persona Definition",
        "Tools",
        "Model",
        "Hard Constraints",
        "Operational Guidelines",
        "Self-Verification Checklist",
        "Communication Style"
    ]

    missing_sections = []
    for section in required_sections:
        if not re.search(rf"##\s+{re.escape(section)}", content):
            missing_sections.append(section)

    if missing_sections:
        errors.append(f"Missing required sections: {', '.join(missing_sections)}")

    # Check for "What This Skill Does" section
    if not re.search(r"##\s+What This Skill Does", content):
        warnings.append("Missing 'What This Skill Does' section (recommended)")

    # Check Persona Definition quality
    if re.search(r"##\s+Persona Definition", content):
        persona_match = re.search(
            r"(?ms)##\s+Persona Definition\s*\n(.+?)(?=\n##|\Z)",
            content
        )
        if persona_match:
            persona_section = persona_match.group(1)

            # Should have expertise level
            if not re.search(r"(?i)(principal|senior|expert|lead|staff)", persona_section):
                warnings.append("Persona Definition missing expertise level (principal/senior/expert)")

            # Should not be generic "developer"
            if re.search(r"\bYou are an? developer\b", persona_section) and \
               not re.search(r"(principal|senior|expert|lead) developer", persona_section):
                warnings.append("Persona too generic ('developer' should be 'principal developer', etc.)")

    # Check Self-Verification Checklist format
    if re.search(r"##\s+Self-Verification Checklist", content):
        checklist_match = re.search(
            r"(?ms)##\s+Self-Verification Checklist\s*\n(.+?)(?=\n##|\Z)",
            content
        )
        if checklist_match:
            checklist_section = checklist_match.group(1)

            if not re.search(r"\[\s*\]", checklist_section):
                warnings.append("Self-Verification Checklist should use checkbox format [ ]")


def validate_agent_sections(
    content: str,
    warnings: list[str],
    info: list[str]
) -> None:
    """Validate agent-specific sections."""
    # Required sections for agents
    required_sections = [
        "Core Responsibilities",
        "Hard Constraints"
    ]

    missing_sections = []
    for section in required_sections:
        if not re.search(rf"##\s+{re.escape(section)}", content):
            missing_sections.append(section)

    if missing_sections:
        warnings.append(f"Missing recommended sections: {', '.join(missing_sections)}")

    # Check for YAML frontmatter fields
    yaml_match = re.search(r"^---\s*\n(.+?)\n---", content, re.DOTALL | re.MULTILINE)
    if yaml_match:
        yaml_content = yaml_match.group(1)

        # Check for tools field
        if re.search(r"tools:", yaml_content):
            info.append("Agent defines tools")

        # Check for model field
        if re.search(r"model:", yaml_content):
            info.append("Agent specifies model")


def validate_structure(
    file_path: Path,
    component_type: str = "auto",
    strict: bool = False
) -> StructureValidationResult:
    """
    Validate skill/agent structure.

    Args:
        file_path: Path to SKILL.md or agent.md
        component_type: Type (auto, skill, agent)
        strict: Enable strict validation (warnings become errors)

    Returns:
        StructureValidationResult
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Auto-detect type
    if component_type == "auto":
        component_type = detect_type(file_path)

    # Read file
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Failed to read file: {e}")

    # Initialize collections
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    # Validate YAML frontmatter
    validate_yaml_frontmatter(content, errors, warnings, info)

    # Validate common issues
    validate_common_issues(content, errors, warnings)

    # Type-specific validations
    if component_type == "skill":
        validate_skill_sections(content, errors, warnings)
    elif component_type == "agent":
        validate_agent_sections(content, warnings, info)

    # Determine validity
    if strict:
        valid = len(errors) == 0 and len(warnings) == 0
    else:
        valid = len(errors) == 0

    return StructureValidationResult(
        file=str(file_path),
        type=component_type,
        valid=valid,
        errors=errors,
        warnings=warnings,
        info=info
    )


class ValidateSkillStructureScript(BaseCLIScript):
    """Validate skill/agent structure for compliance with template standards."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--file",
            type=Path,
            required=True,
            help="Path to SKILL.md or agent.md file"
        )
        parser.add_argument(
            "--type",
            "-t",
            choices=["auto", "skill", "agent"],
            default="auto",
            help="Type of validation (default: auto-detect)"
        )
        parser.add_argument(
            "--strict",
            "-s",
            action="store_true",
            help="Enable strict validation (warnings become errors)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute validation logic."""
        try:
            # Validate structure
            result = validate_structure(
                args.file,
                component_type=args.type,
                strict=args.strict
            )

            self.metrics.track("validate_skill_structure", {
                "file": str(args.file),
                "type": result.type,
                "valid": result.valid,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "strict": args.strict
            })

            return {
                "success": result.valid,
                "file": result.file,
                "type": result.type,
                "valid": result.valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "info": result.info,
                "summary": {
                    "errorCount": result.error_count,
                    "warningCount": result.warning_count,
                    "infoCount": result.info_count
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to validate structure: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = [
            f"Validation: {result['file']}",
            f"Type: {result['type']}",
            ""
        ]

        if result["errors"]:
            lines.append("ERRORS:")
            for error in result["errors"]:
                lines.append(f"  [X] {error}")
            lines.append("")

        if result["warnings"]:
            lines.append("WARNINGS:")
            for warning in result["warnings"]:
                lines.append(f"  [!] {warning}")
            lines.append("")

        if result["info"]:
            lines.append("INFO:")
            for i in result["info"]:
                lines.append(f"  [i] {i}")
            lines.append("")

        status = "[OK]" if result["valid"] else "[FAIL]"
        lines.append(f"{status} Validation {'passed' if result['valid'] else 'failed'}")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        # Check for execution error (not validation failure)
        if "error" in result:
            return f"[ERROR] {result['error']}"

        # Validation result
        status = "[OK]" if result["valid"] else "[FAIL]"
        return (f"{status} ({result['summary']['errorCount']} errors, "
                f"{result['summary']['warningCount']} warnings)")


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(ValidateSkillStructureScript)
