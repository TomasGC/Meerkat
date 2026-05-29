#!/usr/bin/env python3
"""
Run all validation checks on scripts (syntax, tests, coverage).

Replaces: run-all-validations.ps1

Orchestrates multiple validation scripts to provide comprehensive quality checks:
- Syntax validation (validate_script_syntax.py)
- Test coverage check (check_test_coverage.py)
- Test execution (pytest)
- Standards compliance
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript


def get_validation_script_path(script_name: str) -> Optional[Path]:
    """
    Find validation script path.

    Args:
        script_name: Script name (e.g., "validate_script_syntax.py")

    Returns:
        Path to script or None
    """
    script_dir = Path(__file__).parent

    # Try current directory first
    local_path = script_dir / script_name
    if local_path.exists():
        return local_path

    # Try ~/.claude/scripts/cli
    global_path = Path.home() / ".claude" / "scripts" / "cli" / script_name
    if global_path.exists():
        return global_path

    return None


def invoke_validation_script(
    script_path: Path,
    args: list[str]
) -> dict:
    """
    Invoke validation script with arguments.

    Args:
        script_path: Path to script
        args: Command line arguments

    Returns:
        Result dictionary
    """
    if not script_path.exists():
        return {
            "success": False,
            "error": f"Script not found: {script_path}",
            "output": None
        }

    try:
        result = subprocess.run(
            ["python", str(script_path)] + args,
            capture_output=True,
            text=True,
            timeout=300
        )

        return {
            "success": result.returncode == 0,
            "exitCode": result.returncode,
            "output": result.stdout,
            "error": f"Validation failed with exit code {result.returncode}" if result.returncode != 0 else None
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Validation timed out",
            "output": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Exception: {e}",
            "output": None
        }


def run_all_validations(
    path: Path,
    recursive: bool = False,
    stop_on_error: bool = False,
    skip_syntax: bool = False,
    skip_coverage: bool = False,
    skip_tests: bool = False,
    logger=None
) -> dict:
    """
    Run all validation checks.

    Args:
        path: Directory containing scripts
        recursive: Search subdirectories recursively
        stop_on_error: Stop on first validation failure
        skip_syntax: Skip syntax validation
        skip_coverage: Skip test coverage check
        skip_tests: Skip test execution
        logger: Logger instance

    Returns:
        Validation results dictionary
    """
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    # Initialize results
    results = {
        "path": str(path),
        "recursive": recursive,
        "syntax": {
            "ran": False,
            "success": False,
            "scriptsChecked": 0,
            "issuesFound": 0,
            "details": None
        },
        "coverage": {
            "ran": False,
            "success": False,
            "coveragePercent": 0,
            "noTestFile": 0,
            "emptyTestFile": 0,
            "details": None
        },
        "tests": {
            "ran": False,
            "success": False,
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "details": None
        },
        "summary": {
            "totalValidations": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "successRate": 0
        }
    }

    validation_count = 0
    passed_count = 0
    failed_count = 0
    skipped_count = 0

    # Syntax validation
    if not skip_syntax:
        syntax_script = get_validation_script_path("validate_script_syntax.py")

        if syntax_script:
            validation_count += 1
            results["syntax"]["ran"] = True

            if logger:
                logger.info("Running syntax validation...")

            # Get all Python scripts
            if recursive:
                scripts = list(path.rglob("*.py"))
            else:
                scripts = list(path.glob("*.py"))

            # Exclude test files
            scripts = [s for s in scripts if not s.name.startswith("test_")]

            results["syntax"]["scriptsChecked"] = len(scripts)
            issues_found = 0

            for script_path in scripts:
                script_result = invoke_validation_script(
                    syntax_script,
                    ["--file", str(script_path), "--format", "json"]
                )

                if script_result["success"]:
                    try:
                        syntax_data = json.loads(script_result["output"])
                        if not syntax_data.get("valid", True):
                            issues_found += 1
                    except json.JSONDecodeError:
                        issues_found += 1
                else:
                    issues_found += 1

            results["syntax"]["issuesFound"] = issues_found
            results["syntax"]["success"] = issues_found == 0

            if results["syntax"]["success"]:
                passed_count += 1
            else:
                failed_count += 1
                if stop_on_error:
                    raise RuntimeError("Syntax validation failed. Stopping.")
        else:
            skipped_count += 1
            if logger:
                logger.warning("validate_script_syntax.py not found, skipping syntax validation")
    else:
        skipped_count += 1

    # Test coverage check
    if not skip_coverage:
        coverage_script = get_validation_script_path("check_test_coverage.py")

        if coverage_script:
            validation_count += 1
            results["coverage"]["ran"] = True

            if logger:
                logger.info("Running test coverage check...")

            args = ["--path", str(path), "--format", "json"]
            if recursive:
                args.append("--recursive")

            coverage_result = invoke_validation_script(coverage_script, args)

            if coverage_result["output"]:
                try:
                    coverage_data = json.loads(coverage_result["output"])
                    results["coverage"]["coveragePercent"] = coverage_data["summary"]["coveragePercent"]
                    results["coverage"]["noTestFile"] = coverage_data["summary"]["noTestFile"]
                    results["coverage"]["emptyTestFile"] = coverage_data["summary"]["emptyTestFile"]
                    results["coverage"]["details"] = coverage_data
                except json.JSONDecodeError:
                    if logger:
                        logger.warning("Failed to parse coverage data")

            results["coverage"]["success"] = coverage_result["success"]

            if results["coverage"]["success"]:
                passed_count += 1
            else:
                failed_count += 1
                if stop_on_error:
                    raise RuntimeError("Test coverage check failed. Stopping.")
        else:
            skipped_count += 1
            if logger:
                logger.warning("check_test_coverage.py not found, skipping coverage check")
    else:
        skipped_count += 1

    # Test execution
    if not skip_tests:
        validation_count += 1
        results["tests"]["ran"] = True

        if logger:
            logger.info("Running pytest tests...")

        tests_dir = path / "tests"

        if tests_dir.exists():
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", str(tests_dir), "-q", "--tb=no", "--json-report", "--json-report-file=/tmp/pytest_report.json"],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                # Parse pytest output for counts
                output = result.stdout
                if "passed" in output:
                    # Extract counts from pytest output (e.g., "463 passed, 1 skipped")
                    import re
                    passed_match = re.search(r"(\d+) passed", output)
                    failed_match = re.search(r"(\d+) failed", output)
                    skipped_match = re.search(r"(\d+) skipped", output)

                    results["tests"]["passed"] = int(passed_match.group(1)) if passed_match else 0
                    results["tests"]["failed"] = int(failed_match.group(1)) if failed_match else 0
                    results["tests"]["skipped"] = int(skipped_match.group(1)) if skipped_match else 0
                    results["tests"]["total"] = results["tests"]["passed"] + results["tests"]["failed"] + results["tests"]["skipped"]

                results["tests"]["success"] = result.returncode == 0

                if results["tests"]["success"]:
                    passed_count += 1
                else:
                    failed_count += 1
                    if stop_on_error:
                        raise RuntimeError("Tests failed. Stopping.")

            except subprocess.TimeoutExpired:
                results["tests"]["success"] = False
                failed_count += 1
                if logger:
                    logger.warning("Pytest tests timed out")

                if stop_on_error:
                    raise RuntimeError("Test execution failed. Stopping.")
            except Exception as e:
                results["tests"]["success"] = False
                failed_count += 1
                if logger:
                    logger.warning(f"Failed to run pytest tests: {e}")

                if stop_on_error:
                    raise RuntimeError("Test execution failed. Stopping.")
        else:
            results["tests"]["success"] = True
            skipped_count += 1
            if logger:
                logger.warning(f"No tests directory found at {tests_dir}")
    else:
        skipped_count += 1

    # Calculate summary
    results["summary"]["totalValidations"] = validation_count
    results["summary"]["passed"] = passed_count
    results["summary"]["failed"] = failed_count
    results["summary"]["skipped"] = skipped_count
    results["summary"]["successRate"] = round((passed_count / validation_count * 100), 2) if validation_count > 0 else 0

    return results


class RunAllValidationsScript(BaseCLIScript):
    """Run all validation checks on scripts."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--path",
            "-p",
            default=".",
            help="Path to directory containing scripts (default: current directory)"
        )
        parser.add_argument(
            "--recursive",
            "-r",
            action="store_true",
            help="Search subdirectories recursively"
        )
        parser.add_argument(
            "--stop-on-error",
            action="store_true",
            help="Stop execution on first validation failure"
        )
        parser.add_argument(
            "--skip-syntax",
            action="store_true",
            help="Skip syntax validation"
        )
        parser.add_argument(
            "--skip-coverage",
            action="store_true",
            help="Skip test coverage check"
        )
        parser.add_argument(
            "--skip-tests",
            action="store_true",
            help="Skip test execution"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute validation checks."""
        try:
            path = Path(args.path).resolve()

            # Run validations
            results = run_all_validations(
                path=path,
                recursive=args.recursive,
                stop_on_error=args.stop_on_error,
                skip_syntax=args.skip_syntax,
                skip_coverage=args.skip_coverage,
                skip_tests=args.skip_tests,
                logger=self.logger
            )

            self.metrics.track("run_all_validations", {
                "totalValidations": results["summary"]["totalValidations"],
                "passed": results["summary"]["passed"],
                "failed": results["summary"]["failed"]
            })

            return {
                "success": results["summary"]["failed"] == 0,
                **results
            }

        except FileNotFoundError as e:
            self.logger.error(str(e))
            return {
                "success": False,
                "error": str(e)
            }
        except RuntimeError as e:
            self.logger.error(str(e))
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            self.logger.error(f"Failed to run validations: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success") and "error" in result:
            return f"Error: {result['error']}"

        lines = [
            "Validation Report",
            f"Path: {result['path']}",
            f"Recursive: {result['recursive']}",
            "",
            "Summary:",
            f"  Total validations: {result['summary']['totalValidations']}",
            f"  Passed: {result['summary']['passed']}",
            f"  Failed: {result['summary']['failed']}",
            f"  Skipped: {result['summary']['skipped']}",
            f"  Success rate: {result['summary']['successRate']}%",
            ""
        ]

        if result["syntax"]["ran"]:
            status = "[OK]" if result["syntax"]["success"] else "[FAIL]"
            lines.append(f"{status} Syntax validation: {result['syntax']['scriptsChecked']} scripts checked")
            if not result["syntax"]["success"]:
                lines.append(f"   Issues: {result['syntax']['issuesFound']}")
            lines.append("")

        if result["coverage"]["ran"]:
            status = "[OK]" if result["coverage"]["success"] else "[FAIL]"
            lines.append(f"{status} Test coverage: {result['coverage']['coveragePercent']}%")
            if result["coverage"]["noTestFile"] > 0:
                lines.append(f"   Missing tests: {result['coverage']['noTestFile']} scripts")
            if result["coverage"]["emptyTestFile"] > 0:
                lines.append(f"   Empty tests: {result['coverage']['emptyTestFile']} scripts")
            lines.append("")

        if result["tests"]["ran"]:
            status = "[OK]" if result["tests"]["success"] else "[FAIL]"
            lines.append(f"{status} Test execution: {result['tests']['passed']}/{result['tests']['total']} tests passed")
            if result["tests"]["failed"] > 0:
                lines.append(f"   Failed: {result['tests']['failed']}")
            if result["tests"]["skipped"] > 0:
                lines.append(f"   Skipped: {result['tests']['skipped']}")
            lines.append("")

        if result["summary"]["failed"] > 0:
            lines.append("[FAIL] Validation failed")
        else:
            lines.append("[OK] All validations passed")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success") and "error" in result:
            return f"[ERROR] {result['error']}"

        status = "[OK]" if result["summary"]["failed"] == 0 else "[FAIL]"
        message = f"{status} Validations: {result['summary']['passed']}/{result['summary']['totalValidations']} passed"

        if result["coverage"]["ran"] and result["coverage"]["coveragePercent"] < 100:
            message += f" | Coverage: {result['coverage']['coveragePercent']}%"

        if result["tests"]["ran"] and result["tests"]["failed"] > 0:
            message += f" | Tests: {result['tests']['failed']} failed"

        return message


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(RunAllValidationsScript)
