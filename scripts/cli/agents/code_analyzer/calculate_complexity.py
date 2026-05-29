#!/usr/bin/env python3
"""
Calculate code complexity metrics (cyclomatic complexity, nesting depth).

Uses AST parsing to analyze Python code structure.
"""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.cli.base import BaseCLIScript


@dataclass
class ComplexityMetric:
    """Code complexity metric."""
    file: str
    function: str
    cyclomatic: int
    nesting_depth: int
    lines: int
    severity: str  # high, medium, low


class CalculateComplexityScript(BaseCLIScript):
    """Calculate code complexity metrics."""

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
            "--threshold",
            "-t",
            type=int,
            default=10,
            help="Cyclomatic complexity threshold (default: 10)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute complexity calculation."""
        path = args.path.resolve()

        if not path.exists():
            return {
                "success": False,
                "error": f"Path not found: {path}"
            }

        self.logger.info(f"Calculating complexity for {path}")

        # Find Python files
        files = list(path.rglob("*.py")) if path.is_dir() else [path]

        # Calculate complexity
        metrics = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Calculate cyclomatic complexity
                        cyclomatic = self._calculate_cyclomatic(node)

                        # Calculate nesting depth
                        nesting = self._calculate_nesting(node)

                        # Calculate LOC
                        lines = (node.end_lineno or node.lineno) - node.lineno + 1

                        # Only include if exceeds threshold
                        if cyclomatic >= args.threshold or nesting >= 4 or lines >= 50:
                            metrics.append(ComplexityMetric(
                                file=str(file.relative_to(path.parent if path.is_file() else path)),
                                function=node.name,
                                cyclomatic=cyclomatic,
                                nesting_depth=nesting,
                                lines=lines,
                                severity=self._calculate_severity(cyclomatic, nesting, lines)
                            ))

            except Exception:
                continue

        result = {
            "success": True,
            "path": str(path),
            "files_analyzed": len(files),
            "high_complexity_count": sum(1 for m in metrics if m.severity == "high"),
            "complexity_issues": [
                {
                    "file": m.file,
                    "function": m.function,
                    "cyclomatic_complexity": m.cyclomatic,
                    "nesting_depth": m.nesting_depth,
                    "lines": m.lines,
                    "severity": m.severity
                }
                for m in metrics
            ]
        }

        self.metrics.track("calculate_complexity", {
            "files": len(files),
            "high_complexity": result["high_complexity_count"]
        })

        return result

    def _calculate_cyclomatic(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity."""
        # Cyclomatic complexity = decision points + 1
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1

        return complexity

    def _calculate_nesting(self, node: ast.FunctionDef) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0

        def walk_depth(n, depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, depth)

            nesting_nodes = (ast.If, ast.While, ast.For, ast.With, ast.Try)

            for child in ast.iter_child_nodes(n):
                if isinstance(child, nesting_nodes):
                    walk_depth(child, depth + 1)
                else:
                    walk_depth(child, depth)

        walk_depth(node)
        return max_depth

    def _calculate_severity(self, cyclomatic: int, nesting: int, lines: int) -> str:
        """Calculate severity."""
        if cyclomatic >= 15 or nesting >= 5 or lines >= 100:
            return "high"
        elif cyclomatic >= 10 or nesting >= 4 or lines >= 50:
            return "medium"
        else:
            return "low"


def main():
    """CLI entry point."""
    from common.cli.base import create_cli_script
    create_cli_script(CalculateComplexityScript)


if __name__ == "__main__":
    main()
