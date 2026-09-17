#!/usr/bin/env python3
"""Phase 0: Analyze project structure and detect language/frameworks.

Auto-detects:
- Programming language (Go, TypeScript, C#, Python, Java)
- Web frameworks (gin, Express, ASP.NET, FastAPI, Spring Boot)
- Test frameworks (testing, Jest, xUnit, pytest, JUnit)
- Endpoint count (estimated)
- Test file count
"""

import argparse
import json
import re
import sys
from pathlib import Path

from common.constants import (
    API_PATH_PREFIXES,
    BLOCKCHAIN_PATTERNS,
    CLI_PATTERNS,
    DESKTOP_PATTERNS,
    ENDPOINT_PATTERNS,
    FRAMEWORK_PATTERNS,
    FRONTEND_PATTERNS,
    FULLSTACK_PATTERNS,
    LANGUAGE_INDICATORS,
    LLM_PATTERNS,
    MESSAGE_QUEUE_PATTERNS,
    MOBILE_PATTERNS,
    PROJECT_TYPE_FILE_MARKERS,
    SERVERLESS_PATTERNS,
    SQL_PATTERNS,
    TEST_FILE_PATTERNS,
    TEST_FRAMEWORK_PATTERNS,
    WORKER_PATTERNS,
)
from common.models import Language, ProjectInfo, ProjectType, TestFramework
from common.utils import find_project_root, read_file_safe, walk_files


def detect_language(project_path: Path) -> Language:
    """
    Detect project language from indicator files.

    Args:
        project_path: Project root directory

    Returns:
        Detected Language enum
    """
    for language, indicators in LANGUAGE_INDICATORS.items():
        for indicator in indicators:
            if "*" in indicator:
                # Glob pattern
                if list(project_path.glob(indicator)):
                    return Language(language)
            else:
                # Exact file
                if (project_path / indicator).exists():
                    return Language(language)

    return Language.UNKNOWN


def detect_frameworks(project_path: Path, language: Language) -> list[str]:
    """
    Detect web frameworks from package files.

    Args:
        project_path: Project root directory
        language: Detected language

    Returns:
        List of detected framework names
    """
    frameworks = []

    # Language-specific package files
    package_files = {
        Language.GO: ["go.mod"],
        Language.TYPESCRIPT: ["package.json"],
        Language.JAVASCRIPT: ["package.json"],
        Language.CSHARP: ["*.csproj"],
        Language.PYTHON: ["requirements.txt", "pyproject.toml"],
        Language.JAVA: ["pom.xml", "build.gradle"],
        Language.KOTLIN: ["build.gradle.kts"],
        Language.RUST: ["Cargo.toml"],
        Language.SWIFT: ["Package.swift"],
    }

    files_to_check = package_files.get(language, [])

    for file_pattern in files_to_check:
        if "*" in file_pattern:
            # Glob pattern
            matching_files = list(project_path.glob(file_pattern))
        else:
            # Exact file
            matching_files = [project_path / file_pattern] if (project_path / file_pattern).exists() else []

        for file_path in matching_files:
            content = read_file_safe(file_path)
            if not content:
                continue

            # Check each framework pattern
            for framework_name, pattern in FRAMEWORK_PATTERNS.items():
                if re.search(pattern, content):
                    if framework_name not in frameworks:
                        frameworks.append(framework_name)

    return frameworks


