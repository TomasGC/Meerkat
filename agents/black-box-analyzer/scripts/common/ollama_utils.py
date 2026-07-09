#!/usr/bin/env python3
"""Shared Ollama utilities — call_ollama, JSON extraction, health check."""

import json
import subprocess
import sys
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "ollama"


def check_ollama_available(model: str = "qwen2.5-coder:7b") -> bool:
    """Return True if ollama is in PATH and the requested model is available."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False
        return model in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def call_ollama(prompt: str, model: str = "qwen2.5-coder:7b", timeout: int = 120) -> str | None:
    """
    Call Ollama via CLI. Returns raw text response or None on failure.

    Exits with a clear error message if ollama is not found — avoids silent
    empty-JSON failures that cause downstream parsing errors.
    """
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            print(f"[WARN] Ollama returned non-zero exit: {result.stderr[:300]}", file=sys.stderr)
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        print(
            "[ERROR] 'ollama' not found in PATH.\n"
            "  Install: https://ollama.ai\n"
            "  Then run: ollama pull qwen2.5-coder:7b",
            file=sys.stderr,
        )
        return None
    except subprocess.TimeoutExpired:
        print(f"[WARN] Ollama timed out after {timeout}s on this prompt", file=sys.stderr)
        return None


def run_prompt(name: str, model: str = "qwen2.5-coder:7b", timeout: int = 120, **kwargs) -> str | None:
    """Load a .prompt file by name, format with kwargs, and call Ollama."""
    prompt_file = _PROMPTS_DIR / f"{name}.prompt"
    try:
        template = prompt_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[ERROR] Prompt file not found: {prompt_file}", file=sys.stderr)
        return None
    return call_ollama(template.format(**kwargs), model=model, timeout=timeout)


def analyze_file_with_ollama(
    file_path: Path,
    language: str,
    model: str,
    prompt_name: str,
    max_chars: int = 8000,
) -> list[dict]:
    """Read source file, call run_prompt, extract JSON array, annotate with file info."""
    source = file_path.read_text(encoding="utf-8", errors="replace")
    if len(source) > max_chars:
        source = source[:max_chars] + "\n// ... (truncated)"
    response = run_prompt(prompt_name, model=model, language=language, source=source)
    if not response:
        return []
    results = extract_json_array(response)
    if not results:
        print(f"[WARN] Could not parse JSON from Ollama for {file_path.name}", file=sys.stderr)
        return []
    for item in results:
        item["source_file"] = str(file_path)
        item["source_file_name"] = file_path.name
    return results


def extract_json_array(text: str) -> list | None:
    """
    Extract a JSON array from an Ollama response that may have surrounding prose.

    Tries direct parse first, then scans for first '[' … last ']' block.
    Returns None if no valid array found.
    """
    if not text:
        return None

    # Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Scan for array boundaries
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start : end + 1])
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    return None


def extract_json_object(text: str) -> dict | None:
    """
    Extract a JSON object from an Ollama response.

    Tries direct parse first, then scans for first '{' … last '}' block.
    Returns None if no valid object found.
    """
    if not text:
        return None

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    return None
