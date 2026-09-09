"""Unit tests for check_error_handling (SSA copy) — mechanical path only (no AI)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from checkers.check_error_handling import run

_PRINCIPLE = "ErrorHandling"


def _make_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


class TestMechanicalChecks:
    def test_detects_bare_except(self, tmp_path):
        code = "try:\n    risky()\nexcept:\n    pass\n"
        f = _make_file(tmp_path, "handler.py", code)
        result = run(tmp_path, "python", files=[f])
        assert any("bare" in v["message"].lower() or "except" in v["message"].lower()
                   for v in result["violations"])

    def test_detects_swallowed_exception(self, tmp_path):
        code = "try:\n    do_work()\nexcept Exception:\n    pass\n"
        f = _make_file(tmp_path, "handler.py", code)
        result = run(tmp_path, "python", files=[f])
        assert any("swallow" in v["message"].lower() or "pass" in v["message"].lower()
                   or "silent" in v["message"].lower() for v in result["violations"])

    def test_clean_file_no_violations(self, tmp_path):
        code = "try:\n    do_work()\nexcept ValueError as e:\n    logger.error(str(e))\n    raise\n"
        f = _make_file(tmp_path, "good.py", code)
        result = run(tmp_path, "python", files=[f])
        assert result["violations"] == []


class TestCSharpChecks:
    def test_detects_empty_catch(self, tmp_path):
        code = "try\n{\n    Process();\n}\ncatch (Exception ex) { }\n"
        f = _make_file(tmp_path, "Service.cs", code)
        result = run(tmp_path, "csharp", files=[f])
        assert any("Empty catch block" == v["message"] for v in result["violations"])

    def test_detects_todo_catch(self, tmp_path):
        code = "catch (Exception ex) { // TODO handle later }\n"
        f = _make_file(tmp_path, "Service.cs", code)
        result = run(tmp_path, "csharp", files=[f])
        assert any("TODO" in v["message"] for v in result["violations"])

    def test_handled_catch_is_clean(self, tmp_path):
        code = "catch (Exception ex)\n{\n    _logger.LogError(ex, \"failed\");\n    throw;\n}\n"
        f = _make_file(tmp_path, "Service.cs", code)
        result = run(tmp_path, "csharp", files=[f])
        assert result["violations"] == []


class TestTypeScriptAndJavaScriptChecks:
    def test_detects_empty_catch_typescript(self, tmp_path):
        f = _make_file(tmp_path, "client.ts", "try { load(); } catch (e) { }\n")
        result = run(tmp_path, "typescript", files=[f])
        assert any("Empty catch block" == v["message"] for v in result["violations"])

    def test_detects_empty_catch_javascript(self, tmp_path):
        f = _make_file(tmp_path, "client.js", "try { load(); } catch (e) { }\n")
        result = run(tmp_path, "javascript", files=[f])
        assert any("Empty catch block" == v["message"] for v in result["violations"])

    def test_logged_catch_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "client.ts", "try { load(); } catch (e) { console.error(e); }\n")
        result = run(tmp_path, "typescript", files=[f])
        assert result["violations"] == []


class TestGoChecks:
    def test_detects_empty_error_block(self, tmp_path):
        f = _make_file(tmp_path, "main.go", "if err != nil {}\n")
        result = run(tmp_path, "go", files=[f])
        assert any("Empty error check block" == v["message"] for v in result["violations"])

    def test_detects_discarded_error(self, tmp_path):
        f = _make_file(tmp_path, "main.go", "_ = file.Close()\n")
        result = run(tmp_path, "go", files=[f])
        assert any("discarded" in v["message"] for v in result["violations"])

    def test_handled_error_is_clean(self, tmp_path):
        code = "if err := file.Close(); err != nil {\n\treturn err\n}\n"
        f = _make_file(tmp_path, "main.go", code)
        result = run(tmp_path, "go", files=[f])
        assert result["violations"] == []


class TestPowerShellChecks:
    def test_detects_empty_catch(self, tmp_path):
        f = _make_file(tmp_path, "deploy.ps1", "try { Copy-Item $src $dst } catch { }\n")
        result = run(tmp_path, "powershell", files=[f])
        assert any("Empty catch block" == v["message"] for v in result["violations"])

    def test_detects_silently_continue(self, tmp_path):
        f = _make_file(tmp_path, "deploy.ps1", "Remove-Item $path -ErrorAction SilentlyContinue\n")
        result = run(tmp_path, "powershell", files=[f])
        assert any("SilentlyContinue" in v["message"] for v in result["violations"])

    def test_stop_action_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "deploy.ps1", "Remove-Item $path -ErrorAction Stop\n")
        result = run(tmp_path, "powershell", files=[f])
        assert result["violations"] == []


class TestBashChecks:
    def test_detects_or_true(self, tmp_path):
        f = _make_file(tmp_path, "build.sh", "make clean || true\n")
        result = run(tmp_path, "bash", files=[f])
        assert any("|| true" in v["message"] for v in result["violations"])

    def test_detects_stderr_discard(self, tmp_path):
        f = _make_file(tmp_path, "build.sh", "rm -f cache 2>/dev/null\n")
        result = run(tmp_path, "bash", files=[f])
        assert any("Stderr" in v["message"] for v in result["violations"])

    def test_strict_mode_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "build.sh", "set -euo pipefail\nmake clean\n")
        result = run(tmp_path, "bash", files=[f])
        assert result["violations"] == []


class TestFileHandling:
    def test_unknown_language_extension_ignored(self, tmp_path):
        f = _make_file(tmp_path, "notes.yaml", "key: value\n")
        result = run(tmp_path, "yaml", files=[f])
        assert result["violations"] == []

    def test_unparseable_python_does_not_raise(self, tmp_path):
        f = _make_file(tmp_path, "broken.py", "def f(:\n")
        result = run(tmp_path, "python", files=[f])
        assert result["success"] is True
        assert result["violations"] == []

    def test_single_file_path_is_accepted(self, tmp_path):
        f = _make_file(tmp_path, "handler.py", "try:\n    x()\nexcept:\n    pass\n")
        result = run(f, "python")
        assert result["files_analyzed"] == 1
        assert result["violations"]

    def test_directory_walk_finds_nested_files(self, tmp_path):
        nested = tmp_path / "src" / "deep"
        nested.mkdir(parents=True)
        (nested / "handler.py").write_text("try:\n    x()\nexcept:\n    pass\n")
        result = run(tmp_path, "python")
        assert result["violations"]

    def test_violation_paths_are_repo_relative(self, tmp_path):
        nested = tmp_path / "src"
        nested.mkdir()
        (nested / "handler.py").write_text("try:\n    x()\nexcept:\n    pass\n")
        result = run(tmp_path, "python")
        assert all(not Path(v["file"]).is_absolute() for v in result["violations"])


class TestRunFunction:
    def test_returns_correct_schema(self, tmp_path):
        result = run(tmp_path, "python")
        assert result["principle"] == _PRINCIPLE
        assert result["success"] is True
        assert "violations" in result
        assert "files_analyzed" in result
        assert "duration_ms" in result

    def test_empty_dir_no_violations(self, tmp_path):
        result = run(tmp_path, "python")
        assert result["violations"] == []