def count_endpoints(project_path: Path, language: Language, frameworks: list[str]) -> int:
    """
    Estimate endpoint count using pattern matching.

    Args:
        project_path: Project root directory
        language: Detected language
        frameworks: Detected frameworks

    Returns:
        Estimated endpoint count
    """
    endpoint_count = 0

    # File patterns by language
    file_patterns = {
        Language.GO: ["*.go"],
        Language.TYPESCRIPT: ["*.ts"],
        Language.JAVASCRIPT: ["*.js"],
        Language.CSHARP: ["*.cs"],
        Language.PYTHON: ["*.py"],
        Language.JAVA: ["*.java"],
        Language.KOTLIN: ["*.kt"],
        Language.RUST: ["*.rs"],
        Language.SWIFT: ["*.swift"],
        Language.CPP: ["*.cpp", "*.cc", "*.h"],
    }

    patterns = file_patterns.get(language, [])

    for file_path in walk_files(project_path, patterns):
        content = read_file_safe(file_path)
        if not content:
            continue

        # Try each endpoint pattern
        for pattern_name, pattern in ENDPOINT_PATTERNS.items():
            # Filter patterns by language/framework
            if language == Language.GO and pattern_name.startswith("go_"):
                matches = pattern.findall(content)
                endpoint_count += len(matches)
            elif language in (Language.TYPESCRIPT, Language.JAVASCRIPT) and pattern_name.startswith("ts_"):
                matches = pattern.findall(content)
                endpoint_count += len(matches)
            elif language == Language.CSHARP and pattern_name.startswith("cs_"):
                matches = pattern.findall(content)
                endpoint_count += len(matches)
            elif language == Language.PYTHON and pattern_name.startswith("py_"):
                matches = pattern.findall(content)
                endpoint_count += len(matches)
            elif language in (Language.JAVA, Language.KOTLIN) and pattern_name.startswith("java_"):
                matches = pattern.findall(content)
                endpoint_count += len(matches)

    return endpoint_count


def count_test_files(project_path: Path, language: Language) -> int:
    """
    Count test files by language conventions.

    Args:
        project_path: Project root directory
        language: Detected language

    Returns:
        Test file count
    """
    patterns = TEST_FILE_PATTERNS.get(language.value, [])

    test_files = list(walk_files(project_path, patterns))
    return len(test_files)


def detect_test_framework(project_path: Path, language: Language) -> TestFramework:
    """
    Detect test framework from test files.

    Args:
        project_path: Project root directory
        language: Detected language

    Returns:
        Detected TestFramework enum
    """
    patterns = TEST_FILE_PATTERNS.get(language.value, [])

    for file_path in walk_files(project_path, patterns):
        content = read_file_safe(file_path)
        if not content:
            continue

        # Check test framework patterns
        for framework_name, pattern in TEST_FRAMEWORK_PATTERNS.items():
            if pattern.search(content):
                # Map framework name to TestFramework enum
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
                    # Languages without dedicated TestFramework enum values
                    "kotlin_kotest": TestFramework.UNKNOWN,
                    "rust_test": TestFramework.UNKNOWN,
                    "xctest": TestFramework.UNKNOWN,
                    "gtest": TestFramework.UNKNOWN,
                    "catch2": TestFramework.UNKNOWN,
                }
                return framework_map.get(framework_name, TestFramework.UNKNOWN)

    return TestFramework.UNKNOWN


def infer_project_type(frameworks: list[str], endpoint_count: int) -> str:
    """
    Infer project type from frameworks and endpoints.

    Args:
        frameworks: Detected frameworks
        endpoint_count: Number of endpoints

    Returns:
        Project type string
    """
    if endpoint_count == 0:
        return "Library/CLI"

    # Check for specific frameworks
    framework_str = " ".join(frameworks).lower()

    if "graphql" in framework_str:
        return "GraphQL API"
    elif "grpc" in framework_str:
        return "gRPC Service"
    elif endpoint_count < 10:
        return "Microservice"
    else:
        return "REST API"


# Extensions scanned for source-pattern signals. Deliberately not filtered by the
# detected language: a hybrid project mixes languages, and detection must see all
# of them or the second type stays invisible.
_SIGNAL_EXTENSIONS = [
    "*.go", "*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.cs", "*.java", "*.kt",
    "*.swift", "*.rb", "*.rs", "*.sol", "*.sql", "*.cpp", "*.h", "*.xaml", "*.vue",
]

# Minimum distinct source patterns a type needs when it has no file or manifest
# marker. One hit is not enough — several of these patterns are broad enough to
# match ordinary code (`def perform(`, `class \w+Tool`).
_MIN_PATTERN_HITS = 2

