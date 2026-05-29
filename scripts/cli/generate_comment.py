#!/usr/bin/env python3
"""
Generate issue comment from commit analysis.

Uses the active integration profile (GitHub, GitLab, Azure DevOps, etc.)

Generates structured comment with:
- Work summary
- Implementation details
- Files modified by category
- Statistics
- Commit list
"""

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.utils import run_command


# Pattern detection rules
PATTERN_RULES = {
    "testing": {
        "patterns": [r"\.test\.", r"\.spec\.", r"_test\.", r"^test_", r"\.Tests\.", r"/test", r"/tests/", r"fixtures/"],
        "description": "Test Suite"
    },
    "scripts": {
        "patterns": [r"\.ps1$", r"\.sh$", r"\.bash$", r"/scripts/"],
        "exclude": [r"\.Tests\.ps1$", r"/test"],
        "description": "Utility Scripts"
    },
    "standards": {
        "patterns": [r"rules/.*\.md$", r"standards.*\.md$", r"coding-standards/"],
        "description": "Coding Standards"
    },
    "skills": {
        "patterns": [r"skills/.*\.md$", r"SKILL\.md$"],
        "description": "Custom Skills"
    },
    "agents": {
        "patterns": [r"agents/.*\.md$", r"AGENT\.md$"],
        "description": "Agents"
    },
    "documentation": {
        "patterns": [r"\.md$", r"/docs/", r"README"],
        "exclude": [r"node_modules", r"vendor", r"CHANGELOG", r"LICENSE"],
        "description": "Documentation"
    },
    "infrastructure": {
        "patterns": [r"Dockerfile", r"docker-compose", r"\.gitlab-ci", r"\.github/", r"k8s/", r"terraform/"],
        "description": "Infrastructure"
    },
    "configuration": {
        "patterns": [r"\.json$", r"\.yaml$", r"\.yml$", r"\.toml$", r"\.config$", r"settings\."],
        "exclude": [r"package-lock\.json", r"node_modules"],
        "description": "Configuration"
    }
}


def get_current_branch() -> str:
    """Get current git branch."""
    returncode, stdout, _ = run_command(["git", "branch", "--show-current"], timeout=5)
    if returncode != 0:
        raise RuntimeError("Not a git repository")
    return stdout.strip()


def get_base_branch() -> str:
    """Auto-detect base branch."""
    for branch in ["main", "master", "develop"]:
        returncode, _, _ = run_command(["git", "rev-parse", "--verify", branch], timeout=5)
        if returncode == 0:
            return branch
    return "main"


def get_commits_in_range(base_branch: str, current_branch: str) -> list[str]:
    """Get commits between base and current branch."""
    returncode, merge_base, _ = run_command(
        ["git", "merge-base", base_branch, current_branch],
        timeout=10
    )
    if returncode != 0:
        raise RuntimeError(f"Failed to find merge base with {base_branch}")

    merge_base = merge_base.strip()

    returncode, stdout, _ = run_command(
        ["git", "rev-list", f"{merge_base}..{current_branch}"],
        timeout=30
    )
    if returncode != 0:
        raise RuntimeError("Failed to get commits")

    return [line.strip() for line in stdout.splitlines() if line.strip()]


def get_commit_files(commit_hash: str) -> list[str]:
    """Get files changed in commit."""
    returncode, stdout, _ = run_command(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
        timeout=10
    )
    if returncode != 0:
        return []
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def get_commit_message(commit_hash: str) -> str:
    """Get commit message."""
    returncode, stdout, _ = run_command(
        ["git", "log", "-1", "--format=%s", commit_hash],
        timeout=5
    )
    if returncode != 0:
        return ""
    return stdout.strip()


def categorize_file(file_path: str) -> str:
    """Categorize file by pattern matching."""
    for category, rule in PATTERN_RULES.items():
        # Check exclusions first
        if "exclude" in rule:
            if any(re.search(pattern, file_path) for pattern in rule["exclude"]):
                continue

        # Check inclusions
        if any(re.search(pattern, file_path) for pattern in rule["patterns"]):
            return category

    return "code"


