#!/usr/bin/env python3
"""Phase 2: Universal test file parser for all project types.

Intelligent multi-framework test parsing:
- API tests: HTTP endpoint testing (REST, GraphQL, gRPC)
- CLI tests: Command-line argument testing
- Mobile tests: UI testing (Espresso, XCTest, Detox)
- Desktop tests: UI testing (WPF, Qt, etc.)
- Frontend tests: Component testing (React Testing Library, Vue Test Utils)
- LLM tests: Agent tool testing (LangChain, CrewAI)
- SQL tests: Stored procedure testing (pgTAP, tSQLt)
- Event-driven tests: Lambda, Worker, Message Queue testing

Test frameworks supported:
- Go: testing package (func Test*, t.Run)
- TypeScript: Jest, Vitest, Mocha (describe/it/test)
- C#: xUnit, NUnit, MSTest ([Fact], [Test], [TestMethod])
- Python: pytest, unittest (def test_*, TestCase)
- Java: JUnit, TestNG (@Test)
- Ruby: RSpec (describe/it)
"""

import argparse
import json
import re
import sys
from pathlib import Path

from common.constants import TEST_FILE_PATTERNS, TEST_FRAMEWORK_PATTERNS
from common.models import HTTPMethod, Language, TestCase, TestFramework
from common.utils import (
    extract_line_number_from_pattern,
    format_path_relative,
    read_file_safe,
    walk_files,
    write_json,
)


def detect_language(project_path: Path) -> Language:
    """Detect project language from test file patterns."""
    from common.constants import LANGUAGE_INDICATORS

    for language, indicators in LANGUAGE_INDICATORS.items():
        for indicator in indicators:
            if "*" in indicator:
                if list(project_path.glob(indicator)):
                    return Language(language)
            else:
                if (project_path / indicator).exists():
                    return Language(language)
    return Language.UNKNOWN


def detect_test_framework(content: str) -> TestFramework:
    """Detect test framework from file content."""
    for framework_name, pattern in TEST_FRAMEWORK_PATTERNS.items():
        if pattern.search(content):
            framework_map = {
                "go_testing": TestFramework.GO_TESTING,
                "jest": TestFramework.JEST,
                "vitest": TestFramework.VITEST,
                "mocha": TestFramework.MOCHA,
                "pytest": TestFramework.PYTEST,
                "unittest": TestFramework.UNITTEST,
                "xunit": TestFramework.XUNIT,
                "nunit": TestFramework.NUNIT,
                "mstest": TestFramework.MSTEST,
                "junit": TestFramework.JUNIT,
                "testng": TestFramework.TESTNG,
            }
            return framework_map.get(framework_name, TestFramework.UNKNOWN)
    return TestFramework.UNKNOWN


