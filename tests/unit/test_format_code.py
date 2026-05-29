#!/usr/bin/env python3
"""Unit tests for format_code.py"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestFormatCode:
    """Test suite for format_code.py"""

    def test_detect_language_python(self, tmp_path):
        """Test Python file detection."""
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock()

        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        language = formatter._detect_language(test_file)
        assert language == "python"

    def test_detect_language_typescript(self, tmp_path):
        """Test TypeScript file detection."""
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock()

        test_file = tmp_path / "test.ts"
        test_file.write_text("console.log('hello')")

        language = formatter._detect_language(test_file)
        assert language == "typescript"

    def test_get_formatter_python(self):
        """Test formatter selection for Python."""
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock()

        assert formatter._get_formatter("python") == "black"

    def test_get_formatter_typescript(self):
        """Test formatter selection for TypeScript."""
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock()

        assert formatter._get_formatter("typescript") == "prettier"

    def test_build_command_black(self, tmp_path):
        """Test black command building."""
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(check_only=False)

        test_file = tmp_path / "test.py"
        cmd = formatter._build_command("black", test_file, "python")

        assert cmd[0] == "black"
        assert str(test_file) in cmd

    def test_build_command_prettier(self, tmp_path):
        """Test prettier command building."""
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(check_only=False)

        test_file = tmp_path / "test.ts"
        cmd = formatter._build_command("prettier", test_file, "typescript")

        assert cmd[0] == "prettier"
        assert "--write" in cmd
        assert str(test_file) in cmd

    def test_build_command_prettier_check_only(self, tmp_path):
        """Test prettier check-only mode."""
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(check_only=True)

        test_file = tmp_path / "test.ts"
        cmd = formatter._build_command("prettier", test_file, "typescript")

        assert "--check" in cmd
        assert "--write" not in cmd

    @patch('subprocess.run')
    def test_format_file_success(self, mock_run, tmp_path):
        """Test successful file formatting."""
        from cli.format_code import FormatCode

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        formatter = FormatCode()
        formatter.args = MagicMock(
            file=tmp_path / "test.py",
            dir=None,
            language="auto",
            check_only=False,
            recursive=False
        )

        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        # Should not raise
        formatter._format_file(test_file)

        # Verify subprocess called
        assert mock_run.called

    @patch('subprocess.run')
    def test_format_file_not_found(self, mock_run, tmp_path):
        """Test formatting non-existent file."""
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(
            file=tmp_path / "nonexistent.py",
            language="auto",
            check_only=False
        )

        with pytest.raises(SystemExit):
            formatter._format_file(tmp_path / "nonexistent.py")

    def test_format_directory_no_files(self, tmp_path):
        """Test formatting empty directory."""
        from cli.format_code import FormatCode

        formatter = FormatCode()
        formatter.args = MagicMock(
            dir=tmp_path,
            recursive=False,
            check_only=False
        )

        # Should not raise
        formatter._format_directory(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
