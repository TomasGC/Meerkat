#!/usr/bin/env python3
"""Shared Ollama utilities — call_ollama, JSON extraction, health check, cache, multi-run, async HTTP."""

import asyncio
import http.client
import json
import json as _json
import re as _re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_THINK_RE = _re.compile(r'<think>.*?</think>', _re.DOTALL)

OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "ollama"
CLAUDE_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "claude"

# Lazy cache import — safe when common/ is on sys.path
try:
    from common.cache import get_cached as _get_cached, set_cached as _set_cached
    _CACHE_AVAILABLE = True
except ImportError:
    _CACHE_AVAILABLE = False
    def _get_cached(file_path, checker, **kwargs): return None  # type: ignore[misc]
    def _set_cached(file_path, checker, violations): pass  # type: ignore[misc]

# Cache availability per model — avoids 6 concurrent `ollama list` subprocesses at startup
_AVAILABILITY_CACHE: dict[str, bool] = {}


def _split_into_chunks(source: str, max_chars: int) -> list[str]:
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


def _http_generate(prompt: str, model: str, timeout: int | None = 600) -> str | None:
    """Synchronous HTTP call to Ollama REST API. Falls back to subprocess on connection error."""
    payload = _json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
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
        return call_ollama(prompt, model, timeout)
    except Exception as exc:
        print(f"[WARN] Ollama HTTP error: {exc}", file=sys.stderr)
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


async def call_ollama_async(prompt: str, model: str = "qwen2.5-coder:7b", timeout: int | None = 600) -> str | None:
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
    """Analyze multiple files concurrently — all HTTP calls in-flight, no per-file timeout."""

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
        for chunk in _split_into_chunks(source, max_chars):
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
                        key = (item.get("file", ""), item.get("line", 0), item.get("principle", item.get("pattern", item.get("type", ""))))
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
            encoding="utf-8",
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


def get_claude_fallback_prompt(name: str, **kwargs) -> str | None:
    """Return formatted Claude fallback prompt when Ollama unavailable."""
    prompt_file = CLAUDE_PROMPTS_DIR / f"{name}.prompt"
    try:
        return prompt_file.read_text(encoding="utf-8").format(**kwargs)
    except FileNotFoundError:
        return None
    except KeyError:
        return prompt_file.read_text(encoding="utf-8")


def call_ollama_multi(prompt: str, model: str = "qwen2.5-coder:7b", n: int = 1, timeout: int = 120) -> list[dict]:
    """Run N parallel Ollama calls on same prompt, dedup results by (file, line, principle/pattern/type)."""
    if n <= 1:
        raw = call_ollama(prompt, model, timeout)
        return extract_json_array(raw) or []

    with ThreadPoolExecutor(max_workers=n) as ex:
        futures = [ex.submit(call_ollama, prompt, model, timeout) for _ in range(n)]
        responses = [f.result() for f in futures]

    seen: set[tuple] = set()
    merged: list[dict] = []
    for resp in responses:
        items = extract_json_array(resp) or []
        for item in items:
            key = (
                item.get("file", ""),
                item.get("line", 0),
                item.get("principle", item.get("pattern", item.get("type", ""))),
            )
            if key not in seen:
                seen.add(key)
                merged.append(item)
    return merged


def analyze_file_with_ollama(
    file_path: Path,
    language: str,
    model: str,
    prompt_name: str,
    max_chars: int = 8000,
    agents: int = 1,
    no_cache: bool = False,
    cache_ttl_days: int = 7,
) -> list[dict]:
    """Read source file, call Ollama (with optional cache + multi-run), annotate results."""
    if not no_cache and _CACHE_AVAILABLE:
        cached = _get_cached(file_path, prompt_name, max_age_days=cache_ttl_days)
        if cached is not None:
            return cached

    source = file_path.read_text(encoding="utf-8", errors="replace")

    prompt_file = _PROMPTS_DIR / f"{prompt_name}.prompt"
    try:
        template = prompt_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[ERROR] Prompt file not found: {prompt_file}", file=sys.stderr)
        return []

    results: list[dict] = []
    for chunk in _split_into_chunks(source, max_chars):
        prompt = template.format(language=language, source=chunk)
        if agents > 1:
            results.extend(call_ollama_multi(prompt, model=model, n=agents))
        else:
            raw = call_ollama(prompt, model=model)
            results.extend(extract_json_array(raw) or [])

    if not results:
        print(f"[WARN] Could not parse JSON from Ollama for {file_path.name}", file=sys.stderr)
    else:
        for item in results:
            item["source_file"] = str(file_path)
            item["source_file_name"] = file_path.name

    if not no_cache and _CACHE_AVAILABLE:
        _set_cached(file_path, prompt_name, results)

    return results


def analyze_files_parallel(
    files: list[Path],
    language: str,
    model: str,
    prompt_name: str,
    max_workers: int = 3,  # kept for backward compat, unused
    max_chars: int = 8000,
    agents: int = 1,
    no_cache: bool = False,
    cache_ttl_days: int = 7,
    timeout: int | None = 600,
) -> list[dict]:
    """Analyze multiple files with Ollama — all HTTP calls in-flight simultaneously via asyncio."""
    return asyncio.run(analyze_files_async(
        files, language, model, prompt_name,
        max_chars=max_chars, agents=agents, no_cache=no_cache,
        cache_ttl_days=cache_ttl_days, timeout=timeout,
    ))


def extract_json_array(text: str) -> list | None:
    """
    Extract a JSON array from an Ollama response that may have surrounding prose.

    Tries direct parse first, then scans for first '[' … last ']' block.
    Returns None if no valid array found.
    """
    if not text:
        return None

    # Strip qwen3 thinking tokens before scanning for JSON boundaries
    text = _THINK_RE.sub('', text).strip()

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