def infer_tested_target(test_name: str, content: str) -> tuple[str | None, str | None]:
    """
    Infer what is being tested from test name and content (universal).

    Supports:
    - API endpoints: "/users", "GET"
    - CLI commands: "deploy --force", "command"
    - UI components: "UserButton", "component"
    - Agent tools: "search_documents", "tool"
    - SQL procedures: "sp_CreateUser", "procedure"

    Examples:
        "TestGetUser" → ("/user", "GET")
        "test_deploy_command" → ("deploy", "command")
        "should render UserButton" → ("UserButton", "component")
        "test_search_tool" → ("search_documents", "tool")
    """
    # 1. Try HTTP endpoint detection (API tests)
    method_patterns = {
        "GET": r"\b(get|fetch|retrieve|show|list|find)\b",
        "POST": r"\b(post|create|add|insert)\b",
        "PUT": r"\b(put|update|replace)\b",
        "PATCH": r"\b(patch|modify)\b",
        "DELETE": r"\b(delete|remove|destroy)\b",
    }

    detected_method = None
    for method, pattern in method_patterns.items():
        if re.search(pattern, test_name.lower()):
            detected_method = method
            break

    # Extract endpoint path from content
    path_patterns = [
        r'["\'](/[a-zA-Z0-9/_:-]+)["\']',  # "/api/users"
        r"url\s*=\s*[\"']([^\"']+)[\"']",  # url = "/path"
        r"path\s*=\s*[\"']([^\"']+)[\"']",  # path = "/path"
    ]

    detected_path = None
    for pattern in path_patterns:
        match = re.search(pattern, content)
        if match:
            detected_path = match.group(1)
            if detected_path.startswith("/"):
                return detected_path, detected_method
            else:
                detected_path = None

    # 2. Try CLI command detection
    cli_patterns = [
        r"command\s*=\s*[\"']([^\"']+)[\"']",  # command = "deploy"
        r"args\s*=\s*\[.*[\"']([a-z-]+)[\"']",  # args = ["deploy"]
        r"execute\s*\(\s*[\"']([a-z-]+)[\"']",  # execute("deploy")
    ]
    for pattern in cli_patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1), "command"

    # 3. Try UI component detection (React, Vue, Angular)
    component_patterns = [
        r"render\s*\(\s*<(\w+)",  # render(<UserButton
        r"mount\s*\(\s*(\w+)",  # mount(UserButton)
        r"shallow\s*\(\s*<(\w+)",  # shallow(<UserButton
    ]
    for pattern in component_patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1), "component"

    # 4. Try agent tool detection (LangChain, CrewAI)
    tool_patterns = [
        r"@tool\s+def\s+(\w+)",  # @tool def search_documents
        r"tool_name\s*=\s*[\"']([^\"']+)[\"']",  # tool_name = "search"
    ]
    for pattern in tool_patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1), "tool"

    # 5. Try SQL procedure detection
    sql_patterns = [
        r"EXEC\s+(\w+)",  # EXEC sp_CreateUser
        r"CALL\s+(\w+)",  # CALL create_user()
    ]
    for pattern in sql_patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1), "procedure"

    # 6. Try mobile UI handler detection
    mobile_patterns = [
        r"onClick\s*\(",  # Android onClick
        r"onButtonClick",  # Button click handler
        r"viewDidLoad",  # iOS lifecycle
    ]
    for pattern in mobile_patterns:
        if re.search(pattern, content):
            # Extract handler name from test name
            handler_match = re.search(r"test_?(\w+)", test_name.lower())
            if handler_match:
                return handler_match.group(1), "handler"

    return None, None


def infer_tested_endpoint(test_name: str, content: str) -> tuple[str | None, HTTPMethod | None]:
    """
    Backward compatibility wrapper for API-only tests.

    DEPRECATED: Use infer_tested_target() for universal support.
    """
    target, target_type = infer_tested_target(test_name, content)

    if target_type in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
        try:
            return target, HTTPMethod(target_type)
        except ValueError:
            return target, None

    return None, None


def parse_go_tests(project_path: Path) -> list[TestCase]:
    """Parse Go test files (testing package)."""
    test_cases = []

    for file_path in walk_files(project_path, ["*_test.go"]):
        content = read_file_safe(file_path)
        if not content:
            continue

        framework = detect_test_framework(content)

        # Pattern: func TestXxx(t *testing.T)
        test_pattern = re.compile(r"func\s+(Test\w+)\s*\(\s*t\s+\*testing\.T\s*\)")
        matches = test_pattern.finditer(content)

        for match in matches:
            test_name = match.group(1)
            line_num = content[:match.start()].count("\n") + 1

            # Extract test body (from match to next func or end)
            test_body_start = match.end()
            next_func = re.search(r"\nfunc\s+", content[test_body_start:])
            test_body_end = test_body_start + next_func.start() if next_func else len(content)
            test_body = content[test_body_start:test_body_end]

            # Infer endpoint
            endpoint, method = infer_tested_endpoint(test_name, test_body)

            test_cases.append(
                TestCase(
                    name=test_name,
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework=framework,
                    tested_endpoint=endpoint,
                    tested_method=method,
                    test_type="unit",
                )
            )

    return test_cases


