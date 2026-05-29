#!/usr/bin/env python3
"""
Analyze code patterns for quality issues (dead code, DRY violations, complexity).

Orchestrates multiple analysis scripts and optionally uses Ollama for validation.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.cli.base import BaseCLIScript
from common.utils import run_command


class AnalyzeCodePatternsScript(BaseCLIScript):
    """Analyze code patterns."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--path",
            "-p",
            type=Path,
            default=Path.cwd(),
            help="Path to analyze (default: current directory)"
        )
        parser.add_argument(
            "--checks",
            "-c",
            default="dead_code,dry,complexity,smells",
            help="Comma-separated checks (default: all)"
        )
        parser.add_argument(
            "--use-ollama",
            action="store_true",
            help="Use Ollama for validation of ambiguous cases"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute code analysis."""
        start_time = time.time()
        path = args.path.resolve()

        if not path.exists():
            return {
                "success": False,
                "error": f"Path not found: {path}"
            }

        checks = [c.strip() for c in args.checks.split(",")]
        self.logger.info(f"Analyzing {path} with checks: {', '.join(checks)}")

        results = {
            "success": True,
            "path": str(path),
            "checks_performed": checks,
            "dead_code": [],
            "dry_violations": [],
            "code_smells": [],
            "complexity_issues": []
        }

        # Run checks in parallel (simplified - sequential for now)
        if "dead_code" in checks:
            dead_code_result = self._run_dead_code_check(path)
            if dead_code_result:
                results["dead_code"] = dead_code_result.get("unused_symbols", [])

        if "dry" in checks:
            dry_result = self._run_dry_check(path)
            if dry_result:
                results["dry_violations"] = dry_result.get("duplicates", [])

        if "complexity" in checks:
            complexity_result = self._run_complexity_check(path)
            if complexity_result:
                results["complexity_issues"] = complexity_result.get("complexity_issues", [])

        if "smells" in checks:
            # Code smells detection (simplified - magic numbers, long methods)
            smells = self._detect_code_smells(path)
            results["code_smells"] = smells

        # Validate with Ollama if requested
        if args.use_ollama:
            results = self._validate_with_ollama(results)

        # Calculate totals
        results["total_issues"] = (
            len(results["dead_code"]) +
            len(results["dry_violations"]) +
            len(results["code_smells"]) +
            len(results["complexity_issues"])
        )

        results["analysis_time_ms"] = int((time.time() - start_time) * 1000)
        results["estimated_token_savings"] = self._estimate_token_savings(results)

        self.metrics.track("analyze_code_patterns", {
            "total_issues": results["total_issues"],
            "token_savings": results["estimated_token_savings"]
        })

        return results

    def _run_dead_code_check(self, path: Path) -> dict | None:
        """Run dead code detection."""
        script_path = Path(__file__).parent / "find_unused_code.py"

        if not script_path.exists():
            self.logger.warning("find_unused_code.py not found")
            return None

        returncode, stdout, stderr = run_command(
            ["python", str(script_path), "--path", str(path), "--format", "json"],
            timeout=60
        )

        if returncode == 0 and stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                pass

        return None

    def _run_dry_check(self, path: Path) -> dict | None:
        """Run DRY violation detection."""
        script_path = Path(__file__).parent / "find_duplicates.py"

        if not script_path.exists():
            self.logger.warning("find_duplicates.py not found")
            return None

        returncode, stdout, stderr = run_command(
            ["python", str(script_path), "--path", str(path), "--format", "json"],
            timeout=60
        )

        if returncode == 0 and stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                pass

        return None

    def _run_complexity_check(self, path: Path) -> dict | None:
        """Run complexity calculation."""
        script_path = Path(__file__).parent / "calculate_complexity.py"

        if not script_path.exists():
            self.logger.warning("calculate_complexity.py not found")
            return None

        returncode, stdout, stderr = run_command(
            ["python", str(script_path), "--path", str(path), "--format", "json"],
            timeout=60
        )

        if returncode == 0 and stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                pass

        return None

    def _detect_code_smells(self, path: Path) -> list[dict]:
        """Detect code smells (simplified)."""
        smells = []

        # Find Python files
        files = list(path.rglob("*.py")) if path.is_dir() else [path]

        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Check for magic numbers
                for i, line in enumerate(lines):
                    # Simple regex for numeric literals (excluding 0, 1, 2)
                    import re
                    for match in re.finditer(r'\b(\d{3,})\b', line):
                        number = match.group(1)
                        if number not in ["100", "200", "404", "500"]:  # Common HTTP codes
                            smells.append({
                                "file": str(file.relative_to(path.parent if path.is_file() else path)),
                                "type": "magic_number",
                                "value": number,
                                "line": i + 1,
                                "severity": "medium",
                                "suggestion": f"Extract to named constant"
                            })

            except Exception:
                continue

        return smells[:20]  # Limit results

    def _validate_with_ollama(self, results: dict) -> dict:
        """Validate findings with Ollama (for low-confidence items)."""
        # Check Ollama availability
        returncode, _, _ = run_command(["ollama", "ps"], timeout=5)
        if returncode != 0:
            self.logger.warning("Ollama unavailable - skipping validation")
            return results

        # Validate low-confidence dead code
        validated_dead_code = []
        for item in results["dead_code"]:
            if item.get("confidence") == "low":
                # Ask Ollama
                is_dead = self._ask_ollama_dead_code(item)
                if is_dead:
                    item["confidence"] = "medium"
                    validated_dead_code.append(item)
            else:
                validated_dead_code.append(item)

        results["dead_code"] = validated_dead_code
        return results

    def _ask_ollama_dead_code(self, item: dict) -> bool:
        """Ask Ollama if code is truly dead."""
        prompt = f"""Is this code truly unused?

Function: {item['name']}
File: {item['file']}

Respond with only 'yes' or 'no'.
"""

        try:
            result = subprocess.run(
                ["ollama", "run", "qwen2.5-coder:7b", prompt],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace"
            )

            if result.returncode == 0:
                response = result.stdout.strip().lower()
                return "yes" in response

        except Exception:
            pass

        return False

    def _estimate_token_savings(self, results: dict) -> int:
        """Estimate Claude token savings."""
        # Estimate tokens saved by delegating this analysis
        base_savings = 5000  # Base orchestration
        per_issue_savings = 300  # Per issue found

        return base_savings + (results["total_issues"] * per_issue_savings)


def main():
    """CLI entry point."""
    from common.cli.base import create_cli_script
    create_cli_script(AnalyzeCodePatternsScript)


if __name__ == "__main__":
    main()
