"""Unit tests for checkers/check_cqrs.py — mocks local AI calls.

Pattern mirrors test_check_solid_unit.py: check_cqrs keeps its own
check_server_available guard (hard-fails when the AI server is down), then
delegates to lib.engine.hybrid.run_hybrid(). The guard is patched on the
checker module; the AI pass itself is patched on lib.engine.hybrid, since
that's where run_hybrid's real call sites live.
"""

from unittest.mock import patch

from cca.checkers.check_cqrs import run

_CHECK_AVAILABLE = "cca.checkers.check_cqrs.check_server_available"
_HYBRID_CHECK_AVAILABLE = "lib.engine.hybrid.check_server_available"
_HYBRID_ANALYZE_PARALLEL = "lib.engine.hybrid.analyze_files_parallel"


def test_cqrs_returns_violations_when_server_available(tmp_path):
    """CQRS checker maps local AI items to violations."""
    (tmp_path / "app.py").write_text("class OrderService:\n" "    def save_and_get(self, order): pass\n")
    mock_items = [
        {
            "source_file": str(tmp_path / "app.py"),
            "line": 2,
            "severity": "high",
            "violation": "Command and query mixed in one method",
            "suggestion": "Separate into save() and get() methods",
        }
    ]
    with patch(_CHECK_AVAILABLE, return_value=True), patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=mock_items
    ):
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert len(result["violations"]) == 1


def test_cqrs_empty_when_no_violations(tmp_path):
    """Empty response → 0 violations, success=True."""
    (tmp_path / "app.py").write_text("class QueryService: pass\n")
    with patch(_CHECK_AVAILABLE, return_value=True), patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=[]
    ):
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


def test_cqrs_failure_when_server_unavailable(tmp_path):
    """server not available → success=False, violations=[]."""
    with patch(_CHECK_AVAILABLE, return_value=False):
        result = run(tmp_path, "python")

    assert result["success"] is False
    assert result["violations"] == []


def test_cqrs_return_schema(tmp_path):
    """Return dict has all required keys."""
    with patch(_CHECK_AVAILABLE, return_value=False):
        result = run(tmp_path, "python")

    assert "principle" in result
    assert "success" in result
    assert "violations" in result
    assert isinstance(result["violations"], list)


# ── files param + test file exclusion ───────────────────────────────────────────


def test_cqrs_files_param_uses_only_given_files(tmp_path):
    """When files param provided, only those files are analyzed."""
    explicit = tmp_path / "service.py"
    explicit.write_text("class OrderService: pass\n")
    other = tmp_path / "other.py"
    other.write_text("class X: pass\n")

    with patch(_CHECK_AVAILABLE, return_value=True), patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=[]
    ) as mock_analyze:
        run(tmp_path, "python", files=[explicit])

    called_files = mock_analyze.call_args[0][0]
    assert explicit in called_files
    assert other not in called_files


def test_cqrs_test_files_excluded_in_discovery(tmp_path):
    """Test files (test_*.py) excluded when files=None (full discovery)."""
    source = tmp_path / "service.py"
    source.write_text("class OrderService: pass\n")
    test_file = tmp_path / "test_service.py"
    test_file.write_text("def test_order(): pass\n")

    with patch(_CHECK_AVAILABLE, return_value=True), patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=[]
    ) as mock_analyze:
        run(tmp_path, "python")

    called_files = mock_analyze.call_args[0][0]
    assert source in called_files
    assert test_file not in called_files
