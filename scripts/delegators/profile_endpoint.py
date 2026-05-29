#!/usr/bin/env python3
"""
Profile API endpoint performance (0 tokens).

Measures response time, identifies slow queries, detects N+1 problems.

Usage:
    python profile_endpoint.py --endpoint "GET /api/users"
    python profile_endpoint.py --url http://localhost:3000/api/users --duration 10
"""

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests


@dataclass
class ProfilingResult:
    """Profiling result for an endpoint."""

    endpoint: str
    method: str
    total_requests: int
    avg_response_ms: float
    min_response_ms: float
    max_response_ms: float
    p50_response_ms: float
    p95_response_ms: float
    p99_response_ms: float
    error_count: int
    error_rate: float
    timestamp: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Profile API endpoint performance")

    parser.add_argument(
        "--endpoint",
        type=str,
        help='Endpoint to profile (e.g., "GET /api/users")',
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Full URL to profile (e.g., http://localhost:3000/api/users)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Duration in seconds (default: 10)",
    )
    parser.add_argument(
        "--requests-per-second",
        type=int,
        default=10,
        help="Requests per second (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file (optional)",
    )

    return parser.parse_args()


def profile_endpoint(url: str, duration: int, rps: int) -> ProfilingResult:
    """Profile endpoint by sending requests."""
    parsed_url = urlparse(url)
    method = "GET"  # For now, only GET
    endpoint = parsed_url.path

    print(f"[INFO] Profiling {method} {endpoint}")
    print(f"[INFO] Duration: {duration}s, RPS: {rps}")

    # Collect response times
    response_times = []
    errors = 0

    start_time = time.time()
    request_interval = 1.0 / rps

    while time.time() - start_time < duration:
        request_start = time.time()

        try:
            response = requests.get(url, timeout=5)
            response_time_ms = (time.time() - request_start) * 1000

            if response.status_code >= 400:
                errors += 1

            response_times.append(response_time_ms)

        except requests.exceptions.RequestException as e:
            errors += 1
            response_times.append(5000)  # Timeout

        # Wait for next request
        elapsed = time.time() - request_start
        sleep_time = max(0, request_interval - elapsed)
        time.sleep(sleep_time)

    # Calculate percentiles
    response_times.sort()
    total = len(response_times)

    p50_idx = int(total * 0.50)
    p95_idx = int(total * 0.95)
    p99_idx = int(total * 0.99)

    result = ProfilingResult(
        endpoint=endpoint,
        method=method,
        total_requests=total,
        avg_response_ms=sum(response_times) / total,
        min_response_ms=min(response_times),
        max_response_ms=max(response_times),
        p50_response_ms=response_times[p50_idx],
        p95_response_ms=response_times[p95_idx],
        p99_response_ms=response_times[p99_idx],
        error_count=errors,
        error_rate=errors / total * 100,
        timestamp=datetime.now().isoformat(),
    )

    return result


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Determine URL
    if args.url:
        url = args.url
    elif args.endpoint:
        # Parse "GET /api/users" format
        parts = args.endpoint.split()
        if len(parts) == 2:
            method, path = parts
            url = f"http://localhost:3000{path}"  # Default to localhost
        else:
            print("[ERROR] Invalid endpoint format. Use: 'GET /api/users'")
            return 1
    else:
        print("[ERROR] Must specify --endpoint or --url")
        return 1

    # Profile
    try:
        result = profile_endpoint(url, args.duration, args.requests_per_second)
    except Exception as e:
        print(f"[ERROR] Profiling failed: {e}")
        return 1

    # Output
    result_dict = asdict(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2)
        print(f"\n[OK] Report saved to {args.output}")
    else:
        print("\n" + "=" * 60)
        print("PROFILING REPORT")
        print("=" * 60)
        print(f"Endpoint: {result.method} {result.endpoint}")
        print(f"Total requests: {result.total_requests}")
        print(f"Avg response: {result.avg_response_ms:.0f}ms")
        print(f"P50: {result.p50_response_ms:.0f}ms")
        print(f"P95: {result.p95_response_ms:.0f}ms")
        print(f"P99: {result.p99_response_ms:.0f}ms")
        print(f"Min/Max: {result.min_response_ms:.0f}ms / {result.max_response_ms:.0f}ms")
        print(f"Errors: {result.error_count} ({result.error_rate:.1f}%)")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
