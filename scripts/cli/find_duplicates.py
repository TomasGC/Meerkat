#!/usr/bin/env python3
"""
Find duplicate code blocks in codebase (DRY violations).

Uses token-based similarity matching to detect copy-paste code.
"""

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript


@dataclass
class DuplicateBlock:
    """Duplicate code block."""
    locations: list[dict]  # [{"file": "a.py", "lines": "10-15"}, ...]
    similarity: float
    lines: int
    severity: str  # high, medium, low


class FindDuplicatesScript(BaseCLIScript):
    """Find duplicate code blocks."""

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
            default=5,
            help="Minimum lines to consider duplicate (default: 5)"
        )
        parser.add_argument(
            "--similarity",
            "-s",
            type=float,
            default=0.85,
            help="Similarity threshold 0-1 (default: 0.85)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute duplicate detection."""
        path = args.path.resolve()

        if not path.exists():
            return {
                "success": False,
                "error": f"Path not found: {path}"
            }

        self.logger.info(f"Finding duplicates in {path}")

        # Find Python files
        files = list(path.rglob("*.py")) if path.is_dir() else [path]

        # Extract code blocks
        blocks = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Extract blocks (sliding window)
                for i in range(len(lines) - args.threshold + 1):
                    block_lines = lines[i:i + args.threshold]
                    # Skip empty or comment-only blocks
                    non_empty = [l for l in block_lines if l.strip() and not l.strip().startswith("#")]
                    if len(non_empty) >= args.threshold // 2:
                        blocks.append({
                            "file": str(file.relative_to(path.parent if path.is_file() else path)),
                            "start_line": i + 1,
                            "end_line": i + args.threshold,
                            "content": "".join(block_lines),
                            "hash": self._hash_code("".join(block_lines))
                        })

            except Exception:
                continue

        # Find duplicates
        duplicates = []
        seen = set()

        for i, block1 in enumerate(blocks):
            for block2 in blocks[i+1:]:
                # Skip same file close lines
                if block1["file"] == block2["file"] and abs(block1["start_line"] - block2["start_line"]) < args.threshold:
                    continue

                similarity = self._calculate_similarity(block1["content"], block2["content"])

                if similarity >= args.similarity:
                    key = tuple(sorted([block1["hash"], block2["hash"]]))
                    if key not in seen:
                        seen.add(key)
                        duplicates.append(DuplicateBlock(
                            locations=[
                                {"file": block1["file"], "lines": f"{block1['start_line']}-{block1['end_line']}"},
                                {"file": block2["file"], "lines": f"{block2['start_line']}-{block2['end_line']}"}
                            ],
                            similarity=similarity,
                            lines=args.threshold,
                            severity=self._calculate_severity(similarity, args.threshold)
                        ))

        result = {
            "success": True,
            "path": str(path),
            "files_analyzed": len(files),
            "blocks_analyzed": len(blocks),
            "duplicates_found": len(duplicates),
            "duplicates": [
                {
                    "locations": d.locations,
                    "similarity": round(d.similarity, 2),
                    "lines": d.lines,
                    "severity": d.severity
                }
                for d in duplicates
            ]
        }

        self.metrics.track("find_duplicates", {
            "files": len(files),
            "duplicates": len(duplicates)
        })

        return result

    def _hash_code(self, code: str) -> str:
        """Hash code content (normalized)."""
        # Normalize whitespace
        normalized = " ".join(code.split())
        return hashlib.md5(normalized.encode()).hexdigest()

    def _calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate token-based similarity."""
        # Simple token-based similarity
        tokens1 = set(code1.split())
        tokens2 = set(code2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union) if union else 0.0

    def _calculate_severity(self, similarity: float, lines: int) -> str:
        """Calculate severity based on similarity and size."""
        if similarity >= 0.95 and lines >= 10:
            return "high"
        elif similarity >= 0.90 or lines >= 15:
            return "medium"
        else:
            return "low"


def main():
    """CLI entry point."""
    from common.cli.base import create_cli_script
    create_cli_script(FindDuplicatesScript)


if __name__ == "__main__":
    main()
