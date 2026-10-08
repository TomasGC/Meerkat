#!/usr/bin/env python3
"""Tests for parse_test_files.py — unit tests"""

import json
import sys
from unittest.mock import patch

import pytest

import bba.model_utils as model_utils
from bba.models import HTTPMethod, Language, TestFramework
from parse_test_files import (
    _classify_by_regex,
    detect_test_framework,
    infer_test_type,
    infer_tested_endpoint,
    infer_tested_target,
)
from parse_test_files import main as parse_main
from parse_test_files import (
    parse_csharp_tests,
    parse_go_tests,
    parse_java_tests,
    parse_python_tests,
    parse_ruby_tests,
    parse_tests,
    parse_typescript_tests,
)


@pytest.fixture(autouse=True)
def no_local_ai():
    """Ambiguous test bodies fall back to the local AI: keep it switched off unless a test says otherwise."""
    with patch.object(model_utils, "check_server_available", return_value=False):
        yield


def test_classify_by_regex_e2e_cypress():
    assert _classify_by_regex("import cypress from 'cypress'") == "e2e"


def test_classify_by_regex_e2e_playwright():
    assert _classify_by_regex("await page.goto('/')") is None
    assert _classify_by_regex("playwright.launch()") == "e2e"


def test_classify_by_regex_e2e_selenium():
    assert _classify_by_regex("WebDriver driver = new ChromeDriver()") == "e2e"


def test_classify_by_regex_int_real_testcontainers():
    assert _classify_by_regex("testcontainers.start()") == "int_real"


def test_classify_by_regex_int_real_http_client():
    assert _classify_by_regex("requests.get('http://api/users')") == "int_real"


def test_classify_by_regex_int_real_real_file():
    assert _classify_by_regex("os.Open('/tmp/data.csv')") == "int_real"


def test_classify_by_regex_int_mock_mockito():
    assert _classify_by_regex("Mockito.when(repo.find()).thenReturn(user)") == "int_mock"


def test_classify_by_regex_int_mock_unittest_mock():
    assert _classify_by_regex("@patch('app.service.db')") == "int_mock"


def test_classify_by_regex_int_mock_jest():
    assert _classify_by_regex("jest.fn()") == "int_mock"


def test_classify_by_regex_ambiguous_returns_none():
    assert _classify_by_regex("assert result == 42") is None


def test_classify_by_regex_e2e_takes_priority_over_mock():
    assert _classify_by_regex("cypress.visit(); mock.setup()") == "e2e"


def test_infer_test_type_empty_body_returns_unit():
    assert infer_test_type("test_something", "") == "unit"


def test_infer_test_type_whitespace_body_returns_unit():
    assert infer_test_type("test_something", "   \n  ") == "unit"


def test_infer_test_type_e2e_playwright():
    body = "const page = await playwright.chromium.launch();\nawait page.goto('/')"
    assert infer_test_type("test_login_flow", body) == "e2e"


def test_infer_test_type_int_mock_magicmock():
    body = "mock_db = MagicMock()\nmock_db.get.return_value = None\nassert mock_db.get.called"
    assert infer_test_type("test_get_item", body) == "int_mock"


def test_infer_test_type_int_real_requests():
    body = "response = requests.get('http://localhost:8080/api')\nassert response.status_code == 200"
    assert infer_test_type("test_get_users_real", body) == "int_real"


def test_infer_test_type_pure_logic_returns_valid():
    body = "result = add(2, 3)\nassert result == 5"
    result = infer_test_type("test_add", body)
    assert result in ("unit", "int_mock", "int_real", "e2e")


def test_parse_go_tests_count(sample_go_project):
    cases = parse_go_tests(sample_go_project)
    assert len(cases) == 3


def test_parse_go_tests_names(sample_go_project):
    cases = parse_go_tests(sample_go_project)
    names = {tc.name for tc in cases}
    assert "TestGetUser" in names
    assert "TestCreateUser" in names
    assert "TestCreateUserInvalidInput" in names


def test_parse_go_tests_framework(sample_go_project):
    cases = parse_go_tests(sample_go_project)
    for tc in cases:
        assert tc.framework == TestFramework.GO_TESTING


def test_parse_python_tests_count(sample_python_project):
    cases = parse_python_tests(sample_python_project)
    assert len(cases) == 4


def test_parse_python_tests_names(sample_python_project):
    cases = parse_python_tests(sample_python_project)
    names = {tc.name for tc in cases}
    assert "test_get_item_success" in names
    assert "test_create_item_invalid_data" in names


def test_parse_typescript_tests_count(sample_typescript_project):
    cases = parse_typescript_tests(sample_typescript_project)
    assert len(cases) == 4


