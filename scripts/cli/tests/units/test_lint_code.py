"""Tests for lint_code.py — language-specific code linter."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.lint_code import LintCode

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def linter():
    return LintCode()

@pytest.fixture
def py_file(tmp_path: Path) -> Path:
    f = tmp_path / "sample.py"
    f.write_text('x = 1\n')
    return f

@pytest.fixture
def ts_file(tmp_path: Path) -> Path:
    f = tmp_path / "sample.ts"
    f.write_text('const x = 1;\n')
    return f

@pytest.fixture
def go_file(tmp_path: Path) -> Path:
    f = tmp_path / "sample.go"
    f.write_text('package main\n')
    return f

# ---------------------------------------------------------------------------
# Unit: language detection
# ---------------------------------------------------------------------------

def test_detect_language_python(linter, py_file):
    linter.args = MagicMock(language="auto", fix=False)
    assert linter._detect_language(py_file) == "python"

def test_detect_language_typescript(linter, ts_file):
    linter.args = MagicMock(language="auto", fix=False)
    assert linter._detect_language(ts_file) == "typescript"

def test_detect_language_tsx(linter, tmp_path):
    f = tmp_path / "App.tsx"
    f.write_text('')
    linter.args = MagicMock(language="auto", fix=False)
    assert linter._detect_language(f) == "typescript"

def test_detect_language_javascript(linter, tmp_path):
    f = tmp_path / "app.js"
    f.write_text('')
    linter.args = MagicMock(language="auto", fix=False)
    assert linter._detect_language(f) == "javascript"

def test_detect_language_go(linter, go_file):
    linter.args = MagicMock(language="auto", fix=False)
    assert linter._detect_language(go_file) == "go"

def test_detect_language_unknown_exits(linter, tmp_path):
    f = tmp_path / "file.xyz"
    f.write_text('')
    linter.args = MagicMock(language="auto", fix=False)
    with pytest.raises(SystemExit):
        linter._detect_language(f)

# ---------------------------------------------------------------------------
# Unit: linter selection
# ---------------------------------------------------------------------------

def test_get_linter_python(linter):
    assert linter._get_linter("python") == "ruff"

def test_get_linter_typescript(linter):
    assert linter._get_linter("typescript") == "eslint"

def test_get_linter_javascript(linter):
    assert linter._get_linter("javascript") == "eslint"

def test_get_linter_go(linter):
    assert linter._get_linter("go") == "golangci-lint"

def test_get_linter_unknown_returns_none(linter):
    assert linter._get_linter("rust") is None

# ---------------------------------------------------------------------------
# Unit: command building
# ---------------------------------------------------------------------------

def test_build_command_ruff(linter, py_file):
    linter.args = MagicMock(fix=False)
    cmd = linter._build_command("ruff", py_file, "python")
    assert cmd[0] == "ruff"
    assert "check" in cmd

def test_build_command_ruff_fix(linter, py_file):
    linter.args = MagicMock(fix=True)
    cmd = linter._build_command("ruff", py_file, "python")
    assert "--fix" in cmd

def test_build_command_eslint(linter, ts_file):
    linter.args = MagicMock(fix=False)
    cmd = linter._build_command("eslint", ts_file, "typescript")
    assert cmd[0] == "eslint"

def test_build_command_eslint_fix(linter, ts_file):
    linter.args = MagicMock(fix=True)
    cmd = linter._build_command("eslint", ts_file, "typescript")
    assert "--fix" in cmd

def test_build_command_golangci(linter, go_file):
    linter.args = MagicMock(fix=False)
    cmd = linter._build_command("golangci-lint", go_file, "go")
    assert "golangci-lint" in cmd

def test_build_command_unknown_exits(linter, py_file):
    linter.args = MagicMock(fix=False)
    with pytest.raises(SystemExit):
        linter._build_command("unknown-linter", py_file, "python")

# ---------------------------------------------------------------------------
# Unit: lint_file (mocked subprocess)
# ---------------------------------------------------------------------------

@patch("cli.lint_code.subprocess.run")
def test_lint_file_passes(mock_run, linter, py_file, capsys):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    linter.args = MagicMock(language="python", fix=False)
    linter._lint_file(py_file)
    captured = capsys.readouterr()
    assert "[OK]" in captured.out

@patch("cli.lint_code.subprocess.run")
def test_lint_file_has_issues(mock_run, linter, py_file, capsys):
    mock_run.return_value = MagicMock(returncode=1, stdout="line 1: error", stderr="")
    linter.args = MagicMock(language="python", fix=False)
    linter._lint_file(py_file)
    captured = capsys.readouterr()
    assert "[WARN]" in captured.out

def test_lint_file_not_found_exits(linter, tmp_path):
    linter.args = MagicMock(language="python", fix=False)
    with pytest.raises(SystemExit):
        linter._lint_file(tmp_path / "nonexistent.py")

def test_lint_file_no_linter_exits(linter, tmp_path):
    f = tmp_path / "file.rs"
    f.write_text("")
    linter.args = MagicMock(language="auto", fix=False)
    with pytest.raises(SystemExit):
        linter._lint_file(f)

# ---------------------------------------------------------------------------
# Unit: lint_directory (mocked subprocess)
# ---------------------------------------------------------------------------

@patch("cli.lint_code.subprocess.run")
def test_lint_directory_no_files(mock_run, linter, tmp_path, capsys):
    linter.args = MagicMock(language="auto", fix=False, recursive=False)
    linter._lint_directory(tmp_path)
    captured = capsys.readouterr()
    assert "No files found" in captured.out

@patch("cli.lint_code.subprocess.run")
def test_lint_directory_with_py_files(mock_run, linter, tmp_path, capsys):
    (tmp_path / "a.py").write_text("x=1")
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    linter.args = MagicMock(language="auto", fix=False, recursive=False)
    linter._lint_directory(tmp_path)
    captured = capsys.readouterr()
    assert "passed linting" in captured.out

def test_lint_directory_not_found_exits(linter, tmp_path):
    linter.args = MagicMock(language="auto", fix=False, recursive=False)
    with pytest.raises(SystemExit):
        linter._lint_directory(tmp_path / "nonexistent")

# ---------------------------------------------------------------------------
# Integration: CLI via run()
# ---------------------------------------------------------------------------

def test_run_no_target_exits():
    linter = LintCode()
    result = linter.run(["--language", "python"])
    assert result == 1

def test_run_file_not_found_exits(tmp_path):
    linter = LintCode()
    result = linter.run(["--file", str(tmp_path / "missing.py")])
    assert result == 1
