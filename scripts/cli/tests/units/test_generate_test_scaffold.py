#!/usr/bin/env python3
"""Tests for generate_test_scaffold.py"""

from pathlib import Path

import pytest

from cli.generate_test_scaffold import (
    detect_language,
    generate_bash_tests,
    generate_output_path,
    generate_powershell_tests,
    generate_python_tests,
    generate_test_scaffold,
)
from common.utils import write_file_safe

def test_detect_language_powershell():
    """Test language detection for PowerShell."""
    file_path = Path("script.ps1")
    language = detect_language(file_path)
    assert language == "powershell"

    file_path = Path("module.psm1")
    language = detect_language(file_path)
    assert language == "powershell"

def test_detect_language_python():
    """Test language detection for Python."""
    file_path = Path("script.py")
    language = detect_language(file_path)
    assert language == "python"

def test_detect_language_bash():
    """Test language detection for Bash."""
    file_path = Path("script.sh")
    language = detect_language(file_path)
    assert language == "bash"

    file_path = Path("script.bash")
    language = detect_language(file_path)
    assert language == "bash"

def test_detect_language_unknown():
    """Test language detection for unknown extension."""
    file_path = Path("script.txt")
    with pytest.raises(ValueError, match="Unsupported file extension"):
        detect_language(file_path)

def test_generate_output_path_powershell():
    """Test output path generation for PowerShell."""
    file_path = Path("/path/to/script.ps1")
    output = generate_output_path(file_path, "powershell")
    assert output.name == "script.Tests.ps1"

def test_generate_output_path_python():
    """Test output path generation for Python."""
    file_path = Path("/path/to/script.py")
    output = generate_output_path(file_path, "python")
    assert output.name == "test_script.py"

def test_generate_output_path_bash():
    """Test output path generation for Bash."""
    file_path = Path("/path/to/script.sh")
    output = generate_output_path(file_path, "bash")
    assert output.name == "script.bats"

def test_generate_powershell_tests():
    """Test PowerShell test generation."""
    file_path = Path("my-script.ps1")
    content = generate_powershell_tests(file_path)

    assert "#!/usr/bin/env pwsh" in content
    assert "#Requires -Version 7.0" in content
    assert "BeforeAll" in content
    assert "Describe" in content
    assert "Context" in content
    assert "It" in content
    assert "my-script.ps1" in content

def test_generate_python_tests():
    """Test Python test generation."""
    file_path = Path("my_script.py")
    content = generate_python_tests(file_path)

    assert "#!/usr/bin/env python3" in content
    assert "import pytest" in content
    assert "def test_" in content
    assert "from my_script import main" in content
    assert "tmp_path" in content

def test_generate_bash_tests():
    """Test Bash test generation."""
    file_path = Path("my-script.sh")
    content = generate_bash_tests(file_path)

    assert "#!/usr/bin/env bats" in content
    assert "setup()" in content
    assert "@test" in content
    assert "my-script.sh" in content

def test_generate_test_scaffold_powershell(tmp_path):
    """Test test scaffold generation for PowerShell."""
    script = tmp_path / "script.ps1"
    write_file_safe(script, "Write-Host 'Hello'")

    output = generate_test_scaffold(script, language="powershell")

    assert output.exists()
    assert output.name == "script.Tests.ps1"
    content = output.read_text()
    assert "BeforeAll" in content

def test_generate_test_scaffold_python(tmp_path):
    """Test test scaffold generation for Python."""
    script = tmp_path / "script.py"
    write_file_safe(script, "print('Hello')")

    output = generate_test_scaffold(script, language="python")

    assert output.exists()
    assert output.name == "test_script.py"
    content = output.read_text()
    assert "import pytest" in content

def test_generate_test_scaffold_bash(tmp_path):
    """Test test scaffold generation for Bash."""
    script = tmp_path / "script.sh"
    write_file_safe(script, "echo 'Hello'")

    output = generate_test_scaffold(script, language="bash")

    assert output.exists()
    assert output.name == "script.bats"
    content = output.read_text()
    assert "@test" in content

def test_generate_test_scaffold_auto_detect(tmp_path):
    """Test test scaffold generation with auto language detection."""
    script = tmp_path / "script.py"
    write_file_safe(script, "print('Hello')")

    output = generate_test_scaffold(script, language="auto")

    assert output.exists()
    assert output.name == "test_script.py"

def test_generate_test_scaffold_custom_output(tmp_path):
    """Test test scaffold generation with custom output path."""
    script = tmp_path / "script.py"
    write_file_safe(script, "print('Hello')")

    custom_output = tmp_path / "custom_test.py"
    output = generate_test_scaffold(script, language="python", output_file=custom_output)

    assert output == custom_output
    assert output.exists()

def test_generate_test_scaffold_no_overwrite(tmp_path):
    """Test test scaffold refuses to overwrite without force."""
    script = tmp_path / "script.py"
    write_file_safe(script, "print('Hello')")

    # Generate first time
    output = generate_test_scaffold(script, language="python")

    # Try to generate again without force
    with pytest.raises(FileExistsError, match="already exists"):
        generate_test_scaffold(script, language="python")

def test_generate_test_scaffold_force_overwrite(tmp_path):
    """Test test scaffold overwrites with force flag."""
    script = tmp_path / "script.py"
    write_file_safe(script, "print('Hello')")

    # Generate first time
    output = generate_test_scaffold(script, language="python")
    first_content = output.read_text()

    # Generate again with force
    output = generate_test_scaffold(script, language="python", force=True)
    second_content = output.read_text()

    assert output.exists()
    assert first_content == second_content  # Content should be the same

def test_generate_test_scaffold_nonexistent_file():
    """Test test scaffold with nonexistent file."""
    with pytest.raises(FileNotFoundError):
        generate_test_scaffold(Path("/nonexistent/script.py"))