def test_parse_typescript_tests_names(sample_typescript_project):
    cases = parse_typescript_tests(sample_typescript_project)
    names = {tc.name for tc in cases}
    assert "should create a post with valid data" in names
    assert "should return 404 when not found" in names


def test_parse_csharp_tests_count(sample_csharp_project):
    cases = parse_csharp_tests(sample_csharp_project)
    assert len(cases) == 4


def test_parse_csharp_tests_framework_xunit(sample_csharp_project):
    cases = parse_csharp_tests(sample_csharp_project)
    for tc in cases:
        assert tc.framework == TestFramework.XUNIT


def test_parse_tests_go(sample_go_project):
    assert len(parse_tests(sample_go_project, Language.GO)) == 3


def test_parse_tests_python(sample_python_project):
    assert len(parse_tests(sample_python_project, Language.PYTHON)) == 4


def test_parse_tests_unknown_returns_empty(temp_dir):
    assert parse_tests(temp_dir, Language.UNKNOWN) == []


# ── infer_test_type: local AI fallback ──────────────────────────────────────


@pytest.mark.parametrize(
    ("answer", "expected"),
    [("int_real\n", "int_real"), ("E2E because it drives a browser", "e2e"), ("integration", "unit"), ("", "unit")],
)
def test_infer_test_type_uses_first_word_of_ai_answer(answer, expected):
    with (
        patch.object(model_utils, "check_server_available", return_value=True),
        patch.object(model_utils, "run_prompt", return_value=answer) as run_prompt,
    ):
        assert infer_test_type("test_total", "assert total([1, 2]) == 3") == expected
    assert run_prompt.call_args.kwargs["test_name"] == "test_total"


def test_infer_test_type_truncates_body_sent_to_ai():
    with (
        patch.object(model_utils, "check_server_available", return_value=True),
        patch.object(model_utils, "run_prompt", return_value="unit") as run_prompt,
    ):
        infer_test_type("test_long", "x = 1\n" * 500)
    assert len(run_prompt.call_args.kwargs["test_body"]) == 600


def test_infer_test_type_ai_error_falls_back_to_unit():
    with (
        patch.object(model_utils, "check_server_available", return_value=True),
        patch.object(model_utils, "run_prompt", side_effect=RuntimeError("server gone")),
    ):
        assert infer_test_type("test_total", "assert total([1, 2]) == 3") == "unit"


def test_infer_test_type_ai_unavailable_is_unit_without_prompt():
    with patch.object(model_utils, "run_prompt") as run_prompt:
        assert infer_test_type("test_total", "assert total([1, 2]) == 3") == "unit"
    run_prompt.assert_not_called()


# ── detect_test_framework ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("func TestX(t *testing.T) {}", TestFramework.GO_TESTING),
        ("describe('x', () => {})", TestFramework.JEST),
        ("def test_x(): pass", TestFramework.PYTEST),
        ("class T(unittest.TestCase): pass", TestFramework.UNITTEST),
        ("[Fact] public void X() {}", TestFramework.XUNIT),
        ("[TestMethod] public void X() {}", TestFramework.MSTEST),
        ("@Test public void x() {}", TestFramework.JUNIT),
        ("#[test] fn x() {}", TestFramework.UNKNOWN),
        ("plain text", TestFramework.UNKNOWN),
    ],
)
def test_detect_test_framework_maps_content_to_framework(content, expected):
    assert detect_test_framework(content) == expected


# ── infer_tested_target / infer_tested_endpoint ─────────────────────────────


@pytest.mark.parametrize(
    ("name", "content", "expected"),
    [
        ("should get the user", 'client.get("/users/1")', ("/users/1", "GET")),
        ("remove an item", "path = '/items/9'", ("/items/9", "DELETE")),
        ("TestHealth", "fetch('/health')", ("/health", None)),
        ("test_ping", 'url = "http://host"\n', (None, None)),
        ("test_deploy", 'command = "deploy --force"', ("deploy --force", "command")),
        ("test_cli", 'args = ["run", "build"]', ("build", "command")),
        ("test_cli_exec", "execute('migrate')", ("migrate", "command")),
        ("renders", "render(<UserButton label='x' />)", ("UserButton", "component")),
        ("mounts", "mount(Counter)", ("Counter", "component")),
        ("tool", "@tool def search_documents(q): ...", ("search_documents", "tool")),
        ("tool name", "tool_name = 'lookup'", ("lookup", "tool")),
        ("proc", "EXEC sp_CreateUser @name", ("sp_CreateUser", "procedure")),
        ("proc call", "CALL create_user()", ("create_user", "procedure")),
        ("test_login_button", "button.onClick()", ("login_button", "handler")),
        ("nothing", "assert 1 == 1", (None, None)),
    ],
)
def test_infer_tested_target_recognises_each_target_kind(name, content, expected):
    assert infer_tested_target(name, content) == expected


