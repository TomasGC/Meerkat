#!/usr/bin/env python3
"""Golden fixture projects — run an agent end to end with recorded AI responses.

Layout, rooted at ~/.claude/fixtures/:

    projects/<project>/<source files>               scanned by the agents — sources only
    golden/<project>/expected/<agent>.json          {"agent", "project", "violations", "reconciliation"}
    golden/<project>/ai_responses/<agent>/<prompt>.json   {"<posix relpath>[#<chunk>]": "<raw model text>"}

Metadata lives outside the scanned tree so it can never change what an agent
discovers (data files used to outvote the sources in extension-based detection).

`replay` swaps the model call for a lookup in the recorded responses; everything
else — discovery, mechanical passes, prompt rendering, JSON extraction,
formatting, reconciliation, cache, orchestrator — runs for real.

A call is identified by matching the rendered prompt against each
`<prompts_dir>/<name>.prompt` template (literal text fixed, slots free) and then
the captured `{source}` slot against the text of each fixture file (or chunk).
Both must resolve to exactly one candidate, otherwise the call is an error.
"""

import importlib
import json
import re
import string
import sys
import tempfile
import threading
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import lib.ai.model_utils as _model_utils  # noqa: E402
import lib.engine.dedup as _dedup  # noqa: E402
import lib.engine.orchestrator as _orchestrator  # noqa: E402

_CLAUDE_ROOT = _SCRIPTS.parent
_MAX_CHARS = 8000  # analyze_files_async's default chunk size

# agent -> (agent directory, app name, label, max workers) — mirrors each agent's orchestrate.main()
AGENTS: dict[str, tuple[str, str, str, int]] = {
    "cca": ("clean-code-analyzer", "Clean Code Analysis", "principle", 6),
    "ssa": ("security-safety-analyzer", "Security Safety Analysis", "checker", 5),
}

_IDENTITY_FIELDS = ("file", "line", "principle")


class ReplayError(AssertionError):
    """A replayed run could not be served exactly from the recorded responses."""


def projects_root() -> Path:
    return _CLAUDE_ROOT / "fixtures" / "projects"


def golden_root() -> Path:
    return _CLAUDE_ROOT / "fixtures" / "golden"


def project_path(name: str | Path) -> Path:
    return Path(name) if isinstance(name, Path) else projects_root() / name


def golden_path(project: str | Path, golden_dir: Path | None = None) -> Path:
    """Metadata dir of a project: `golden_dir` if given, else fixtures/golden/<project name>."""
    return Path(golden_dir) if golden_dir is not None else golden_root() / project_path(project).name


def agent_scripts_dir(agent: str) -> Path:
    if agent not in AGENTS:
        raise ValueError(f"unknown agent {agent!r}; expected one of {sorted(AGENTS)}")
    return _CLAUDE_ROOT / "agents" / AGENTS[agent][0] / "scripts"


def project_names() -> list[str]:
    return sorted(p.name for p in projects_root().iterdir() if p.is_dir())


def expected_path(project: str | Path, agent: str, golden_dir: Path | None = None) -> Path:
    return golden_path(project, golden_dir) / "expected" / f"{agent}.json"


def load_expected(project: str | Path, agent: str, golden_dir: Path | None = None) -> dict:
    return json.loads(expected_path(project, agent, golden_dir).read_text(encoding="utf-8"))


def load_responses(project: str | Path, agent: str, golden_dir: Path | None = None) -> dict[str, dict[str, str]]:
    """Return {prompt name: {source key: raw response text}}."""
    folder = golden_path(project, golden_dir) / "ai_responses" / agent
    if not folder.is_dir():
        return {}
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(folder.glob("*.json"))}


def source_texts(project: str | Path) -> dict[str, str]:
    """Return {source key: text} for every fixture file — one key per chunk when a file splits."""
    root = project_path(project)
    texts: dict[str, str] = {}
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root)
        if not f.is_file():
            continue
        chunks = _model_utils.split_into_chunks(f.read_text(encoding="utf-8", errors="replace"), _MAX_CHARS)
        if len(chunks) == 1:
            texts[rel.as_posix()] = chunks[0]
        else:
            texts.update({f"{rel.as_posix()}#{i}": c for i, c in enumerate(chunks)})
    return texts


def _template_regex(template: str) -> re.Pattern:
    """Literal text matched exactly; `{source}` captured; every other slot free."""
    parts: list[str] = []
    seen_source = False
    for literal, field, _spec, _conv in string.Formatter().parse(template):
        parts.append(re.escape(literal))
        if field is None:
            continue
        if field == "source":
            parts.append("(?P=source)" if seen_source else "(?P<source>.*)")
            seen_source = True
        else:
            parts.append(".*?")
    return re.compile("".join(parts), re.DOTALL)


