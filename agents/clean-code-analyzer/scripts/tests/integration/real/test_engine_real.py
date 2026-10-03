"""Real-AI engine tests: per-file cache round-trip and YAGNI reconciliation on live output.

Each test drives orchestrate.py as a subprocess against the configured local AI
server. CCA_CACHE_DIR points every run at a tmp directory so the real user cache
is never read or written.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
_ORCHESTRATE = _SCRIPTS_DIR / "orchestrate.py"
_TIMEOUT_S = 900
_NEAR_LINES = 3

_MIXED_ABSTRACTION = '''\
class ReportJob:
    def run(self, path):
        rows = self.load(path)
        total = 0
        for line in open(path).read().split("\\n"):
            if line.strip() and not line.startswith("#"):
                total += int(line.split(",")[2].strip())
        self.publish(rows, total)

    def load(self, path):
        return []

    def publish(self, rows, total):
        return None
'''

_UNUSED_FUNCTION = '''\
"""Order service."""


def legacy_discount(total):
    return total * 0.9


def compute_total(prices):
    return sum(prices)


if __name__ == "__main__":
    print(compute_total([1, 2, 3]))
'''


def _run_orchestrate(project: Path, cache_dir: Path, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(_ORCHESTRATE), "--path", str(project), "--full",
         "--format", "json", *args],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        env={**os.environ, "CCA_CACHE_DIR": str(cache_dir)},
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    return json.loads(result.stdout)


def _def_line(source: str, name: str) -> int:
    """1-based line of `def name(` in `source`."""
    for lineno, text in enumerate(source.splitlines(), start=1):
        if text.startswith(f"def {name}("):
            return lineno
    raise AssertionError(f"Fixture has no def {name}")


def _violation_set(data: dict) -> set[tuple]:
    return {(v["file"], v["line"], v["message"]) for v in data["violations"]}


@pytest.mark.live_ai
@pytest.mark.integration_real
def test_cache_round_trip_second_run_hits(tmp_path):
    """Run 2 on unchanged content is served entirely from the cache with identical output."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "report_job.py").write_text(_MIXED_ABSTRACTION)
    cache_dir = tmp_path / "cache"

    first = _run_orchestrate(project, cache_dir, "--checks", "slap")
    assert first.get("cache", {}).get("total", 0) >= 1, f"No AI pass recorded: {first}"
    assert first["cache"]["hits"] == 0
    assert list(cache_dir.glob("*.json")), "Run 1 wrote no cache entry"

    second = _run_orchestrate(project, cache_dir, "--checks", "slap")
    assert second["cache"]["hits"] == second["cache"]["total"]
    assert _violation_set(second) == _violation_set(first)


@pytest.mark.live_ai
@pytest.mark.integration_real
def test_yagni_reconciliation_invariant_on_real_output(tmp_path):
    """Mechanical and AI YAGNI findings share one relative path form and never overlap within 3 lines."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "service.py").write_text(_UNUSED_FUNCTION)

    data = _run_orchestrate(project, tmp_path / "cache", "--checks", "yagni", "--no-cache")

    mechanical = [v for v in data["violations"] if v["message"].startswith("Unused")]
    ai = [v for v in data["violations"] if v["message"].startswith("Speculative")]
    assert mechanical, (
        "Broken fixture: find_unused_code.py reported no unused symbol in service.py; "
        f"got violations {data['violations']}"
    )
    for v in mechanical + ai:
        assert v["file"] == "service.py", f"Unexpected path form: {v['file']!r}"
    # Script <-> checker key contract: the finding must sit on the unused def's real line.
    def_line = _def_line(_UNUSED_FUNCTION, "legacy_discount")
    unused_lines = [m["line"] for m in mechanical if "legacy_discount" in m["message"]]
    assert unused_lines == [def_line], f"Expected legacy_discount at line {def_line}; got {unused_lines}"
    for a in ai:
        near = [m for m in mechanical if abs(m["line"] - a["line"]) <= _NEAR_LINES]
        assert not near, f"AI finding {a} survived next to mechanical {near}"
