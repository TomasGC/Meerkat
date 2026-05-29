#!/usr/bin/env python3
"""
Analyze GitHub Actions CI/CD failures and extract actionable errors.

Replaces: ~/.claude/scripts/analyze-ci-failure.ps1

Downloads failed logs from GitHub Actions, categorizes errors, and provides
a concise summary with actionable recommendations.

Supports both direct run IDs and full GitHub URLs (pipeline or PR).
"""

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.utils import run_command


# Error patterns for categorization (order matters - most specific first)
ERROR_PATTERNS = {
    "lint": [
        r"Lint found",
        r"UnspecifiedRegisterReceiverFlag",
        r"UnsafeImplicitIntentLaunch",
        r"SecurityException",
        r"pylint.*error",
        r"eslint.*error",
    ],
    "test": [
        r"pytest.*FAILED",
        r"Test.*failed",
        r"AssertionError:",
        r"expected.*but was",
        r"java\.lang\.",
        r"kotlin\.",
        r"org\.junit\.",
        r"\bFAILED\b(?!.*npm)",  # FAILED but not "npm ERR!" context
    ],
    "build": [
        r"npm ERR!",
        r"yarn error",
        r"Could not resolve",
        r"Dependency",
        r"artifact not found",
        r"A problem occurred",
        r"Execution failed for task",
    ],
    "compilation": [
        r"^e: ",
        r"Unresolved reference",
        r"Compilation error",
        r"BUILD FAILED in",
        r"cannot find symbol",
        r"\berror:\s",  # Word boundary + space to avoid matching "Real error"
    ],
    "infrastructure": [
        r"device offline",
        r"Connection refused",
        r"timeout|timed out",
        r"Unable to connect",
        r"emulator.*failed",
        r"INSTALL_FAILED",
        r"adb.*offline",
        r"daemon.*failed",
    ],
}

# Noise patterns to skip
NOISE_PATTERNS = [
    r"^\[command\]",
    r"^INFO ",
    r"^WARNING.*Node\.js",
    r"^##\[",
    r"daemon started",
    r"daemon not running",
]


@dataclass
class CIAnalysis:
    """CI failure analysis result."""
    run_id: str
    repo: str
    infrastructure_errors: list[str]
    compilation_errors: list[str]
    test_failures: list[str]
    lint_errors: list[str]
    build_errors: list[str]
    unknown_errors: list[str]

    @property
    def total_errors(self) -> int:
        """Total number of errors."""
        return (len(self.infrastructure_errors) + len(self.compilation_errors) +
                len(self.test_failures) + len(self.lint_errors) +
                len(self.build_errors) + len(self.unknown_errors))

    @property
    def priority_category(self) -> str:
        """Determine priority category for fixing (highest priority first)."""
        if self.compilation_errors:
            return "compilation"
        elif self.build_errors:
            return "build"
        elif self.infrastructure_errors:
            return "infrastructure"
        elif self.test_failures:
            return "test"
        elif self.lint_errors:
            return "lint"
        else:
            return "unknown"


def parse_github_url(url: str) -> Optional[tuple[str, str]]:
    """Parse GitHub URL to extract repo and run ID."""
    # Pipeline URL: https://github.com/owner/repo/actions/runs/12345
    match = re.search(r"github\.com/([^/]+/[^/]+)/actions/runs/(\d+)", url)
    if match:
        return match.group(1), match.group(2)

    # PR URL: https://github.com/owner/repo/pull/67
    match = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if match:
        repo = match.group(1)
        pr_number = match.group(2)

        # Get latest run ID for this PR
        cmd = ["gh", "pr", "view", pr_number, "--repo", repo, "--json", "statusCheckRollup"]
        returncode, stdout, _ = run_command(cmd, timeout=30)

        if returncode == 0 and stdout:
            # Extract first workflow run ID from JSON
            run_match = re.search(r'"workflowRunId":(\d+)', stdout)
            if run_match:
                return repo, run_match.group(1)

    return None