def test_infer_tested_endpoint_converts_verb_to_http_method():
    assert infer_tested_endpoint("create an order", 'post("/orders")') == ("/orders", HTTPMethod.POST)


@pytest.mark.parametrize("name", ["TestGetUser", "test_get_user", "getUserReturnsUser"])
def test_infer_tested_target_reads_verb_from_code_style_names(name):
    assert infer_tested_target(name, 'client.get("/users/1")') == ("/users/1", "GET")


def test_infer_tested_endpoint_keeps_path_without_verb():
    assert infer_tested_endpoint("TestHealth", 'call("/health")') == ("/health", None)


def test_infer_tested_endpoint_drops_non_http_targets():
    assert infer_tested_endpoint("test_deploy", 'command = "deploy"') == ("deploy", None)


def test_infer_tested_endpoint_nothing_found():
    assert infer_tested_endpoint("test_math", "assert 2 + 2 == 4") == (None, None)


# ── per-language parsers ────────────────────────────────────────────────────


def test_parsers_skip_empty_test_files(temp_dir):
    (temp_dir / "empty_test.go").write_text("")
    (temp_dir / "empty.test.ts").write_text("")
    (temp_dir / "EmptyTests.cs").write_text("")
    (temp_dir / "test_empty.py").write_text("")
    (temp_dir / "EmptyTest.java").write_text("")
    (temp_dir / "empty_spec.rb").write_text("")
    for parser in (
        parse_go_tests,
        parse_typescript_tests,
        parse_csharp_tests,
        parse_python_tests,
        parse_java_tests,
        parse_ruby_tests,
    ):
        assert parser(temp_dir) == []


def test_parse_go_tests_infers_endpoint_and_type(temp_dir):
    (temp_dir / "api_test.go").write_text(
        "package api\n\nfunc TestGetUser(t *testing.T) {\n"
        '    srv := httptest.NewServer(h)\n    get(srv.URL + "/users/1")\n}\n'
    )
    [case] = parse_go_tests(temp_dir)
    assert case.line_number == 3
    assert case.tested_endpoint == "/users/1"
    assert case.test_type == "int_real"


def test_parse_java_tests_extracts_junit_methods(temp_dir):
    src = temp_dir / "src" / "test" / "java"
    src.mkdir(parents=True)
    (src / "UserServiceTest.java").write_text(
        "import org.junit.jupiter.api.Test;\n\nclass UserServiceTest {\n"
        "    @Test\n    public void getUserReturnsUser() {\n"
        '        Mockito.when(repo.find("/users/1")).thenReturn(user);\n    }\n\n'
        "    @Test\n    public void deleteUserRemovesRow() {\n        service.delete(1);\n    }\n}\n"
    )
    cases = parse_java_tests(temp_dir)
    assert [c.name for c in cases] == ["getUserReturnsUser", "deleteUserRemovesRow"]
    first, second = cases
    assert first.framework == TestFramework.JUNIT
    assert first.file_path.replace("\\", "/") == "src/test/java/UserServiceTest.java"
    assert first.tested_endpoint == "/users/1"
    assert first.test_type == "int_mock"
    assert second.test_type == "unit"


def test_parse_ruby_tests_frameworks_follow_file_suffix(temp_dir):
    (temp_dir / "user_spec.rb").write_text("describe 'User' do\n  it 'saves' do\n    x = 1\n  end\nend\n")
    (temp_dir / "order_test.rb").write_text("class OrderTest\n  it 'totals' do\n    y = 2\n  end\nend\n")
    frameworks = {c.name: c.framework for c in parse_ruby_tests(temp_dir)}
    assert frameworks == {"saves": TestFramework.RSPEC, "totals": TestFramework.MINITEST}


def test_parse_ruby_tests_detects_selenium_test_as_e2e(temp_dir):
    (temp_dir / "login_spec.rb").write_text(
        "describe 'Login' do\n  it 'opens the page' do\n    selenium.visit('/login')\n  end\nend\n"
    )
    [case] = parse_ruby_tests(temp_dir)
    assert case.name == "opens the page"
    assert case.line_number == 2
    assert case.tested_endpoint == "/login"
    assert case.test_type == "e2e"


def test_parse_ruby_tests_body_stops_at_its_own_end(temp_dir):
    (temp_dir / "users_spec.rb").write_text(
        "describe 'Users' do\n"
        "  it 'creates user' do\n    expect(1).to eq(1)\n  end\n\n"
        "  it 'lists users' do\n    selenium.visit('/users')\n  end\nend\n"
    )
    types = {c.name: c.test_type for c in parse_ruby_tests(temp_dir)}
    assert types == {"creates user": "unit", "lists users": "e2e"}