class Replay:
    """State of one replayed run. Use through `replay(...)`."""

    def __init__(self, project: str | Path, agent: str, prompts_dir: Path, strict_unused: bool = True,
                 golden_dir: Path | None = None):
        self.project = project_path(project)
        self.agent = agent
        self.strict_unused = strict_unused
        self.templates = {p.stem: _template_regex(p.read_text(encoding="utf-8"))
                          for p in sorted(Path(prompts_dir).glob("*.prompt"))}
        self.sources = source_texts(self.project)
        self.responses = load_responses(self.project, agent, golden_dir)
        self.used: set[tuple[str, str]] = set()
        self.errors: list[str] = []
        self.failures: list[str] = []
        self.calls = 0
        self.reconciliation: dict[str, dict[str, int]] = {}
        self._lock = threading.Lock()
        self._local = threading.local()

    # -- identification ---------------------------------------------------
    def _fail(self, message: str) -> "ReplayError":
        with self._lock:
            self.errors.append(message)
        return ReplayError(message)

    def respond(self, prompt: str) -> str:
        matches = [(name, m) for name, rx in self.templates.items() if (m := rx.fullmatch(prompt))]
        if len(matches) != 1:
            names = [n for n, _ in matches] or "none"
            raise self._fail(f"prompt matched {names} templates, expected exactly one: {prompt[:120]!r}")
        name, match = matches[0]
        source = match.groupdict().get("source")
        keys = [k for k, text in self.sources.items() if text == source]
        if len(keys) != 1:
            raise self._fail(f"prompt {name!r}: embedded source matched {keys or 'no'} fixture files")
        key = keys[0]
        text = self.responses.get(name, {}).get(key)
        if text is None:
            raise self._fail(f"no recorded response for prompt {name!r}, file {key!r} "
                             f"(add it to golden/<project>/ai_responses/{self.agent}/{name}.json)")
        items = _model_utils.extract_json_array(text) or []
        with self._lock:
            self.used.add((name, key))
            self.calls += 1
        counts = getattr(self._local, "counts", None)
        if counts is not None:
            counts["ai_items"] += len(items)
            counts["called"] = True
        return text

    def unused(self) -> list[str]:
        return [f"{name}: {key}" for name, entries in self.responses.items()
                for key in entries if (name, key) not in self.used]

    # -- seams --------------------------------------------------------------
    def _fake_call_model_async(self):
        async def fake(prompt: str, role: str = "fast", timeout: int | None = 600) -> str:
            return self.respond(prompt)
        return fake

    def _forbidden_sync_call(self, *args, **kwargs):
        raise self._fail("synchronous model call during replay — only call_model_async is replayed")

    def _wrap_run_checker(self, original):
        def run_checker(name, *args, **kwargs):
            self._local.counts = {"ai_items": 0, "dropped": 0, "called": False}
            try:
                result = original(name, *args, **kwargs)
            finally:
                counts = self._local.counts
                self._local.counts = None
            principle = result.get("principle", name)
            with self._lock:
                if not result.get("success", False):
                    self.failures.append(f"{principle}: {result.get('error', 'failed')}")
                if counts["called"]:
                    self.reconciliation[principle] = {"ai_items": counts["ai_items"],
                                                      "dropped": counts["dropped"]}
            return result
        return run_checker

    def _wrap_drop(self, original):
        def drop_near_duplicates(ai_violations, mechanical_violations, *args, **kwargs):
            kept = original(ai_violations, mechanical_violations, *args, **kwargs)
            counts = getattr(self._local, "counts", None)
            if counts is not None:
                counts["dropped"] += len(ai_violations) - len(kept)
            return kept
        return drop_near_duplicates


def _patch_bindings(stack: ExitStack, name: str, original, replacement) -> None:
    """Patch every loaded module attribute bound to `original` — `from x import f` copies included."""
    for module in list(sys.modules.values()):
        if module is not None and getattr(module, name, None) is original:
            stack.enter_context(mock.patch.object(module, name, replacement))


class replay:  # noqa: N801 — used as a context manager, reads like a function
    """Serve every model call of the run from the recorded responses.

    Patches `lib.ai.model_utils.call_model_async` (and every module binding of
    it), forces the server availability probe to succeed, disables model_utils'
    own per-file cache, and forbids synchronous model calls. Module bindings of
    `drop_near_duplicates` are wrapped to count reconciliation drops — import the
    checker modules before entering so their bindings are seen.

    On exit raises ReplayError for any unmatched call, missing response, or —
    when `strict_unused` — any recorded response the run never asked for.
    """

    def __init__(self, project: str | Path, agent: str, prompts_dir: Path, *, strict_unused: bool = True,
                 golden_dir: Path | None = None):
        self.state = Replay(project, agent, prompts_dir, strict_unused, golden_dir)
        self._stack = ExitStack()

    def __enter__(self) -> Replay:
        s, stack = self.state, self._stack
        _patch_bindings(stack, "call_model_async", _model_utils.call_model_async, s._fake_call_model_async())
        stack.enter_context(mock.patch.object(_model_utils, "_http_generate", s._forbidden_sync_call))
        _patch_bindings(stack, "call_model", _model_utils.call_model, s._forbidden_sync_call)
        stack.enter_context(mock.patch.object(_model_utils, "_model_listed", lambda model: True))
        stack.enter_context(mock.patch.dict(_model_utils._AVAILABILITY_CACHE, clear=True))
        stack.enter_context(mock.patch.object(_model_utils, "_CACHE_AVAILABLE", False))
        stack.enter_context(mock.patch.object(_orchestrator, "_run_checker",
                                              s._wrap_run_checker(_orchestrator._run_checker)))
        _patch_bindings(stack, "drop_near_duplicates", _dedup.drop_near_duplicates,
                        s._wrap_drop(_dedup.drop_near_duplicates))
        return s

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._stack.close()
        if exc_type is not None:
            return False
        s = self.state
        problems = list(s.errors)
        if s.strict_unused:
            problems += [f"recorded response never used (stale fixture): {u}" for u in s.unused()]
        if problems:
            raise ReplayError(f"{s.project.name}/{s.agent}:\n  " + "\n  ".join(problems))
        return False