def fetch_failed_logs(repo: str, run_id: str) -> Optional[str]:
    """Fetch failed logs from GitHub Actions."""
    cmd = ["gh", "run", "view", run_id, "--repo", repo, "--log-failed"]

    returncode, stdout, stderr = run_command(cmd, timeout=60)

    if returncode != 0:
        return None

    return stdout


def analyze_logs(logs: str) -> dict[str, list[str]]:
    """Analyze logs and categorize errors."""
    errors: dict[str, list[str]] = {
        "infrastructure": [],
        "compilation": [],
        "test": [],
        "lint": [],
        "build": [],
        "unknown": []
    }

    seen_errors: set[str] = set()

    for line in logs.splitlines():
        line = line.strip()

        # Skip empty lines and noise
        if not line or any(re.search(pattern, line) for pattern in NOISE_PATTERNS):
            continue

        # Categorize error
        categorized = False
        for category, patterns in ERROR_PATTERNS.items():
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
                # Deduplicate
                error_key = f"{category}:{line[:100]}"
                if error_key not in seen_errors:
                    errors[category].append(line)
                    seen_errors.add(error_key)
                categorized = True
                break

        # Unknown errors
        if not categorized and any(word in line.lower() for word in ["error", "fail", "exception"]):
            error_key = f"unknown:{line[:100]}"
            if error_key not in seen_errors:
                errors["unknown"].append(line)
                seen_errors.add(error_key)

    return errors


