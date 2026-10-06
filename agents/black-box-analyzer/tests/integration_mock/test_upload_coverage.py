#!/usr/bin/env python3
"""Tests for upload_coverage.py — int_mock tests (shutil.which patched)"""

import json
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from upload_coverage import _find_codecov, _merge_lcov
from upload_coverage import main as upload_main
from upload_coverage import upload_with_codecov


def test_find_codecov_returns_none_when_absent():
    with patch("shutil.which", return_value=None):
        assert _find_codecov() is None


def test_find_codecov_returns_path_when_present():
    with patch("shutil.which", side_effect=lambda name: "/usr/bin/codecov" if name == "codecov" else None):
        assert _find_codecov() == "/usr/bin/codecov"


def test_merge_lcov_fallback_concatenates(temp_dir, minimal_lcov_file):
    output = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        ok = _merge_lcov([minimal_lcov_file], output)
    assert ok is True
    assert output.exists()
    assert "SF:" in output.read_text()


def test_merge_lcov_skips_nonexistent_files(temp_dir):
    output = temp_dir / "combined.lcov"
    ghost = temp_dir / "ghost.lcov"
    with patch("shutil.which", return_value=None):
        ok = _merge_lcov([ghost], output)
    assert ok is True
    content = output.read_text(encoding="utf-8")
    assert "SF:" not in content


def test_merge_lcov_multiple_files(temp_dir, minimal_lcov_file):
    second = temp_dir / "coverage_int.lcov"
    second.write_text("SF:src/other.py\nDA:5,2\nend_of_record\n")
    output = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        ok = _merge_lcov([minimal_lcov_file, second], output)
    assert ok
    content = output.read_text()
    assert "src/main.py" in content
    assert "src/other.py" in content


# ── _merge_lcov with the lcov tool ──────────────────────────────────────────


def test_merge_lcov_tool_gets_only_existing_tracefiles(temp_dir, minimal_lcov_file):
    output = temp_dir / "combined.lcov"
    ghost = temp_dir / "ghost.lcov"
    done = SimpleNamespace(returncode=0, stderr="")
    with patch("shutil.which", return_value="/usr/bin/lcov"), patch("subprocess.run", return_value=done) as run:
        assert _merge_lcov([minimal_lcov_file, ghost], output) is True
    assert run.call_args.args[0] == [
        "lcov",
        "--add-tracefile",
        str(minimal_lcov_file),
        "--output-file",
        str(output),
    ]


def test_merge_lcov_tool_failure_returns_false(temp_dir, minimal_lcov_file, capsys):
    failed = SimpleNamespace(returncode=1, stderr="lcov: ERROR: bad tracefile")
    with patch("shutil.which", return_value="/usr/bin/lcov"), patch("subprocess.run", return_value=failed):
        assert _merge_lcov([minimal_lcov_file], temp_dir / "out.lcov") is False
    assert "bad tracefile" in capsys.readouterr().err


# ── upload_with_codecov, real (mocked) upload ───────────────────────────────


def test_upload_with_codecov_passes_repo_metadata(temp_dir, minimal_lcov_file):
    done = SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=done) as run:
        rc = upload_with_codecov(minimal_lcov_file, "unit", "own/repo", "abc123", "main", "42", None, False, "cc")
    assert rc == 0
    cmd = run.call_args.args[0]
    for flag, value in (("--slug", "own/repo"), ("--sha", "abc123"), ("--branch", "main"), ("--pr", "42")):
        assert cmd[cmd.index(flag) + 1] == value


def test_upload_with_codecov_echoes_report_url(temp_dir, minimal_lcov_file, capsys):
    done = SimpleNamespace(returncode=0, stdout="info\n  View at https://app.codecov.io/gh/o/r  \n", stderr="")
    with patch("subprocess.run", return_value=done):
        upload_with_codecov(minimal_lcov_file, "unit", None, None, None, None, None, False, "cc")
    assert "  View at https://app.codecov.io/gh/o/r\n" in capsys.readouterr().err


def test_upload_with_codecov_failure_returns_tool_exit_code(temp_dir, minimal_lcov_file, capsys):
    failed = SimpleNamespace(returncode=3, stdout="", stderr="401 unauthorized")
    with patch("subprocess.run", return_value=failed):
        rc = upload_with_codecov(minimal_lcov_file, "e2e", None, None, None, None, None, False, "cc")
    assert rc == 3
    assert "flag=e2e failed" in capsys.readouterr().err


# ── main (CLI) ───────────────────────────────────────────────────────────────


def _lcov_dir(temp_dir, tiers=("unit", "int_mock")):
    d = temp_dir / "tiers"
    d.mkdir()
    for tier in tiers:
        (d / f"coverage_{tier}.lcov").write_text(f"SF:src/{tier}.py\nDA:1,1\nend_of_record\n")
    return d


def _run_main(monkeypatch, capsys, *argv):
    monkeypatch.setattr(sys, "argv", ["upload_coverage.py", *argv])
    rc = upload_main()
    captured = capsys.readouterr()
    return rc, captured


def test_main_without_source_exits_with_usage_error(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["upload_coverage.py"])
    with pytest.raises(SystemExit) as exc:
        upload_main()
    assert exc.value.code == 2


