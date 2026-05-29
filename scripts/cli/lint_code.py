#!/usr/bin/env python3
"""
Lint code files using language-specific linters (0 tokens).

Supports: Python (pylint/ruff), TypeScript/JavaScript (eslint), Go (golangci-lint)

Usage:
    python lint_code.py --file src/main.py
    python lint_code.py --dir src/ --recursive
    python lint_code.py --file src/api.ts --fix
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base_cli import BaseCLIScript


class LintCode(BaseCLIScript):
    """Lint code files with language-specific linters."""

    def add_arguments(self) -> None:
        self.parser.add_argument(
            "--file",
            type=Path,
            help="File to lint",
        )
        self.parser.add_argument(
            "--dir",
            type=Path,
            help="Directory to lint",
        )
        self.parser.add_argument(
            "--recursive",
            action="store_true",
            help="Lint directory recursively",
        )
        self.parser.add_argument(
            "--fix",
            action="store_true",
            help="Auto-fix issues where possible",
        )
        self.parser.add_argument(
            "--language",
            type=str,
            choices=["python", "typescript", "javascript", "go", "auto"],
            default="auto",
            help="Language (auto-detected if not specified)",
        )

    def execute(self) -> None:
        """Execute linting."""
        if not self.args.file and not self.args.dir:
            self.error("Must specify --file or --dir")

        if self.args.file:
            self._lint_file(self.args.file)
        elif self.args.dir:
            self._lint_directory(self.args.dir)

    def _lint_file(self, file_path: Path) -> None:
        """Lint a single file."""
        if not file_path.exists():
            self.error(f"File not found: {file_path}")

        # Detect language
        language = self.args.language
        if language == "auto":
            language = self._detect_language(file_path)

        # Select linter
        linter = self._get_linter(language)
        if not linter:
            self.error(f"No linter available for {language}")

        # Run linter
        try:
            cmd = self._build_command(linter, file_path, language)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # Linters return non-zero on issues
                encoding="utf-8",
                errors="replace",
            )

            # Parse output
            if result.returncode == 0:
                print(f"[OK] {file_path} passed linting")
            else:
                print(f"[WARN] {file_path} has linting issues:")
                print(result.stdout)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)

        except subprocess.CalledProcessError as e:
            self.error(f"Linting failed: {e.stderr}")

    def _lint_directory(self, dir_path: Path) -> None:
        """Lint all files in directory."""
        if not dir_path.exists():
            self.error(f"Directory not found: {dir_path}")

        # Find files
        pattern = "**/*" if self.args.recursive else "*"
        files = []

        for ext in [".py", ".ts", ".tsx", ".js", ".jsx", ".go"]:
            files.extend(dir_path.glob(f"{pattern}{ext}"))

        if not files:
            print("[WARN] No files found to lint")
            return

        # Lint each file
        passed = 0
        failed = 0

        for file_path in files:
            try:
                self._lint_file(file_path)
                passed += 1
            except SystemExit:
                failed += 1
                continue

        # Summary
        print(f"\n[OK] {passed} files passed linting")
        if failed:
            print(f"[WARN] {failed} files have issues")

    def _detect_language(self, file_path: Path) -> str:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()

        mapping = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".go": "go",
        }

        language = mapping.get(ext)
        if not language:
            self.error(f"Unknown file type: {ext}")

        return language

    def _get_linter(self, language: str) -> Optional[str]:
        """Get linter command for language."""
        linters = {
            "python": "ruff",  # Fast, modern Python linter
            "typescript": "eslint",
            "javascript": "eslint",
            "go": "golangci-lint",
        }

        return linters.get(language)

    def _build_command(self, linter: str, file_path: Path, language: str) -> list[str]:
        """Build linter command."""
        if linter == "ruff":
            cmd = ["ruff", "check"]
            if self.args.fix:
                cmd.append("--fix")
            cmd.append(str(file_path))

        elif linter == "eslint":
            cmd = ["eslint"]
            if self.args.fix:
                cmd.append("--fix")
            cmd.append(str(file_path))

        elif linter == "golangci-lint":
            cmd = ["golangci-lint", "run"]
            if self.args.fix:
                cmd.append("--fix")
            cmd.append(str(file_path))

        else:
            self.error(f"Unknown linter: {linter}")

        return cmd


if __name__ == "__main__":
    LintCode().run()
