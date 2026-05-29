#!/usr/bin/env python3
"""
Analyze work patterns from git commits by examining file changes (cross-platform).

Replaces: analyze-work-patterns.ps1

Intelligently detects patterns in commits by analyzing modified files, not commit messages.
Identifies: tests, scripts, documentation, standards, infrastructure changes, etc.
Used by generate-kanban-entry.py and generate-github-comment.py for automation.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.utils import run_command

# Pattern detection rules
PATTERN_RULES = {
    "testing": {
        "patterns": ["*.Tests.ps1", "*.test.ts", "*.test.js", "*_test.go", "*.spec.ts", "test/", "tests/", "__tests__/", "fixtures/"],
        "excludePatterns": [],
        "keywords": ["test", "spec", "fixture", "mock"],
        "description": "Comprehensive test suite"
    },
    "scripts": {
        "patterns": ["scripts/*.ps1", "*.ps1", "*.sh", "*.bash"],
        "excludePatterns": ["*.Tests.ps1", "test"],
        "keywords": ["script", "automation", "utility"],
        "description": "Utility scripts"
    },
    "standards": {
        "patterns": ["rules/*.md", "standards*.md", "coding-standards/"],
        "excludePatterns": [],
        "keywords": ["standard", "guideline", "convention", "best-practice"],
        "description": "Coding standards"
    },
    "hooks": {
        "patterns": ["hooks/*.md", ".git/hooks/", "githooks/"],
        "excludePatterns": [],
        "keywords": ["hook", "pre-commit", "post-commit"],
        "description": "Git hooks"
    },
    "skills": {
        "patterns": ["skills/", "SKILL.md"],
        "excludePatterns": [],
        "keywords": ["skill", "automation", "workflow"],
        "description": "Claude Code skills"
    },
    "agents": {
        "patterns": ["agents/", "AGENT.md"],
        "excludePatterns": [],
        "keywords": ["agent", "autonomous"],
        "description": "Claude Code agents"
    },
    "documentation": {
        "patterns": ["docs/", "*.md", "README*", "CHANGELOG*"],
        "excludePatterns": ["SKILL.md", "AGENT.md", "rules/", "standards"],
        "keywords": ["doc", "readme", "guide", "tutorial"],
        "description": "Documentation"
    },
    "infrastructure": {
        "patterns": ["Dockerfile", "docker-compose.yml", ".github/", "azure-pipelines.yml", "*.tf", "terraform/"],
        "excludePatterns": [],
        "keywords": ["infra", "deploy", "ci", "cd", "pipeline"],
        "description": "Infrastructure changes"
    },
    "configuration": {
        "patterns": ["*.json", "*.yaml", "*.yml", "*.toml", "*.config", ".env*"],
        "excludePatterns": ["package.json", "package-lock.json"],
        "keywords": ["config", "settings", "environment"],
        "description": "Configuration updates"
    },
    "refactoring": {
        "patterns": [],
        "excludePatterns": [],
        "keywords": ["refactor", "cleanup", "simplify", "extract", "rename"],
        "description": "Code refactoring"
    }
}


def get_commit_hashes(
    commits: Optional[str],
    auto: bool,
    base_branch: str
) -> list[str]:
    """
    Get list of commit hashes to analyze.

    Args:
        commits: Explicit commit spec (range, single hash, etc.)
        auto: Auto mode (current branch vs base branch)
        base_branch: Base branch for auto mode

    Returns:
        List of commit hashes
    """
    if commits:
        # Explicit commit spec
        cmd = ["git", "rev-list", commits]
    elif auto:
        # Auto mode: current branch vs base branch
        # Get merge base
        returncode, merge_base, _ = run_command(
            ["git", "merge-base", "HEAD", base_branch],
            timeout=10
        )

        if returncode != 0:
            raise ValueError(f"Failed to find merge base with {base_branch}")

        merge_base = merge_base.strip()

        # Get commits since merge base
        cmd = ["git", "rev-list", f"{merge_base}..HEAD"]
    else:
        # Last commit only
        cmd = ["git", "rev-list", "-1", "HEAD"]

    returncode, stdout, stderr = run_command(cmd, timeout=30)

    if returncode != 0:
        raise ValueError(f"Failed to get commit hashes: {stderr}")

    commit_hashes = [line.strip() for line in stdout.splitlines() if line.strip()]

    if not commit_hashes:
        raise ValueError("No commits found")

    return commit_hashes


def matches_file_pattern(
    file_path: str,
    patterns: list[str],
    exclude_patterns: list[str]
) -> bool:
    """
    Check if file matches pattern rules.

    Args:
        file_path: File path to check
        patterns: Include patterns (glob-style)
        exclude_patterns: Exclude patterns (substring match)

    Returns:
        True if file matches patterns
    """
    # Check exclusions first
    for exclude in exclude_patterns:
        if exclude in file_path:
            return False

    # Check inclusions
    for pattern in patterns:
        pattern_regex = pattern.replace("*", ".*").replace("/", r"[/\\]")
        if re.search(pattern_regex, file_path):
            return True

    return False


def get_technology_from_extension(extension: str) -> Optional[str]:
    """Get technology from file extension."""
    tech_map = {
        ".ts": "TypeScript", ".js": "JavaScript", ".py": "Python",
        ".go": "Go", ".rs": "Rust", ".cs": "C#", ".java": "Java",
        ".ps1": "PowerShell", ".sh": "Bash"
    }
    return tech_map.get(extension.lower())


def analyze_work_patterns(
    commits: Optional[str] = None,
    auto: bool = False,
    base_branch: str = "main"
) -> dict:
    """
    Analyze work patterns from git commits.

    Args:
        commits: Commit spec (range, single hash, etc.)
        auto: Auto mode (current branch vs base branch)
        base_branch: Base branch for auto mode

    Returns:
        Dictionary with patterns detected, files changed, etc.
    """
    # Get commit hashes
    commit_hashes = get_commit_hashes(commits, auto, base_branch)

    # Get file changes for all commits
    cmd = ["git", "diff", "--name-only", f"{commit_hashes[-1]}^", commit_hashes[0]]

    returncode, stdout, stderr = run_command(cmd, timeout=30)

    if returncode != 0:
        raise ValueError(f"Failed to get file changes: {stderr}")

    changed_files = [line.strip() for line in stdout.splitlines() if line.strip()]

    # Detect patterns
    patterns_detected: dict[str, list[str]] = {}
    technologies_used: set[str] = set()

    for file_path in changed_files:
        # Detect technology
        extension = Path(file_path).suffix
        tech = get_technology_from_extension(extension)
        if tech:
            technologies_used.add(tech)

        # Detect patterns
        for pattern_name, rule in PATTERN_RULES.items():
            if matches_file_pattern(file_path, rule["patterns"], rule["excludePatterns"]):
                if pattern_name not in patterns_detected:
                    patterns_detected[pattern_name] = []
                patterns_detected[pattern_name].append(file_path)

    # Also check commit messages for refactoring keywords
    for commit_hash in commit_hashes:
        returncode, commit_msg, _ = run_command(
            ["git", "log", "-1", "--format=%s", commit_hash],
            timeout=10
        )

        if returncode == 0:
            msg_lower = commit_msg.lower()
            for keyword in PATTERN_RULES["refactoring"]["keywords"]:
                if keyword in msg_lower:
                    if "refactoring" not in patterns_detected:
                        patterns_detected["refactoring"] = []
                    break

    # Build result
    patterns_summary = []
    for pattern_name in patterns_detected:
        rule = PATTERN_RULES[pattern_name]
        patterns_summary.append({
            "name": pattern_name,
            "description": rule["description"],
            "filesAffected": len(patterns_detected[pattern_name]) if pattern_name != "refactoring" else None
        })

    return {
        "commitsAnalyzed": len(commit_hashes),
        "filesChanged": len(changed_files),
        "patternsDetected": patterns_summary,
        "technologiesUsed": sorted(list(technologies_used)),
        "commitHashes": commit_hashes
    }


class AnalyzeWorkPatternsScript(BaseCLIScript):
    """Analyze work patterns from git commits."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--commits",
            "-c",
            help="Commit range (e.g., 'HEAD~5..HEAD', 'abc123..def456')"
        )
        parser.add_argument(
            "--auto",
            "-a",
            action="store_true",
            help="Auto mode: analyze current branch vs base branch"
        )
        parser.add_argument(
            "--base-branch",
            "-b",
            default="main",
            help="Base branch for auto mode (default: main)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute work pattern analysis."""
        try:
            # Analyze work patterns
            result = analyze_work_patterns(
                commits=args.commits,
                auto=args.auto,
                base_branch=args.base_branch
            )

            self.metrics.track("analyze_work_patterns", {
                "commitsAnalyzed": result["commitsAnalyzed"],
                "filesChanged": result["filesChanged"],
                "patternsDetected": len(result["patternsDetected"])
            })

            return {
                "success": True,
                **result
            }

        except ValueError as e:
            self.logger.error(str(e))
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            self.logger.error(f"Failed to analyze work patterns: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = [
            "Work Pattern Analysis",
            "",
            f"Commits Analyzed: {result['commitsAnalyzed']}",
            f"Files Changed: {result['filesChanged']}",
            ""
        ]

        if result['patternsDetected']:
            lines.append("Patterns Detected:")
            for pattern in result['patternsDetected']:
                files_info = f" ({pattern['filesAffected']} files)" if pattern['filesAffected'] else ""
                lines.append(f"  - {pattern['name']}: {pattern['description']}{files_info}")
            lines.append("")

        if result['technologiesUsed']:
            lines.append(f"Technologies: {', '.join(result['technologiesUsed'])}")
            lines.append("")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        patterns = [p['name'] for p in result['patternsDetected']]
        return (f"{result['commitsAnalyzed']} commits, {result['filesChanged']} files changed. "
                f"Patterns: {', '.join(patterns) if patterns else 'none'}")


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(AnalyzeWorkPatternsScript)
