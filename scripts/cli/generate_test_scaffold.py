#!/usr/bin/env python3
"""
Generate test scaffold for scripts (Pester, pytest, bats).

Replaces: generate-test-scaffold.ps1

Auto-generates test file templates with basic structure:
- PowerShell → Pester (.Tests.ps1)
- Python → pytest (test_*.py)
- Bash → bats (*.bats or test-*.sh)
"""

import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript


def detect_language(file_path: Path) -> str:
    """Detect script language from extension."""
    suffix = file_path.suffix.lower()

    if suffix in [".ps1", ".psm1"]:
        return "powershell"
    elif suffix == ".py":
        return "python"
    elif suffix in [".sh", ".bash"]:
        return "bash"
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")


def generate_output_path(file_path: Path, language: str) -> Path:
    """Generate test file path based on language conventions."""
    stem = file_path.stem

    if language == "powershell":
        # Remove .Tests suffix if already present
        if stem.endswith(".Tests"):
            stem = stem[:-6]
        return file_path.parent / f"{stem}.Tests.ps1"

    elif language == "python":
        # Add test_ prefix if not present
        if not stem.startswith("test_"):
            stem = f"test_{stem}"
        return file_path.parent / f"{stem}.py"

    elif language == "bash":
        # Use bats convention
        return file_path.parent / f"{stem}.bats"

    return file_path.parent / f"test_{stem}{file_path.suffix}"


def generate_powershell_tests(file_path: Path) -> str:
    """Generate Pester test template."""
    script_name = file_path.name
    stem = file_path.stem

    return f"""#!/usr/bin/env pwsh
#Requires -Version 7.0

BeforeAll {{
    $scriptPath = Join-Path $PSScriptRoot "{script_name}"
}}

Describe "{script_name}" {{
    Context "Happy path" {{
        It "Should execute successfully with valid input" {{
            # Arrange
            $testInput = "valid-value"

            # Act
            $result = & $scriptPath -Parameter $testInput

            # Assert
            $result | Should -Not -BeNullOrEmpty
        }}
    }}

    Context "Edge cases" {{
        It "Should handle empty input" {{
            # Arrange
            $testInput = ""

            # Act/Assert
            {{ & $scriptPath -Parameter $testInput }} | Should -Throw
        }}
    }}

    Context "Error handling" {{
        It "Should fail gracefully with invalid input" {{
            # Arrange
            $testInput = "invalid"

            # Act/Assert
            {{ & $scriptPath -Parameter $testInput -ErrorAction Stop }} | Should -Throw
        }}
    }}
}}
"""


def generate_python_tests(file_path: Path) -> str:
    """Generate pytest test template."""
    script_name = file_path.stem
    module_name = script_name.replace("-", "_").replace(".", "_")

    return f'''#!/usr/bin/env python3
"""Tests for {file_path.name}"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from {module_name} import main  # Adjust import as needed


def test_happy_path():
    """Test normal execution."""
    # Arrange
    test_input = "valid-value"

    # Act
    result = main(test_input)

    # Assert
    assert result is not None


def test_edge_case_empty_input():
    """Test with empty input."""
    # Arrange
    test_input = ""

    # Act/Assert
    with pytest.raises(ValueError):
        main(test_input)


def test_error_handling_invalid_input():
    """Test error handling with invalid input."""
    # Arrange
    test_input = "invalid"

    # Act/Assert
    with pytest.raises(Exception):
        main(test_input)


def test_with_temp_directory(tmp_path):
    """Test with temporary directory."""
    # Arrange
    test_file = tmp_path / "test.txt"
    test_file.write_text("test data")

    # Act
    result = main(str(test_file))

    # Assert
    assert result is not None
'''


def generate_bash_tests(file_path: Path) -> str:
    """Generate bats test template."""
    script_name = file_path.name

    return f"""#!/usr/bin/env bats

setup() {{
    load 'test_helper/bats-support/load'
    load 'test_helper/bats-assert/load'

    SCRIPT_DIR="$( cd "$( dirname "$BATS_TEST_FILENAME" )" && pwd )"
    SCRIPT_PATH="$SCRIPT_DIR/{script_name}"
}}

@test "Should execute successfully with valid input" {{
    run "$SCRIPT_PATH" "valid-value"
    assert_success
    assert_output --partial "expected-output"
}}

@test "Should handle empty input" {{
    run "$SCRIPT_PATH" ""
    assert_failure
}}

@test "Should fail gracefully with invalid input" {{
    run "$SCRIPT_PATH" "invalid"
    assert_failure
    assert_output --partial "Error"
}}
"""


def generate_test_scaffold(
    file_path: Path,
    language: str = "auto",
    output_file: Optional[Path] = None,
    force: bool = False
) -> Path:
    """Generate test scaffold file."""
    # Detect language
    if language == "auto":
        language = detect_language(file_path)

    # Determine output path
    if output_file is None:
        output_file = generate_output_path(file_path, language)

    # Check if output exists
    if output_file.exists() and not force:
        raise FileExistsError(f"Test file already exists: {output_file}. Use --force to overwrite.")

    # Generate test content
    if language == "powershell":
        content = generate_powershell_tests(file_path)
    elif language == "python":
        content = generate_python_tests(file_path)
    elif language == "bash":
        content = generate_bash_tests(file_path)
    else:
        raise ValueError(f"Unsupported language: {language}")

    # Write test file
    output_file.write_text(content, encoding="utf-8")

    return output_file


def print_next_steps(output_file: Path, language: str) -> str:
    """Generate next steps message."""
    lines = [
        f"Generated test file: {output_file}",
        "",
        "Next steps:"
    ]

    if language == "powershell":
        lines.extend([
            "1. Update test parameters and assertions",
            "2. Run tests: Invoke-Pester -Path " + str(output_file),
            "3. Check coverage: Invoke-Pester -CodeCoverage"
        ])
    elif language == "python":
        lines.extend([
            "1. Update imports and test logic",
            "2. Run tests: pytest " + str(output_file),
            "3. Check coverage: pytest --cov"
        ])
    elif language == "bash":
        lines.extend([
            "1. Install bats: npm install -g bats",
            "2. Update test assertions",
            "3. Run tests: bats " + str(output_file)
        ])

    return "\n".join(lines)


class GenerateTestScaffoldScript(BaseCLIScript):
    """Generate test scaffold for scripts."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--file",
            type=Path,
            required=True,
            help="Path to script file"
        )
        parser.add_argument(
            "--language",
            "-l",
            choices=["auto", "powershell", "python", "bash"],
            default="auto",
            help="Language (default: auto-detect)"
        )
        parser.add_argument(
            "--output",
            "-o",
            type=Path,
            help="Output test file path (optional)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing test file"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute test scaffold generation."""
        try:
            # Generate test scaffold
            output_file = generate_test_scaffold(
                args.file,
                language=args.language,
                output_file=args.output,
                force=args.force
            )

            # Detect final language (in case it was auto)
            language = detect_language(args.file) if args.language == "auto" else args.language

            # Generate next steps
            next_steps = print_next_steps(output_file, language)

            self.metrics.track("generate_test_scaffold", {
                "file": str(args.file),
                "language": language,
                "output": str(output_file)
            })

            return {
                "success": True,
                "output_file": str(output_file),
                "language": language,
                "next_steps": next_steps
            }

        except Exception as e:
            self.logger.error(f"Failed to generate test scaffold: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        return result["next_steps"]

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return f"Generated {result['language']} test file: {result['output_file']}"


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(GenerateTestScaffoldScript)