# Per type: the manifest frameworks that imply it, and the pattern table its own
# analyzer already uses for extraction. Reusing that table keeps detection and
# extraction from drifting apart. `prefixes` narrows a shared table (MOBILE_PATTERNS
# covers both Android and iOS) to the keys belonging to this type.
_TYPE_SIGNALS: dict[ProjectType, dict] = {
    ProjectType.CLI_APP: {
        "frameworks": (
            "cobra", "urfave_cli", "clap", "click", "typer", "commander", "yargs",
            "picocli",
        ),
        "patterns": CLI_PATTERNS,
    },
    ProjectType.ANDROID_APP: {"patterns": MOBILE_PATTERNS, "prefixes": ("android_",)},
    ProjectType.IOS_APP: {"patterns": MOBILE_PATTERNS, "prefixes": ("ios_",)},
    ProjectType.FRONTEND_REACT: {
        "frameworks": ("react",),
        "patterns": FRONTEND_PATTERNS,
        "prefixes": ("react_",),
    },
    ProjectType.FRONTEND_VUE: {
        "frameworks": ("vue",),
        "patterns": FRONTEND_PATTERNS,
        "prefixes": ("vue_",),
    },
    ProjectType.FRONTEND_ANGULAR: {
        "frameworks": ("angular",),
        "patterns": FRONTEND_PATTERNS,
        "prefixes": ("angular_",),
    },
    ProjectType.FULLSTACK: {
        "frameworks": ("nextjs", "remix", "sveltekit"),
        "patterns": FULLSTACK_PATTERNS,
    },
    ProjectType.LLM_AI_AGENT: {
        "frameworks": ("langchain", "llamaindex", "crewai", "openai", "anthropic"),
        "patterns": LLM_PATTERNS,
    },
    ProjectType.SQL_PROJECT: {"patterns": SQL_PATTERNS},
    ProjectType.SERVERLESS: {
        "frameworks": ("serverless",),
        "patterns": SERVERLESS_PATTERNS,
    },
    ProjectType.BACKGROUND_WORKER: {
        "frameworks": ("celery", "sidekiq", "bull", "asynq"),
        "patterns": WORKER_PATTERNS,
    },
    ProjectType.MESSAGE_QUEUE: {
        "frameworks": ("kafka", "pika", "amqplib"),
        "patterns": MESSAGE_QUEUE_PATTERNS,
    },
    ProjectType.SMART_CONTRACT: {
        "frameworks": ("hardhat", "truffle", "ethers", "web3"),
        "patterns": BLOCKCHAIN_PATTERNS,
    },
    ProjectType.DESKTOP_WINDOWS: {
        "patterns": DESKTOP_PATTERNS,
        "prefixes": ("wpf_", "winforms_"),
    },
    ProjectType.DESKTOP_MAC: {"patterns": DESKTOP_PATTERNS, "prefixes": ("macos_",)},
    ProjectType.DESKTOP_LINUX: {
        "patterns": DESKTOP_PATTERNS,
        "prefixes": ("qt_", "gtk_"),
    },
}


def _has_file_marker(project_path: Path, project_type: ProjectType) -> bool:
    """Check for a file that on its own identifies this project type."""
    for marker in PROJECT_TYPE_FILE_MARKERS.get(project_type.value, []):
        if next(walk_files(project_path, [marker]), None) is not None:
            return True
    return False


def _count_pattern_hits(sources: dict[Path, str], signal: dict) -> int:
    """Count distinct pattern keys from a type's table matching any source file.

    Several tables carry plain strings as file hints rather than compiled patterns
    (`"android_manifest": "AndroidManifest.xml"`); those are covered by
    PROJECT_TYPE_FILE_MARKERS and skipped here.
    """
    prefixes = signal.get("prefixes", ())
    hits = 0

    for key, pattern in signal["patterns"].items():
        if not isinstance(pattern, re.Pattern):
            continue
        if prefixes and not key.startswith(prefixes):
            continue
        if any(pattern.search(content) for content in sources.values()):
            hits += 1

    return hits


