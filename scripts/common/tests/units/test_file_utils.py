#!/usr/bin/env python3
"""Tests for common/file_utils.py"""

import pytest
from pathlib import Path

from common.file_utils import read_file_safe, read_files_safe, FileReadResult

class TestFileReadResult:
    """Test FileReadResult dataclass."""

    def test_file_read_result_success(self):
        """Test successful file read result."""
        result = FileReadResult(
            exists=True,
            path="/test/file.txt",
            content="Hello World",
            lines=1
        )

        assert result.exists is True
        assert result.path == "/test/file.txt"
        assert result.content == "Hello World"
        assert result.lines == 1
        assert result.error is None

    def test_file_read_result_not_found(self):
        """Test file not found result."""
        result = FileReadResult(
            exists=False,
            path="/test/missing.txt"
        )

        assert result.exists is False
        assert result.content is None
        assert result.error is None

    def test_file_read_result_with_error(self):
        """Test file read with error."""
        result = FileReadResult(
            exists=True,
            path="/test/file.txt",
            error="Permission denied"
        )

        assert result.exists is True
        assert result.content is None
        assert result.error == "Permission denied"

class TestReadFileSafe:
    """Test read_file_safe function."""

    def test_read_existing_file(self, tmp_path):
        """Test reading existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")

        result = read_file_safe(test_file)

        assert result.exists is True
        assert result.path == str(test_file)
        assert result.content == "Line 1\nLine 2\nLine 3"
        assert result.lines == 3
        assert result.error is None

    def test_read_missing_file(self, tmp_path):
        """Test reading non-existent file."""
        test_file = tmp_path / "missing.txt"

        result = read_file_safe(test_file)

        assert result.exists is False
        assert result.path == str(test_file)
        assert result.content is None
        assert result.lines == 0
        assert result.error is None

    def test_read_empty_file(self, tmp_path):
        """Test reading empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        result = read_file_safe(test_file)

        assert result.exists is True
        assert result.content == ""
        assert result.lines == 0
        assert result.error is None

    def test_read_file_with_utf8(self, tmp_path):
        """Test reading file with UTF-8 content."""
        test_file = tmp_path / "utf8.txt"
        test_file.write_text("Héllo Wörld 日本語", encoding="utf-8")

        result = read_file_safe(test_file)

        assert result.exists is True
        assert result.content == "Héllo Wörld 日本語"
        assert result.error is None

    def test_read_file_with_custom_encoding(self, tmp_path):
        """Test reading file with custom encoding."""
        test_file = tmp_path / "latin1.txt"
        test_file.write_text("Héllo", encoding="latin-1")

        result = read_file_safe(test_file, encoding="latin-1")

        assert result.exists is True
        assert result.content == "Héllo"
        assert result.error is None

    def test_read_file_encoding_error(self, tmp_path):
        """Test reading file with wrong encoding."""
        test_file = tmp_path / "binary.txt"
        test_file.write_bytes(b'\x80\x81\x82')  # Invalid UTF-8

        result = read_file_safe(test_file, encoding="utf-8")

        assert result.exists is True
        assert result.content is None
        assert result.error is not None
        assert "codec" in result.error.lower() or "decode" in result.error.lower()

    def test_read_file_permission_error(self, tmp_path):
        """Test reading file with permission error (Unix only)."""
        import platform
        if platform.system() == "Windows":
            pytest.skip("Permission test not applicable on Windows")

        test_file = tmp_path / "noperm.txt"
        test_file.write_text("Secret", encoding="utf-8")
        test_file.chmod(0o000)  # Remove all permissions

        try:
            result = read_file_safe(test_file)

            assert result.exists is True
            assert result.content is None
            assert result.error is not None
            assert "Permission denied" in result.error
        finally:
            test_file.chmod(0o644)  # Restore for cleanup

    def test_read_file_multiline(self, tmp_path):
        """Test reading multiline file."""
        test_file = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        test_file.write_text(content, encoding="utf-8")

        result = read_file_safe(test_file)

        assert result.lines == 5
        assert result.content == content

    def test_read_file_with_blank_lines(self, tmp_path):
        """Test counting lines with blank lines."""
        test_file = tmp_path / "blank.txt"
        content = "Line 1\n\nLine 3\n\nLine 5"
        test_file.write_text(content, encoding="utf-8")

        result = read_file_safe(test_file)

        assert result.lines == 5  # Blank lines count
        assert result.content == content

class TestReadFilesSafe:
    """Test read_files_safe function."""

    def test_read_multiple_files(self, tmp_path):
        """Test reading multiple files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file3 = tmp_path / "file3.txt"

        file1.write_text("Content 1", encoding="utf-8")
        file2.write_text("Content 2", encoding="utf-8")
        file3.write_text("Content 3", encoding="utf-8")

        results = read_files_safe([file1, file2, file3])

        assert len(results) == 3
        assert all(r.exists for r in results)
        assert results[0].content == "Content 1"
        assert results[1].content == "Content 2"
        assert results[2].content == "Content 3"

    def test_read_mixed_existing_missing(self, tmp_path):
        """Test reading mix of existing and missing files."""
        file1 = tmp_path / "exists.txt"
        file2 = tmp_path / "missing.txt"
        file3 = tmp_path / "also_exists.txt"

        file1.write_text("Exists", encoding="utf-8")
        file3.write_text("Also exists", encoding="utf-8")

        results = read_files_safe([file1, file2, file3])

        assert len(results) == 3
        assert results[0].exists is True
        assert results[1].exists is False
        assert results[2].exists is True

    def test_read_empty_list(self):
        """Test reading empty file list."""
        results = read_files_safe([])

        assert len(results) == 0
        assert results == []

    def test_read_files_with_errors(self, tmp_path):
        """Test reading files with some errors."""
        file1 = tmp_path / "valid.txt"
        file2 = tmp_path / "invalid.txt"

        file1.write_text("Valid", encoding="utf-8")
        file2.write_bytes(b'\x80\x81\x82')  # Invalid UTF-8

        results = read_files_safe([file1, file2])

        assert len(results) == 2
        assert results[0].exists is True
        assert results[0].content == "Valid"
        assert results[0].error is None

        assert results[1].exists is True
        assert results[1].content is None
        assert results[1].error is not None

    def test_read_files_custom_encoding(self, tmp_path):
        """Test reading multiple files with custom encoding."""
        file1 = tmp_path / "latin1.txt"
        file2 = tmp_path / "latin2.txt"

        file1.write_text("Café", encoding="latin-1")
        file2.write_text("Résumé", encoding="latin-1")

        results = read_files_safe([file1, file2], encoding="latin-1")

        assert len(results) == 2
        assert results[0].content == "Café"
        assert results[1].content == "Résumé"
