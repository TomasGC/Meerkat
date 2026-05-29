#!/usr/bin/env python3
"""Tests for common/cli/base.py"""

import pytest
from pathlib import Path
import sys
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.cli.base import BaseCLIScript, create_cli_script


class MockScript(BaseCLIScript):
    """Mock script for testing."""

    def __init__(self):
        super().__init__()
        self.execute_called = False
        self.execute_args = None

    def execute(self, args) -> dict:
        """Execute mock logic."""
        self.execute_called = True
        self.execute_args = args

        if hasattr(args, 'fail') and args.fail:
            raise ValueError("Mock failure")

        return {
            "success": True,
            "value": 42,
            "format": args.format if hasattr(args, 'format') else "json"
        }

    def format_text(self, result: dict) -> str:
        """Format as text."""
        return f"Success: {result['success']}\nValue: {result['value']}"

    def format_summary(self, result: dict) -> str:
        """Format as summary."""
        return f"Result: {result['value']}"


class MockScriptWithCustomArgs(BaseCLIScript):
    """Mock script with custom arguments."""

    def setup_parser(self, parser):
        """Add custom arguments."""
        parser.add_argument("--custom", type=int, default=10, help="Custom value")
        parser.add_argument("--flag", action="store_true", help="Custom flag")

    def execute(self, args) -> dict:
        """Execute with custom args."""
        return {
            "custom": args.custom,
            "flag": args.flag
        }


class TestBaseCLIScript:
    """Test BaseCLIScript base class."""

    def test_init(self):
        """Test initialization."""
        script = MockScript()

        assert script.logger is not None
        assert script.metrics is not None

    def test_create_parser_default_args(self):
        """Test parser creation with default arguments."""
        script = MockScript()
        parser = script.create_parser()

        args = parser.parse_args([])

        assert args.format == "json"  # Default format

    def test_create_parser_custom_format(self):
        """Test parser with custom format."""
        script = MockScript()
        parser = script.create_parser()

        args = parser.parse_args(["--format", "text"])

        assert args.format == "text"

    def test_setup_parser_custom_args(self):
        """Test setup_parser for custom arguments."""
        script = MockScriptWithCustomArgs()
        parser = script.create_parser()

        args = parser.parse_args(["--custom", "20", "--flag"])

        assert args.custom == 20
        assert args.flag is True

    def test_execute_called(self):
        """Test that execute is called."""
        script = MockScript()

        exit_code = script.run(["--format", "json"])

        assert script.execute_called is True
        assert exit_code == 0

    def test_run_success_json(self, capsys):
        """Test successful run with JSON output."""
        script = MockScript()

        exit_code = script.run(["--format", "json"])

        assert exit_code == 0

        captured = capsys.readouterr()
        assert '"success": true' in captured.out
        assert '"value": 42' in captured.out

    def test_run_success_text(self, capsys):
        """Test successful run with text output."""
        script = MockScript()

        exit_code = script.run(["--format", "text"])

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Success: True" in captured.out
        assert "Value: 42" in captured.out

    def test_run_success_summary(self, capsys):
        """Test successful run with summary output."""
        script = MockScript()

        exit_code = script.run(["--format", "summary"])

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Result: 42" in captured.out

    def test_run_error_handling(self, capsys):
        """Test error handling during execution."""
        class FailScript(BaseCLIScript):
            def execute(self, args) -> dict:
                raise ValueError("Test error")

        script = FailScript()
        exit_code = script.run([])

        assert exit_code == 1

    def test_run_keyboard_interrupt(self):
        """Test keyboard interrupt handling."""
        class InterruptScript(BaseCLIScript):
            def execute(self, args) -> dict:
                raise KeyboardInterrupt()

        script = InterruptScript()
        exit_code = script.run([])

        assert exit_code == 130

    def test_output_json(self, capsys):
        """Test JSON output formatting."""
        script = MockScript()
        result = {"test": "value"}

        script.output(result, "json")

        captured = capsys.readouterr()
        assert '"test": "value"' in captured.out

    def test_output_text(self, capsys):
        """Test text output formatting."""
        script = MockScript()
        result = {"success": True, "value": 42}

        script.output(result, "text")

        captured = capsys.readouterr()
        assert "Success: True" in captured.out

    def test_output_summary(self, capsys):
        """Test summary output formatting."""
        script = MockScript()
        result = {"success": True, "value": 42}

        script.output(result, "summary")

        captured = capsys.readouterr()
        assert "Result: 42" in captured.out

    def test_format_text_default(self, capsys):
        """Test default format_text (uses JSON)."""
        class DefaultScript(BaseCLIScript):
            def execute(self, args) -> dict:
                return {"test": "value"}

        script = DefaultScript()
        result = {"test": "value"}
        text = script.format_text(result)

        assert '"test": "value"' in text

    def test_format_summary_default(self):
        """Test default format_summary (same as format_text)."""
        class DefaultScript(BaseCLIScript):
            def execute(self, args) -> dict:
                return {"test": "value"}

        script = DefaultScript()
        result = {"test": "value"}

        summary = script.format_summary(result)

        # Default implementation uses format_text which uses JSON
        assert '"test": "value"' in summary


class TestCreateCLIScript:
    """Test create_cli_script helper function."""

    def test_create_cli_script_success(self, monkeypatch, capsys):
        """Test create_cli_script with successful execution."""
        # Mock sys.argv and sys.exit
        monkeypatch.setattr('sys.argv', ['script.py', '--format', 'summary'])

        exit_code = None
        def mock_exit(code):
            nonlocal exit_code
            exit_code = code

        monkeypatch.setattr('sys.exit', mock_exit)

        # Create and run
        create_cli_script(MockScript)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Result: 42" in captured.out

    def test_create_cli_script_error(self, monkeypatch):
        """Test create_cli_script with error."""
        class FailScript(BaseCLIScript):
            def execute(self, args) -> dict:
                raise ValueError("Test error")

        monkeypatch.setattr('sys.argv', ['script.py'])

        exit_code = None
        def mock_exit(code):
            nonlocal exit_code
            exit_code = code

        monkeypatch.setattr('sys.exit', mock_exit)

        create_cli_script(FailScript)

        assert exit_code == 1


class TestIntegration:
    """Integration tests for full CLI workflow."""

    def test_full_workflow_json(self, capsys):
        """Test complete workflow with JSON output."""
        script = MockScriptWithCustomArgs()

        exit_code = script.run(["--custom", "99", "--flag", "--format", "json"])

        assert exit_code == 0

        captured = capsys.readouterr()
        assert '"custom": 99' in captured.out
        assert '"flag": true' in captured.out

    def test_full_workflow_no_args(self, capsys):
        """Test workflow with no arguments (defaults)."""
        script = MockScript()

        exit_code = script.run([])

        assert exit_code == 0
        assert script.execute_called is True
