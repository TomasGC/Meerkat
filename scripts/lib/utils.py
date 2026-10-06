#!/usr/bin/env python3
"""
Shared utilities for all scripts.

Common functions used across skills, agents, and utility scripts.
"""

import subprocess
from pathlib import Path


def write_file_safe(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """
    Safely write file with error handling.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding (default: utf-8)

    Returns:
        True if success, False otherwise
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding=encoding)
        return True
    except Exception:
        return False


def run_command(command: list[str], cwd: Path | None = None, timeout: int = 30) -> tuple[int, str, str]:
    """
    Run shell command and return result.

    Args:
        command: Command and arguments as list
        cwd: Working directory (optional)
        timeout: Timeout in seconds

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)
