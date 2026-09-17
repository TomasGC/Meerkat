#!/usr/bin/env python3
"""
Output formatting utilities.

Consistent formatting for JSON, YAML, text, markdown outputs.
"""

import json
from typing import Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .models import OutputFormat, ValidationResult


def format_json(data: Any, indent: int = 2) -> str:
    """
    Format data as JSON.

    Args:
        data: Data to format
        indent: Indentation spaces

    Returns:
        JSON string
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)


def format_yaml(data: Any) -> str:
    """
    Format data as YAML.

    Args:
        data: Data to format

    Returns:
        YAML string
    """
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML not installed. Run: pip install pyyaml")

    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def format_text(data: dict[str, Any]) -> str:
    """
    Format data as human-readable text.

    Args:
        data: Dictionary to format

    Returns:
        Text string
    """
    lines = []
    for key, value in data.items():
        if isinstance(value, (list, dict)):
            lines.append(f"{key}:")
            if isinstance(value, list):
                for item in value:
                    lines.append(f"  - {item}")
            else:
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
        else:
            lines.append(f"{key}: {value}")

    return "\n".join(lines)


def format_validation_result(result: ValidationResult, format: OutputFormat) -> str:
    """
    Format validation result for output.

    Args:
        result: ValidationResult to format
        format: Output format

    Returns:
        Formatted string
    """
    if format == OutputFormat.JSON:
        return format_json({
            "success": result.success,
            "errors": result.errors,
            "warnings": result.warnings,
            "info": result.info,
            "metadata": result.metadata,
        })

    elif format == OutputFormat.YAML:
        return format_yaml({
            "success": result.success,
            "errors": result.errors,
            "warnings": result.warnings,
            "info": result.info,
            "metadata": result.metadata,
        })

    else:  # TEXT
        lines = []

        if result.success:
            lines.append("✅ Validation passed")
        else:
            lines.append("❌ Validation failed")

        if result.errors:
            lines.append("\nErrors:")
            for error in result.errors:
                lines.append(f"  - {error}")

        if result.warnings:
            lines.append("\nWarnings:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")

        if result.info:
            lines.append("\nInfo:")
            for info in result.info:
                lines.append(f"  - {info}")

        return "\n".join(lines)


def format_table(
    headers: list[str],
    rows: list[list[str]],
    markdown: bool = False
) -> str:
    """
    Format data as ASCII or Markdown table.

    Args:
        headers: Column headers
        rows: Data rows
        markdown: Use Markdown format

    Returns:
        Table string
    """
    if not rows:
        return ""

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    lines = []

    if markdown:
        # Markdown table
        header_line = "| " + " | ".join(
            h.ljust(col_widths[i]) for i, h in enumerate(headers)
        ) + " |"
        lines.append(header_line)

        separator = "| " + " | ".join("-" * w for w in col_widths) + " |"
        lines.append(separator)

        for row in rows:
            row_line = "| " + " | ".join(
                str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
            ) + " |"
            lines.append(row_line)

    else:
        # ASCII table
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

        lines.append(separator)

        header_line = "|" + "|".join(
            f" {h.ljust(col_widths[i])} " for i, h in enumerate(headers)
        ) + "|"
        lines.append(header_line)
        lines.append(separator)

        for row in rows:
            row_line = "|" + "|".join(
                f" {str(cell).ljust(col_widths[i])} " for i, cell in enumerate(row)
            ) + "|"
            lines.append(row_line)

        lines.append(separator)

    return "\n".join(lines)


def format_summary(
    title: str,
    stats: dict[str, Any],
    details: list[str] | None = None
) -> str:
    """
    Format a summary report.

    Args:
        title: Report title
        stats: Statistics dict
        details: Optional detailed list

    Returns:
        Formatted summary
    """
    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
    ]

    for key, value in stats.items():
        # Format key (replace underscores with spaces, title case)
        formatted_key = key.replace("_", " ").title()
        lines.append(f"- **{formatted_key}**: {value}")

    if details:
        lines.extend([
            "",
            "## Details",
            "",
        ])
        for detail in details:
            lines.append(f"- {detail}")

    return "\n".join(lines)


def format_error(error_message: str, context: dict[str, Any] | None = None) -> str:
    """
    Format error message with optional context.

    Args:
        error_message: Error message
        context: Optional context dict

    Returns:
        Formatted error string
    """
    lines = [f"❌ Error: {error_message}"]

    if context:
        lines.append("\nContext:")
        for key, value in context.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)