def test_parse_python_tests_body_stops_at_next_function(temp_dir):
    (temp_dir / "test_calc.py").write_text(
        "def test_a():\n    x = 1\n    assert x == 1\n\n\n" "def test_b():\n    m = MagicMock()\n    assert m\n"
    )
    types = {c.name: c.test_type for c in parse_python_tests(temp_dir)}
    assert types == {"test_a": "unit", "test_b": "int_mock"}


def test_parse_python_tests_body_starts_after_multiline_signature(temp_dir):
    (temp_dir / "test_svc.py").write_text(
        "def test_a(\n    tmp_path,\n):\n    m = MagicMock()\n\n\ndef test_b():\n    assert 1\n"
    )
    types = {c.name: c.test_type for c in parse_python_tests(temp_dir)}
    assert types == {"test_a": "int_mock", "test_b": "unit"}


# ── parse_tests dispatch ────────────────────────────────────────────────────


def test_parse_tests_autodetects_language(sample_go_project):
    assert {c.name for c in parse_tests(sample_go_project)} == {
        "TestGetUser",
        "TestCreateUser",
        "TestCreateUserInvalidInput",
    }


@pytest.mark.parametrize(
    ("language", "filename", "content", "name"),
    [
        (Language.JAVASCRIPT, "a.test.js", "test('adds', () => { expect(1).toBe(1); });", "adds"),
        (Language.TYPESCRIPT, "a.spec.ts", "it('subtracts', () => { expect(0).toBe(0); });", "subtracts"),
        (Language.CSHARP, "CalcTests.cs", "[Fact]\npublic void Adds() { Assert.True(true); }", "Adds"),
        (Language.JAVA, "CalcTest.java", "@Test\npublic void adds() { assertTrue(true); }", "adds"),
        (Language.RUBY, "calc_spec.rb", "it 'adds' do\n  x = 1\nend\n", "adds"),
    ],
)
def test_parse_tests_dispatches_by_language(temp_dir, language, filename, content, name):
    (temp_dir / filename).write_text(content)
    assert [c.name for c in parse_tests(temp_dir, language)] == [name]


# ── main (CLI) ───────────────────────────────────────────────────────────────


def _run_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["parse_test_files.py", *map(str, argv)])
    return parse_main()


def test_main_writes_inventory_and_auto_snapshot(sample_go_project, temp_dir, monkeypatch):
    out = temp_dir / "tests.json"
    assert _run_main(monkeypatch, sample_go_project, "--language", "go", "--output", out) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["test_count"] == 3
    assert {t["name"] for t in data["tests"]} >= {"TestGetUser"}
    snapshot = sample_go_project / ".claude" / "bbanalysis-last-tests.json"
    assert json.loads(snapshot.read_text(encoding="utf-8")) == data


def test_main_save_snapshot_writes_full_inventory(sample_go_project, temp_dir, monkeypatch, capsys):
    snap = temp_dir / "snap.json"
    assert _run_main(monkeypatch, sample_go_project, "--save-snapshot", snap) == 0
    captured = capsys.readouterr()
    assert json.loads(snap.read_text(encoding="utf-8")) == json.loads(captured.out)
    assert "Snapshot saved" in captured.err


def test_main_previous_pass_reports_only_new_tests(sample_go_project, temp_dir, monkeypatch, capsys):
    prev = temp_dir / "prev.json"
    prev.write_text(json.dumps({"tests": [{"name": "TestGetUser"}, {"name": "TestCreateUser"}]}))
    assert _run_main(monkeypatch, sample_go_project, "--previous-pass", prev) == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["new_since_last_pass"] == 1
    assert data["total_in_project"] == 3
    assert [t["name"] for t in data["tests"]] == ["TestCreateUserInvalidInput"]
    assert "1 new / 2 already known" in captured.err


def test_main_unreadable_previous_pass_reports_everything(sample_go_project, temp_dir, monkeypatch, capsys):
    prev = temp_dir / "prev.json"
    prev.write_text("{not json")
    assert _run_main(monkeypatch, sample_go_project, "--previous-pass", prev) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["test_count"] == 3
    assert "Could not load previous pass" in captured.err


def test_main_parse_failure_returns_one(sample_go_project, monkeypatch, capsys):
    with patch("parse_test_files.parse_tests", side_effect=RuntimeError("disk on fire")):
        assert _run_main(monkeypatch, sample_go_project) == 1
    assert "Error: disk on fire" in capsys.readouterr().err
