#!/usr/bin/env python3
"""Common utilities for black-box-analyzer scripts.

File operations, JSON helpers, and utility functions.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Generator

from .constants import EXCLUDED_DIRS
from .models import Parameter


def walk_files(
    root_path: Path, patterns: list[str], recursive: bool = True
) -> Generator[Path, None, None]:
    """
    Walk directory tree and yield files matching patterns.

    Args:
        root_path: Root directory to search
        patterns: Glob patterns to match (e.g., ["*.py", "test_*.py"])
        recursive: Search subdirectories

    Yields:
        Path objects for matching files
    """
    if not root_path.exists():
        raise FileNotFoundError(f"Path not found: {root_path}")

    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_path}")

    for pattern in patterns:
        if recursive:
            # Use rglob for recursive search
            for file_path in root_path.rglob(pattern):
                # Skip excluded directories
                if any(excluded in file_path.parts for excluded in EXCLUDED_DIRS):
                    continue
                if file_path.is_file():
                    yield file_path
        else:
            # Use glob for non-recursive search
            for file_path in root_path.glob(pattern):
                if file_path.is_file():
                    yield file_path


def read_file_safe(file_path: Path, encoding: str = "utf-8") -> str | None:
    """
    Safely read file contents with error handling.

    Args:
        file_path: Path to file
        encoding: File encoding (default: utf-8)

    Returns:
        File contents as string, or None if error
    """
    try:
        return file_path.read_text(encoding=encoding)
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Failed to read {file_path}: {e}", file=sys.stderr)
        return None


def write_json(data: Any, output_path: Path | None = None, indent: int = 2) -> None:
    """
    Write data as JSON to file or stdout.

    Args:
        data: Data to serialize
        output_path: Output file path (None = stdout)
        indent: JSON indentation level
    """
    json_str = json.dumps(data, indent=indent, ensure_ascii=False)

    if output_path:
        output_path.write_text(json_str, encoding="utf-8")
    else:
        print(json_str)


def read_json(file_path: Path) -> Any:
    """
    Read JSON file with error handling.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If invalid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in {file_path}: {e.msg}", e.doc, e.pos
        )


def find_project_root(start_path: Path) -> Path | None:
    """
    Find project root by looking for common indicators.

    Searches upward from start_path for:
    - go.mod
    - package.json
    - *.csproj
    - requirements.txt
    - pom.xml

    Args:
        start_path: Starting directory

    Returns:
        Project root path, or None if not found
    """
    indicators = [
        "go.mod",
        "package.json",
        "*.csproj",
        "requirements.txt",
        "pyproject.toml",
        "pom.xml",
        "build.gradle",
        "Cargo.toml",
    ]

    current = start_path.resolve()

    # Search up to 10 levels
    for _ in range(10):
        for indicator in indicators:
            if "*" in indicator:
                # Glob pattern
                if list(current.glob(indicator)):
                    return current
            else:
                # Exact file
                if (current / indicator).exists():
                    return current

        # Move up one level
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    return None


def count_lines_of_code(file_path: Path) -> int:
    """
    Count non-empty, non-comment lines in a file.

    Args:
        file_path: Path to source file

    Returns:
        Line count
    """
    content = read_file_safe(file_path)
    if not content:
        return 0

    lines = content.splitlines()
    # Simple heuristic: skip empty lines and lines starting with # or //
    return sum(
        1
        for line in lines
        if line.strip() and not line.strip().startswith(("#", "//"))
    )


def format_path_relative(file_path: Path, root_path: Path) -> str:
    """
    Format file path relative to root.

    Args:
        file_path: Absolute file path
        root_path: Root directory

    Returns:
        Relative path as string
    """
    try:
        return str(file_path.relative_to(root_path))
    except ValueError:
        # Not relative to root
        return str(file_path)


def extract_line_number_from_pattern(content: str, pattern: str) -> int:
    """
    Find line number where pattern first appears.

    Args:
        content: File content
        pattern: String pattern to find

    Returns:
        Line number (1-indexed), or 0 if not found
    """
    for line_num, line in enumerate(content.splitlines(), start=1):
        if pattern in line:
            return line_num
    return 0


def merge_dicts_deep(dict1: dict, dict2: dict) -> dict:
    """
    Deep merge two dictionaries.

    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)

    Returns:
        Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts_deep(result[key], value)
        else:
            result[key] = value

    return result


def ensure_dir(dir_path: Path) -> None:
    """
    Ensure directory exists, create if needed.

    Args:
        dir_path: Directory path
    """
    dir_path.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    return filename


def extract_params_from_path(path: str):
    """
    Extract path parameters from URL pattern.

    Supports multiple parameter styles:
    - Express/Gin style: /users/:id
    - ASP.NET/Spring style: /users/{id}

    Args:
        path: URL path with parameter placeholders

    Returns:
        List of Parameter objects

    Examples:
        >>> extract_params_from_path("/users/:id")
        [Parameter(name="id", param_type="path", data_type="string", required=True)]

        >>> extract_params_from_path("/posts/{postId}/comments/{id}")
        [Parameter(name="postId", ...), Parameter(name="id", ...)]
    """
    params = []

    # Pattern 1: Express/Gin style (:param)
    colon_params = re.findall(r":(\w+)", path)
    for param in colon_params:
        params.append(
            Parameter(
                name=param,
                param_type="path",
                data_type="string",
                required=True,
            )
        )

    # Pattern 2: ASP.NET/Spring style ({param})
    brace_params = re.findall(r"\{(\w+)\}", path)
    for param in brace_params:
        if param not in [p.name for p in params]:
            params.append(
                Parameter(
                    name=param,
                    param_type="path",
                    data_type="string",
                    required=True,
                )
            )

    return params
