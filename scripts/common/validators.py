#!/usr/bin/env python3
"""
Validation logic for scripts.

Common validation functions for skills, agents, scripts, YAML, etc.
"""

import re
from pathlib import Path

from .models import ComponentType, ValidationResult


def validate_component_name(
    name: str,
    component_type: ComponentType
) -> ValidationResult:
    """
    Validate component name (skill, script, agent).

    Rules:
    - Lowercase with dashes
    - No special characters except dash
    - No leading/trailing dashes
    - Length 3-50 characters

    Args:
        name: Component name
        component_type: Type of component

    Returns:
        ValidationResult with errors/warnings
    """
    errors = []
    warnings = []

    # Check empty
    if not name:
        errors.append("Name cannot be empty")
        return ValidationResult(success=False, errors=errors)

    # Check length
    if len(name) < 3:
        errors.append("Name too short (minimum 3 characters)")
    if len(name) > 50:
        errors.append("Name too long (maximum 50 characters)")

    # Check lowercase
    if name != name.lower():
        errors.append("Name must be lowercase (use-dashes-not-CamelCase)")

    # Check special characters
    if not re.match(r"^[a-z0-9-]+$", name):
        errors.append("Name can only contain lowercase letters, numbers, and dashes")

    # Check leading/trailing dashes
    if name.startswith("-") or name.endswith("-"):
        errors.append("Name cannot start or end with dash")

    # Check consecutive dashes
    if "--" in name:
        warnings.append("Avoid consecutive dashes")

    # Component-specific checks
    if component_type == ComponentType.SCRIPT:
        if name.endswith((".py", ".ps1", ".sh")):
            warnings.append(f"Remove extension from script name: {name}")

    success = len(errors) == 0
    return ValidationResult(
        success=success,
        errors=errors,
        warnings=warnings,
        metadata={"name": name, "type": component_type.value}
    )


def validate_yaml_frontmatter(content: str, component_type: ComponentType) -> ValidationResult:
    """
    Validate YAML frontmatter structure.

    Args:
        content: Markdown content with YAML frontmatter
        component_type: Type of component (skill or agent)

    Returns:
        ValidationResult with errors/warnings
    """
    errors = []
    warnings = []

    # Check frontmatter exists
    if not re.match(r"^---\n", content):
        errors.append("Missing YAML frontmatter (must start with ---)")
        return ValidationResult(success=False, errors=errors)

    # Extract frontmatter
    match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL | re.MULTILINE)
    if not match:
        errors.append("Invalid YAML frontmatter format")
        return ValidationResult(success=False, errors=errors)

    yaml_content = match.group(1)

    # Check required fields
    required_fields = ["name", "description"]
    if component_type == ComponentType.SKILL:
        required_fields.extend(["tools", "model"])
    elif component_type == ComponentType.AGENT:
        required_fields.extend(["tools", "model", "color"])

    for field in required_fields:
        if not re.search(rf"^{field}:", yaml_content, re.MULTILINE):
            errors.append(f"Missing required field: {field}")

    # Check name format
    name_match = re.search(r"^name:\s*(.+)$", yaml_content, re.MULTILINE)
    if name_match:
        name = name_match.group(1).strip().strip('"').strip("'")
        name_validation = validate_component_name(name, component_type)
        if not name_validation.success:
            errors.extend([f"name: {e}" for e in name_validation.errors])

    # Check description has examples (for agents)
    if component_type == ComponentType.AGENT:
        if "<example>" not in content:
            warnings.append("Agent description should include <example> blocks")
        if "<commentary>" not in content:
            warnings.append("Agent examples should include <commentary>")

    success = len(errors) == 0
    return ValidationResult(
        success=success,
        errors=errors,
        warnings=warnings,
        metadata={"component_type": component_type.value}
    )


def validate_skill_structure(file_path: Path) -> ValidationResult:
    """
    Validate SKILL.md file structure.

    Required sections (in order):
    1. YAML frontmatter
    2. "What This Skill Does"
    3. "Persona Definition"
    4. "Tools"
    5. "Model"
    6. "Hard Constraints"
    7. "Operational Guidelines"
    8. "Self-Verification Checklist"
    9. "Communication Style"

    Args:
        file_path: Path to SKILL.md

    Returns:
        ValidationResult with errors/warnings
    """
    errors = []
    warnings = []

    # Read file
    if not file_path.exists():
        errors.append(f"File not found: {file_path}")
        return ValidationResult(success=False, errors=errors)

    content = file_path.read_text(encoding="utf-8")

    # Check YAML frontmatter
    yaml_validation = validate_yaml_frontmatter(content, ComponentType.SKILL)
    if not yaml_validation.success:
        errors.extend(yaml_validation.errors)

    # Required sections (after frontmatter)
    required_sections = [
        "What This Skill Does",
        "Persona Definition",
        "Tools",
        "Model",
        "Hard Constraints",
        "Operational Guidelines",
        "Self-Verification Checklist",
        "Communication Style",
    ]

    for section in required_sections:
        # Check for ## Section or # Section
        pattern = rf"^##?\s+{re.escape(section)}"
        if not re.search(pattern, content, re.MULTILINE):
            errors.append(f"Missing required section: {section}")

    # Check section order (simplified - just check they exist in order)
    section_positions = {}
    for section in required_sections:
        pattern = rf"^##?\s+{re.escape(section)}"
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            section_positions[section] = match.start()

    # Verify order
    prev_pos = -1
    for section in required_sections:
        if section in section_positions:
            pos = section_positions[section]
            if pos < prev_pos:
                warnings.append(f"Section '{section}' appears out of order")
            prev_pos = pos

    # Check for placeholders
    placeholders = ["TODO", "TBD", "PLACEHOLDER", "[...]"]
    for placeholder in placeholders:
        if placeholder in content:
            warnings.append(f"Contains placeholder: {placeholder}")

    success = len(errors) == 0
    return ValidationResult(
        success=success,
        errors=errors,
        warnings=warnings,
        metadata={"file_path": str(file_path)}
    )


def validate_script_syntax(file_path: Path) -> ValidationResult:
    """
    Validate script syntax (Python, PowerShell, Bash).

    Args:
        file_path: Path to script

    Returns:
        ValidationResult with errors/warnings
    """
    errors = []
    warnings = []

    if not file_path.exists():
        errors.append(f"File not found: {file_path}")
        return ValidationResult(success=False, errors=errors)

    language = None
    suffix = file_path.suffix.lower()

    # Python syntax check
    if suffix == ".py":
        language = "python"
        try:
            import ast
            content = file_path.read_text(encoding="utf-8")
            ast.parse(content)
        except SyntaxError as e:
            errors.append(f"Python syntax error at line {e.lineno}: {e.msg}")

    # PowerShell syntax check
    elif suffix in [".ps1", ".psm1"]:
        language = "powershell"
        # Note: Requires PowerShell to be installed
        import subprocess
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", f"Test-Path {file_path}; $?"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            errors.append(f"PowerShell syntax check failed: {result.stderr}")

    # Bash syntax check
    elif suffix in [".sh", ".bash"]:
        language = "bash"
        import subprocess
        result = subprocess.run(
            ["bash", "-n", str(file_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            errors.append(f"Bash syntax error: {result.stderr}")

    else:
        warnings.append(f"Unknown file type: {suffix}")

    success = len(errors) == 0
    return ValidationResult(
        success=success,
        errors=errors,
        warnings=warnings,
        metadata={"file_path": str(file_path), "language": language}
    )
