#!/usr/bin/env python3
"""Tests for lib/engine/discovery.py — test-file marking, language grouping, the shared vote."""

from pathlib import Path

import pytest

from lib.engine import discovery
from lib.engine.discovery import dominant_language, group_by_language, is_test_file


@pytest.fixture(autouse=True)
def fresh_discovery_cache():
    """discover_files caches per path; tmp_path is unique, but never let a test see another's walk."""
    discovery._DISCOVERY_CACHE.clear()
    yield
    discovery._DISCOVERY_CACHE.clear()


def _touch(root: Path, *names: str) -> None:
    for name in names:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("x", encoding="utf-8")


class TestIsTestFile:
    @pytest.mark.parametrize(
        "name",
        [
            "test_app.py",
            "app_test.go",
            "app.spec.ts",
            "mock_db.py",
            "fixture_data.py",
            "0001_migration.py",
            "AppTests.cs",
        ],
    )
    def test_marked(self, name):
        assert is_test_file(Path("src") / name) is True

    @pytest.mark.parametrize("name", ["app.py", "users.go", "Service.kt"])
    def test_source(self, name):
        assert is_test_file(Path("src") / name) is False

    def test_directory_name_alone_does_not_mark(self):
        """Only the file name counts: tier directories are BBA's concern, not discovery's."""
        assert is_test_file(Path("tests/unit/helpers.py")) is False


class TestGroupByLanguage:
    def test_groups_code_by_default(self):
        files = [Path("a.py"), Path("b.go"), Path("c.py"), Path("d.yaml")]
        assert group_by_language(files) == {"python": [Path("a.py"), Path("c.py")], "go": [Path("b.go")]}

    def test_kinds_admit_data_and_config(self):
        files = [Path("a.py"), Path("ci.yaml"), Path("Dockerfile")]
        groups = group_by_language(files, ("code", "data", "config"))
        assert groups == {"python": [Path("a.py")], "yaml": [Path("ci.yaml")], "dockerfile": [Path("Dockerfile")]}

    def test_unknown_files_dropped(self):
        assert group_by_language([Path("notes.txt"), Path("README")]) == {}

    def test_groups_follow_config_order_not_file_order(self):
        """Deterministic run order, whatever order the files arrive in."""
        groups = group_by_language([Path("a.go"), Path("b.py")])
        assert list(groups) == ["python", "go"]

    def test_file_order_kept_inside_a_group(self):
        files = [Path("z.py"), Path("a.py")]
        assert group_by_language(files)["python"] == files


class TestDominantLanguageCodeOnly:
    """The vote counts code files only (#20): data and markup never outvote sources."""

    def test_yaml_never_outvotes_code(self, tmp_path):
        _touch(tmp_path, "a.py", "b.py", "c.yaml", "d.yaml", "e.yaml", "f.yaml")
        assert dominant_language(tmp_path) == "python"

    def test_yaml_never_makes_a_repo_mixed(self, tmp_path):
        _touch(tmp_path, "a.py", "b.yaml")
        assert dominant_language(tmp_path) == "python"

    def test_repo_without_code_is_voted_on_by_its_other_files(self, tmp_path):
        """An SQL-only repo reads "sql", not "unknown" (#42)."""
        _touch(tmp_path, "a.sql", "b.sql", "c.yaml")
        assert dominant_language(tmp_path) == "sql"

    def test_one_code_file_still_outranks_any_number_of_others(self, tmp_path):
        _touch(tmp_path, "a.sql", "b.sql", "c.sql", "main.py")
        assert dominant_language(tmp_path) == "python"

    def test_no_file_with_a_language_is_unknown(self, tmp_path):
        _touch(tmp_path, "notes.txt", "README")
        assert dominant_language(tmp_path) == "unknown"

    def test_skip_dirs_do_not_vote(self, tmp_path):
        _touch(tmp_path, "a.go", "node_modules/x.py", "node_modules/y.py")
        assert dominant_language(tmp_path) == "go"

    def test_threshold_zero_always_names_the_leader(self, tmp_path):
        _touch(tmp_path, "a.go", "b.go", "c.py", "d.ts")
        assert dominant_language(tmp_path) == "mixed"
        assert dominant_language(tmp_path, threshold=0) == "go"

    def test_tie_breaks_toward_config_order(self, tmp_path):
        _touch(tmp_path, "a.go", "b.py")
        assert dominant_language(tmp_path, threshold=0) == "python"