class AnalyzeCIFailureScript(BaseCLIScript):
    """Analyze GitHub Actions CI/CD failures."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--url",
            "-u",
            help="GitHub URL (pipeline run or pull request)"
        )
        parser.add_argument(
            "--run-id",
            "-r",
            help="GitHub Actions run ID (alternative to --url)"
        )
        parser.add_argument(
            "--repo",
            help="Repository in format 'owner/repo' (required with --run-id)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute CI failure analysis."""
        # Check gh CLI
        returncode, _, _ = run_command(["gh", "--version"], timeout=5)
        if returncode != 0:
            self.logger.error("gh CLI not found. Install from: https://cli.github.com/")
            return {
                "success": False,
                "error": "gh CLI not found"
            }

        # Parse arguments
        if args.url:
            parsed = parse_github_url(args.url)
            if not parsed:
                self.logger.error("Invalid GitHub URL format")
                return {
                    "success": False,
                    "error": "Invalid GitHub URL format"
                }

            repo, run_id = parsed

        elif args.run_id and args.repo:
            repo = args.repo
            run_id = args.run_id

        else:
            return {
                "success": False,
                "error": "Either --url or (--run-id and --repo) must be provided"
            }

        self.logger.info(f"Analyzing run #{run_id} for repo {repo}")

        # Fetch logs
        logs = fetch_failed_logs(repo, run_id)
        if logs is None:
            return {
                "success": False,
                "error": "Failed to fetch logs"
            }

        if not logs.strip():
            self.logger.info("No failed logs found. Run may have passed or is still in progress.")
            return {
                "success": True,
                "run_id": run_id,
                "repo": repo,
                "total_errors": 0
            }

        # Analyze logs
        errors = analyze_logs(logs)

        # Create analysis result
        analysis = CIAnalysis(
            run_id=run_id,
            repo=repo,
            infrastructure_errors=errors["infrastructure"],
            compilation_errors=errors["compilation"],
            test_failures=errors["test"],
            lint_errors=errors["lint"],
            build_errors=errors["build"],
            unknown_errors=errors["unknown"],
        )

        self.metrics.track("analyze_ci_failure", {
            "run_id": run_id,
            "repo": repo,
            "total_errors": analysis.total_errors,
            "priority": analysis.priority_category
        })

        return {
            "success": True,
            "run_id": analysis.run_id,
            "repo": analysis.repo,
            "total_errors": analysis.total_errors,
            "priority_category": analysis.priority_category,
            "infrastructure_errors": analysis.infrastructure_errors,
            "compilation_errors": analysis.compilation_errors,
            "test_failures": analysis.test_failures,
            "lint_errors": analysis.lint_errors,
            "build_errors": analysis.build_errors,
            "unknown_errors": analysis.unknown_errors
        }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = [
            "=" * 63,
            "  CI Failure Analysis",
            "=" * 63,
            "",
            f"Run ID: {result['run_id']}",
            f"Repo: {result['repo']}",
            f"Total Errors: {result['total_errors']}",
            f"Priority: {result['priority_category']}",
            ""
        ]

        # Infrastructure errors
        if result['infrastructure_errors']:
            lines.append(f"[!] Infrastructure Errors ({len(result['infrastructure_errors'])} found)")
            lines.append("-" * 60)
            for err in result['infrastructure_errors'][:10]:
                lines.append(f"  [X] {err}")
            if len(result['infrastructure_errors']) > 10:
                lines.append(f"  [i] ... and {len(result['infrastructure_errors']) - 10} more")
            lines.append("")

        # Compilation errors
        if result['compilation_errors']:
            lines.append(f"[!] Compilation Errors ({len(result['compilation_errors'])} found)")
            lines.append("-" * 60)
            for err in result['compilation_errors'][:10]:
                lines.append(f"  [X] {err}")
            if len(result['compilation_errors']) > 10:
                lines.append(f"  [i] ... and {len(result['compilation_errors']) - 10} more")
            lines.append("")

        # Build errors
        if result['build_errors']:
            lines.append(f"[!] Build Errors ({len(result['build_errors'])} found)")
            lines.append("-" * 60)
            for err in result['build_errors'][:10]:
                lines.append(f"  [X] {err}")
            if len(result['build_errors']) > 10:
                lines.append(f"  [i] ... and {len(result['build_errors']) - 10} more")
            lines.append("")

        # Test failures
        if result['test_failures']:
            lines.append(f"[!] Test Failures ({len(result['test_failures'])} found)")
            lines.append("-" * 60)
            for err in result['test_failures'][:15]:
                lines.append(f"  [X] {err}")
            if len(result['test_failures']) > 15:
                lines.append(f"  [i] ... and {len(result['test_failures']) - 15} more")
            lines.append("")

        # Lint errors
        if result['lint_errors']:
            lines.append(f"[!] Lint Errors ({len(result['lint_errors'])} found)")
            lines.append("-" * 60)
            for err in result['lint_errors'][:10]:
                lines.append(f"  [!] {err}")
            if len(result['lint_errors']) > 10:
                lines.append(f"  [i] ... and {len(result['lint_errors']) - 10} more")
            lines.append("")

        # Unknown errors
        if result['unknown_errors']:
            lines.append(f"[!] Other Errors ({len(result['unknown_errors'])} found)")
            lines.append("-" * 60)
            for err in result['unknown_errors'][:5]:
                lines.append(f"  [X] {err}")
            if len(result['unknown_errors']) > 5:
                lines.append(f"  [i] ... and {len(result['unknown_errors']) - 5} more")
            lines.append("")

        # Recommendations
        lines.append("=" * 63)
        lines.append("  Recommendations")
        lines.append("=" * 63)
        lines.append("")

        priority = result['priority_category']
        if priority == "infrastructure":
            lines.append("[!] Retry the workflow (infrastructure failure, likely transient)")
            lines.append(f"  gh run rerun {result['run_id']} --repo {result['repo']}")
        elif priority == "compilation":
            lines.append("[!] Fix compilation errors first (code changes needed)")
        elif priority == "build":
            lines.append("[!] Fix build configuration (build files or dependencies)")
        elif priority == "test":
            lines.append("[!] Fix failing tests (test code or assertions need updates)")
        else:
            lines.append("[!] Review logs manually")
            lines.append(f"  gh run view {result['run_id']} --repo {result['repo']} --log-failed")

        lines.append("")
        lines.append(f"View full run: https://github.com/{result['repo']}/actions/runs/{result['run_id']}")
        lines.append("")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return (f"[{result['priority_category'].upper()}] "
                f"{result['total_errors']} errors in run {result['run_id']}")


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(AnalyzeCIFailureScript)