def detect_project_types(
    project_path: Path, frameworks: list[str], endpoint_count: int
) -> list[ProjectType]:
    """
    Detect every project type present, not only API types.

    A type is included when it has a file marker or a manifest framework, or when
    at least _MIN_PATTERN_HITS distinct source patterns from its own analyzer's
    table match. HYBRID is appended when more than one type is found.

    Args:
        project_path: Project root directory
        frameworks: Detected frameworks
        endpoint_count: Number of HTTP endpoints

    Returns:
        List of detected ProjectType values (empty means library/unknown)
    """
    sources: dict[Path, str] = {}
    for file_path in walk_files(project_path, _SIGNAL_EXTENSIONS):
        content = read_file_safe(file_path)
        if content:
            sources[file_path] = content

    framework_set = {f.lower() for f in frameworks}
    types: list[ProjectType] = []

    # API types come from endpoint counting, which already works
    if endpoint_count > 0:
        framework_str = " ".join(framework_set)
        if "graphql" in framework_str:
            types.append(ProjectType.GRAPHQL_API)
        elif "grpc" in framework_str:
            types.append(ProjectType.GRPC_API)
        else:
            types.append(ProjectType.REST_API)

    for project_type, signal in _TYPE_SIGNALS.items():
        if _has_file_marker(project_path, project_type):
            types.append(project_type)
        elif framework_set & {f.lower() for f in signal.get("frameworks", ())}:
            types.append(project_type)
        elif _count_pattern_hits(sources, signal) >= _MIN_PATTERN_HITS:
            types.append(project_type)

    if len(types) > 1:
        types.append(ProjectType.HYBRID)

    return types


def analyze_project(project_path: Path) -> ProjectInfo:
    """
    Analyze project structure and detect all metadata.

    Args:
        project_path: Project root directory

    Returns:
        ProjectInfo object with all metadata
    """
    # Auto-detect project root if needed
    if not project_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {project_path}")

    detected_root = find_project_root(project_path)
    if detected_root:
        project_path = detected_root

    # Phase 1: Detect language
    language = detect_language(project_path)
    if language == Language.UNKNOWN:
        raise ValueError(f"Could not detect language for project: {project_path}")

    # Phase 2: Detect frameworks
    frameworks = detect_frameworks(project_path, language)

    # Phase 3: Count endpoints
    endpoint_count = count_endpoints(project_path, language, frameworks)

    # Phase 4: Count test files
    test_file_count = count_test_files(project_path, language)

    # Phase 5: Detect test framework
    test_framework = detect_test_framework(project_path, language)

    # Phase 6: Infer project type
    project_type = infer_project_type(frameworks, endpoint_count)

    # Phase 7: Detect every project type present. Endpoint count alone cannot do
    # this — a CLI, Android or SQL project serves no HTTP and previously fell into
    # the library branch, making all non-API types unreachable.
    types = detect_project_types(project_path, frameworks, endpoint_count)

    # Nothing recognised → library mode (white-box analysis)
    is_library = not types
    primary = types[0] if types else ProjectType.UNKNOWN

    return ProjectInfo(
        language=language,
        frameworks=frameworks,
        endpoint_count=endpoint_count,
        test_file_count=test_file_count,
        primary_type=primary,
        project_types=types,
        root_path=str(project_path),
        test_framework=test_framework,
        detected_patterns={},
        metadata={
            "has_api_prefixes": any(
                (project_path / prefix.strip("/")).exists()
                for prefix in API_PATH_PREFIXES
            ),
            "legacy_project_type": project_type,
            "is_library": is_library,
        },
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze project structure and detect language/frameworks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_project_structure.py /path/to/project
  python analyze_project_structure.py . --output-format json > project.json
  python analyze_project_structure.py ~/myapp --output project-info.json
        """,
    )

    parser.add_argument(
        "project_path",
        type=Path,
        help="Path to project root directory",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file path (default: stdout)",
    )

    parser.add_argument(
        "--output-format",
        choices=["json", "summary"],
        default="json",
        help="Output format (default: json)",
    )

    args = parser.parse_args()

    try:
        # Analyze project
        project_info = analyze_project(args.project_path)

        if args.output_format == "json":
            # JSON output
            output_data = project_info.to_dict()
            json_str = json.dumps(output_data, indent=2, ensure_ascii=False)

            if args.output:
                args.output.write_text(json_str, encoding="utf-8")
            else:
                print(json_str)
        else:
            # Summary output
            print(f"Project: {project_info.root_path}")
            print(f"Language: {project_info.language.value}")
            print(f"Frameworks: {', '.join(project_info.frameworks) if project_info.frameworks else 'None'}")
            print(f"Project Type: {project_info.primary_type.value}")
            print(f"Endpoints: {project_info.endpoint_count}")
            print(f"Test Files: {project_info.test_file_count}")
            print(f"Test Framework: {project_info.test_framework.value}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
