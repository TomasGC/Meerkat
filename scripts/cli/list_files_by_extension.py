#!/usr/bin/env python3
"""
List files by extension with smart exclusions.

Replaces: list-files-by-extension.ps1

Recursively finds files matching specified extensions while excluding
common build/dependency directories.
"""

import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript

# Default exclusion patterns
DEFAULT_EXCLUDES = [
    "node_modules/",
    "vendor/",
    "bin/",
    "obj/",
    "dist/",
    "build/",
    ".git/",
    ".tmp/",
    "tmpclaude/",
    "packages/",
    "target/",
    "__pycache__/",
    ".venv/",
    "venv/"
]


def is_excluded(file_path: Path, root: Path, exclude_patterns: list[str]) -> bool:
    """
    Check if file should be excluded based on patterns.

    Args:
        file_path: File path to check
        root: Root search path
        exclude_patterns: List of exclusion patterns

    Returns:
        True if file should be excluded
    """
    try:
        relative = file_path.relative_to(root)
    except ValueError:
        return False

    relative_str = str(relative).replace("\\", "/")

    for pattern in exclude_patterns:
        # Match pattern anywhere in path
        if pattern in relative_str or relative_str.startswith(pattern):
            return True

    return False


def find_files_by_extension(
    root: Path,
    extensions: list[str],
    exclude_patterns: list[str]
) -> list[Path]:
    """
    Find files matching extensions, excluding patterns.

    Args:
        root: Root path to search
        extensions: List of extensions (e.g., [".md", ".txt"])
        exclude_patterns: List of exclusion patterns

    Returns:
        List of matching file paths
    """
    files = []

    # Normalize extensions (ensure they start with dot)
    extensions = [ext if ext.startswith(".") else f".{ext}" for ext in extensions]

    for ext in extensions:
        # Use rglob for recursive search
        for file_path in root.rglob(f"*{ext}"):
            if file_path.is_file() and not is_excluded(file_path, root, exclude_patterns):
                files.append(file_path)

    # Remove duplicates and sort
    files = sorted(set(files))

    return files


class ListFilesByExtensionScript(BaseCLIScript):
    """List files by extension with smart exclusions."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--path",
            "-p",
            default=".",
            help="Root path to search (default: current directory)"
        )
        parser.add_argument(
            "--extensions",
            "-e",
            nargs="+",
            required=True,
            help="Extensions to search (e.g., .md .txt .cs)"
        )
        parser.add_argument(
            "--exclude",
            "-x",
            nargs="*",
            default=DEFAULT_EXCLUDES,
            help="Directory patterns to exclude"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute file listing."""
        try:
            # Resolve path
            root = Path(args.path).resolve()

            if not root.exists():
                return {
                    "success": False,
                    "error": f"Path does not exist: {root}"
                }

            if not root.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {root}"
                }

            # Find files
            files = find_files_by_extension(root, args.extensions, args.exclude)

            self.metrics.track("list_files_by_extension", {
                "extensions": len(args.extensions),
                "files_found": len(files),
            })

            return {
                "success": True,
                "path": str(root),
                "extensions": args.extensions,
                "excluded": args.exclude,
                "count": len(files),
                "files": [
                    {
                        "path": str(f),
                        "relativePath": str(f.relative_to(root)),
                        "name": f.name,
                        "extension": f.suffix,
                        "size": f.stat().st_size
                    }
                    for f in files
                ]
            }

        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = [
            f"Found {result['count']} files in {result['path']}",
            "",
            f"Extensions: {', '.join(result['extensions'])}",
            f"Excluded: {len(result['excluded'])} patterns",
            ""
        ]

        for file in result['files']:
            lines.append(file['path'])

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return f"[OK] Found {result['count']} files ({', '.join(result['extensions'])})"


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(ListFilesByExtensionScript)
