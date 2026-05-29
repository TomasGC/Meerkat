#!/usr/bin/env python3
"""
Common Resume Script for Claude Code Projects.

Replaces: resume-project-common.ps1

This script is called by individual project resume scripts.
Validates project setup, displays status, and launches Claude Code.

Required variables:
  - project_name: Display name (e.g., "Lynx", "Admin UI")
  - project_description: Short description (e.g., "C# .NET 10 app")
  - project_root: Project root directory

Auto-detected:
  - .claude/ directory
  - KANBAN.md presence
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript

# ANSI color codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def write_info(message: str):
    """Write info message in cyan."""
    print(f"{CYAN}{message}{RESET}")


def write_success(message: str):
    """Write success message in green."""
    print(f"{GREEN}{message}{RESET}")


def write_warning(message: str):
    """Write warning message in yellow."""
    print(f"{YELLOW}{message}{RESET}")


def write_error(message: str):
    """Write error message in red."""
    print(f"{RED}{message}{RESET}", file=sys.stderr)


def print_banner(project_name: str):
    """Print project banner."""
    banner_width = max(40, len(project_name) + 30)
    separator = "=" * banner_width

    print()
    write_info(separator)
    write_info(f"   {project_name} - Resume Claude".ljust(banner_width))
    write_info(separator)
    print()


def validate_project_setup(project_root: Path) -> bool:
    """
    Validate project setup and display status.

    Args:
        project_root: Path to project root

    Returns:
        True if setup is valid
    """
    claude_dir = project_root / ".claude"
    kanban_file = claude_dir / "KANBAN.md"

    # Check context
    write_info("(Instructions auto-loaded from CLAUDE.md)")

    if kanban_file.exists():
        write_success("[OK] Task tracking found: KANBAN.md")
    else:
        write_warning("[WARN] No task tracking yet (create .claude/KANBAN.md when needed)")

    print()

    return True


def check_claude_cli() -> bool:
    """
    Check if Claude Code CLI is available.

    Returns:
        True if available
    """
    if shutil.which("claude") is None:
        write_error("ERROR: Claude Code CLI not found. Please install it first.")
        write_info("Visit: https://github.com/anthropics/claude-code")
        return False

    return True


def convert_to_git_bash_path(path: Path) -> str:
    """
    Convert Windows path to Git Bash format.

    Args:
        path: Windows path

    Returns:
        Git Bash path (e.g., /c/path)
    """
    # Convert to string and normalize
    path_str = str(path).replace("\\", "/")

    # Convert C:\path to /c/path
    if path_str[1:3] == ":/":
        drive = path_str[0].lower()
        return f"/{drive}{path_str[2:]}"

    return path_str


def resume_project(
    project_name: str,
    project_description: str,
    project_root: Path
) -> int:
    """
    Resume Claude Code project.

    Args:
        project_name: Display name
        project_description: Short description
        project_root: Project root directory

    Returns:
        Exit code (0 for success)
    """
    # Validate required variables
    if not project_name:
        write_error("ERROR: project_name must be provided")
        return 1

    if not project_description:
        write_error("ERROR: project_description must be provided")
        return 1

    if not project_root:
        write_error("ERROR: project_root must be provided")
        return 1

    if not project_root.exists():
        write_error(f"ERROR: Project root not found: {project_root}")
        return 1

    # Print banner
    print_banner(project_name)

    # Validate project setup
    if not validate_project_setup(project_root):
        return 1

    # Check Claude CLI
    if not check_claude_cli():
        return 1

    # Launch Claude
    write_success(f"Launching Claude Code ({project_description})...\n")

    # Convert path for Git Bash
    git_bash_path = convert_to_git_bash_path(project_root)

    # Launch Claude with cd command
    # session-start.md hook will automatically:
    #   - Load settings.json, CLAUDE.md, KANBAN.md, ARCHITECTURE.md, rules/, docs/
    #   - Invoke /start-session skill (detect branch, offer to read issue)
    try:
        subprocess.run(
            ["claude", f"cd {git_bash_path}"],
            cwd=project_root,
            check=True
        )
    except subprocess.CalledProcessError as e:
        write_error(f"ERROR: Failed to launch Claude: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\nClaude session interrupted by user.")
        return 0

    return 0


class ResumeProjectScript(BaseCLIScript):
    """Resume Claude Code project."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--name",
            "-n",
            required=True,
            help="Project display name (e.g., 'Lynx')"
        )
        parser.add_argument(
            "--description",
            "-d",
            required=True,
            help="Project description (e.g., 'C# .NET 10 app')"
        )
        parser.add_argument(
            "--root",
            "-r",
            required=True,
            help="Project root directory"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute project resumption."""
        try:
            project_root = Path(args.root).resolve()

            exit_code = resume_project(
                project_name=args.name,
                project_description=args.description,
                project_root=project_root
            )

            self.metrics.track("resume_project_common", {
                "project_name": args.name,
                "success": exit_code == 0
            })

            return {
                "success": exit_code == 0,
                "project_name": args.name,
                "project_description": args.description,
                "project_root": str(project_root)
            }

        except Exception as e:
            self.logger.error(f"Failed to resume project: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        return f"Successfully resumed project: {result['project_name']}"

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return f"[OK] Resumed {result['project_name']}"


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(ResumeProjectScript)
