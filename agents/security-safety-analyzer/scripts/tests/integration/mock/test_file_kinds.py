#!/usr/bin/env python3
"""Each checker sees only the file kinds it declares, each file under its own language (#20).

Real filesystem and real checker registry; the AI layer is switched off.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import orchestrate
from lib.engine import discovery, orchestrator


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "service"
    root.mkdir()
    (root / "app.py").write_text("import hashlib\nhashlib.md5(b'x')\n", encoding="utf-8")
    (root / "pod.yaml").write_text("spec:\n  containers:\n    - securityContext:\n        privileged: true\n",
                                   encoding="utf-8")
    (root / "Dockerfile").write_text("FROM python:latest\n", encoding="utf-8")
    discovery._DISCOVERY_CACHE.clear()
    return root


def _run(root: Path, tmp_path: Path, checks: str) -> dict:
    out = tmp_path / "report.json"
    with patch("lib.ai.model_utils.check_server_available", return_value=False), \
         patch("lib.engine.hybrid.check_server_available", return_value=False):
        orchestrator.main(registry=orchestrate.CHECKERS, app_name="SSA", label_singular="checker",
                          cache_dir=tmp_path / "cache",
                          argv=["--path", str(root), "--full", "--checks", checks, "--no-stream",
                                "--no-cache", "--output", str(out)])
    return json.loads(out.read_text(encoding="utf-8"))


def test_misconfiguration_scans_manifests_and_dockerfiles(project, tmp_path):
    report = _run(project, tmp_path, "misconfiguration")
    flagged = {v["file"] for v in report["violations"]}
    assert {"pod.yaml", "Dockerfile"} <= flagged


def test_code_only_checker_never_sees_config_files(project, tmp_path):
    report = _run(project, tmp_path, "crypto")
    assert {v["file"] for v in report["violations"]} == {"app.py"}
    assert report["languages"] == {"python": 1}


def test_report_labels_the_repo_by_its_code(project, tmp_path):
    """One .py beside a yaml and a Dockerfile: before #20 the vote said "mixed"."""
    report = _run(project, tmp_path, "misconfiguration")
    assert report["language"] == "python"
    assert report["languages"] == {"python": 1, "yaml": 1, "dockerfile": 1}


def test_sql_only_repo_is_analyzed(tmp_path):
    """Before #42 no checker accepted the query kind: an SQL-only repo analyzed zero files."""
    root = tmp_path / "warehouse"
    root.mkdir()
    (root / "grants.sql").write_text("GRANT ALL ON orders TO reporting;\n", encoding="utf-8")
    discovery._DISCOVERY_CACHE.clear()
    report = _run(root, tmp_path, "misconfiguration,crypto")
    assert report["language"] == "sql"
    assert report["languages"] == {"sql": 1}
    assert [(v["principle"], v["line"]) for v in report["violations"]] == [("Misconfiguration", 1)]