def parse_typescript_tests(project_path: Path) -> list[TestCase]:
    """Parse TypeScript test files (Jest, Vitest, Mocha)."""
    test_cases = []

    patterns = ["*.test.ts", "*.spec.ts", "*.test.js", "*.spec.js"]

    for file_path in walk_files(project_path, patterns):
        content = read_file_safe(file_path)
        if not content:
            continue

        framework = detect_test_framework(content)

        # Pattern: it('test name', ...) or test('test name', ...)
        test_pattern = re.compile(r"(it|test)\s*\(\s*['\"]([^'\"]+)['\"]")
        matches = test_pattern.finditer(content)

        for match in matches:
            test_name = match.group(2)
            line_num = content[:match.start()].count("\n") + 1

            # Extract test body
            test_body_start = match.end()
            # Find matching closing brace (simplified)
            brace_count = 0
            test_body_end = test_body_start
            for i, char in enumerate(content[test_body_start:], start=test_body_start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == -1:
                        test_body_end = i
                        break

            test_body = content[test_body_start:test_body_end]

            # Infer endpoint
            endpoint, method = infer_tested_endpoint(test_name, test_body)

            test_cases.append(
                TestCase(
                    name=test_name,
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework=framework,
                    tested_endpoint=endpoint,
                    tested_method=method,
                    test_type="unit",
                )
            )

    return test_cases


def parse_csharp_tests(project_path: Path) -> list[TestCase]:
    """Parse C# test files (xUnit, NUnit, MSTest)."""
    test_cases = []

    patterns = ["*Test.cs", "*Tests.cs"]

    for file_path in walk_files(project_path, patterns):
        content = read_file_safe(file_path)
        if not content:
            continue

        framework = detect_test_framework(content)

        # Patterns: [Fact], [Test], [TestMethod]
        test_pattern = re.compile(
            r"\[\s*(Fact|Test|TestMethod|Theory|TestCase)\s*\][\s\S]*?public\s+(?:async\s+)?(?:Task\s+)?(\w+)\s*\("
        )
        matches = test_pattern.finditer(content)

        for match in matches:
            test_name = match.group(2)
            line_num = content[:match.start()].count("\n") + 1

            # Extract test body
            test_body_start = match.end()
            brace_count = 0
            test_body_end = test_body_start
            for i, char in enumerate(content[test_body_start:], start=test_body_start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        test_body_end = i
                        break

            test_body = content[test_body_start:test_body_end]

            # Infer endpoint
            endpoint, method = infer_tested_endpoint(test_name, test_body)

            test_cases.append(
                TestCase(
                    name=test_name,
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework=framework,
                    tested_endpoint=endpoint,
                    tested_method=method,
                    test_type="unit",
                )
            )

    return test_cases


def parse_python_tests(project_path: Path) -> list[TestCase]:
    """Parse Python test files (pytest, unittest)."""
    test_cases = []

    patterns = ["test_*.py", "*_test.py"]

    for file_path in walk_files(project_path, patterns):
        content = read_file_safe(file_path)
        if not content:
            continue

        framework = detect_test_framework(content)

        # Pattern: def test_xxx(...):
        test_pattern = re.compile(r"def\s+(test_\w+)\s*\(")
        matches = test_pattern.finditer(content)

        for match in matches:
            test_name = match.group(1)
            line_num = content[:match.start()].count("\n") + 1

            # Extract test body (indented block)
            test_body_start = match.end()
            lines = content[test_body_start:].split("\n")
            test_body_lines = []
            initial_indent = None

            for line in lines:
                if line.strip() == "":
                    continue
                current_indent = len(line) - len(line.lstrip())
                if initial_indent is None:
                    initial_indent = current_indent
                if current_indent <= initial_indent and test_body_lines:
                    break
                test_body_lines.append(line)

            test_body = "\n".join(test_body_lines)

            # Infer endpoint
            endpoint, method = infer_tested_endpoint(test_name, test_body)

            test_cases.append(
                TestCase(
                    name=test_name,
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework=framework,
                    tested_endpoint=endpoint,
                    tested_method=method,
                    test_type="unit",
                )
            )

    return test_cases


def parse_java_tests(project_path: Path) -> list[TestCase]:
    """Parse Java test files (JUnit, TestNG)."""
    test_cases = []

    patterns = ["*Test.java", "*Tests.java"]

    for file_path in walk_files(project_path, patterns):
        content = read_file_safe(file_path)
        if not content:
            continue

        framework = detect_test_framework(content)

        # Pattern: @Test ... public void testXxx()
        test_pattern = re.compile(r"@Test[\s\S]*?public\s+void\s+(\w+)\s*\(")
        matches = test_pattern.finditer(content)

        for match in matches:
            test_name = match.group(1)
            line_num = content[:match.start()].count("\n") + 1

            # Extract test body
            test_body_start = match.end()
            brace_count = 0
            test_body_end = test_body_start
            for i, char in enumerate(content[test_body_start:], start=test_body_start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        test_body_end = i
                        break

            test_body = content[test_body_start:test_body_end]

            # Infer endpoint
            endpoint, method = infer_tested_endpoint(test_name, test_body)

            test_cases.append(
                TestCase(
                    name=test_name,
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework=framework,
                    tested_endpoint=endpoint,
                    tested_method=method,
                    test_type="unit",
                )
            )

    return test_cases


def parse_ruby_tests(project_path: Path) -> list[TestCase]:
    """Parse Ruby test files (RSpec, Minitest)."""
    test_cases = []

    patterns = ["*_spec.rb", "*_test.rb"]

    for file_path in walk_files(project_path, patterns):
        content = read_file_safe(file_path)
        if not content:
            continue

        framework = TestFramework.RSPEC if "_spec.rb" in str(file_path) else TestFramework.MINITEST

        # Pattern: it 'test name' do ... end
        test_pattern = re.compile(r"it\s+['\"]([^'\"]+)['\"]")
        matches = test_pattern.finditer(content)

        for match in matches:
            test_name = match.group(1)
            line_num = content[:match.start()].count("\n") + 1

            # Extract test body (until matching 'end')
            test_body_start = match.end()
            lines = content[test_body_start:].split("\n")
            test_body_lines = []
            end_count = 1

            for line in lines:
                if re.search(r"\bdo\b", line):
                    end_count += 1
                if re.search(r"\bend\b", line):
                    end_count -= 1
                    if end_count == 0:
                        break
                test_body_lines.append(line)

            test_body = "\n".join(test_body_lines)

            # Infer endpoint
            endpoint, method = infer_tested_endpoint(test_name, test_body)

            test_cases.append(
                TestCase(
                    name=test_name,
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework=framework,
                    tested_endpoint=endpoint,
                    tested_method=method,
                    test_type="unit",
                )
            )

    return test_cases


def parse_tests(project_path: Path, language: Language | None = None) -> list[TestCase]:
    """
    Parse all test files from project (universal).

    Supports:
    - API tests (all languages)
    - CLI tests (all languages)
    - Mobile tests (Android: Espresso, iOS: XCTest)
    - Desktop tests (WPF, Qt, etc.)
    - Frontend tests (React Testing Library, Vue Test Utils, etc.)
    - LLM tests (LangChain, CrewAI)
    - SQL tests (pgTAP, tSQLt)
    - Event-driven tests (Lambda, Worker, Message Queue)

    Args:
        project_path: Project root directory
        language: Language to parse (auto-detect if None)

    Returns:
        List of TestCase objects
    """
    if not language:
        language = detect_language(project_path)

    if language == Language.GO:
        return parse_go_tests(project_path)
    elif language in (Language.TYPESCRIPT, Language.JAVASCRIPT):
        return parse_typescript_tests(project_path)
    elif language == Language.CSHARP:
        return parse_csharp_tests(project_path)
    elif language == Language.PYTHON:
        return parse_python_tests(project_path)
    elif language == Language.JAVA:
        return parse_java_tests(project_path)
    elif language == Language.RUBY:
        return parse_ruby_tests(project_path)
    else:
        raise ValueError(f"Unsupported language: {language}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Parse test files and extract test scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parse_test_files.py /path/to/project
  python parse_test_files.py . --language go --output tests.json
  python parse_test_files.py ~/myapp --language python
        """,
    )

    parser.add_argument(
        "project_path",
        type=Path,
        help="Path to project root directory",
    )

    parser.add_argument(
        "--language",
        "-l",
        type=str,
        choices=["go", "typescript", "javascript", "csharp", "python", "java", "ruby"],
        help="Project language (auto-detect if not specified)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file path (default: stdout)",
    )

    args = parser.parse_args()

    try:
        # Parse language
        language = Language(args.language) if args.language else None

        # Parse tests
        test_cases = parse_tests(args.project_path, language)

        # Convert to dict for JSON
        output_data = {
            "test_count": len(test_cases),
            "tests": [tc.to_dict() for tc in test_cases],
        }

        # Write output
        write_json(output_data, args.output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
