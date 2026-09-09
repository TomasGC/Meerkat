#!/usr/bin/env python3
"""Generic local AI client — provider-agnostic, role-based model routing.

All model names are resolved from configs/local_models_config.json via model_config.py.
No model name strings appear in this file.
"""

import asyncio
import http.client
import json
import json as _json
import re as _re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# model_config lives in the same scripts/ directory
sys.path.insert(0, str(Path(__file__).parent))
from model_config import get_model, _load as _load_config

_THINK_RE = _re.compile(r'<think>.*?</think>', _re.DOTALL)


def _parse_local_server() -> tuple[str, int]:
    """Parse host and port from local.base_url in config."""
    cfg = _load_config().get("local", {})
    base_url = cfg.get("base_url", "http://localhost:11434")
    host_part = base_url.split("://")[-1]
    if ":" in host_part:
        host, port_str = host_part.rsplit(":", 1)
        return host, int(port_str)
    return host_part, 11434


LOCAL_AI_HOST, LOCAL_AI_PORT = _parse_local_server()

# Availability cache — avoids repeated subprocess calls
_AVAILABILITY_CACHE: dict[str, bool] = {}

# Optional per-file result cache — resolved at call time based on sys.path
def _get_cached(file_path, checker, **kwargs): return None  # noqa: E704
def _set_cached(file_path, checker, results): pass  # noqa: E704
_CACHE_AVAILABLE = False

try:
    from common.cache import get_model_cached as _get_cached, set_model_cached as _set_cached  # type: ignore[no-redef]
    _CACHE_AVAILABLE = True
except ImportError:
    try:
        from common.cache import get_cached as _get_cached, set_cached as _set_cached  # type: ignore[no-redef]
        _CACHE_AVAILABLE = True
    except ImportError:
        pass


def check_server_available(role: str = "fast") -> bool:
    """Return True if local AI server is reachable and the model for role is available."""
    model = get_model(role)
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


