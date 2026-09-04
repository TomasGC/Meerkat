"""Real-Ollama integration tests — automatically skipped if Ollama not running."""

from pathlib import Path
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from .conftest import ollama_skip

DIRTY_CODE = """
class GodClass:
    def handle_user(self, user): pass
    def send_email(self, to, body): pass
    def save_to_db(self, obj): pass
    def calculate_tax(self, amount): return amount * 86400

try:
    risky_operation()
except:
    pass
"""

CLEAN_CODE = """
SECONDS_PER_DAY = 86400

class UserService:
    def __init__(self, repo) -> None:
        self._repo = repo

    def get_user(self, user_id: int):
        return self._repo.find_by_id(user_id)

try:
    db.connect()
except ConnectionError as exc:
    logger.error("DB error: %s", exc)
    raise
"""


@pytest.fixture
def dirty_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text(DIRTY_CODE)
    return tmp_path


@pytest.fixture
def clean_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text(CLEAN_CODE)
    return tmp_path


@ollama_skip
@pytest.mark.integration_real
def test_error_handling_real(dirty_project):
    """Real checker on dirty code → at least one ErrorHandling violation."""
    from checkers.check_error_handling import run
    result = run(dirty_project / "src", "python")
    assert result["success"] is True
    assert len(result["violations"]) > 0


@ollama_skip
@pytest.mark.integration_real
def test_naming_real(dirty_project):
    """Real checker on dirty code → magic number 86400 flagged."""
    from checkers.check_naming import run
    result = run(dirty_project / "src", "python")
    assert result["success"] is True
    messages = [v.get("message", "") for v in result["violations"]]
    assert any("86400" in msg for msg in messages), (
        f"Expected 86400 magic number violation; got: {messages}"
    )


@ollama_skip
@pytest.mark.integration_real
def test_clean_code_no_violations_real(clean_project):
    """Clean code → 0 violations from mechanical checkers."""
    from checkers.check_error_handling import run as run_eh
    from checkers.check_naming import run as run_n

    eh_result = run_eh(clean_project / "src", "python")
    assert eh_result["success"] is True
    assert len(eh_result["violations"]) == 0, (
        f"Unexpected error handling violations: {eh_result['violations']}"
    )

    naming_result = run_n(clean_project / "src", "python")
    # SECONDS_PER_DAY should NOT be flagged (it's a constant definition)
    messages = [v.get("message", "") for v in naming_result["violations"]]
    assert not any("SECONDS_PER_DAY" in msg for msg in messages), (
        f"SECONDS_PER_DAY incorrectly flagged: {messages}"
    )
