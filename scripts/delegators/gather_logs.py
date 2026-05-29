#!/usr/bin/env python3
"""
Gather application logs for debugging (0 tokens).

Collects logs from common locations, filters by time/level, extracts errors.

Usage:
    python gather_logs.py --since "2026-05-11 10:00"
    python gather_logs.py --level error --last 100
    python gather_logs.py --search "NullPointerException"
"""

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class LogEntry:
    """Single log entry."""

    timestamp: str
    level: str
    message: str
    file: str
    line_number: Optional[int] = None
    context: Optional[str] = None


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Gather application logs")

    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log file path (default: auto-detect)",
    )
    parser.add_argument(
        "--since",
        type=str,
        help='Start time (e.g., "2026-05-11 10:00")',
    )
    parser.add_argument(
        "--last",
        type=int,
        help="Last N lines",
    )
    parser.add_argument(
        "--level",
        type=str,
        choices=["debug", "info", "warn", "error", "fatal"],
        help="Filter by log level",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="Search term (regex)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file (optional)",
    )

    return parser.parse_args()


def find_log_file() -> Optional[Path]:
    """Auto-detect log file."""
    common_locations = [
        Path("logs/app.log"),
        Path("logs/application.log"),
        Path("var/log/app.log"),
        Path("/var/log/app.log"),
        Path("app.log"),
    ]

    for location in common_locations:
        if location.exists():
            return location

    return None


def parse_log_line(line: str) -> Optional[LogEntry]:
    """Parse a log line."""
    # Common log format: [TIMESTAMP] [LEVEL] message
    pattern = r"\[([^\]]+)\]\s*\[(\w+)\]\s*(.*)"
    match = re.match(pattern, line)

    if not match:
        return None

    timestamp_str, level, message = match.groups()

    return LogEntry(
        timestamp=timestamp_str,
        level=level.upper(),
        message=message.strip(),
        file="",  # Would need to parse from message
    )


def filter_logs(
    entries: list[LogEntry],
    since: Optional[str],
    level: Optional[str],
    search: Optional[str],
    last: Optional[int],
) -> list[LogEntry]:
    """Filter log entries."""
    filtered = entries

    # Filter by time
    if since:
        since_dt = datetime.fromisoformat(since)
        filtered = [
            e
            for e in filtered
            if datetime.fromisoformat(e.timestamp) >= since_dt
        ]

    # Filter by level
    if level:
        level_priority = {
            "debug": 0,
            "info": 1,
            "warn": 2,
            "error": 3,
            "fatal": 4,
        }
        min_priority = level_priority[level.lower()]

        filtered = [
            e
            for e in filtered
            if level_priority.get(e.level.lower(), 0) >= min_priority
        ]

    # Filter by search
    if search:
        pattern = re.compile(search, re.IGNORECASE)
        filtered = [e for e in filtered if pattern.search(e.message)]

    # Take last N
    if last:
        filtered = filtered[-last:]

    return filtered


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Find log file
    log_file = args.log_file or find_log_file()
    if not log_file:
        print("[ERROR] No log file found")
        return 1

    if not log_file.exists():
        print(f"[ERROR] Log file not found: {log_file}")
        return 1

    print(f"[INFO] Reading logs from {log_file}")

    # Parse logs
    entries = []
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                entry = parse_log_line(line.strip())
                if entry:
                    entries.append(entry)
    except Exception as e:
        print(f"[ERROR] Failed to read log file: {e}")
        return 1

    print(f"[INFO] Parsed {len(entries)} log entries")

    # Filter
    filtered = filter_logs(
        entries,
        args.since,
        args.level,
        args.search,
        args.last,
    )

    print(f"[INFO] {len(filtered)} entries after filtering")

    # Output
    result = {
        "log_file": str(log_file),
        "total_entries": len(entries),
        "filtered_entries": len(filtered),
        "logs": [asdict(e) for e in filtered],
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\n[OK] Report saved to {args.output}")
    else:
        print("\n" + "=" * 60)
        print(f"LOG ENTRIES ({len(filtered)})")
        print("=" * 60)
        for entry in filtered[-10:]:  # Show last 10
            print(f"[{entry.timestamp}] [{entry.level}] {entry.message}")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