def test_main_empty_lcov_dir_returns_one(temp_dir, monkeypatch, capsys):
    rc, captured = _run_main(monkeypatch, capsys, "--lcov-dir", str(temp_dir))
    assert rc == 1
    assert "No lcov files found" in captured.err


def test_main_without_codecov_binary_returns_one(temp_dir, monkeypatch, capsys):
    d = _lcov_dir(temp_dir)
    with patch("upload_coverage._find_codecov", return_value=None):
        rc, captured = _run_main(monkeypatch, capsys, "--lcov-dir", str(d))
    assert rc == 1
    assert "codecov binary not found" in captured.err


def test_main_dry_run_reports_found_tiers_and_skips_missing(temp_dir, monkeypatch, capsys):
    d = _lcov_dir(temp_dir)
    monkeypatch.delenv("CODECOV_TOKEN", raising=False)
    with patch("upload_coverage._find_codecov", return_value=None):
        rc, captured = _run_main(monkeypatch, capsys, "--lcov-dir", str(d), "--dry-run")
    assert rc == 0
    assert json.loads(captured.out) == {"uploaded": ["unit", "int_mock"], "errors": 0}
    assert "[SKIP] No lcov file for tier=e2e" in captured.err
    assert "codecov --file" in captured.err  # dry-run placeholder binary


def test_main_manifest_skips_files_that_do_not_exist(temp_dir, monkeypatch, capsys, minimal_lcov_file):
    manifest = temp_dir / "manifest.json"
    manifest.write_text(json.dumps({"unit": str(minimal_lcov_file), "e2e": str(temp_dir / "gone.lcov")}))
    done = SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=done) as run:
        rc, captured = _run_main(monkeypatch, capsys, str(manifest), "--codecov-bin", "cc")
    assert rc == 0
    assert json.loads(captured.out) == {"uploaded": ["unit"], "errors": 0}
    assert "[SKIP] File not found" in captured.err
    assert run.call_count == 1


def test_main_uses_token_and_slug_from_environment(temp_dir, monkeypatch, capsys):
    d = _lcov_dir(temp_dir, ("unit",))
    monkeypatch.setenv("CODECOV_TOKEN", "tok-123")
    monkeypatch.setenv("CODECOV_SLUG", "env/slug")
    done = SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=done) as run:
        rc, _ = _run_main(monkeypatch, capsys, "--lcov-dir", str(d), "--codecov-bin", "cc", "--tiers", "unit")
    assert rc == 0
    cmd = run.call_args.args[0]
    assert cmd[cmd.index("--token") + 1] == "tok-123"
    assert cmd[cmd.index("--slug") + 1] == "env/slug"


def test_main_upload_failure_counts_errors_and_returns_one(temp_dir, monkeypatch, capsys):
    d = _lcov_dir(temp_dir)
    failed = SimpleNamespace(returncode=1, stdout="", stderr="boom")
    with patch("subprocess.run", return_value=failed):
        rc, captured = _run_main(monkeypatch, capsys, "--lcov-dir", str(d), "--codecov-bin", "cc")
    assert rc == 1
    assert json.loads(captured.out) == {"uploaded": [], "errors": 2}


def test_main_merge_uploads_combined_file(temp_dir, monkeypatch, capsys):
    d = _lcov_dir(temp_dir)
    done = SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch("shutil.which", return_value=None), patch("subprocess.run", return_value=done) as run:
        rc, captured = _run_main(monkeypatch, capsys, "--lcov-dir", str(d), "--codecov-bin", "cc", "--merge")
    assert rc == 0
    assert json.loads(captured.out)["uploaded"] == ["unit", "int_mock", "combined"]
    combined = d / "combined.lcov"
    assert "src/unit.py" in combined.read_text(encoding="utf-8")
    last_cmd = run.call_args.args[0]
    assert last_cmd[last_cmd.index("--file") + 1] == str(combined)
    assert last_cmd[last_cmd.index("--flag") + 1] == "combined"


def test_main_merge_dry_run_honours_merged_output(temp_dir, monkeypatch, capsys):
    d = _lcov_dir(temp_dir, ("unit",))
    target = temp_dir / "all.lcov"
    rc, captured = _run_main(
        monkeypatch, capsys, "--lcov-dir", str(d), "--dry-run", "--merge", "--merged-output", str(target)
    )
    assert rc == 0
    assert json.loads(captured.out)["uploaded"] == ["unit", "combined"]
    assert f"Uploading merged (all tiers) → {target}" in captured.err
    assert not target.exists()  # dry run writes nothing


def test_main_merge_upload_failure_returns_one(temp_dir, monkeypatch, capsys):
    d = _lcov_dir(temp_dir, ("unit",))

    def run(cmd, **kwargs):
        rc = 1 if "combined" in cmd else 0
        return SimpleNamespace(returncode=rc, stdout="", stderr="")

    with patch("shutil.which", return_value=None), patch("subprocess.run", side_effect=run):
        rc, captured = _run_main(monkeypatch, capsys, "--lcov-dir", str(d), "--codecov-bin", "cc", "--merge")
    assert rc == 1
    assert json.loads(captured.out) == {"uploaded": ["unit"], "errors": 1}
