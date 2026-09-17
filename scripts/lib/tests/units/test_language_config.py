#!/usr/bin/env python3
"""Tests for lib/config/language_config.py"""

import json

import pytest

from lib.config import language_config as lc


@pytest.fixture
def custom_config(monkeypatch):
    """Install an arbitrary config dict as the loaded singleton."""

    def _install(config: dict) -> None:
        monkeypatch.setattr(lc, "_config", config)

    return _install


@pytest.fixture(autouse=True)
def real_config():
    """Ensure the shipped config is loaded, and that a test never leaves a stub behind."""
    lc._config = {}
    lc._load()
    yield
    lc._config = {}
    lc._load()


class TestLoad:
    """Config loading and template fallback."""

    def test_load_returns_cached_config(self, custom_config):
        custom_config({"languages": {"only": {}}})
        assert lc._load() == {"languages": {"only": {}}}

    def test_copies_template_when_local_missing(self, tmp_path, monkeypatch):
        template = tmp_path / "template.json"
        template.write_text(json.dumps({"languages": {"toy": {"extensions": [".toy"]}}}))
        local = tmp_path / "local.json"

        monkeypatch.setattr(lc, "_config", {})
        monkeypatch.setattr(lc, "_TEMPLATE_PATH", template)
        monkeypatch.setattr(lc, "_CONFIG_PATH", local)

        assert lc._load()["languages"]["toy"]["extensions"] == [".toy"]
        assert local.exists()

    def test_missing_template_yields_empty_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lc, "_config", {})
        monkeypatch.setattr(lc, "_TEMPLATE_PATH", tmp_path / "absent.json")
        monkeypatch.setattr(lc, "_CONFIG_PATH", tmp_path / "absent-local.json")

        assert lc._load() == {}

    def test_malformed_json_is_swallowed(self, tmp_path, monkeypatch):
        local = tmp_path / "local.json"
        local.write_text("{ not json")

        monkeypatch.setattr(lc, "_config", {})
        monkeypatch.setattr(lc, "_CONFIG_PATH", local)

        assert lc._load() == {}


class TestLanguages:
    """Language table accessors against the shipped config."""

    def test_all_languages_non_empty(self):
        assert len(lc.all_languages()) >= 20

    @pytest.mark.parametrize(
        "language",
        ["python", "typescript", "javascript", "vue", "csharp", "razor", "go", "java",
         "kotlin", "swift", "rust", "ruby", "cpp", "php", "perl", "powershell",
         "bash", "sql", "yaml", "dockerfile"],
    )
    def test_language_present(self, language):
        assert lc.get_language(language)

    @pytest.mark.parametrize("language", ["ruby", "rust", "swift", "cpp", "php", "perl"])
    def test_languages_only_bba_used_are_kept(self, language):
        """BBA exposes these as --language choices. Dropping one is a CLI regression."""
        assert lc.extensions(language)

    def test_unknown_language_is_empty_not_error(self):
        assert lc.get_language("klingon") == {}
        assert lc.extensions("klingon") == []

    def test_extensions_for_language(self):
        assert lc.extensions("kotlin") == [".kt", ".kts"]

    def test_extensions_all_is_flat_and_deduplicated(self):
        every = lc.extensions()
        assert ".py" in every and ".sql" in every and ".vue" in every
        assert len(every) == len(set(every))

    def test_language_extensions_shape(self):
        table = lc.language_extensions()
        assert table["python"] == [".py"]
        assert table["dockerfile"] == []

    def test_language_extensions_is_a_copy(self):
        lc.language_extensions()["python"].append(".nope")
        assert lc.extensions("python") == [".py"]


class TestLanguageForExtension:
    """Inverse lookup, replacing the two ext -> language maps."""

    @pytest.mark.parametrize(
        "ext,expected",
        [(".py", "python"), (".tsx", "typescript"), (".cjs", "javascript"),
         (".cshtml", "razor"), (".kts", "kotlin"), (".pm", "perl"), (".sql", "sql")],
    )
    def test_known_extensions(self, ext, expected):
        assert lc.language_for_extension(ext) == expected

    def test_case_insensitive(self):
        assert lc.language_for_extension(".PY") == "python"

    def test_unknown_extension_returns_none(self):
        assert lc.language_for_extension(".zzz") is None


class TestSkipDirs:
    """Global skip set plus per-language additions."""

    @pytest.mark.parametrize(
        "directory",
        [".git", ".svn", "node_modules", "vendor", "bin", "obj", "dist", "build",
         "out", "target", "coverage", ".nyc_output", "__pycache__", ".pytest_cache",
         ".venv", "venv", ".tox", "eggs", ".eggs"],
    )
    def test_union_of_both_agent_sets(self, directory):
        """The shipped set is _SKIP_DIRS (CCA/SSA) union EXCLUDED_DIRS (BBA)."""
        assert directory in lc.skip_dirs()

    def test_returns_a_set(self):
        assert isinstance(lc.skip_dirs(), set)

    def test_language_additions_are_merged(self, custom_config):
        custom_config({
            "skip_dirs": ["global"],
            "languages": {"toy": {"skip_dirs": ["toy_only"]}},
        })
        assert lc.skip_dirs("toy") == {"global", "toy_only"}
        assert lc.skip_dirs() == {"global"}

    def test_language_without_additions_matches_global(self):
        assert lc.skip_dirs("python") == lc.skip_dirs()

    def test_mutating_result_does_not_affect_config(self):
        lc.skip_dirs().add("intruder")
        assert "intruder" not in lc.skip_dirs()


