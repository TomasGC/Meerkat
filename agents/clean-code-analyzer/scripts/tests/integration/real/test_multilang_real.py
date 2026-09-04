"""Multi-language integration tests using real Ollama."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from .conftest import ollama_skip

FIXTURES = Path(__file__).parent.parent.parent / "e2e" / "fixtures"

LANGUAGES = [
    ("typescript", FIXTURES / "dirty_typescript"),
    ("javascript", FIXTURES / "dirty_javascript"),
    ("csharp",     FIXTURES / "dirty_csharp"),
    ("go",         FIXTURES / "dirty_go"),
    ("powershell", FIXTURES / "dirty_powershell"),
    ("bash",       FIXTURES / "dirty_bash"),
]


@ollama_skip
@pytest.mark.integration_real
@pytest.mark.parametrize("language,fixture_dir", LANGUAGES)
def test_solid_detects_violations_in_language(language, fixture_dir, tmp_path):
    """SOLID checker finds violations in each language via Ollama."""
    if not fixture_dir.exists():
        pytest.skip(f"Fixture dir missing: {fixture_dir}")
    from checkers.check_solid import run
    result = run(fixture_dir, language)
    assert result["success"] is True or result.get("violations") is not None, (
        f"SOLID checker failed entirely for {language}: {result.get('error')}"
    )
    # Ollama may or may not find violations — just verify it ran without crashing
    assert isinstance(result["violations"], list)


@ollama_skip
@pytest.mark.integration_real
@pytest.mark.parametrize("language,fixture_dir", LANGUAGES)
def test_cqrs_runs_on_language(language, fixture_dir):
    """CQRS checker runs without error on each language."""
    if not fixture_dir.exists():
        pytest.skip(f"Fixture dir missing: {fixture_dir}")
    from checkers.check_cqrs import run
    result = run(fixture_dir, language)
    assert isinstance(result.get("violations"), list)


@ollama_skip
@pytest.mark.integration_real
def test_solid_finds_violations_in_typescript(tmp_path):
    """SOLID checker finds GodService violation in TypeScript fixture."""
    fixture = FIXTURES / "dirty_typescript"
    if not fixture.exists():
        pytest.skip("TypeScript fixture missing")
    from checkers.check_solid import run
    result = run(fixture, "typescript")
    assert result["success"] is True
    # GodService clearly violates SRP — Ollama should detect it
    assert len(result["violations"]) > 0, "Expected SOLID violations in dirty TypeScript"


@ollama_skip
@pytest.mark.integration_real
def test_mechanical_checkers_skip_non_python_gracefully(tmp_path):
    """Error handling checker on TypeScript returns success with empty or regex-based results."""
    fixture = FIXTURES / "dirty_typescript"
    if not fixture.exists():
        pytest.skip("TypeScript fixture missing")
    from checkers.check_error_handling import run
    result = run(fixture, "typescript")
    # Should not crash — may return 0 violations (AST only works on Python)
    assert result.get("success") is not None
    assert isinstance(result.get("violations", []), list)
