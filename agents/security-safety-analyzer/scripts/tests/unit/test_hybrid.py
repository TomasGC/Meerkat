"""Unit tests for common/hybrid.py — the shared mechanical-then-AI driver."""
import re
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ssa.hybrid import run_hybrid
from lib.engine.hybrid import resolve_language, scan_patterns, select_files

_RULES = {
    "python": [(re.compile(r'\bdanger\b'), "Danger called", "high", "Stop calling danger")],
    "*": [(re.compile(r'\bTODO\b'), "Leftover marker", "low", "Resolve or track it")],
}


def _make_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


class TestResolveLanguage:
    def test_explicit_language_wins(self, tmp_path):
        assert resolve_language(tmp_path / "a.py", "python") == "python"

    def test_mixed_resolved_by_extension(self, tmp_path):
        assert resolve_language(tmp_path / "Service.cs", "mixed") == "csharp"

    def test_unknown_extension_returns_unknown(self, tmp_path):
        assert resolve_language(tmp_path / "notes.txt", "mixed") == "unknown"

    def test_dockerfile_recognised_by_name(self, tmp_path):
        assert resolve_language(tmp_path / "Dockerfile", "mixed") == "dockerfile"

    def test_dockerfile_variant_recognised(self, tmp_path):
        assert resolve_language(tmp_path / "Dockerfile.prod", "python") == "dockerfile"


class TestSelectFiles:
    def test_explicit_files_filtered_by_extension(self, tmp_path):
        keep = _make_file(tmp_path, "a.py", "x = 1\n")
        drop = _make_file(tmp_path, "notes.txt", "hello\n")
        assert select_files(tmp_path, "python", [keep, drop]) == [keep]

    def test_discovery_skips_test_files(self, tmp_path):
        _make_file(tmp_path, "service.py", "x = 1\n")
        _make_file(tmp_path, "test_service.py", "x = 1\n")
        found = [f.name for f in select_files(tmp_path, "python", None)]
        assert found == ["service.py"]

    def test_empty_directory_returns_empty(self, tmp_path):
        assert select_files(tmp_path, "python", None) == []