class TestExtensionsWhere:
    """Capability lookup, replacing CCA's exclusion-derived _CLASS_LANG_EXTS."""

    @pytest.mark.parametrize("ext", [".cs", ".java", ".kt", ".ts", ".rb", ".py"])
    def test_class_languages_included(self, ext):
        assert ext in lc.extensions_where("has_classes")

    @pytest.mark.parametrize("ext", [".sql", ".yaml", ".yml", ".sh", ".bash", ".vue", ".go"])
    def test_non_class_languages_excluded(self, ext):
        """The old set was 'everything except python/bash/yaml/dockerfile', which
        would have admitted .sql and .vue as soon as they became visible."""
        assert ext not in lc.extensions_where("has_classes")

    def test_value_false_selects_the_complement(self):
        assert ".sql" in lc.extensions_where("has_classes", value=False)
        assert ".cs" not in lc.extensions_where("has_classes", value=False)

    def test_missing_field_counts_as_false(self, custom_config):
        custom_config({"languages": {"toy": {"extensions": [".toy"]}}})
        assert lc.extensions_where("has_classes") == set()
        assert lc.extensions_where("has_classes", value=False) == {".toy"}


class TestCommentStyle:
    @pytest.mark.parametrize("ext", [".py", ".ps1", ".sh", ".yaml", ".rb", ".pl"])
    def test_hash_comment_extensions(self, ext):
        assert ext in lc.comment_style_extensions("hash")

    @pytest.mark.parametrize("ext", [".cs", ".ts", ".go"])
    def test_slash_languages_are_not_hash(self, ext):
        assert ext not in lc.comment_style_extensions("hash")

    def test_unknown_style_is_empty(self):
        assert lc.comment_style_extensions("hieroglyph") == set()


class TestFilenamePatterns:
    def test_only_dockerfile_declares_one(self):
        assert list(lc.filename_patterns()) == ["dockerfile"]

    @pytest.mark.parametrize("name", ["Dockerfile", "dockerfile", "Dockerfile.prod"])
    def test_matching_names(self, name):
        assert lc.matches_filename("dockerfile", name)

    @pytest.mark.parametrize("name", ["NotADockerfile", "Dockerfile-prod", "docker file"])
    def test_non_matching_names(self, name):
        assert not lc.matches_filename("dockerfile", name)

    def test_language_without_pattern_never_matches(self):
        assert not lc.matches_filename("python", "anything.py")

    def test_patterns_are_compiled(self):
        import re
        assert isinstance(lc.filename_patterns()["dockerfile"], re.Pattern)


class TestStandards:
    def test_language_standards(self):
        assert lc.standards_for("typescript") == "rules/standards-typescript.md"

    def test_language_without_standards_document(self):
        """rules/ has no csharp document; standards-cshtml.md is razor."""
        assert lc.standards_for("csharp") is None
        assert lc.standards_for("razor") == "rules/standards-cshtml.md"

    def test_dialect_standards(self):
        assert lc.standards_for("sql", "mssql") == "rules/standards-sqlserver.md"
        assert lc.standards_for("sql", "postgresql") == "rules/standards-postgresql.md"

    def test_sql_has_no_dialect_free_standards(self):
        assert lc.standards_for("sql") is None

    def test_unknown_dialect_returns_none(self):
        assert lc.standards_for("sql", "oracle") is None


class TestCommands:
    def test_commands_for_language(self):
        assert lc.commands_for("go") == {
            "build": "go build ./...",
            "test": "go test ./...",
            "format": "gofmt -w .",
        }

    def test_absent_commands_are_none_not_missing(self):
        commands = lc.commands_for("sql")
        assert set(commands) == {"build", "test", "format"}
        assert all(value is None for value in commands.values())

    def test_unknown_language_still_returns_all_keys(self):
        assert lc.commands_for("klingon") == {"build": None, "test": None, "format": None}


class TestDialects:
    def test_languages_with_dialects(self):
        assert set(lc.dialects("sql")) == {"mssql", "postgresql"}
        assert set(lc.dialects("vue")) == {"typescript", "javascript"}

    def test_language_without_dialects(self):
        assert lc.dialects("python") == {}

    @pytest.mark.parametrize(
        "content",
        ["CREATE TABLE t (a NVARCHAR(9))\nGO\n", "SELECT * FROM [dbo].[Users]", "  go  "],
    )
    def test_detect_mssql(self, content):
        assert lc.detect_dialect("sql", content) == "mssql"

    @pytest.mark.parametrize(
        "content",
        ["CREATE TABLE t (id SERIAL)", "SELECT id::text FROM t", "INSERT INTO t VALUES (1) RETURNING id"],
    )
    def test_detect_postgresql(self, content):
        assert lc.detect_dialect("sql", content) == "postgresql"

    def test_ambiguous_sql_is_not_guessed(self):
        """SQL declares no default: a file matching nothing must stay unassigned."""
        assert lc.detect_dialect("sql", "SELECT 1") is None

    def test_strongest_signal_wins_when_both_match(self):
        content = "CREATE TABLE t (id SERIAL, name NVARCHAR(9))\nGO\nSELECT id::text RETURNING id"
        assert lc.detect_dialect("sql", content) == "postgresql"

    def test_detect_vue_typescript(self):
        assert lc.detect_dialect("vue", '<script setup lang="ts">') == "typescript"

    def test_vue_single_quotes(self):
        assert lc.detect_dialect("vue", "<script lang='ts'>") == "typescript"

    def test_vue_falls_back_to_declared_default(self):
        assert lc.detect_dialect("vue", "<script>") == "javascript"

    def test_language_without_dialects_returns_none(self):
        assert lc.detect_dialect("python", "class Foo: pass") is None

    def test_unknown_language_returns_none(self):
        assert lc.detect_dialect("klingon", "anything") is None
