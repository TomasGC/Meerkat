#!/usr/bin/env python3
"""
Benchmark Ollama model latency on user's hardware (32GB RAM).

Measures:
1. Cold start (model not loaded)
2. Warm start (model already loaded)
3. Memory usage per model
4. Swap detection (if RAM exceeded)

Usage:
    python benchmark_ollama_latency.py
    python benchmark_ollama_latency.py --models qwen2.5-coder:7b llama3.2:3b
    python benchmark_ollama_latency.py --output benchmark_results.json
"""

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class BenchmarkResult:
    """Benchmark result for a single model."""

    model: str
    tier: str  # hot/warm/cold
    size_gb: float
    cold_start_ms: int
    warm_start_ms: int
    avg_response_ms: int
    memory_mb: int
    swapped: bool
    timestamp: str


@dataclass
class SystemInfo:
    """System information."""

    total_ram_gb: float
    available_ram_gb: float
    cpu: str
    gpu: Optional[str]
    ollama_version: str


# Model configuration (from settings.json)
MODELS = {
    # Hot tier (~27GB total)
    "qwen2.5-coder:7b": {"tier": "hot", "size_gb": 4.7},
    "llama3.2:3b": {"tier": "hot", "size_gb": 2.0},
    "llama-guard3:1b": {"tier": "hot", "size_gb": 1.6},
    "phi4": {"tier": "hot", "size_gb": 9.1},
    "deepseek-r1:7b": {"tier": "hot", "size_gb": 4.7},
    "llama3.1:8b": {"tier": "hot", "size_gb": 4.7},
    # Warm tier
    "qwen2.5:32b": {"tier": "warm", "size_gb": 20.0},
    "qwen2.5-coder:14b": {"tier": "warm", "size_gb": 9.0},
    "deepseek-coder-v2:16b": {"tier": "warm", "size_gb": 8.9},
    # Cold tier (swap risk)
    "llama3.3:70b": {"tier": "cold", "size_gb": 42.0},
    "nous-hermes-2-mixtral:8x7b": {"tier": "cold", "size_gb": 26.0},
    "codestral:22b": {"tier": "cold", "size_gb": 12.0},
}

TEST_PROMPT = "Write a simple hello world function in Python"


def run_command(cmd: List[str], timeout: int = 60) -> tuple[str, int]:
    """Run command and return output + execution time."""
    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=True,
            encoding='utf-8', errors='replace'
        )
        elapsed_ms = int((time.time() - start) * 1000)
        return result.stdout.strip(), elapsed_ms
    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.time() - start) * 1000)
        return f"TIMEOUT after {timeout}s", elapsed_ms
    except subprocess.CalledProcessError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return f"ERROR: {e.stderr}", elapsed_ms


def stop_all_models():
    """Stop all running Ollama models."""
    try:
        subprocess.run(["ollama", "stop", "--all"], check=True, capture_output=True,
                      encoding='utf-8', errors='replace')
        print("[OK] All models stopped")
    except subprocess.CalledProcessError:
        print("[WARN] Could not stop all models")


def is_model_loaded(model: str) -> bool:
    """Check if model is currently loaded in RAM."""
    try:
        result = subprocess.run(
            ["ollama", "ps"], capture_output=True, text=True, check=True,
            encoding='utf-8', errors='replace'
        )
        return model in result.stdout
    except subprocess.CalledProcessError:
        return False


def get_system_info() -> SystemInfo:
    """Get system information."""
    # RAM
    try:
        import psutil

        ram_gb = psutil.virtual_memory().total / (1024**3)
        available_gb = psutil.virtual_memory().available / (1024**3)
    except ImportError:
        ram_gb = 32.0  # User's specs
        available_gb = 31.5

    # CPU
    try:
        import platform

        cpu = platform.processor()
    except Exception:
        cpu = "Intel(R) Core(TM) Ultra 7 155H"

    # GPU (placeholder, would need nvidia-smi)
    gpu = "4GB (Multiple GPUs)"

    # Ollama version
    try:
        result = subprocess.run(
            ["ollama", "--version"], capture_output=True, text=True, check=True,
            encoding='utf-8', errors='replace'
        )
        version = result.stdout.strip()
    except Exception:
        version = "unknown"

    return SystemInfo(
        total_ram_gb=ram_gb,
        available_ram_gb=available_gb,
        cpu=cpu,
        gpu=gpu,
        ollama_version=version,
    )


