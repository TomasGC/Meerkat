#!/usr/bin/env python3
"""
File I/O utilities.

Provides safe file reading operations with graceful error handling.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileReadResult:
    """
    Result of safe file read operation.

    Attributes:
        exists: Whether file exists
        path: File path (as string)
        content: File content (None if error or not exists)
        lines: Number of lines in content (0 if not exists)
        error: Error message if read failed (None if success)
    """
    exists: bool
    path: str
    content: Optional[str] = None
    lines: int = 0
    error: Optional[str] = None


def read_file_safe(file_path: Path, encoding: str = "utf-8") -> FileReadResult:
    """
    Read file with graceful error handling.

    Args:
        file_path: Path to file
        encoding: File encoding (default: utf-8)

    Returns:
        FileReadResult with content or error

    Examples:
        >>> result = read_file_safe(Path("test.txt"))
        >>> if result.exists and result.content:
        ...     print(result.content)

        >>> result = read_file_safe(Path("missing.txt"))
        >>> if not result.exists:
        ...     print("File not found")

        >>> result = read_file_safe(Path("test.txt"))
        >>> if result.error:
        ...     print(f"Error reading file: {result.error}")
    """
    # Check if file exists
    if not file_path.exists():
        return FileReadResult(
            exists=False,
            path=str(file_path)
        )

    # Try to read file
    try:
        content = file_path.read_text(encoding=encoding)
        lines = len(content.splitlines())

        return FileReadResult(
            exists=True,
            path=str(file_path),
            content=content,
            lines=lines
        )

    except Exception as e:
        # Any error during read (encoding, permission, etc.)
        return FileReadResult(
            exists=True,
            path=str(file_path),
            error=str(e)
        )


def read_files_safe(
    file_paths: list[Path],
    encoding: str = "utf-8"
) -> list[FileReadResult]:
    """
    Read multiple files with graceful error handling.

    Args:
        file_paths: List of file paths
        encoding: File encoding (default: utf-8)

    Returns:
        List of FileReadResult (one per file)

    Examples:
        >>> files = [Path("file1.txt"), Path("file2.txt")]
        >>> results = read_files_safe(files)
        >>> for result in results:
        ...     if result.exists and result.content:
        ...         print(f"{result.path}: {result.lines} lines")

        >>> results = read_files_safe([Path("a.txt"), Path("b.txt")])
        >>> successful = [r for r in results if r.content]
        >>> print(f"{len(successful)}/{len(results)} files read")
    """
    return [read_file_safe(p, encoding) for p in file_paths]
