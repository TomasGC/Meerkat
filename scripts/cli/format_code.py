#!/usr/bin/env python3
"""
Format code files using language-specific formatters (0 tokens).

Supports: Python (black), TypeScript/JavaScript (prettier), Go (gofmt), C# (dotnet format)

Usage:
    python format_code.py --file src/main.py
    python format_code.py --dir src/ --recursive
    python format_code.py --file src/api.ts --check-only
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base_cli import BaseCLIScript


class FormatCode(BaseCLIScript):
    """Format code files with language-specific formatters."""

    def add_arguments(self) -> None:
        self.parser.add_argument(
            "--file",
            type=Path,
            help="File to format",
        )
        self.parser.add_argument(
            "--dir",
            type=Path,
            help="Directory to format",
        )
        self.parser.add_argument(
            "--recursive",
            action="store_true",
            help="Format directory recursively",
        )
        self.parser.add_argument(
            "--check-only",
            action="store_true",
            help="Check formatting without modifying files",
        )
        self.parser.add_argument(
            "--language",
            type=str,
            choices=["python", "typescript", "javascript", "go", "csharp", "auto"],
            default="auto",
            help="Language (auto-detected if not specified)",
        )

    def execute(self) -> None:
        """Execute code formatting."""
        if not self.args.file and not self.args.dir:
            self.error("Must specify --file or --dir")

        if self.args.file:
            self._format_file(self.args.file)
        elif self.args.dir:
            self._format_directory(self.args.dir)

    def _format_file(self, file_path: Path) -> None:
        """Format a single file."""
        if not file_path.exists():
            self.error(f"File not found: {file_path}")

        # Detect language
        language = self.args.language
        if language == "auto":
            language = self._detect_language(file_path)

        # Select formatter
        formatter = self._get_formatter(language)
        if not formatter:
            self.error(f"No formatter available for {language}")

        # Run formatter
        try:
            cmd = self._build_command(formatter, file_path, language)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace",
            )

            if self.args.check_only:
                print(f"[OK] {file_path} is properly formatted")
            else:
                print(f"[OK] Formatted {file_path}")

        except subprocess.CalledProcessError as e:
            if self.args.check_only:
                self.error(f"[FAIL] {file_path} needs formatting")
            else:
                self.error(f"Formatting failed: {e.stderr}")

    def _format_directory(self, dir_path: Path) -> None:
        """Format all files in directory."""
        if not dir_path.exists():
            self.error(f"Directory not found: {dir_path}")

        # Find files
        pattern = "**/*" if self.args.recursive else "*"
        files = []

        for ext in [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".cs"]:
            files.extend(dir_path.glob(f"{pattern}{ext}"))

        if not files:
            print("[WARN] No files found to format")
            return

        # Format each file
        formatted = 0
        failed = 0

        for file_path in files:
            try:
                self._format_file(file_path)
                formatted += 1
            except SystemExit:
                failed += 1
                continue

        # Summary
        print(f"\n[OK] Formatted {formatted} files")
        if failed:
            print(f"[WARN] {failed} files failed")

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
            ".cs": "csharp",
        }

        language = mapping.get(ext)
        if not language:
            self.error(f"Unknown file type: {ext}")

        return language

    def _get_formatter(self, language: str) -> Optional[str]:
        """Get formatter command for language."""
        formatters = {
            "python": "black",
            "typescript": "prettier",
            "javascript": "prettier",
            "go": "gofmt",
            "csharp": "dotnet",
        }

        return formatters.get(language)

    def _build_command(
        self, formatter: str, file_path: Path, language: str
    ) -> list[str]:
        """Build formatter command."""
        if formatter == "black":
            cmd = ["black"]
            if self.args.check_only:
                cmd.append("--check")
            cmd.append(str(file_path))

        elif formatter == "prettier":
            cmd = ["prettier"]
            if self.args.check_only:
                cmd.append("--check")
            else:
                cmd.append("--write")
            cmd.append(str(file_path))

        elif formatter == "gofmt":
            if self.args.check_only:
                cmd = ["gofmt", "-l", str(file_path)]
            else:
                cmd = ["gofmt", "-w", str(file_path)]

        elif formatter == "dotnet":
            cmd = ["dotnet", "format"]
            if self.args.check_only:
                cmd.append("--verify-no-changes")
            cmd.append(str(file_path))

        else:
            self.error(f"Unknown formatter: {formatter}")

        return cmd


if __name__ == "__main__":
    FormatCode().run()