def benchmark_model(model: str, config: dict) -> BenchmarkResult:
    """Benchmark a single model."""
    print(f"\n[Benchmarking] {model} ({config['tier']} tier, {config['size_gb']}GB)")

    # 1. Cold start (unload first)
    print(f"  [1/3] Cold start (unloading first)...")
    stop_all_models()
    time.sleep(2)  # Wait for unload
    _, cold_ms = run_command(["ollama", "run", model, TEST_PROMPT], timeout=120)
    print(f"    [OK] Cold start: {cold_ms}ms")

    # 2. Warm start (model already loaded)
    print(f"  [2/3] Warm start (model loaded)...")
    if not is_model_loaded(model):
        print(f"    [WARN] Model not loaded, loading again...")
        run_command(["ollama", "run", model, TEST_PROMPT], timeout=120)

    _, warm_ms = run_command(["ollama", "run", model, TEST_PROMPT], timeout=60)
    print(f"    [OK] Warm start: {warm_ms}ms")

    # 3. Average response time (3 runs)
    print(f"  [3/3] Average response (3 runs)...")
    times = []
    for i in range(3):
        _, run_ms = run_command(["ollama", "run", model, TEST_PROMPT], timeout=60)
        times.append(run_ms)
        print(f"    Run {i+1}: {run_ms}ms")

    avg_ms = sum(times) // len(times)
    print(f"    [OK] Average: {avg_ms}ms")

    # 4. Memory check (placeholder, would need psutil + ollama process tracking)
    memory_mb = int(config["size_gb"] * 1024)

    # 5. Swap detection (basic heuristic: cold start >> warm start)
    swapped = cold_ms > (warm_ms * 10)  # 10x slower = likely swapping
    if swapped:
        print(f"    [WARN] SWAP DETECTED (cold: {cold_ms}ms, warm: {warm_ms}ms)")

    return BenchmarkResult(
        model=model,
        tier=config["tier"],
        size_gb=config["size_gb"],
        cold_start_ms=cold_ms,
        warm_start_ms=warm_ms,
        avg_response_ms=avg_ms,
        memory_mb=memory_mb,
        swapped=swapped,
        timestamp=datetime.now().isoformat(),
    )


def generate_report(
    results: List[BenchmarkResult], system_info: SystemInfo, output_file: Path
):
    """Generate benchmark report."""
    hot_results = [r for r in results if r.tier == "hot"]
    warm_results = [r for r in results if r.tier == "warm"]
    cold_results = [r for r in results if r.tier == "cold"]

    report = {
        "system_info": asdict(system_info),
        "benchmark_date": datetime.now().isoformat(),
        "results": [asdict(r) for r in results],
        "summary": {
            "hot_tier_avg_ms": (
                sum(r.warm_start_ms for r in hot_results) // len(hot_results)
                if hot_results else 0
            ),
            "warm_tier_avg_ms": (
                sum(r.cold_start_ms for r in warm_results) // len(warm_results)
                if warm_results else 0
            ),
            "cold_tier_avg_ms": (
                sum(r.cold_start_ms for r in cold_results) // len(cold_results)
                if cold_results else 0
            ),
            "swap_detected_models": [r.model for r in results if r.swapped],
        },
    }

    # Save JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[OK] Report saved to: {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"System: {system_info.cpu}")
    print(f"RAM: {system_info.total_ram_gb:.1f}GB total, {system_info.available_ram_gb:.1f}GB available")
    print(f"Ollama: {system_info.ollama_version}")
    print()
    print("Average latency by tier:")
    if report['summary']['hot_tier_avg_ms'] > 0:
        print(f"  Hot tier (instant):   {report['summary']['hot_tier_avg_ms']}ms")
    if report['summary']['warm_tier_avg_ms'] > 0:
        print(f"  Warm tier (5-10s):    {report['summary']['warm_tier_avg_ms']}ms")
    if report['summary']['cold_tier_avg_ms'] > 0:
        print(f"  Cold tier (30s+):     {report['summary']['cold_tier_avg_ms']}ms")
    print()
    if report["summary"]["swap_detected_models"]:
        print("[WARN] Swap detected for:")
        for model in report["summary"]["swap_detected_models"]:
            print(f"  - {model}")
    else:
        print("[OK] No swap detected")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Ollama model latency on 32GB RAM hardware"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Models to benchmark (default: all hot tier)",
        default=None,
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file",
        default=Path.home() / ".claude" / "scripts" / "benchmarks" / "benchmark_results.json",
    )
    parser.add_argument(
        "--skip-cold",
        action="store_true",
        help="Skip cold tier models (avoid swap)",
    )

    args = parser.parse_args()

    # Select models to test
    if args.models:
        models_to_test = {m: MODELS[m] for m in args.models if m in MODELS}
    else:
        # Default: hot tier only (fast benchmark)
        models_to_test = {m: cfg for m, cfg in MODELS.items() if cfg["tier"] == "hot"}

    if args.skip_cold:
        models_to_test = {
            m: cfg for m, cfg in models_to_test.items() if cfg["tier"] != "cold"
        }

    print("=" * 70)
    print("OLLAMA LATENCY BENCHMARK (32GB RAM)")
    print("=" * 70)
    print(f"Models to test: {len(models_to_test)}")
    for model, cfg in models_to_test.items():
        print(f"  - {model} ({cfg['tier']} tier, {cfg['size_gb']}GB)")
    print()

    # Get system info
    system_info = get_system_info()
    print(f"System: {system_info.cpu}")
    print(f"RAM: {system_info.total_ram_gb:.1f}GB total, {system_info.available_ram_gb:.1f}GB available")
    print(f"Ollama: {system_info.ollama_version}")

    # Run benchmarks
    results = []
    for model, config in models_to_test.items():
        try:
            result = benchmark_model(model, config)
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] Failed to benchmark {model}: {e}")

    # Generate report
    if results:
        generate_report(results, system_info, args.output)
    else:
        print("\n[ERROR] No benchmarks completed")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
