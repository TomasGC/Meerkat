#!/usr/bin/env python3
"""
Extract and parse YAML frontmatter from markdown files.

Replaces: ~/.claude/scripts/read-yaml-frontmatter.ps1

Reads YAML frontmatter from markdown files (between --- delimiters)
and parses it into structured data. Used for skills, agents, hooks.
"""

import re
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from common.cli.base import BaseCLIScript
from common.formatters import format_yaml


def extract_frontmatter(file_path: Path) -> Optional[dict]:
    """Extract YAML frontmatter between --- delimiters."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return None

    # Match frontmatter (multiline)
    pattern = r'^---\n(.*?)\n---'
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)

    if not match:
        return None

    yaml_content = match.group(1)

    # Parse YAML
    if YAML_AVAILABLE:
        try:
            parsed = yaml.safe_load(yaml_content)
            return parsed if isinstance(parsed, dict) else {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML: {e}")
    else:
        # Fallback: simple key-value parser
        return parse_yaml_simple(yaml_content)


def parse_yaml_simple(yaml_content: str) -> dict:
    """Simple YAML parser (fallback when PyYAML not installed)."""
    parsed = {}
    current_key = None
    current_value_lines = []
    in_multiline = False

    for line in yaml_content.split("\n"):
        line = line.rstrip()

        # Skip empty lines
        if not line.strip():
            continue

        # Check for key: value pattern
        if ":" in line and not line.startswith(" "):
            # Save previous multiline value
            if in_multiline and current_key:
                parsed[current_key] = "\n".join(current_value_lines).strip()
                current_value_lines = []
                in_multiline = False

            key, _, value = line.partition(":")
            current_key = key.strip()
            value = value.strip()

            if value in ["|", ">"]:
                # Multiline string
                in_multiline = True
                current_value_lines = []
            elif value.startswith("[") and value.endswith("]"):
                # Array
                array_content = value[1:-1]
                parsed[current_key] = [
                    item.strip().strip('"').strip("'")
                    for item in array_content.split(",")
                ]
            else:
                # Simple value - strip quotes if present
                if value.startswith('"') and value.endswith('"'):
                    parsed[current_key] = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    parsed[current_key] = value[1:-1]
                else:
                    parsed[current_key] = value if value else None
        elif in_multiline:
            # Multiline continuation
            if line.startswith("  "):
                current_value_lines.append(line[2:])
            else:
                current_value_lines.append(line)

    # Save final multiline value
    if in_multiline and current_key:
        parsed[current_key] = "\n".join(current_value_lines).strip()

    return parsed


class ReadYamlFrontmatterScript(BaseCLIScript):
    """Extract and parse YAML frontmatter from markdown files."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--file",
            required=True,
            type=Path,
            help="Path to markdown file with YAML frontmatter"
        )
        parser.add_argument(
            "--format-yaml",
            action="store_true",
            help="Output as YAML (alternative to --format)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute YAML frontmatter extraction."""
        try:
            # Extract frontmatter
            frontmatter = extract_frontmatter(args.file)

            if not YAML_AVAILABLE and args.format_yaml:
                self.logger.warning("PyYAML not installed, using JSON output")

            self.metrics.track("read_yaml_frontmatter", {
                "file": str(args.file),
                "has_yaml": YAML_AVAILABLE
            })

            return {
                "success": True,
                "frontmatter": frontmatter,
                "format_yaml": args.format_yaml if hasattr(args, 'format_yaml') and YAML_AVAILABLE else False
            }

        except Exception as e:
            self.logger.error(f"Failed to extract frontmatter: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = []
        for key, value in result["frontmatter"].items():
            if isinstance(value, list):
                lines.append(f"{key}: {', '.join(str(v) for v in value)}")
            elif isinstance(value, str) and "\n" in value:
                lines.append(f"{key}:")
                for line in value.split("\n"):
                    lines.append(f"  {line}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        keys = list(result["frontmatter"].keys())
        return f"Extracted {len(keys)} fields: {', '.join(keys)}"

    def output(self, result: dict, format: str) -> None:
        """Override output to support YAML format."""
        if result.get("format_yaml"):
            print(format_yaml(result["frontmatter"]))
        else:
            super().output(result, format)


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(ReadYamlFrontmatterScript)
