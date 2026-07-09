#!/usr/bin/env python3
"""
TDD refactoring scanner — detect testability anti-patterns in any language library.

Uses Ollama (qwen2.5-coder:7b) to identify code constructs that block unit/integration
testing, and proposes minimal refactorings to unlock new tests.

Output: JSON list of blockers with proposed refactorings and tests unlocked.
"""

import argparse
import json
import sys
from pathlib import Path

from common.ollama_utils import analyze_file_with_ollama, check_ollama_available

# Source file extensions per language (same as analyze_library_branches.py)
LANGUAGE_EXTENSIONS = {
    "csharp": [".cs"],
    "python": [".py"],
    "kotlin": [".kt"],
    "java": [".java"],
    "go": [".go"],
    "rust": [".rs"],
    "ruby": [".rb"],
    "typescript": [".ts"],
    "javascript": [".js"],
    "swift": [".swift"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp"],
}

ANTI_PATTERNS = [
    "static_method_call",       # calling static methods on concrete types
    "new_in_method",            # new ConcreteType() inside constructor or method body
    "no_interface",             # collaborator has no interface/abstraction
    "sealed_or_final",          # sealed/final class with no test accessor
    "global_mutable_state",     # static fields, singletons without reset
    "hardcoded_io",             # hardcoded file paths, URLs, connection strings
    "private_complex_logic",    # private methods with complex branching
    "deep_method_chain",        # a.GetB().GetC().DoD() — impossible to intercept
    "thread_sleep_or_datetime_now",  # non-deterministic time in production code
    "unhandled_exception_swallow",   # empty catch blocks
]


def detect_language(src_path: Path) -> str:
    counts = {}
    for lang, exts in LANGUAGE_EXTENSIONS.items():
        count = sum(len(list(src_path.rglob(f"*{ext}"))) for ext in exts)
        if count > 0:
            counts[lang] = count
    if not counts:
        return "unknown"
    return max(counts, key=counts.get)


def get_source_files(src_path: Path, language: str) -> list[Path]:
    exts = LANGUAGE_EXTENSIONS.get(language, [])
    files = []
    test_indicators = ["_test.", "_spec.", "test_", "spec_", ".test.", ".spec.", "tests.", "specs."]
    test_dirs = {"test", "tests", "spec", "specs", "__tests__"}
    for ext in exts:
        for f in src_path.rglob(f"*{ext}"):
            fname = f.name.lower()
            if any(ind in fname for ind in test_indicators):
                continue
            if set(p.lower() for p in f.parts) & test_dirs:
                continue
            parts = set(f.parts)
            if parts & {"obj", "bin", "build", "dist", "__pycache__", "target", ".git"}:
                continue
            files.append(f)
    return sorted(files)


def scan_file(file_path: Path, language: str, model: str, max_chars: int) -> list[dict]:
    return analyze_file_with_ollama(file_path, language, model, "scan_tdd_refactoring", max_chars)


EFFORT_ORDER = {"Tiny": 0, "Small": 1, "Medium": 2, "Large": 3}


def summarize(blockers: list[dict]) -> dict:
    by_pattern: dict[str, int] = {}
    total_tests_unlocked = 0
    for b in blockers:
        pat = b.get("anti_pattern", "unknown")
        by_pattern[pat] = by_pattern.get(pat, 0) + 1
        total_tests_unlocked += len(b.get("tests_unlocked", []))

    return {
        "total_blockers": len(blockers),
        "total_tests_unlocked": total_tests_unlocked,
        "by_anti_pattern": by_pattern,
    }


def _merge_blocker_runs(runs: list[list[dict]]) -> list[dict]:
    """Merge N independent TDD scan runs, deduplicating by (location, anti_pattern)."""
    seen: set[tuple] = set()
    merged: list[dict] = []
    for run in runs:
        for blocker in run:
            key = (
                blocker.get("location", "").lower()[:80],
                blocker.get("anti_pattern", ""),
            )
            if key not in seen:
                seen.add(key)
                merged.append(blocker)
    return merged


def main():
    parser = argparse.ArgumentParser(
        description="Detect testability anti-patterns and propose TDD refactorings via Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scan_tdd_refactoring.py ./src --language csharp --output refactoring.json
  python scan_tdd_refactoring.py ./lib --language auto --verbose
  python scan_tdd_refactoring.py . --language python --model qwen2.5-coder:14b
        """,
    )
    parser.add_argument("src_path", type=Path, help="Path to source directory")
    parser.add_argument(
        "--language", "-l",
        default="auto",
        choices=["auto"] + list(LANGUAGE_EXTENSIONS.keys()),
        help="Source language (default: auto-detect)",
    )
    parser.add_argument(
        "--model", "-m",
        default="qwen2.5-coder:7b",
        help="Ollama model to use (default: qwen2.5-coder:7b)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSON file (default: stdout)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress to stderr",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=8000,
        help="Max characters per file sent to Ollama (default: 8000)",
    )
    parser.add_argument(
        "--sort-by",
        choices=["effort", "tests_unlocked", "file"],
        default="tests_unlocked",
        help="Sort blockers by this field (default: tests_unlocked)",
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=1,
        help="Number of independent Ollama runs to merge (default: 1)",
    )

    args = parser.parse_args()

    if not args.src_path.exists():
        print(f"Error: {args.src_path} does not exist", file=sys.stderr)
        return 1

    if not check_ollama_available(args.model):
        print(
            f"[ERROR] Ollama model '{args.model}' not available.\n"
            f"  Run: ollama pull {args.model}",
            file=sys.stderr,
        )
        return 1

    language = args.language
    if language == "auto":
        language = detect_language(args.src_path)
        if args.verbose:
            print(f"[INFO] Auto-detected language: {language}", file=sys.stderr)

    files = get_source_files(args.src_path, language)
    if not files:
        print(f"[WARN] No {language} source files found", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"[INFO] Language: {language}", file=sys.stderr)
        print(f"[INFO] Source files to scan: {len(files)}", file=sys.stderr)

    def _scan_all_files() -> list[dict]:
        result = []
        for i, f in enumerate(files, 1):
            if args.verbose:
                print(f"[{i}/{len(files)}] Scanning {f.name}...", file=sys.stderr)
            result.extend(scan_file(f, language, args.model, args.max_chars))
        return result

    if args.agents > 1:
        from concurrent.futures import ThreadPoolExecutor
        if args.verbose:
            print(f"[INFO] Running {args.agents} parallel agents for broader coverage...", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=args.agents) as pool:
            runs = list(pool.map(lambda _: _scan_all_files(), range(args.agents)))
        all_blockers = _merge_blocker_runs(runs)
        if args.verbose:
            print(f"[INFO] Merged {args.agents} runs: {len(all_blockers)} unique blockers", file=sys.stderr)
    else:
        all_blockers = _scan_all_files()

    # Sort
    if args.sort_by == "effort":
        all_blockers.sort(key=lambda b: EFFORT_ORDER.get(b.get("effort", "Large"), 99))
    elif args.sort_by == "tests_unlocked":
        all_blockers.sort(key=lambda b: len(b.get("tests_unlocked", [])), reverse=True)
    else:
        all_blockers.sort(key=lambda b: b.get("source_file_name", ""))

    output = {
        "language": language,
        "src_path": str(args.src_path),
        "summary": summarize(all_blockers),
        "blockers": all_blockers,
    }

    if args.verbose:
        s = output["summary"]
        print(
            f"[INFO] Total blockers: {s['total_blockers']}, tests unlocked if fixed: {s['total_tests_unlocked']}",
            file=sys.stderr,
        )

    json_out = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(json_out, encoding="utf-8")
        if args.verbose:
            print(f"[INFO] Written to {args.output}", file=sys.stderr)
    else:
        print(json_out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