def _bind_agent(agent: str) -> Path:
    """Put the agent's scripts dir first on sys.path; refuse if another agent's packages are loaded."""
    scripts = agent_scripts_dir(agent)
    for name in ("common", "orchestrate", "checkers"):
        mod = sys.modules.get(name)
        origin = getattr(mod, "__file__", None) or next(iter(getattr(mod, "__path__", []) or []), None)
        if mod is not None and origin and not Path(origin).resolve().is_relative_to(scripts.resolve()):
            raise RuntimeError(f"`{name}` already imported from {origin}; run one agent per process")
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    return scripts


def run_agent(
    project: str | Path,
    agent: str,
    *,
    cache_dir: Path,
    extra_args: tuple[str, ...] = (),
    strict_unused: bool = True,
) -> dict:
    """Run the agent's own checker registry over a fixture project under replay.

    Returns the orchestrator's JSON report plus `reconciliation` (per principle:
    AI items replayed, items dropped as near-duplicates) and `ai_calls`.
    Raises ReplayError if any checker reported failure.
    """
    scripts = _bind_agent(agent)
    orchestrate = importlib.import_module("orchestrate")
    for module_path in orchestrate.CHECKERS.values():
        importlib.import_module(module_path)
    _dir, app_name, label, workers = AGENTS[agent]
    root = project_path(project)

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.json"
        argv = ["--path", str(root), "--full", "--format", "json", "--output", str(out),
                "--no-stream", *extra_args]
        with replay(root, agent, scripts / "prompts" / "local", strict_unused=strict_unused) as state:
            _orchestrator.main(registry=orchestrate.CHECKERS, app_name=app_name, label_singular=label,
                               cache_dir=Path(cache_dir), max_workers=workers, argv=argv)
        report = json.loads(out.read_text(encoding="utf-8"))

    if state.failures:
        raise ReplayError(f"{root.name}/{agent}: checkers failed: " + "; ".join(sorted(state.failures)))
    report["reconciliation"] = dict(sorted(state.reconciliation.items()))
    report["ai_calls"] = state.calls
    return report


def _posix_rel(file: str, root: Path | None) -> str:
    p = Path(file)
    if root is not None and p.is_absolute():
        try:
            p = p.resolve().relative_to(Path(root).resolve())
        except ValueError:
            pass
    return p.as_posix() if not p.is_absolute() else str(p).replace("\\", "/")


def normalise(violations: list[dict], root: Path | None = None) -> list[dict]:
    """Copy violations with `file` as a posix path relative to `root`, sorted deterministically."""
    out = [{**v, "file": _posix_rel(str(v.get("file", "")), root)} for v in violations]
    return sorted(out, key=lambda v: (v["file"], int(v.get("line", 0)),
                                      str(v.get("principle", "")), str(v.get("message", ""))))


def _identity(v: dict) -> tuple:
    return tuple(v.get(k) for k in _IDENTITY_FIELDS)


def _label(key: tuple) -> str:
    file, line, principle = key
    return f"{file}:{line} [{principle}]"


def compare(actual: list[dict], expected: list[dict]) -> list[str]:
    """Readable diff: missing, unexpected, and changed records (identity = file, line, principle)."""
    act = {_identity(v): v for v in actual}
    exp = {_identity(v): v for v in expected}
    diff: list[str] = []
    for key in sorted(exp.keys() - act.keys(), key=str):
        diff.append(f"missing    {_label(key)}: {exp[key].get('message', '')}")
    for key in sorted(act.keys() - exp.keys(), key=str):
        diff.append(f"unexpected {_label(key)}: {act[key].get('message', '')}")
    for key in sorted(exp.keys() & act.keys(), key=str):
        for field in sorted(set(exp[key]) | set(act[key])):
            if exp[key].get(field) != act[key].get(field):
                diff.append(f"changed    {_label(key)} {field}: "
                            f"expected {exp[key].get(field)!r}, got {act[key].get(field)!r}")
    return diff


def expected_record(project: str | Path, agent: str, report: dict) -> dict:
    root = project_path(project)
    return {
        "agent": agent,
        "project": root.name,
        "violations": normalise(report["violations"], root),
        "reconciliation": report["reconciliation"],
    }