class TestScanPatterns:
    def test_language_rule_matches(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        violations = scan_patterns(f, tmp_path, "python", "Test", _RULES)
        assert [v["message"] for v in violations] == ["Danger called"]

    def test_universal_rule_applies_to_every_language(self, tmp_path):
        f = _make_file(tmp_path, "Service.cs", "// TODO later\n")
        violations = scan_patterns(f, tmp_path, "csharp", "Test", _RULES)
        assert [v["message"] for v in violations] == ["Leftover marker"]

    def test_line_numbers_are_one_based(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\ndanger()\n")
        violations = scan_patterns(f, tmp_path, "python", "Test", _RULES)
        assert violations[0]["line"] == 2

    def test_paths_are_relative_to_root(self, tmp_path):
        nested = tmp_path / "src"
        nested.mkdir()
        f = nested / "a.py"
        f.write_text("danger()\n")
        violations = scan_patterns(f, tmp_path, "python", "Test", _RULES)
        assert violations[0]["file"] == str(Path("src") / "a.py")

    def test_language_without_rules_returns_empty(self, tmp_path):
        empty_rules = {"python": _RULES["python"]}
        f = _make_file(tmp_path, "main.go", "package main\n")
        assert scan_patterns(f, tmp_path, "go", "Test", empty_rules) == []

    def test_missing_file_returns_empty(self, tmp_path):
        assert scan_patterns(tmp_path / "gone.py", tmp_path, "python", "Test", _RULES) == []

    def test_violation_carries_principle_and_suggestion(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        violation = scan_patterns(f, tmp_path, "python", "Test", _RULES)[0]
        assert violation["principle"] == "Test"
        assert violation["severity"] == "high"
        assert violation["suggestion"] == "Stop calling danger"


class TestRunHybrid:
    def test_returns_checker_contract(self, tmp_path):
        with patch("lib.engine.hybrid.check_server_available", return_value=False):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES)
        assert result["principle"] == "Test"
        assert result["success"] is True
        assert result["violations"] == []
        assert result["files_analyzed"] == 0
        assert "duration_ms" in result

    def test_mechanical_findings_reported_without_server(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        with patch("lib.engine.hybrid.check_server_available", return_value=False):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[f])
        assert [v["message"] for v in result["violations"]] == ["Danger called"]

    def test_ai_findings_appended(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        fake_item = {"source_file": str(f), "issue_type": "SOMETHING", "line": 1,
                     "severity": "low", "description": "detail", "fix": "do this"}
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[f])
        assert result["violations"][0]["message"] == "[SOMETHING]: detail"
        assert result["violations"][0]["suggestion"] == "do this"

    def test_ai_type_key_is_configurable(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        fake_item = {"source_file": str(f), "leak_type": "UNCLOSED_HANDLE", "line": 1,
                     "description": "detail", "fix": ""}
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES,
                                files=[f], ai_type_key="leak_type")
        assert result["violations"][0]["message"].startswith("[UNCLOSED_HANDLE]")

    def test_default_severity_applied_when_absent(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        fake_item = {"source_file": str(f), "issue_type": "X", "line": 1, "description": "d", "fix": ""}
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES,
                                files=[f], default_severity="high")
        assert result["violations"][0]["severity"] == "high"

    def test_ai_finding_near_mechanical_one_dropped(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        fake_item = {"source_file": str(f), "issue_type": "DUP", "line": 2,
                     "description": "same thing", "fix": ""}
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[f])
        assert [v["message"] for v in result["violations"]] == ["Danger called"]

    def test_known_findings_slot_carries_mechanical_messages(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        captured = {}

        def fake_analyze(files, *args, **kwargs):
            captured["extra_slots"] = kwargs.get("extra_slots")
            return []

        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", side_effect=fake_analyze):
            run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[f])
        assert "Danger called" in captured["extra_slots"][f]["known_findings"]

    def test_ai_not_called_when_no_files(self, tmp_path):
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel") as analyze:
            run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[])
        analyze.assert_not_called()


class TestRunHybridMechanicalFn:
    def test_mechanical_fn_replaces_scan_patterns(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        def mech(path, files):
            return [{"principle": "Test", "file": "a.py", "line": 1,
                     "severity": "high", "message": "custom", "suggestion": ""}], 1
        with patch("lib.engine.hybrid.check_server_available", return_value=False):
            result = run_hybrid(tmp_path, "python", "Test", None, {}, mechanical_fn=mech)
        assert [v["message"] for v in result["violations"]] == ["custom"]
        assert result["files_analyzed"] == 1

    def test_mechanical_fn_short_circuits_on_dict_return(self, tmp_path):
        def mech(path, files):
            return {"success": False, "error": "boom", "violations": [], "files_analyzed": 0}
        result = run_hybrid(tmp_path, "python", "Test", "prompt", {}, mechanical_fn=mech)
        assert result["success"] is False
        assert result["error"] == "boom"

    def test_mechanical_fn_findings_feed_ai_dedup(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        def mech(path, files):
            return [{"principle": "Test", "file": "a.py", "line": 1,
                     "severity": "high", "message": "mechanical", "suggestion": ""}], 1
        fake_item = {"source_file": str(f), "issue_type": "DUP", "line": 2,
                     "description": "same area", "fix": ""}
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", {}, files=[f], mechanical_fn=mech)
        assert [v["message"] for v in result["violations"]] == ["mechanical"]

    def test_prompt_none_skips_ai_pass_entirely(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        with patch("lib.engine.hybrid.analyze_files_parallel") as analyze:
            run_hybrid(tmp_path, "python", "Test", None, {}, files=[f])
        analyze.assert_not_called()

    def test_format_ai_violation_overrides_default_shape(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        fake_item = {"source_file": str(f), "principle": "SRP", "line": 1, "violation": "too big"}
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(
                tmp_path, "python", "SOLID", "prompt", {}, files=[f],
                format_ai_violation=lambda item, rel: {
                    "principle": f"SOLID:{item.get('principle')}",
                    "file": rel, "line": item.get("line", 0),
                    "severity": "medium", "message": item.get("violation", ""), "suggestion": "",
                },
            )
        assert result["violations"][0]["principle"] == "SOLID:SRP"


def _ai_item(f: Path, line: int = 1, description: str = "detail") -> dict:
    return {"source_file": str(f), "source_file_name": f.name, "issue_type": "X",
            "line": line, "severity": "low", "description": description, "fix": ""}


def _fake_analyze(calls: list, items_for: dict):
    """analyze_files_parallel stand-in: records the files it was given, returns items_for[name]."""
    def fake(files, *args, **kwargs):
        calls.append(list(files))
        out = []
        for f in files:
            out.extend(_ai_item(f, **spec) for spec in items_for.get(f.name, []))
        return out
    return fake


class TestRunHybridCache:
    def _run(self, tmp_path, files, cache_dir, **kwargs):
        return run_hybrid(tmp_path, "python", "Test", "prompt", {}, files=files,
                          cache_dir=cache_dir, **kwargs)

    def test_hit_skips_ai_call_for_that_file(self, tmp_path):
        cached = _make_file(tmp_path, "a.py", "x = 1\n")
        fresh = _make_file(tmp_path, "b.py", "y = 2\n")
        cache_dir = tmp_path / ".cache"
        calls: list = []
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel",
                   side_effect=_fake_analyze(calls, {"a.py": [{"line": 1}]})):
            self._run(tmp_path, [cached], cache_dir)
            calls.clear()
            self._run(tmp_path, [cached, fresh], cache_dir)
        assert calls == [[fresh]]

    def test_miss_writes_cache_and_second_run_is_full_hit(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        cache_dir = tmp_path / ".cache"
        calls: list = []
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel",
                   side_effect=_fake_analyze(calls, {"a.py": [{"line": 5, "description": "d"}]})):
            first = self._run(tmp_path, [f], cache_dir)
            second = self._run(tmp_path, [f], cache_dir)
        assert len(calls) == 1
        assert list(cache_dir.glob("*.json"))
        assert second["violations"] == first["violations"]
        assert second["violations"][0]["message"] == "[X]: d"

    def test_no_cache_neither_reads_nor_writes(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        cache_dir = tmp_path / ".cache"
        calls: list = []
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel",
                   side_effect=_fake_analyze(calls, {"a.py": [{"line": 1}]})):
            self._run(tmp_path, [f], cache_dir)          # populate the cache
            calls.clear()
            with patch("lib.engine.hybrid.get_cached") as get, \
                 patch("lib.engine.hybrid.set_cached") as put:
                result = self._run(tmp_path, [f], cache_dir, no_cache=True)
        assert calls == [[f]]
        get.assert_not_called()
        put.assert_not_called()
        assert "cache_hits" not in result

    def test_file_with_zero_items_cached_as_empty_list(self, tmp_path):
        f = _make_file(tmp_path, "clean.py", "x = 1\n")
        cache_dir = tmp_path / ".cache"
        calls: list = []
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel",
                   side_effect=_fake_analyze(calls, {})):
            self._run(tmp_path, [f], cache_dir)
            second = self._run(tmp_path, [f], cache_dir)
        entries = list(cache_dir.glob("*.json"))
        assert len(entries) == 1
        assert entries[0].read_text(encoding="utf-8") == "[]"
        assert len(calls) == 1
        assert second["cache_hits"] == 1

    def test_hit_reattaches_current_path(self, tmp_path):
        original = _make_file(tmp_path, "a.py", "x = 1\n")
        cache_dir = tmp_path / ".cache"
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel",
                   side_effect=_fake_analyze([], {"a.py": [{"line": 1}]})):
            self._run(tmp_path, [original], cache_dir)
        stored = next(cache_dir.glob("*.json")).read_text(encoding="utf-8")
        assert "source_file" not in stored

        moved_dir = tmp_path / "moved"
        moved_dir.mkdir()
        moved = moved_dir / "renamed.py"
        moved.write_text(original.read_text())
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel") as analyze:
            result = self._run(tmp_path, [moved], cache_dir)
        analyze.assert_not_called()
        assert [v["file"] for v in result["violations"]] == [str(Path("moved") / "renamed.py")]

    def test_cache_dir_none_never_touches_engine_cache(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", return_value=[_ai_item(f)]), \
             patch("lib.engine.hybrid.get_cached") as get, \
             patch("lib.engine.hybrid.set_cached") as put:
            result = run_hybrid(tmp_path, "python", "Test", "prompt", {}, files=[f])
        get.assert_not_called()
        put.assert_not_called()
        assert "cache_hits" not in result and "cache_total" not in result

    def test_cache_counters(self, tmp_path):
        a = _make_file(tmp_path, "a.py", "x = 1\n")
        b = _make_file(tmp_path, "b.py", "y = 2\n")
        c = _make_file(tmp_path, "c.py", "z = 3\n")
        cache_dir = tmp_path / ".cache"
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel",
                   side_effect=_fake_analyze([], {})):
            first = self._run(tmp_path, [a, b], cache_dir)
            second = self._run(tmp_path, [a, b, c], cache_dir)
        assert (first["cache_hits"], first["cache_total"]) == (0, 2)
        assert (second["cache_hits"], second["cache_total"]) == (2, 3)

    def test_failed_file_not_cached_and_retried_next_run(self, tmp_path):
        """A file the AI call failed on is never cached; a clean `[]` file in the same run still is."""
        broken = _make_file(tmp_path, "broken.py", "x = 1\n")
        clean = _make_file(tmp_path, "clean.py", "y = 2\n")
        cache_dir = tmp_path / ".cache"
        calls: list = []
        base = _fake_analyze(calls, {})

        def fails_on_broken(files, *args, **kwargs):
            out = base(files, *args, **kwargs)
            if broken in files:
                kwargs["failed"].add(broken)
            return out

        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", side_effect=fails_on_broken):
            first = self._run(tmp_path, [broken, clean], cache_dir)
            second = self._run(tmp_path, [broken, clean], cache_dir)

        assert calls == [[broken, clean], [broken]]
        assert [e.read_text(encoding="utf-8") for e in cache_dir.glob("*.json")] == ["[]"]
        assert (first["cache_hits"], second["cache_hits"]) == (0, 1)

    def test_failed_set_passed_only_when_caching(self, tmp_path):
        """With cache_dir=None, analyze_files_parallel is called exactly as before — no `failed` kwarg."""
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel", return_value=[]) as analyze:
            run_hybrid(tmp_path, "python", "Test", "prompt", {}, files=[f])
        assert "failed" not in analyze.call_args.kwargs

    def test_key_separates_roles(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        cache_dir = tmp_path / ".cache"
        calls: list = []
        with patch("lib.engine.hybrid.check_server_available", return_value=True), \
             patch("lib.engine.hybrid.analyze_files_parallel",
                   side_effect=_fake_analyze(calls, {})):
            self._run(tmp_path, [f], cache_dir, role="analyzer")
            self._run(tmp_path, [f], cache_dir, role="fast")
        assert len(calls) == 2


def test_shim_hands_ssa_model_cache_to_run_hybrid(tmp_path):
    """SSA's checkers take no cache_dir: their only AI cache is the one this shim passes (#21)."""
    from unittest.mock import patch as _patch

    import ssa.hybrid as shim
    import ssa.model_utils as ssa_mu

    with _patch("ssa.hybrid._run_hybrid", return_value={}) as engine:
        shim.run_hybrid(tmp_path, "python", "P", None, {})
    assert engine.call_args.kwargs["model_cache"] is ssa_mu.CACHE


def test_model_utils_wrappers_pass_the_ssa_cache(tmp_path):
    from unittest.mock import patch as _patch

    import ssa.model_utils as ssa_mu

    with _patch.object(ssa_mu._lib, "analyze_files_parallel", return_value=[]) as lib_call:
        ssa_mu.analyze_files_parallel([], "python")
    assert lib_call.call_args.kwargs["cache"] is ssa_mu.CACHE
