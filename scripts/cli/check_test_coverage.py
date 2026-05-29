#!/usr/bin/env python3
"""
Check test coverage for Python and PowerShell scripts.

Verifies that each script has an associated test file and reports coverage statistics.
Identifies scripts without tests and empty test files.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript, create_cli_script
from common.models import TestCoverageResult


@dataclass
class ScriptCoverageInfo:
    """Coverage info for a single script."""
    script: str
    script_path: str
    test_file: str | None
    has_test_file: bool
    test_count: int
    functions: int
    lines: int
    status: str  # "covered", "no_test_file", "empty_test_file"


class CheckTestCoverageScript(BaseCLIScript):
    """Check test coverage for Python and PowerShell scripts."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--path",
            "-p",
            type=Path,
            default=Path("."),
            help="Path to directory (default: current directory)"
        )
        parser.add_argument(
            "--recursive",
            "-r",
            action="store_true",
            help="Search subdirectories recursively"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute coverage check."""
        path = args.path.resolve()

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {args.path}")

        # Find scripts
        scripts = self._find_scripts(path, args.recursive)

        if not scripts:
            self.logger.warning(f"No scripts found in {args.path}")
            return self._empty_result(str(path), args.recursive)

        # Analyze coverage
        coverage_info = []
        total_tested = 0
        total_untested = 0
        total_empty = 0
        total_tests = 0

        for script_path in scripts:
            info = self._analyze_script(script_path, path)
            coverage_info.append(info)

            if info.has_test_file and info.test_count > 0:
                total_tested += 1
                total_tests += info.test_count
            elif info.has_test_file and info.test_count == 0:
                total_empty += 1
            else:
                total_untested += 1

        # Calculate coverage
        total_scripts = len(scripts)
        coverage_percent = (total_tested / total_scripts * 100) if total_scripts > 0 else 0.0

        # Build result
        result = TestCoverageResult(
            total_scripts=total_scripts,
            tested_scripts=total_tested,
            untested_scripts=total_untested,
            coverage_percent=coverage_percent,
            empty_test_files=total_empty,
            total_tests=total_tests,
            untested_list=[info.script for info in coverage_info if not info.has_test_file],
            test_details={
                "path": str(path),
                "recursive": args.recursive,
                "scripts": [self._info_to_dict(info) for info in coverage_info]
            }
        )

        # Track metrics
        self.metrics.track("check_test_coverage", {
            "total_scripts": total_scripts,
            "coverage_percent": coverage_percent
        })

        return self._result_to_dict(result)

    def _find_scripts(self, path: Path, recursive: bool) -> list[Path]:
        """Find all scripts in directory."""
        patterns = ["*.py", "*.ps1"]
        scripts = []

        for pattern in patterns:
            if recursive:
                scripts.extend(path.rglob(pattern))
            else:
                scripts.extend(path.glob(pattern))

        # Exclude test files and certain directories
        excluded_patterns = [
            r"test_.*\.py$",
            r".*\.Tests\.ps1$",
            r"__pycache__",
            r"venv",
            r"\.venv",
            r"node_modules",
        ]

        def should_exclude(script_path: Path) -> bool:
            path_str = str(script_path)
            return any(re.search(pattern, path_str) for pattern in excluded_patterns)

        scripts = [s for s in scripts if not should_exclude(s)]

        return sorted(scripts)

    def _analyze_script(self, script_path: Path, search_root: Path) -> ScriptCoverageInfo:
        """Analyze single script coverage."""
        has_test, test_path = self._find_test_file(script_path, search_root)

        test_count = 0
        if has_test and test_path:
            test_count = self._count_test_cases(test_path)

        # Determine status
        if has_test and test_count > 0:
            status = "covered"
        elif has_test and test_count == 0:
            status = "empty_test_file"
        else:
            status = "no_test_file"

        # Count functions in script
        functions = self._count_functions(script_path)
        lines = self._count_lines(script_path)

        return ScriptCoverageInfo(
            script=script_path.name,
            script_path=str(script_path),
            test_file=str(test_path) if test_path else None,
            has_test_file=has_test,
            test_count=test_count,
            functions=functions,
            lines=lines,
            status=status
        )

    def _find_test_file(self, script_path: Path, search_root: Path) -> tuple[bool, Path | None]:
        """Find test file for script."""
        script_name = script_path.stem
        script_dir = script_path.parent

        # Try multiple test file naming conventions
        possible_test_paths = []

        if script_path.suffix == ".py":
            # Python conventions
            possible_test_paths = [
                script_dir / "tests" / f"test_{script_name}.py",
                script_dir / f"test_{script_name}.py",
                search_root / "tests" / f"test_{script_name}.py",
                script_path.parent.parent / "tests" / f"test_{script_name}.py",  # For cli/ scripts
            ]
        elif script_path.suffix == ".ps1":
            # PowerShell conventions
            possible_test_paths = [
                script_dir / "tests" / f"{script_name}.Tests.ps1",
                script_dir / f"{script_name}.Tests.ps1",
                search_root / "tests" / f"{script_name}.Tests.ps1",
            ]

        for test_path in possible_test_paths:
            if test_path.exists():
                return True, test_path

        return False, None

    def _count_test_cases(self, test_file_path: Path) -> int:
        """Count test cases in test file."""
        if not test_file_path.exists():
            return 0

        try:
            content = test_file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.warning(f"Failed to read test file {test_file_path}: {e}")
            return 0

        count = 0

        # Python: def test_*
        if test_file_path.suffix == ".py":
            count = len(re.findall(r'^\s*def test_\w+', content, re.MULTILINE))

        # PowerShell: It "..."
        elif test_file_path.suffix == ".ps1":
            count = len(re.findall(r'It\s+"[^"]+"', content))

        return count

    def _count_functions(self, script_path: Path) -> int:
        """Count functions in script."""
        try:
            content = script_path.read_text(encoding="utf-8")
        except Exception:
            return 0

        count = 0

        if script_path.suffix == ".py":
            count = len(re.findall(r'^\s*def \w+', content, re.MULTILINE))
        elif script_path.suffix == ".ps1":
            count = len(re.findall(r'^\s*function \w+', content, re.MULTILINE))

        return count

    def _count_lines(self, script_path: Path) -> int:
        """Count lines in script."""
        try:
            content = script_path.read_text(encoding="utf-8")
            return len(content.splitlines())
        except Exception:
            return 0

    def _empty_result(self, path: str, recursive: bool) -> dict:
        """Create empty result."""
        return {
            "total_scripts": 0,
            "tested_scripts": 0,
            "untested_scripts": 0,
            "coverage_percent": 0.0,
            "empty_test_files": 0,
            "total_tests": 0,
            "untested_list": [],
            "test_details": {
                "path": path,
                "recursive": recursive,
                "scripts": []
            }
        }

    def _info_to_dict(self, info: ScriptCoverageInfo) -> dict:
        """Convert ScriptCoverageInfo to dict."""
        return {
            "script": info.script,
            "script_path": info.script_path,
            "test_file": info.test_file,
            "has_test_file": info.has_test_file,
            "test_count": info.test_count,
            "functions": info.functions,
            "lines": info.lines,
            "status": info.status
        }

    def _result_to_dict(self, result: TestCoverageResult) -> dict:
        """Convert TestCoverageResult to dict."""
        return {
            "total_scripts": result.total_scripts,
            "tested_scripts": result.tested_scripts,
            "untested_scripts": result.untested_scripts,
            "coverage_percent": result.coverage_percent,
            "empty_test_files": result.empty_test_files,
            "total_tests": result.total_tests,
            "untested_list": result.untested_list,
            "test_details": result.test_details
        }

    def format_text(self, result: dict) -> str:
        """Format result as human-readable text."""
        lines = [
            "Test Coverage Report",
            f"Path: {result['test_details']['path']}",
            f"Recursive: {result['test_details']['recursive']}",
            "",
            "Summary:",
            f"  Total scripts: {result['total_scripts']}",
            f"  Tested: {result['tested_scripts']}",
            f"  Untested: {result['untested_scripts']}",
            f"  Empty test files: {result['empty_test_files']}",
            f"  Coverage: {result['coverage_percent']:.1f}%",
            f"  Total tests: {result['total_tests']}",
            ""
        ]

        if result['untested_list']:
            lines.append("Scripts without tests:")
            for script in result['untested_list']:
                lines.append(f"  - {script}")
            lines.append("")

        # Detailed script info
        lines.append("Detailed Coverage:")
        for script_info in result['test_details']['scripts']:
            status_icon = "✅" if script_info['status'] == "covered" else "❌"
            lines.append(f"{status_icon} {script_info['script']}")
            lines.append(f"   Tests: {script_info['test_count']}, "
                        f"Functions: {script_info['functions']}, "
                        f"Lines: {script_info['lines']}")

            if script_info['status'] == "no_test_file":
                lines.append("   ⚠️  No test file found")
            elif script_info['status'] == "empty_test_file":
                lines.append("   ⚠️  Test file exists but has no tests")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format result as brief summary."""
        return (f"Coverage: {result['tested_scripts']}/{result['total_scripts']} scripts "
                f"({result['coverage_percent']:.1f}%), "
                f"{result['total_tests']} tests")


if __name__ == "__main__":
    create_cli_script(CheckTestCoverageScript)