def generate_summary(categories: dict[str, int]) -> str:
    """Generate work summary from categories."""
    parts = []

    if categories.get("testing", 0) > 0:
        parts.append("comprehensive test suite")
    if categories.get("scripts", 0) > 0:
        parts.append("utility scripts")
    if categories.get("standards", 0) > 0:
        parts.append("coding standards")
    if categories.get("skills", 0) > 0:
        parts.append("custom skills")
    if categories.get("agents", 0) > 0:
        parts.append("agents")
    if categories.get("documentation", 0) > 0:
        parts.append("documentation")
    if categories.get("infrastructure", 0) > 0:
        parts.append("infrastructure changes")
    if categories.get("configuration", 0) > 0:
        parts.append("configuration updates")
    if categories.get("code", 0) > 0:
        parts.append("code implementation")

    return ", ".join(parts) if parts else "project updates"


def generate_implementation_details(categories: dict[str, int]) -> list[str]:
    """Generate implementation details list."""
    details = []

    for category, count in sorted(categories.items(), key=lambda x: -x[1]):
        if category == "code":
            details.append(f"- {PATTERN_RULES.get(category, {}).get('description', 'Code')}: {count} files")
        elif category in PATTERN_RULES:
            details.append(f"- {PATTERN_RULES[category]['description']}: {count} files")

    return details


class GenerateCommentScript(BaseCLIScript):
    """Generate issue comment from commit analysis (uses active integration profile)."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--commits",
            "-c",
            default="",
            help="Comma-separated commit hashes to analyze"
        )
        parser.add_argument(
            "--auto",
            "-a",
            action="store_true",
            help="Auto-detect commits from current branch vs base"
        )
        parser.add_argument(
            "--base-branch",
            "-b",
            default="",
            help="Base branch for auto-detection (default: auto-detect)"
        )
        parser.add_argument(
            "--style",
            "-s",
            choices=["detailed", "summary", "technical"],
            default="detailed",
            help="Comment style (default: detailed)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute comment generation."""
        try:
            # Get commits to analyze
            if args.auto:
                current_branch = get_current_branch()
                base_branch = args.base_branch if args.base_branch else get_base_branch()
                commit_hashes = get_commits_in_range(base_branch, current_branch)
            elif args.commits:
                commit_hashes = [c.strip() for c in args.commits.split(",")]
            else:
                return {
                    "success": False,
                    "error": "Either --auto or --commits must be specified"
                }

            if not commit_hashes:
                return {
                    "success": True,
                    "comment": "No commits to analyze."
                }

            # Analyze commits
            all_files = []
            commits_info = []

            for commit_hash in commit_hashes:
                files = get_commit_files(commit_hash)
                message = get_commit_message(commit_hash)
                all_files.extend(files)
                commits_info.append({
                    "hash": commit_hash[:7],
                    "message": message,
                    "files": len(files)
                })

            # Categorize files
            categories = defaultdict(int)
            for file_path in all_files:
                category = categorize_file(file_path)
                categories[category] += 1

            # Generate comment
            summary = generate_summary(dict(categories))
            details = generate_implementation_details(dict(categories))

            if args.style == "summary":
                comment = f"Work completed: {summary}\n\nFiles modified: {len(all_files)} across {len(commit_hashes)} commits"
            elif args.style == "technical":
                comment = "Implementation Details:\n" + "\n".join(details)
            else:  # detailed
                lines = [
                    f"Work Summary: {summary}",
                    "",
                    "Implementation Details:",
                    *details,
                    "",
                    f"Statistics: {len(all_files)} files modified across {len(commit_hashes)} commits",
                    "",
                    "Commits:",
                    *[f"- {c['hash']}: {c['message']}" for c in commits_info]
                ]
                comment = "\n".join(lines)

            self.metrics.track("generate_comment", {
                "commits": len(commit_hashes),
                "files": len(all_files),
                "style": args.style
            })

            return {
                "success": True,
                "comment": comment,
                "commits": len(commit_hashes),
                "files": len(all_files),
                "categories": dict(categories)
            }

        except Exception as e:
            self.logger.error(f"Failed to generate comment: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        return result["comment"]

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return f"Generated comment for {result.get('commits', 0)} commits, {result.get('files', 0)} files"


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(GenerateCommentScript)
