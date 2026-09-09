"""Unit tests for checkers/check_resource_leaks.py — mechanical layer only (server patched off)."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from checkers import check_resource_leaks


def _run(tmp_path: Path, name: str, content: str, language: str) -> list[dict]:
    f = tmp_path / name
    f.write_text(content)
    with patch("common.hybrid.check_server_available", return_value=False):
        result = check_resource_leaks.run(tmp_path, language, files=[f])
    assert result["success"] is True
    assert result["principle"] == "ResourceLeak"
    return result["violations"]


class TestCSharpChecks:
    def test_detects_undisposed_connection(self, tmp_path):
        v = _run(tmp_path, "Repo.cs", "var conn = new SqlConnection(cs);\n", "csharp")
        assert any("without a using block" in x["message"] for x in v)

    def test_using_declaration_is_clean(self, tmp_path):
        v = _run(tmp_path, "Repo.cs", "using var conn = new SqlConnection(cs);\n", "csharp")
        assert v == []

    def test_using_statement_is_clean(self, tmp_path):
        v = _run(tmp_path, "Repo.cs", "using (new StreamReader(path))\n", "csharp")
        assert v == []

    def test_detects_blocking_result(self, tmp_path):
        v = _run(tmp_path, "Repo.cs", "var data = FetchAsync().Result;\n", "csharp")
        assert any(".Result" in x["message"] for x in v)

    def test_detects_blocking_wait(self, tmp_path):
        v = _run(tmp_path, "Repo.cs", "FetchAsync().Wait();\n", "csharp")
        assert any(".Wait()" in x["message"] for x in v)

    def test_detects_async_void(self, tmp_path):
        v = _run(tmp_path, "Worker.cs", "public async void Process()\n", "csharp")
        assert any("async void" in x["message"] for x in v)

    def test_detects_get_awaiter_get_result(self, tmp_path):
        v = _run(tmp_path, "Repo.cs", "var d = FetchAsync().GetAwaiter().GetResult();\n", "csharp")
        assert any("Synchronous wait" in x["message"] for x in v)

    def test_awaited_call_is_clean(self, tmp_path):
        code = "public async Task<Data> Process()\n{\n    return await FetchAsync();\n}\n"
        assert _run(tmp_path, "Worker.cs", code, "csharp") == []


class TestPythonChecks:
    def test_detects_open_outside_with(self, tmp_path):
        v = _run(tmp_path, "io.py", 'handle = open("data.txt")\n', "python")
        assert any("outside a with block" in x["message"] for x in v)

    def test_with_statement_is_clean(self, tmp_path):
        code = 'with open("data.txt") as handle:\n    data = handle.read()\n'
        assert _run(tmp_path, "io.py", code, "python") == []

    def test_detects_socket_outside_with(self, tmp_path):
        v = _run(tmp_path, "net.py", "sock = socket.socket(AF_INET, SOCK_STREAM)\n", "python")
        assert any("outside a with block" in x["message"] for x in v)

    def test_detects_executor_without_context_manager(self, tmp_path):
        v = _run(tmp_path, "pool.py", "pool = ThreadPoolExecutor(max_workers=4)\n", "python")
        assert any("without a context manager" in x["message"] for x in v)

    def test_executor_context_manager_is_clean(self, tmp_path):
        code = "with ThreadPoolExecutor(max_workers=4) as pool:\n    pool.submit(work)\n"
        assert _run(tmp_path, "pool.py", code, "python") == []

    def test_detects_unreferenced_task(self, tmp_path):
        v = _run(tmp_path, "tasks.py", "asyncio.create_task(worker())\n", "python")
        assert any("garbage collected" in x["message"] for x in v)


class TestJavaScriptChecks:
    def test_detects_unawaited_persistence_call(self, tmp_path):
        v = _run(tmp_path, "repo.js", "  repo.save(user);\n", "javascript")
        assert any("not awaited" in x["message"] for x in v)

    def test_awaited_call_is_clean(self, tmp_path):
        assert _run(tmp_path, "repo.js", "  await repo.save(user);\n", "javascript") == []

    def test_returned_call_is_clean(self, tmp_path):
        assert _run(tmp_path, "repo.js", "  return repo.save(user);\n", "javascript") == []

    def test_chained_catch_is_clean(self, tmp_path):
        assert _run(tmp_path, "repo.js", "  repo.save(user).catch(log);\n", "javascript") == []

    def test_detects_stream_creation(self, tmp_path):
        v = _run(tmp_path, "io.js", "const s = fs.createReadStream(path);\n", "javascript")
        assert any("Stream created" in x["message"] for x in v)

    def test_detects_uncleared_interval(self, tmp_path):
        v = _run(tmp_path, "poll.js", "setInterval(poll, 1000);\n", "javascript")
        assert any("clearInterval" in x["message"] for x in v)

    def test_typescript_shares_javascript_rules(self, tmp_path):
        v = _run(tmp_path, "poll.ts", "setInterval(poll, 1000);\n", "typescript")
        assert any("clearInterval" in x["message"] for x in v)


class TestOtherLanguages:
    def test_detects_powershell_stream_reader(self, tmp_path):
        v = _run(tmp_path, "io.ps1", "$r = New-Object System.IO.StreamReader $path\n", "powershell")
        assert any("without a using block" in x["message"] for x in v)

    def test_detects_powershell_sql_connection(self, tmp_path):
        code = "$c = New-Object System.Data.SqlClient.SqlConnection $cs\n"
        v = _run(tmp_path, "db.ps1", code, "powershell")
        assert len(v) == 1

    def test_go_has_no_mechanical_rules(self, tmp_path):
        code = "f, _ := os.Open(path)\n_ = f\n"
        assert _run(tmp_path, "io.go", code, "go") == []
