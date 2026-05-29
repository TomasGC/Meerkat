#!/usr/bin/env python3
"""Tests for propose_ci_fixes.py"""

import json
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from cli.agents.ci_fix_proposer.propose_ci_fixes import (
    ErrorInput,
    should_delegate_to_ollama,
    extract_context,
)


class TestShouldDelegateToOllama:
    """Test delegation decision logic."""

    def test_mechanical_error_delegated(self):
        """Mechanical errors should be delegated to Ollama."""
        error = ErrorInput(
            error_id="err1",
            error_type="compilation",
            error_message="Unresolved reference: ContextCompat"
        )

        assert should_delegate_to_ollama(error) is True

    def test_complex_error_escalated(self):
        """Complex errors should be escalated to Claude."""
        error = ErrorInput(
            error_id="err2",
            error_type="build",
            error_message="Circular dependency detected between ModuleA and ModuleB"
        )

        assert should_delegate_to_ollama(error) is False

    def test_test_assertion_delegated(self):
        """Test assertion errors should be delegated."""
        error = ErrorInput(
            error_id="err3",
            error_type="test",
            error_message="AssertionError: expected 2 but was 1"
        )

        assert should_delegate_to_ollama(error) is True

    def test_architecture_escalated(self):
        """Architecture issues should be escalated."""
        error = ErrorInput(
            error_id="err4",
            error_type="compilation",
            error_message="Refactor needed: design pattern violation"
        )

        assert should_delegate_to_ollama(error) is False


class TestExtractContext:
    """Test context extraction."""

    def test_extract_context_with_file(self, tmp_path):
        """Should extract file context around error line."""
        # Create test file
        test_file = tmp_path / "Test.kt"
        test_file.write_text("""line 1
line 2
line 3
line 4
line 5 ERROR
line 6
line 7
line 8
""")

        error = ErrorInput(
            error_id="err1",
            error_type="compilation",
            error_message="Error at line 5",
            file_path="Test.kt",
            line_number=5
        )

        context = extract_context(error, tmp_path)

        assert context["file_content"] is not None
        assert "line 5 ERROR" in context["file_content"]
        assert "line 1" in context["file_content"]  # Context before

    def test_extract_context_missing_file(self, tmp_path):
        """Should handle missing file gracefully."""
        error = ErrorInput(
            error_id="err1",
            error_type="compilation",
            error_message="Error",
            file_path="NonExistent.kt",
            line_number=5
        )

        context = extract_context(error, tmp_path)

        assert context["file_content"] is None

    def test_extract_context_no_file_path(self, tmp_path):
        """Should handle errors without file path."""
        error = ErrorInput(
            error_id="err1",
            error_type="build",
            error_message="Build failed",
            file_path=None
        )

        context = extract_context(error, tmp_path)

        assert context["file_content"] is None


class TestProposeCIFixesIntegration:
    """Integration tests for propose_ci_fixes.py"""

    def test_script_requires_errors_json(self, tmp_path):
        """Script should fail without errors JSON."""
        from cli.agents.ci_fix_proposer.propose_ci_fixes import ProposeCIFixesScript

        script = ProposeCIFixesScript()

        # Parse args without errors-json
        with pytest.raises(SystemExit):
            script.run(["--repo-path", str(tmp_path)])

    def test_script_handles_missing_file(self, tmp_path):
        """Script should handle missing errors file."""
        from cli.agents.ci_fix_proposer.propose_ci_fixes import ProposeCIFixesScript

        script = ProposeCIFixesScript()

        result = script.run([
            "--errors-json", str(tmp_path / "missing.json"),
            "--repo-path", str(tmp_path),
            "--format", "json"
        ])

        # Script returns 0 but with success=false in JSON
        assert result == 0

    def test_script_with_valid_errors(self, tmp_path):
        """Script should process valid errors JSON."""
        # Create errors JSON
        errors_json = tmp_path / "errors.json"
        errors_json.write_text(json.dumps({
            "errors": [
                {
                    "id": "err1",
                    "type": "compilation",
                    "message": "Unresolved reference: ContextCompat",
                    "file": "Test.kt",
                    "line": 45
                }
            ]
        }))

        from cli.agents.ci_fix_proposer.propose_ci_fixes import ProposeCIFixesScript

        script = ProposeCIFixesScript()

        # Should not crash (even if Ollama unavailable)
        result = script.run([
            "--errors-json", str(errors_json),
            "--repo-path", str(tmp_path),
            "--format", "json"
        ])

        # Either 0 (success) or 1 (Ollama unavailable) is acceptable
        assert result in [0, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