def _http_generate(prompt: str, role: str, timeout: int | None = 600) -> str | None:
    """Synchronous HTTP call to local AI REST API. Falls back to subprocess on connection error."""
    model = get_model(role)
    payload = _json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    conn = None
    try:
        conn = http.client.HTTPConnection(LOCAL_AI_HOST, LOCAL_AI_PORT, timeout=timeout)
        conn.request("POST", "/api/generate", body=payload, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        if resp.status != 200:
            print(f"[WARN] local AI HTTP {resp.status}", file=sys.stderr)
            return None
        data = _json.loads(resp.read().decode())
        raw = data.get("response", "").strip()
        return _THINK_RE.sub("", raw).strip()
    except (ConnectionRefusedError, OSError):
        return call_model(prompt, role=role, timeout=timeout or 600)
    except Exception as exc:
        print(f"[WARN] local AI HTTP error: {exc}", file=sys.stderr)
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def call_model(prompt: str, role: str = "fast", timeout: int = 120) -> str | None:
    """Call local AI via CLI. Returns response text or None on failure."""
    model = get_model(role)
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
            print(f"[WARN] local AI non-zero exit: {result.stderr[:300]}", file=sys.stderr)
            return None
        raw = result.stdout.strip()
        return _THINK_RE.sub("", raw).strip()
    except FileNotFoundError:
        print(
            "[ERROR] Local AI CLI not found in PATH.\n"
            "  Install: https://ollama.ai\n"
            f"  Then run: ollama pull {model}",
            file=sys.stderr,
        )
        return None
    except subprocess.TimeoutExpired:
        print(f"[WARN] local AI timed out after {timeout}s", file=sys.stderr)
        return None


async def call_model_async(prompt: str, role: str = "fast", timeout: int | None = 600) -> str | None:
    """Async wrapper — runs HTTP call in thread executor (truly non-blocking)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _http_generate, prompt, role, timeout)


def call_model_multi(prompt: str, role: str = "fast", n: int = 1, timeout: int = 120) -> list[dict]:
    """Run N parallel local AI calls on same prompt, dedup results by (file, line, principle/pattern/type)."""
    if n <= 1:
        raw = call_model(prompt, role=role, timeout=timeout)
        return extract_json_array(raw) or []

    with ThreadPoolExecutor(max_workers=n) as ex:
        futures = [ex.submit(call_model, prompt, role, timeout) for _ in range(n)]
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


def run_prompt(name: str, prompts_dir: Path, role: str = "fast", timeout: int = 120, **kwargs) -> str | None:
    """Load a .prompt file from prompts_dir, format with kwargs, call local AI."""
    prompt_file = prompts_dir / f"{name}.prompt"
    try:
        template = prompt_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[ERROR] Prompt file not found: {prompt_file}", file=sys.stderr)
        return None
    return call_model(template.format(**kwargs), role=role, timeout=timeout)


def analyze_file_with_model(
    file_path: Path,
    language: str,
    role: str = "analyzer",
    prompt_name: str = "analyze",
    prompts_dir: Path | None = None,
    max_chars: int = 8000,
    agents: int = 1,
    no_cache: bool = False,
    cache_ttl_days: int = 7,
) -> list[dict]:
    """Read source file, call local AI (with optional cache + multi-run), annotate results."""
    if prompts_dir is None:
        raise ValueError("prompts_dir is required")

    if not no_cache and _CACHE_AVAILABLE:
        cached = _get_cached(file_path, prompt_name, max_age_days=cache_ttl_days)
        if cached is not None:
            return cached

    source = file_path.read_text(encoding="utf-8", errors="replace")
    prompt_file = prompts_dir / f"{prompt_name}.prompt"
    try:
        template = prompt_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[ERROR] Prompt file not found: {prompt_file}", file=sys.stderr)
        return []

    results: list[dict] = []
    for chunk in split_into_chunks(source, max_chars):
        prompt = template.format(language=language, source=chunk)
        if agents > 1:
            results.extend(call_model_multi(prompt, role=role, n=agents))
        else:
            raw = call_model(prompt, role=role)
            results.extend(extract_json_array(raw) or [])

    if results:
        for item in results:
            item["source_file"] = str(file_path)
            item["source_file_name"] = file_path.name
    else:
        print(f"[WARN] No results from local AI for {file_path.name}", file=sys.stderr)

    if not no_cache and _CACHE_AVAILABLE and results:
        _set_cached(file_path, prompt_name, results)

    return results


async def analyze_files_async(
    file_paths: list,
    language: str,
    role: str = "analyzer",
    prompt_name: str = "analyze",
    prompts_dir: Path | None = None,
    max_chars: int = 8000,
    agents: int = 1,
    no_cache: bool = False,
    cache_ttl_days: int = 7,
    timeout: int | None = 600,
    extra_slots: dict | None = None,
) -> list[dict]:
    """Analyze multiple files concurrently — all HTTP calls in-flight simultaneously.

    extra_slots maps a file Path to additional prompt format slots for that file.
    """
    if prompts_dir is None:
        raise ValueError("prompts_dir is required")

    prompt_file = prompts_dir / f"{prompt_name}.prompt"
    try:
        template = prompt_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[ERROR] Prompt file not found: {prompt_file}", file=sys.stderr)
        return []

    async def analyze_one(file_path: Path) -> list[dict]:
        if not no_cache and _CACHE_AVAILABLE:
            cached = _get_cached(file_path, prompt_name, max_age_days=cache_ttl_days)
            if cached is not None:
                return cached

        source = file_path.read_text(encoding="utf-8", errors="replace")
        results: list[dict] = []
        file_slots = extra_slots.get(file_path, {}) if extra_slots else {}
        for chunk in split_into_chunks(source, max_chars):
            prompt = template.format(language=language, source=chunk, **file_slots)
            if agents > 1:
                responses = await asyncio.gather(
                    *[call_model_async(prompt, role=role, timeout=timeout) for _ in range(agents)],
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
                response = await call_model_async(prompt, role=role, timeout=timeout)
                if response:
                    results.extend(extract_json_array(response) or [])

        for item in results:
            item["source_file"] = str(file_path)
            item["source_file_name"] = file_path.name

        if not no_cache and _CACHE_AVAILABLE and results:
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
    files: list[Path],
    language: str,
    role: str = "analyzer",
    prompt_name: str = "analyze",
    prompts_dir: Path | None = None,
    max_chars: int = 8000,
    agents: int = 1,
    no_cache: bool = False,
    cache_ttl_days: int = 7,
    timeout: int | None = 600,
    extra_slots: dict | None = None,
) -> list[dict]:
    """Analyze multiple files with local AI — all HTTP calls in-flight simultaneously via asyncio."""
    return asyncio.run(analyze_files_async(
        files, language, role, prompt_name, prompts_dir,
        max_chars=max_chars, agents=agents, no_cache=no_cache,
        cache_ttl_days=cache_ttl_days, timeout=timeout, extra_slots=extra_slots,
    ))


def extract_json_array(text: str) -> list | None:
    """Extract a JSON array from a local AI response that may have surrounding prose."""
    if not text:
        return None
    text = _THINK_RE.sub("", text).strip()
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
        data = json.loads(text[start:end + 1])
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return None


def extract_json_object(text: str) -> dict | None:
    """Extract a JSON object from a local AI response."""
    if not text:
        return None
    text = _THINK_RE.sub("", text).strip()
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
        data = json.loads(text[start:end + 1])
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return None
