#!/usr/bin/env python3
"""Unit tests for format_code.py"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest


class TestFormatCode:

    def test_detect_language_python(self, tmp_path):
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock()
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        assert formatter._detect_language(test_file) == "python"

    def test_detect_language_typescript(self, tmp_path):
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock()
        test_file = tmp_path / "test.ts"
        test_file.write_text("console.log('hello')")
        assert formatter._detect_language(test_file) == "typescript"

    def test_get_formatter_python(self):
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock()
        assert formatter._get_formatter("python") == "black"

    def test_get_formatter_typescript(self):
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock()
        assert formatter._get_formatter("typescript") == "prettier"

    def test_build_command_black(self, tmp_path):
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(check_only=False)
        test_file = tmp_path / "test.py"
        cmd = formatter._build_command("black", test_file, "python")
        assert cmd[0] == "black"
        assert str(test_file) in cmd

    def test_build_command_prettier(self, tmp_path):
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(check_only=False)
        test_file = tmp_path / "test.ts"
        cmd = formatter._build_command("prettier", test_file, "typescript")
        assert cmd[0] == "prettier"
        assert "--write" in cmd
        assert str(test_file) in cmd

    def test_build_command_prettier_check_only(self, tmp_path):
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(check_only=True)
        test_file = tmp_path / "test.ts"
        cmd = formatter._build_command("prettier", test_file, "typescript")
        assert "--check" in cmd
        assert "--write" not in cmd

    @patch("subprocess.run")
    def test_format_file_success(self, mock_run, tmp_path):
        from cli.format_code import FormatCode

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        formatter = FormatCode()
        formatter.args = MagicMock(
            file=tmp_path / "test.py", dir=None, language="auto", check_only=False, recursive=False
        )
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        formatter._format_file(test_file)
        assert mock_run.called

    @patch("subprocess.run")
    def test_format_file_not_found(self, mock_run, tmp_path):
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(file=tmp_path / "nonexistent.py", language="auto", check_only=False)
        with pytest.raises(SystemExit):
            formatter._format_file(tmp_path / "nonexistent.py")

    def test_format_directory_no_files(self, tmp_path):
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(dir=tmp_path, recursive=False, check_only=False)
        formatter._format_directory(tmp_path)


def _formatter(check_only=False):
    from cli.format_code import FormatCode

    formatter = FormatCode()
    formatter.args = MagicMock(check_only=check_only)
    return formatter


@pytest.mark.parametrize(
    "formatter_name,check_only,expected",
    [
        ("black", True, ["black", "--check", "f"]),
        ("gofmt", False, ["gofmt", "-w", "f"]),
        ("gofmt", True, ["gofmt", "-l", "f"]),
        ("dotnet", False, ["dotnet", "format", "f"]),
        ("dotnet", True, ["dotnet", "format", "--verify-no-changes", "f"]),
    ],
)
def test_build_command_per_formatter(formatter_name, check_only, expected):
    assert _formatter(check_only)._build_command(formatter_name, "f", "x") == expected


def test_build_command_unknown_formatter_exits(capsys):
    with pytest.raises(SystemExit):
        _formatter()._build_command("rustfmt", "f", "rust")
    assert "Unknown formatter: rustfmt" in capsys.readouterr().err


def test_detect_language_unknown_extension_exits(tmp_path, capsys):
    with pytest.raises(SystemExit):
        _formatter()._detect_language(tmp_path / "a.rb")
    assert "Unknown file type: .rb" in capsys.readouterr().err


@patch("cli.format_code.subprocess.run")
def test_run_formats_file_with_detected_formatter(mock_run, tmp_path, capsys):
    from cli.format_code import FormatCode

    source = tmp_path / "main.go"
    source.write_text("package main\n", encoding="utf-8")

    assert FormatCode().run(["--file", str(source)]) == 0

    assert mock_run.call_args[0][0] == ["gofmt", "-w", str(source)]
    assert capsys.readouterr().out == f"[OK] Formatted {source}\n"


@patch("cli.format_code.subprocess.run")
def test_run_check_only_reports_clean_file(mock_run, tmp_path, capsys):
    from cli.format_code import FormatCode

    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    FormatCode().run(["--file", str(source), "--check-only"])
    assert capsys.readouterr().out == f"[OK] {source} is properly formatted\n"


@pytest.mark.parametrize(
    "check_only,message",
    [(True, "needs formatting"), (False, "Formatting failed: bad syntax")],
)
def test_format_file_failure_exits(tmp_path, capsys, check_only, message):
    source = tmp_path / "a.py"
    source.write_text("x = (\n", encoding="utf-8")
    formatter = _formatter(check_only)
    formatter.args.language = "auto"
    error = subprocess.CalledProcessError(1, "black", stderr="bad syntax")

    with patch("cli.format_code.subprocess.run", side_effect=error), pytest.raises(SystemExit):
        formatter._format_file(source)
    assert message in capsys.readouterr().err


def test_format_file_without_formatter_exits(tmp_path, capsys):
    source = tmp_path / "a.py"
    source.write_text("x", encoding="utf-8")
    formatter = _formatter()
    formatter.args.language = "cobol"
    with pytest.raises(SystemExit):
        formatter._format_file(source)
    assert "No formatter available for cobol" in capsys.readouterr().err


def test_execute_without_target_exits(capsys):
    formatter = _formatter()
    formatter.args.file = None
    formatter.args.dir = None
    with pytest.raises(SystemExit):
        formatter.execute()
    assert "Must specify --file or --dir" in capsys.readouterr().err


def test_format_directory_missing_exits(tmp_path, capsys):
    with pytest.raises(SystemExit):
        _formatter()._format_directory(tmp_path / "absent")
    assert "Directory not found" in capsys.readouterr().err


@patch("cli.format_code.subprocess.run")
def test_run_dir_recursive_counts_formatted_and_failed(mock_run, tmp_path, capsys):
    from cli.format_code import FormatCode

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x\n", encoding="utf-8")
    (tmp_path / "b.ts").write_text("x\n", encoding="utf-8")

    def black_ok_prettier_fails(cmd, **_kwargs):
        if cmd[0] != "black":
            raise subprocess.CalledProcessError(1, cmd, stderr="prettier crashed")
        return MagicMock()

    mock_run.side_effect = black_ok_prettier_fails

    FormatCode().run(["--dir", str(tmp_path), "--recursive"])

    out = capsys.readouterr().out
    assert "[OK] Formatted 1 files" in out
    assert "[WARN] 1 files failed" in out


def test_format_directory_without_recursion_ignores_subdirectories(tmp_path, capsys):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x\n", encoding="utf-8")
    formatter = _formatter()
    formatter.args.recursive = False
    formatter._format_directory(tmp_path)
    assert capsys.readouterr().out == "[WARN] No files found to format\n"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
