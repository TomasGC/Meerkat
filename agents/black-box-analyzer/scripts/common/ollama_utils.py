#!/usr/bin/env python3
"""Shared Ollama utilities — call_ollama, JSON extraction, health check, async HTTP, cache."""

import asyncio
import http.client
import json
import re as _re
import subprocess
import sys
from pathlib import Path

_THINK_RE = _re.compile(r'<think>.*?</think>', _re.DOTALL)

OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "ollama"

# Availability cache — avoids repeated `ollama list` subprocess calls
_AVAILABILITY_CACHE: dict[str, bool] = {}

# Per-file Ollama result cache (lazy import — safe when common/ is on sys.path)
try:
    from common.cache import get_ollama_cached as _get_cached, set_ollama_cached as _set_cached
    _CACHE_AVAILABLE = True
except ImportError:
    _CACHE_AVAILABLE = False
    def _get_cached(file_path, analyzer, **kwargs): return None  # type: ignore[misc]
    def _set_cached(file_path, analyzer, results): pass  # type: ignore[misc]


def check_ollama_available(model: str = "qwen2.5-coder:7b") -> bool:
    """Return True if ollama is in PATH and the requested model is available."""
    if model in _AVAILABILITY_CACHE:
        return _AVAILABILITY_CACHE[model]
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        available = result.returncode == 0 and model in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        available = False
    _AVAILABILITY_CACHE[model] = available
    return available


def split_into_chunks(source: str, max_chars: int) -> list[str]:
    """Split source into line-aligned chunks of at most max_chars each."""
    if len(source) <= max_chars:
        return [source]
    lines = source.splitlines(keepends=True)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        if current_len + len(line) > max_chars and current:
            chunks.append("".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append("".join(current))
    return chunks


def _http_generate(prompt: str, model: str, timeout: int | None = 600) -> str | None:
    """Synchronous HTTP call to Ollama REST API. Falls back to subprocess on connection error."""
    import json as _json
    payload = _json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    conn = None
    try:
        conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=timeout)
        conn.request("POST", "/api/generate", body=payload, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        if resp.status != 200:
            print(f"[WARN] Ollama HTTP {resp.status}", file=sys.stderr)
            return None
        data = _json.loads(resp.read().decode())
        return data.get("response", "").strip()
    except (ConnectionRefusedError, OSError):
        return call_ollama(prompt, model, timeout or 600)
    except Exception as exc:
        print(f"[WARN] Ollama HTTP error: {exc}", file=sys.stderr)
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


async def call_ollama_async(
    prompt: str, model: str = "qwen2.5-coder:7b", timeout: int | None = 600
) -> str | None:
    """Async wrapper — runs HTTP call in thread executor (truly non-blocking)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _http_generate, prompt, model, timeout)


async def analyze_files_async(
    file_paths: list,
    language: str,
    model: str,
    prompt_name: str,
    max_chars: int = 8000,
    agents: int = 1,
    no_cache: bool = False,
    cache_ttl_days: int = 7,
    timeout: int | None = 600,
) -> list[dict]:
    """Analyze multiple files concurrently — all HTTP calls in-flight simultaneously."""

    async def analyze_one(file_path: Path) -> list[dict]:
        if not no_cache and _CACHE_AVAILABLE:
            cached = _get_cached(file_path, prompt_name, max_age_days=cache_ttl_days)
            if cached is not None:
                return cached

        source = file_path.read_text(encoding="utf-8", errors="replace")
        prompt_file = _PROMPTS_DIR / f"{prompt_name}.prompt"
        try:
            template = prompt_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []

        results: list[dict] = []
        for chunk in split_into_chunks(source, max_chars):
            prompt = template.format(language=language, source=chunk)
            if agents > 1:
                responses = await asyncio.gather(
                    *[call_ollama_async(prompt, model=model, timeout=timeout) for _ in range(agents)],
                    return_exceptions=True,
                )
                seen: set[tuple] = set()
                for resp in responses:
                    if isinstance(resp, Exception) or not resp:
                        continue
                    for item in extract_json_array(resp) or []:
                        key = (
                            item.get("file", ""),
                            item.get("line", 0),
                            item.get("principle", item.get("pattern", item.get("type", ""))),
                        )
                        if key not in seen:
                            seen.add(key)
                            results.append(item)
            else:
                response = await call_ollama_async(prompt, model=model, timeout=timeout)
                if response:
                    results.extend(extract_json_array(response) or [])

        for item in results:
            item["source_file"] = str(file_path)
            item["source_file_name"] = file_path.name

        if not no_cache and _CACHE_AVAILABLE:
            _set_cached(file_path, prompt_name, results)
        return results

    tasks = [analyze_one(Path(fp)) for fp in file_paths]
    nested = await asyncio.gather(*tasks, return_exceptions=True)
    all_results: list[dict] = []
    for item in nested:
        if isinstance(item, Exception):
            print(f"[WARN] File analysis error: {item}", file=sys.stderr)
        else:
            all_results.extend(item)
    return all_results


def analyze_files_parallel(
    files: list,
    language: str,
    model: str,
    prompt_name: str,
    max_chars: int = 8000,
    agents: int = 1,
    no_cache: bool = False,
    cache_ttl_days: int = 7,
    timeout: int | None = 600,
) -> list[dict]:
    """Analyze multiple files — all HTTP calls in-flight simultaneously via asyncio."""
    return asyncio.run(analyze_files_async(
        files, language, model, prompt_name,
        max_chars=max_chars, agents=agents, no_cache=no_cache,
        cache_ttl_days=cache_ttl_days, timeout=timeout,
    ))


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

    Tries direct parse first, then scans for first '[' ... last ']' block.
    Returns None if no valid array found.
    """
    if not text:
        return None

    text = _THINK_RE.sub('', text).strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

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

    Tries direct parse first, then scans for first '{' ... last '}' block.
    Returns None if no valid object found.
    """
    if not text:
        return None

    text = _THINK_RE.sub('', text).strip()

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
