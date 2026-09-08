#!/usr/bin/env python3
"""Tests for parse_test_files.py — unit tests"""

from pathlib import Path

from parse_test_files import (
    _classify_by_regex,
    infer_test_type,
    parse_csharp_tests,
    parse_go_tests,
    parse_python_tests,
    parse_tests,
    parse_typescript_tests,
)
from common.models import Language, TestFramework

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
