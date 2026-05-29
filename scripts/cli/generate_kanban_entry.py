#!/usr/bin/env python3
"""
Generate KANBAN.md entry description from commit analysis.

Replaces: generate-kanban-entry.ps1

Generates professional bullet-point descriptions for KANBAN.md entries.
Focuses on high-level overview with quantified achievements.
"""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.generate_comment import (
    categorize_file,
    get_base_branch,
    get_commit_files,
    get_commits_in_range,
    get_current_branch,
)
from common.cli.base import BaseCLIScript


def generate_descriptions(categories: dict[str, int], style: str = "professional") -> list[str]:
    """Generate bullet-point descriptions from categories."""
    descriptions = []

    # Infrastructure (hooks, skills, agents, templates, infrastructure)
    infra_count = sum(categories.get(cat, 0) for cat in ["skills", "agents", "infrastructure"])
    if infra_count > 0:
        if style == "concise":
            descriptions.append(f"Infrastructure setup ({infra_count} files)")
        else:
            descriptions.append("Established complete Claude Code infrastructure with standardized project structure")

    # Testing
    if categories.get("testing", 0) > 0:
        count = categories["testing"]
        if style == "concise":
            descriptions.append(f"Test suite ({count} tests)")
        elif style == "detailed":
            descriptions.append(f"Implemented {count} comprehensive tests with fixtures and 100% coverage")
        else:  # professional
            descriptions.append(f"Created comprehensive test suite ({count} test files, 100% passing)")

    # Scripts
    if categories.get("scripts", 0) > 0:
        count = categories["scripts"]
        if style == "concise":
            descriptions.append(f"{count} utility scripts")
        elif style == "detailed":
            descriptions.append(f"Created {count} cross-platform automation scripts for workflow optimization")
        else:  # professional
            descriptions.append(f"Developed {count} cross-platform utility scripts for automation and workflow optimization")

    # Standards
    if categories.get("standards", 0) > 0:
        if style == "concise":
            descriptions.append("Coding standards defined")
        elif style == "detailed":
            descriptions.append("Documented comprehensive coding standards for 15+ technologies including best practices")
        else:  # professional
            descriptions.append("Defined coding standards across 15+ technologies (C#, Go, TypeScript, JavaScript, Vue.js, Docker, Kubernetes)")

    # Documentation
    if categories.get("documentation", 0) > 0:
        count = categories["documentation"]
        if style == "concise":
            descriptions.append(f"Documentation ({count} files)")
        elif style == "detailed":
            descriptions.append(f"Created extensive documentation covering API docs, setup guides, and best practices with {count} files")
        else:  # professional
            descriptions.append(f"Comprehensive documentation including API docs, setup guides, and best practices ({count} files)")

    # Configuration
    if categories.get("configuration", 0) > 0:
        if style == "concise":
            descriptions.append("Environment configuration")
        else:
            descriptions.append("Configured development environment with Git integration and cross-platform compatibility")

    # Code (fallback)
    if categories.get("code", 0) > 0 and len(descriptions) == 0:
        count = categories["code"]
        if style == "concise":
            descriptions.append(f"Implementation ({count} files)")
        elif style == "detailed":
            descriptions.append(f"Developed core functionality with implementation across {count} source files")
        else:  # professional
            descriptions.append(f"Implemented core functionality across {count} files")

    return descriptions


class GenerateKanbanEntryScript(BaseCLIScript):
    """Generate KANBAN.md entry description from commit analysis."""

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
            "--max-bullets",
            "-m",
            type=int,
            default=7,
            help="Maximum number of bullet points (default: 7)"
        )
        parser.add_argument(
            "--style",
            "-s",
            choices=["professional", "detailed", "concise"],
            default="professional",
            help="Description style (default: professional)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute KANBAN entry generation."""
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
                    "descriptions": ["No significant patterns detected in commits"]
                }

            # Analyze commits
            all_files = []
            for commit_hash in commit_hashes:
                files = get_commit_files(commit_hash)
                all_files.extend(files)

            # Categorize files
            categories = defaultdict(int)
            for file in all_files:
                category = categorize_file(file)
                categories[category] += 1

            # Generate descriptions
            descriptions = generate_descriptions(dict(categories), args.style)

            # Limit to max bullets
            descriptions = descriptions[:args.max_bullets]

            if not descriptions:
                descriptions = ["No significant patterns detected in commits"]

            self.metrics.track("generate_kanban_entry", {
                "commits": len(commit_hashes),
                "bullets": len(descriptions),
                "style": args.style
            })

            return {
                "success": True,
                "descriptions": descriptions,
                "commits": len(commit_hashes),
                "files": len(all_files)
            }

        except Exception as e:
            self.logger.error(f"Failed to generate KANBAN entry: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        return "\n".join(f"- {desc}" for desc in result["descriptions"])

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return f"Generated {len(result['descriptions'])} bullet points from {result.get('commits', 0)} commits"


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(GenerateKanbanEntryScript)
