#!/usr/bin/env python3
"""
Analyze commit changes for mechanical quality/security violations.

Checks git diff against ORCA, SonarQube, and OWASP standards for mechanical issues.

Note: This script contains patterns for DETECTING security vulnerabilities in code.
The patterns themselves are not vulnerabilities - they are used to FIND issues.
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.cli.base import BaseCLIScript
from common.utils import run_command


@dataclass
class CommitViolation:
    """Commit quality violation."""
    file: str
    line: int
    type: str  # security, quality, standards
    severity: str  # critical, high, medium, low
    rule: str
    message: str
    suggestion: str


# Security patterns (OWASP Top 10 + ORCA)
# Note: These are DETECTION patterns, not actual vulnerabilities
SECURITY_PATTERNS = {
    "hardcoded_secret": {
        "patterns": [
            r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
            r'(api_key|apikey|token)\s*=\s*["\'][^"\']+["\']',
            r'(secret|private_key)\s*=\s*["\'][^"\']+["\']'
        ],
        "severity": "critical",
        "message": "Hardcoded secret detected",
        "suggestion": "Use environment variables or secure vault"
    },
    "sql_injection": {
        "patterns": [
            r'(execute|exec|query)\([^)]*\+[^)]*\)',  # String concatenation in SQL
            r'(execute|exec|query)\([^)]*%\s*[^)]*\)',  # String formatting in SQL
            r'(execute|exec|query)\([^)]*f["\'][^"\']*\{[^}]+\}'  # f-string in SQL
        ],
        "severity": "critical",
        "message": "Potential SQL injection vulnerability",
        "suggestion": "Use parameterized queries or ORM"
    },
    "xss_vulnerability": {
        "patterns": [
            # Pattern to detect XSS-prone code (not XSS itself)
            r'\.innerHTML\s*=',
            r'document\.write\(',
        ],
        "severity": "high",
        "message": "Potential XSS vulnerability",
        "suggestion": "Use textContent or sanitize HTML"
    },
    "weak_crypto": {
        "patterns": [
            r'\bMD5\b',
            r'\bSHA1\b',
            r'\.DES\b',
        ],
        "severity": "high",
        "message": "Weak cryptography detected",
        "suggestion": "Use SHA-256, bcrypt, or Argon2"
    }
}

# Quality patterns (Code Quality Standards)
QUALITY_PATTERNS = {
    "magic_number": {
        "patterns": [
            r'\b(\d{3,})\b(?!\s*(ms|px|%|rem))',  # Numbers ≥3 digits not followed by units
        ],
        "severity": "medium",
        "message": "Magic number detected",
        "suggestion": "Extract to named constant"
    },
    "todo_fixme": {
        "patterns": [
            r'#\s*(TODO|FIXME|XXX|HACK)\b',
            r'//\s*(TODO|FIXME|XXX|HACK)\b',
        ],
        "severity": "low",
        "message": "TODO/FIXME comment detected",
        "suggestion": "Create tracked issue and replace with issue reference"
    },
    "console_log": {
        "patterns": [
            r'console\.(log|debug|info|warn|error)\(',
            r'print\(',  # Python
            r'System\.out\.println\(',  # Java
        ],
        "severity": "low",
        "message": "Debug statement detected",
        "suggestion": "Remove or replace with proper logging"
    }
}


class AnalyzeCommitQualityScript(BaseCLIScript):
    """Analyze commit quality."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--staged",
            action="store_true",
            default=True,
            help="Analyze staged changes (default: True)"
        )
        parser.add_argument(
            "--commit",
            "-c",
            help="Analyze specific commit SHA"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute commit analysis."""
        # Get diff
        if args.commit:
            diff = self._get_commit_diff(args.commit)
        else:
            diff = self._get_staged_diff()

        if not diff:
            return {
                "success": True,
                "violations": [],
                "message": "No changes to analyze"
            }

        self.logger.info("Analyzing commit changes...")

        # Parse diff
        files_changes = self._parse_diff(diff)

        # Analyze changes
        violations = []
        for file, changes in files_changes.items():
            for line_num, line_content in changes:
                # Check security patterns
                for rule_name, rule_config in SECURITY_PATTERNS.items():
                    for pattern in rule_config["patterns"]:
                        if re.search(pattern, line_content, re.IGNORECASE):
                            violations.append(CommitViolation(
                                file=file,
                                line=line_num,
                                type="security",
                                severity=rule_config["severity"],
                                rule=rule_name,
                                message=rule_config["message"],
                                suggestion=rule_config["suggestion"]
                            ))

                # Check quality patterns
                for rule_name, rule_config in QUALITY_PATTERNS.items():
                    for pattern in rule_config["patterns"]:
                        if re.search(pattern, line_content):
                            violations.append(CommitViolation(
                                file=file,
                                line=line_num,
                                type="quality",
                                severity=rule_config["severity"],
                                rule=rule_name,
                                message=rule_config["message"],
                                suggestion=rule_config["suggestion"]
                            ))

        # Categorize violations
        critical = [v for v in violations if v.severity == "critical"]
        high = [v for v in violations if v.severity == "high"]
        medium = [v for v in violations if v.severity == "medium"]
        low = [v for v in violations if v.severity == "low"]

        result = {
            "success": True,
            "total_violations": len(violations),
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "low": len(low),
            "violations": [
                {
                    "file": v.file,
                    "line": v.line,
                    "type": v.type,
                    "severity": v.severity,
                    "rule": v.rule,
                    "message": v.message,
                    "suggestion": v.suggestion
                }
                for v in violations
            ],
            "blocking": len(critical) > 0 or len(high) > 0,
            "message": self._get_summary_message(critical, high, medium, low)
        }

        self.metrics.track("analyze_commit_quality", {
            "total_violations": len(violations),
            "critical": len(critical),
            "blocking": result["blocking"]
        })

        return result

    def _get_staged_diff(self) -> str:
        """Get staged diff."""
        returncode, stdout, _ = run_command(
            ["git", "diff", "--staged"],
            timeout=30
        )

        if returncode == 0:
            return stdout

        return ""

    def _get_commit_diff(self, commit_sha: str) -> str:
        """Get commit diff."""
        returncode, stdout, _ = run_command(
            ["git", "show", commit_sha],
            timeout=30
        )

        if returncode == 0:
            return stdout

        return ""

    def _parse_diff(self, diff: str) -> dict[str, list[tuple[int, str]]]:
        """Parse diff to extract file changes."""
        files_changes = {}
        current_file = None
        current_line = 0

        for line in diff.split("\n"):
            # File header
            if line.startswith("+++"):
                # Extract filename
                match = re.match(r'\+\+\+ b/(.+)', line)
                if match:
                    current_file = match.group(1)
                    files_changes[current_file] = []

            # Hunk header (line numbers)
            elif line.startswith("@@"):
                match = re.match(r'@@ -\d+,?\d* \+(\d+),?\d* @@', line)
                if match:
                    current_line = int(match.group(1))

            # Added line
            elif line.startswith("+") and not line.startswith("+++"):
                if current_file:
                    files_changes[current_file].append((current_line, line[1:]))
                    current_line += 1

            # Context/removed line
            elif not line.startswith("-"):
                current_line += 1

        return files_changes

    def _get_summary_message(self, critical, high, medium, low) -> str:
        """Generate summary message."""
        if critical:
            return f"❌ BLOCKING: {len(critical)} critical security issue(s) found"
        elif high:
            return f"⚠️ BLOCKING: {len(high)} high severity issue(s) found"
        elif medium:
            return f"⚠️ {len(medium)} medium severity issue(s) found (review recommended)"
        elif low:
            return f"ℹ️ {len(low)} low severity issue(s) found (optional fixes)"
        else:
            return "✅ No violations found"


def main():
    """CLI entry point."""
    from common.cli.base import create_cli_script
    create_cli_script(AnalyzeCommitQualityScript)


if __name__ == "__main__":
    main()
