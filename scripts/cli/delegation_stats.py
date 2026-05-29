#!/usr/bin/env python3
"""
Delegation statistics dashboard (token savings tracking).

Usage:
    python delegation_stats.py
    python delegation_stats.py --last 10
    python delegation_stats.py --export stats.json
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base_cli import BaseCLIScript


class DelegationStats(BaseCLIScript):
    """Track and display delegation statistics."""

    def add_arguments(self) -> None:
        self.parser.add_argument(
            "--last",
            type=int,
            help="Last N sessions",
        )
        self.parser.add_argument(
            "--since",
            type=str,
            help='Since date (e.g., "2026-05-01")',
        )
        self.parser.add_argument(
            "--export",
            type=Path,
            help="Export to JSON file",
        )

    def execute(self) -> None:
        """Generate delegation statistics."""
        log_file = Path.home() / ".claude" / "logs" / "delegation-stats.jsonl"

        if not log_file.exists():
            print("[INFO] No delegation logs found yet")
            return

        # Read logs
        entries = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue

        if not entries:
            print("[INFO] No valid log entries")
            return

        # Filter by date
        if self.args.since:
            since_dt = datetime.fromisoformat(self.args.since)
            entries = [
                e
                for e in entries
                if datetime.fromisoformat(e["timestamp"]) >= since_dt
            ]

        # Filter by last N sessions
        if self.args.last:
            session_starts = [e for e in entries if e.get("event") == "session_start"]
            if len(session_starts) > self.args.last:
                last_session_time = session_starts[-self.args.last]["timestamp"]
                entries = [
                    e
                    for e in entries
                    if e["timestamp"] >= last_session_time
                ]

        # Calculate stats
        stats = self._calculate_stats(entries)

        # Display or export
        if self.args.export:
            with open(self.args.export, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
            print(f"[OK] Stats exported to {self.args.export}")
        else:
            self._display_stats(stats)

    def _calculate_stats(self, entries: list) -> dict:
        """Calculate delegation statistics."""
        total_delegations = 0
        delegations_by_type = defaultdict(int)
        tokens_saved_by_type = defaultdict(int)
        session_count = len([e for e in entries if e.get("event") == "session_start"])

        # Token savings estimates (from delegation-rules.json)
        token_estimates = {
            "format_code": 5000,
            "lint_code": 3000,
            "validate_syntax": 3000,
            "quick_review": 5000,
            "run_tests": 15000,
            "calculate_coverage": 3000,
            "git_operations": 2000,
        }

        for entry in entries:
            if entry.get("delegated"):
                total_delegations += 1
                tool = entry.get("tool", "unknown")
                delegations_by_type[tool] += 1

                # Estimate tokens saved
                tokens = token_estimates.get(tool, 1000)
                tokens_saved_by_type[tool] += tokens

        total_tokens_saved = sum(tokens_saved_by_type.values())

        return {
            "period": {
                "start": entries[0]["timestamp"] if entries else None,
                "end": entries[-1]["timestamp"] if entries else None,
                "sessions": session_count,
            },
            "summary": {
                "total_delegations": total_delegations,
                "total_tokens_saved": total_tokens_saved,
                "avg_tokens_per_session": (
                    total_tokens_saved // session_count if session_count > 0 else 0
                ),
            },
            "by_type": {
                "delegations": dict(delegations_by_type),
                "tokens_saved": dict(tokens_saved_by_type),
            },
            "top_delegations": sorted(
                delegations_by_type.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def _display_stats(self, stats: dict) -> None:
        """Display statistics in terminal."""
        print("\n" + "=" * 70)
        print("DELEGATION STATISTICS")
        print("=" * 70)

        # Period
        period = stats["period"]
        print(f"Period: {period['start'][:10]} to {period['end'][:10]}")
        print(f"Sessions: {period['sessions']}")
        print()

        # Summary
        summary = stats["summary"]
        print(f"Total delegations: {summary['total_delegations']}")
        print(f"Total tokens saved: {summary['total_tokens_saved']:,}")
        print(f"Avg tokens saved per session: {summary['avg_tokens_per_session']:,}")
        print()

        # Top delegations
        print("Top delegated tasks:")
        for task, count in stats["top_delegations"]:
            tokens = stats["by_type"]["tokens_saved"].get(task, 0)
            print(f"  {task:20s} - {count:3d}x ({tokens:,} tokens)")

        print("=" * 70)


if __name__ == "__main__":
    DelegationStats().run()
