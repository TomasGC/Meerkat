#!/usr/bin/env python3
"""
Library branch extractor — white-box analysis for any language library/SDK.

Uses Ollama (qwen2.5-coder:7b) to extract public methods + all internal branches
from source files. Works for C#, Python, Kotlin, Java, Go, Rust, Ruby, TypeScript, etc.

Output: JSON list of methods with their branches and expected test scenarios.
"""

import argparse
import json
import sys
from pathlib import Path

from common.ollama_utils import analyze_file_with_ollama, check_ollama_available

# Source file extensions per language
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

# Auto-detect language from file extensions present in src dir
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
    """Return all source files for given language, excluding test files."""
    exts = LANGUAGE_EXTENSIONS.get(language, [])
    files = []
    test_indicators = ["_test.", "_spec.", "test_", "spec_", ".test.", ".spec.", "tests.", "specs."]
    test_dirs = {"test", "tests", "spec", "specs", "__tests__"}
    for ext in exts:
        for f in src_path.rglob(f"*{ext}"):
            # Skip test files
            fname = f.name.lower()
            if any(ind in fname for ind in test_indicators):
                continue
            # Skip files inside test directories
            if set(p.lower() for p in f.parts) & test_dirs:
                continue
            # Skip obj/bin/build dirs
            parts = set(f.parts)
            if parts & {"obj", "bin", "build", "dist", "__pycache__", "target", ".git"}:
                continue
            files.append(f)
    return sorted(files)


TYPED_PROMPTS = {
    "unit":     "analyze_branches_unit",
    "int_mock": "analyze_branches_int_mock",
    "int_real": "analyze_branches_int_real",
    "e2e":      "analyze_branches_e2e",
}


def analyze_file(file_path: Path, language: str, model: str, max_chars: int = 8000,
                 prompt_name: str = "analyze_library_branches") -> list[dict]:
    """Analyze one source file via Ollama. Returns list of method branch objects."""
    return analyze_file_with_ollama(file_path, language, model, prompt_name, max_chars)


def analyze_file_typed(
    file_path: Path,
    language: str,
    model: str,
    max_chars: int = 8000,
    include_e2e: bool = False,
) -> list[dict]:
    """Run one Ollama agent per test type in parallel, tag results, merge."""
    from concurrent.futures import ThreadPoolExecutor
    types = ["unit", "int_mock", "int_real"] + (["e2e"] if include_e2e else [])

    def _run_type(test_type: str) -> list[dict]:
        results = analyze_file_with_ollama(file_path, language, model, TYPED_PROMPTS[test_type], max_chars)
        for item in results:
            for branch in item.get("branches", []):
                branch["test_type_hint"] = test_type.upper()
        return results

    with ThreadPoolExecutor(max_workers=len(types)) as pool:
        all_runs = list(pool.map(_run_type, types))

    # merge: key = (method, condition[:80], test_type_hint)
    merged: dict[str, dict] = {}
    seen: set[tuple] = set()
    for run in all_runs:
        for method in run:
            key_m = method.get("method", "")
            if key_m not in merged:
                merged[key_m] = {k: v for k, v in method.items() if k != "branches"}
                merged[key_m]["branches"] = []
            for branch in method.get("branches", []):
                bkey = (key_m, branch.get("condition", "").lower()[:80],
                        branch.get("test_type_hint", "").upper())
                if bkey not in seen:
                    seen.add(bkey)
                    merged[key_m]["branches"].append(branch)
    return list(merged.values())


def analyze_library(
    src_path: Path,
    language: str,
    model: str,
    verbose: bool,
    max_chars: int = 8000,
    typed_agents: bool = False,
    include_e2e: bool = False,
) -> list[dict]:
    """Analyze all source files in library. Returns aggregated list of methods."""
    files = get_source_files(src_path, language)
    if not files:
        print(f"[WARN] No {language} source files found in {src_path}", file=sys.stderr)
        return []

    if verbose:
        print(f"[INFO] Language: {language}", file=sys.stderr)
        print(f"[INFO] Source files: {len(files)}", file=sys.stderr)
        print(f"[INFO] Ollama model: {model}", file=sys.stderr)
        if typed_agents:
            types = ["unit", "int_mock", "int_real"] + (["e2e"] if include_e2e else [])
            print(f"[INFO] Typed agents: {types}", file=sys.stderr)

    all_methods = []
    for i, f in enumerate(files, 1):
        if verbose:
            print(f"[{i}/{len(files)}] Analyzing {f.name}...", file=sys.stderr)
        if typed_agents:
            methods = analyze_file_typed(f, language, model, max_chars=max_chars, include_e2e=include_e2e)
        else:
            methods = analyze_file(f, language, model, max_chars=max_chars)
        all_methods.extend(methods)
        if verbose and methods:
            print(f"  → {len(methods)} public method(s) found", file=sys.stderr)

    return all_methods


def _merge_runs(runs: list[list[dict]]) -> list[dict]:
    """Merge N independent Ollama analysis runs, deduplicating by (method, condition)."""
    merged: dict[str, dict] = {}
    seen_branches: set[tuple] = set()
    for run in runs:
        for method in run:
            key_m = method.get("method", "")
            if key_m not in merged:
                merged[key_m] = {k: v for k, v in method.items() if k != "branches"}
                merged[key_m]["branches"] = []
            for branch in method.get("branches", []):
                bkey = (key_m, branch.get("condition", "").lower()[:80])
                if bkey not in seen_branches:
                    seen_branches.add(bkey)
                    merged[key_m]["branches"].append(branch)
    return list(merged.values())


def main():
    parser = argparse.ArgumentParser(
        description="Extract public methods + branches from any language library via Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_library_branches.py ./src --language csharp --output methods.json
  python analyze_library_branches.py ./lib --language auto --verbose
  python analyze_library_branches.py . --language python --model qwen2.5-coder:14b
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
        "--agents",
        type=int,
        default=1,
        help="Number of independent Ollama runs to merge per type (default: 1)",
    )
    parser.add_argument(
        "--typed-agents",
        action="store_true",
        help="Run one dedicated agent per test type (unit/int_mock/int_real[/e2e]) in parallel",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Include e2e agent when --typed-agents is active (for apps/APIs, not pure libraries)",
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

    typed = args.typed_agents
    include_e2e = args.e2e

    if args.agents > 1:
        from concurrent.futures import ThreadPoolExecutor
        if args.verbose:
            print(f"[INFO] Running {args.agents} parallel agents for broader coverage...", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=args.agents) as pool:
            futures = [
                pool.submit(analyze_library, args.src_path, language, args.model, False,
                            args.max_chars, typed, include_e2e)
                for _ in range(args.agents)
            ]
            runs = [f.result() for f in futures]
        methods = _merge_runs(runs)
        if args.verbose:
            print(f"[INFO] Merged {args.agents} runs: {len(methods)} unique methods", file=sys.stderr)
    else:
        methods = analyze_library(args.src_path, language, args.model, args.verbose,
                                  max_chars=args.max_chars, typed_agents=typed, include_e2e=include_e2e)

    output = {
        "language": language,
        "src_path": str(args.src_path),
        "method_count": len(methods),
        "branch_count": sum(len(m.get("branches", [])) for m in methods),
        "methods": methods,
    }

    if args.verbose:
        print(
            f"[INFO] Total: {output['method_count']} methods, {output['branch_count']} branches",
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
