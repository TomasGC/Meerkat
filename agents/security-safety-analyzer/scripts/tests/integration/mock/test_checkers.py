"""Integration/mock tests — real filesystem, AI mocked to False."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

CHECKERS = [
    ("checkers.check_security", "Security"),
    ("checkers.check_crash_bugs", "CrashBug"),
    ("checkers.check_concurrency", "Concurrency"),
    ("checkers.check_error_handling", "ErrorHandling"),
    ("checkers.check_prompt_injection", "PromptInjection"),
]


# Checkers built on common/hybrid.py — the server probe lives in the driver,
# so they are mocked at a different seam than the checkers listed above.
HYBRID_CHECKERS = [
    ("checkers.check_crypto", "Crypto"),
    ("checkers.check_deserialization", "Deserialization"),
    ("checkers.check_misconfiguration", "Misconfiguration"),
    ("checkers.check_resource_leaks", "ResourceLeak"),
    ("checkers.check_sensitive_data", "SensitiveData"),
]


def _make_project(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text(
        "import os\n"
        "password = 'hardcoded_secret_123'\n"
        "def process(user_input):\n"
        "    result = 10 / user_input\n"
        "    try:\n"
        "        risky()\n"
        "    except:\n"
        "        pass\n"
        "    prompt = f'User said: {user_input}'\n"
        "    return prompt\n"
    )
    (src / "utils.py").write_text(
        "def helper(x):\n"
        "    return x\n"
    )
    return tmp_path


_NO_AI = {"checkers.check_error_handling"}  # purely mechanical checkers


@pytest.mark.parametrize("module_path,principle", CHECKERS)
def test_checker_returns_valid_schema(tmp_path, module_path, principle):
    project = _make_project(tmp_path)
    import importlib
    mod = importlib.import_module(module_path)

    mock_target = f"{module_path}.check_server_available"
    if module_path in _NO_AI:
        result = mod.run(project, "python")
    else:
        with patch(mock_target, return_value=False):
            result = mod.run(project, "python")

    assert result["principle"] == principle
    assert result["success"] is True
    assert isinstance(result["violations"], list)
    assert result["files_analyzed"] >= 0
    assert result["duration_ms"] >= 0

    for v in result["violations"]:
        assert "principle" in v
        assert "file" in v
        assert "line" in v
        assert "severity" in v
        assert v["severity"] in ("high", "medium", "low")
        assert "message" in v


@pytest.mark.parametrize("module_path,principle", [
    ("checkers.check_security", "Security"),
    ("checkers.check_crash_bugs", "CrashBug"),
    ("checkers.check_error_handling", "ErrorHandling"),
    ("checkers.check_prompt_injection", "PromptInjection"),
])
def test_hybrid_checkers_find_violations_mechanically(tmp_path, module_path, principle):
    """Hybrid checkers must detect at least one violation in the seeded project without AI."""
    project = _make_project(tmp_path)
    import importlib
    mod = importlib.import_module(module_path)

    mock_target = f"{module_path}.check_server_available"
    if module_path in _NO_AI:
        result = mod.run(project, "python")
    else:
        with patch(mock_target, return_value=False):
            result = mod.run(project, "python")

    assert len(result["violations"]) >= 1, (
        f"{principle} checker found no violations in seeded project (mechanical path)"
    )


def _make_hybrid_project(tmp_path: Path) -> Path:
    """Project seeded with one violation per hybrid checker, across several languages."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "crypto_use.py").write_text(
        "import hashlib\n"
        "def fingerprint(data):\n"
        "    return hashlib.md5(data).hexdigest()\n"
    )
    (src / "loader.py").write_text(
        "import pickle\n"
        "def load(payload):\n"
        "    return pickle.loads(payload)\n"
    )
    (src / "settings.py").write_text(
        "DEBUG = True\n"
        "ALLOWED_HOSTS = ['*']\n"
    )
    (src / "io_helpers.py").write_text(
        "def read(path):\n"
        "    handle = open(path)\n"
        "    return handle.read()\n"
    )
    (src / "audit.py").write_text(
        "import logging\n"
        "logger = logging.getLogger(__name__)\n"
        "def record(user, password):\n"
        "    logger.info('login password=%s', password)\n"
    )
    return tmp_path


@pytest.mark.parametrize("module_path,principle", HYBRID_CHECKERS)
def test_hybrid_driver_checker_returns_valid_schema(tmp_path, module_path, principle):
    project = _make_hybrid_project(tmp_path)
    import importlib
    mod = importlib.import_module(module_path)

    with patch("lib.engine.hybrid.check_server_available", return_value=False):
        result = mod.run(project, "python")

    assert result["principle"] == principle
    assert result["success"] is True
    assert result["files_analyzed"] == 5
    assert result["duration_ms"] >= 0
    for v in result["violations"]:
        assert v["principle"] == principle
        assert v["severity"] in ("high", "medium", "low")
        assert not Path(v["file"]).is_absolute()
        assert v["line"] >= 1
        assert v["message"] and v["suggestion"]


@pytest.mark.parametrize("module_path,principle", HYBRID_CHECKERS)
def test_hybrid_driver_checker_finds_violations_mechanically(tmp_path, module_path, principle):
    project = _make_hybrid_project(tmp_path)
    import importlib
    mod = importlib.import_module(module_path)

    with patch("lib.engine.hybrid.check_server_available", return_value=False):
        result = mod.run(project, "python")

    assert len(result["violations"]) >= 1, (
        f"{principle} checker found no violations in seeded project (mechanical path)"
    )


@pytest.mark.parametrize("module_path,principle", HYBRID_CHECKERS)
def test_hybrid_driver_checker_passes_known_findings_to_ai(tmp_path, module_path, principle):
    """Mechanical results must reach the prompt so the AI layer does not repeat them."""
    project = _make_hybrid_project(tmp_path)
    import importlib
    mod = importlib.import_module(module_path)

    captured = {}

    def fake_analyze(files, *args, **kwargs):
        captured["extra_slots"] = kwargs.get("extra_slots")
        return []

    with patch("lib.engine.hybrid.check_server_available", return_value=True), \
         patch("lib.engine.hybrid.analyze_files_parallel", side_effect=fake_analyze):
        mod.run(project, "python")

    slots = captured["extra_slots"]
    assert len(slots) == 5
    assert all("known_findings" in s for s in slots.values())
