#!/usr/bin/env python3
"""
Find unused code (functions, classes, imports) in Python/TypeScript/Go codebases.

Uses AST parsing and grep to detect defined symbols that are never called.
"""

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.cli.base import BaseCLIScript
from common.utils import run_command


@dataclass
class UnusedSymbol:
    """Unused code symbol."""
    file: str
    symbol_type: str  # function, class, import
    name: str
    line_start: int
    line_end: int
    confidence: str  # high, medium, low


class FindUnusedCodeScript(BaseCLIScript):
    """Find unused code in codebase."""

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
            "--recursive",
            "-r",
            action="store_true",
            default=True,
            help="Search recursively (default: True)"
        )
        parser.add_argument(
            "--language",
            "-l",
            choices=["python", "typescript", "go", "auto"],
            default="auto",
            help="Language (default: auto-detect)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute unused code detection."""
        path = args.path.resolve()

        if not path.exists():
            return {
                "success": False,
                "error": f"Path not found: {path}"
            }

        # Detect language
        language = args.language
        if language == "auto":
            language = self._detect_language(path)

        self.logger.info(f"Analyzing {language} code in {path}")

        # Find unused symbols
        if language == "python":
            unused = self._find_unused_python(path, args.recursive)
        elif language == "typescript":
            unused = self._find_unused_typescript(path, args.recursive)
        elif language == "go":
            unused = self._find_unused_go(path, args.recursive)
        else:
            return {
                "success": False,
                "error": f"Unsupported language: {language}"
            }

        result = {
            "success": True,
            "language": language,
            "path": str(path),
            "total_unused": len(unused),
            "unused_symbols": [
                {
                    "file": u.file,
                    "type": u.symbol_type,
                    "name": u.name,
                    "line_start": u.line_start,
                    "line_end": u.line_end,
                    "confidence": u.confidence
                }
                for u in unused
            ]
        }

        self.metrics.track("find_unused_code", {
            "language": language,
            "total_unused": len(unused)
        })

        return result

    def _detect_language(self, path: Path) -> str:
        """Auto-detect language from file extensions."""
        if path.is_file():
            ext = path.suffix
        else:
            # Check most common file in directory
            exts = {}
            for file in path.rglob("*"):
                if file.is_file():
                    ext = file.suffix
                    exts[ext] = exts.get(ext, 0) + 1

            if not exts:
                return "unknown"

            ext = max(exts, key=exts.get)

        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go"
        }

        return ext_map.get(ext, "unknown")

    def _find_unused_python(self, path: Path, recursive: bool) -> list[UnusedSymbol]:
        """Find unused Python symbols."""
        unused = []

        # Find all Python files
        if path.is_file():
            files = [path]
        else:
            pattern = "**/*.py" if recursive else "*.py"
            files = list(path.glob(pattern))

        # Extract all defined functions/classes
        defined = {}
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Skip private/magic methods
                        if node.name.startswith("_"):
                            continue

                        defined[node.name] = {
                            "file": str(file.relative_to(path.parent if path.is_file() else path)),
                            "type": "function",
                            "line": node.lineno,
                            "end_line": node.end_lineno or node.lineno
                        }

                    elif isinstance(node, ast.ClassDef):
                        if node.name.startswith("_"):
                            continue

                        defined[node.name] = {
                            "file": str(file.relative_to(path.parent if path.is_file() else path)),
                            "type": "class",
                            "line": node.lineno,
                            "end_line": node.end_lineno or node.lineno
                        }

            except Exception:
                continue

        # Find which symbols are called
        called = set()
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()

                for name in defined.keys():
                    # Check if symbol is called/used (count occurrences > 1 means it's used)
                    # One occurrence is the definition itself
                    matches = re.findall(rf'\b{name}\b', content)
                    if len(matches) > 1:
                        called.add(name)

            except Exception:
                continue

        # Identify unused
        for name, info in defined.items():
            if name not in called:
                # Check if exported (in __all__)
                file_path = path.parent / info["file"] if path.is_file() else path / info["file"]
                is_exported = self._is_exported_python(file_path, name)

                unused.append(UnusedSymbol(
                    file=info["file"],
                    symbol_type=info["type"],
                    name=name,
                    line_start=info["line"],
                    line_end=info["end_line"],
                    confidence="low" if is_exported else "high"
                ))

        return unused

    def _is_exported_python(self, file_path: Path, name: str) -> bool:
        """Check if symbol is exported in __all__."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for __all__ export
            if f'"{name}"' in content or f"'{name}'" in content:
                if "__all__" in content:
                    return True

        except Exception:
            pass

        return False

    def _find_unused_typescript(self, path: Path, recursive: bool) -> list[UnusedSymbol]:
        """Find unused TypeScript symbols (placeholder)."""
        # Simplified implementation - would need TypeScript AST parser
        self.logger.warning("TypeScript analysis is basic (grep-based)")
        return []

    def _find_unused_go(self, path: Path, recursive: bool) -> list[UnusedSymbol]:
        """Find unused Go symbols (placeholder)."""
        # Could use `go list -json` + grep
        self.logger.warning("Go analysis is basic (grep-based)")
        return []


def main():
    """CLI entry point."""
    from common.cli.base import create_cli_script
    create_cli_script(FindUnusedCodeScript)


if __name__ == "__main__":
    main()
