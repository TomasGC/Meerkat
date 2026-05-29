#!/usr/bin/env python3
"""
Validate script syntax for multiple languages (PowerShell, Python, Bash, Perl).

Validates script syntax before execution using language-specific tools.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript, create_cli_script
from common.utils import run_command


@dataclass
class ValidationResult:
    """Script syntax validation result."""
    file: str
    language: str
    valid: bool
    errors: list[str]
    warnings: list[str]
    info: list[str]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def info_count(self) -> int:
        return len(self.info)


class ValidateScriptSyntaxScript(BaseCLIScript):
    """Validate script syntax for multiple languages."""

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
            choices=["auto", "powershell", "python", "bash", "perl"],
            default="auto",
            help="Script language (default: auto-detect)"
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat warnings as errors"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute syntax validation."""
        file_path = args.file.resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {args.file}")

        # Detect or use specified language
        if args.language == "auto":
            language = self._detect_language(file_path)
        else:
            language = args.language

        if language == "unknown":
            raise ValueError(f"Cannot detect language for: {file_path.suffix}")

        # Validate syntax
        result = self._validate_syntax(file_path, language)

        # Apply strict mode
        if args.strict and result.warnings:
            result.errors.extend(result.warnings)
            result.warnings = []
            result.valid = False

        # Track metrics
        self.metrics.track("validate_script_syntax", {
            "language": language,
            "valid": result.valid
        })

        return self._result_to_dict(result)

    def _detect_language(self, file_path: Path) -> str:
        """Detect language from file extension."""
        extension_map = {
            ".ps1": "powershell",
            ".psm1": "powershell",
            ".py": "python",
            ".sh": "bash",
            ".bash": "bash",
            ".pl": "perl",
        }
        return extension_map.get(file_path.suffix.lower(), "unknown")

    def _validate_syntax(self, file_path: Path, language: str) -> ValidationResult:
        """Validate script syntax."""
        errors = []
        warnings = []
        info = []

        if language == "powershell":
            self._validate_powershell(file_path, errors, warnings, info)
        elif language == "python":
            self._validate_python(file_path, errors, warnings, info)
        elif language == "bash":
            self._validate_bash(file_path, errors, warnings, info)
        elif language == "perl":
            self._validate_perl(file_path, errors, warnings, info)

        return ValidationResult(
            file=str(file_path),
            language=language,
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def _validate_powershell(self, file_path: Path, errors: list, warnings: list, info: list):
        """Validate PowerShell syntax."""
        info.append("Validating PowerShell syntax...")

        ps_script = f"""
$ErrorActionPreference = 'Stop'
$parseErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile('{file_path}', [ref]$null, [ref]$parseErrors)
if ($parseErrors -and $parseErrors.Count -gt 0) {{
    foreach ($parseError in $parseErrors) {{
        Write-Output "Line $($parseError.Extent.StartLineNumber): $($parseError.Message)"
    }}
    exit 1
}} else {{
    Write-Output "VALID"
    exit 0
}}
"""

        returncode, stdout, stderr = run_command(
            ["pwsh", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            timeout=10
        )

        if returncode == 0 and "VALID" in stdout:
            info.append("PowerShell syntax valid")
        else:
            for line in stdout.strip().split("\n"):
                if line and line != "VALID":
                    errors.append(line)

    def _validate_python(self, file_path: Path, errors: list, warnings: list, info: list):
        """Validate Python syntax."""
        info.append("Validating Python syntax...")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            compile(content, str(file_path), 'exec')
            info.append("Python syntax valid")
        except SyntaxError as e:
            errors.append(f"Line {e.lineno}: {e.msg}")

        # Check shebang
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
            if not first_line.startswith("#!/usr/bin/env python"):
                warnings.append("Missing or incorrect shebang (#!/usr/bin/env python3)")
        except Exception:
            pass

        # Check hardcoded paths (Windows-style)
        try:
            content = file_path.read_text(encoding='utf-8')
            if re.search(r'C:\\', content):
                warnings.append("Hardcoded Windows path detected (use Path for cross-platform)")
        except Exception:
            pass

    def _validate_bash(self, file_path: Path, errors: list, warnings: list, info: list):
        """Validate Bash syntax."""
        info.append("Validating Bash syntax...")

        returncode, stdout, stderr = run_command(
            ["bash", "-n", str(file_path)],
            timeout=5
        )

        if returncode == 0:
            info.append("Bash syntax valid")
        else:
            for line in stderr.strip().split("\n"):
                if line:
                    errors.append(line)

        # Check for 'set -euo pipefail'
        try:
            content = file_path.read_text(encoding='utf-8')
            if "set -euo pipefail" not in content and "set -eu" not in content:
                warnings.append("Missing 'set -euo pipefail' (recommended for safety)")
        except Exception:
            pass

    def _validate_perl(self, file_path: Path, errors: list, warnings: list, info: list):
        """Validate Perl syntax."""
        info.append("Validating Perl syntax...")

        returncode, stdout, stderr = run_command(
            ["perl", "-c", str(file_path)],
            timeout=5
        )

        if returncode == 0:
            info.append("Perl syntax valid")
        else:
            for line in stderr.strip().split("\n"):
                if line and "syntax OK" not in line:
                    errors.append(line)

    def _result_to_dict(self, result: ValidationResult) -> dict:
        """Convert ValidationResult to dict."""
        return {
            "file": result.file,
            "language": result.language,
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "info": result.info,
            "summary": {
                "errorCount": result.error_count,
                "warningCount": result.warning_count,
                "infoCount": result.info_count
            }
        }

    def format_text(self, result: dict) -> str:
        """Format result as human-readable text."""
        lines = [
            f"Syntax Validation: {result['file']}",
            f"Language: {result['language']}",
            ""
        ]

        if result['errors']:
            lines.append("ERRORS:")
            for error in result['errors']:
                lines.append(f"  ❌ {error}")
            lines.append("")

        if result['warnings']:
            lines.append("WARNINGS:")
            for warning in result['warnings']:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")

        if result['info']:
            lines.append("INFO:")
            for info_msg in result['info']:
                lines.append(f"  ℹ️  {info_msg}")
            lines.append("")

        if result['valid']:
            lines.append("✅ Syntax is valid")
        else:
            lines.append("❌ Syntax validation failed")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format result as brief summary."""
        status = "OK" if result['valid'] else "FAIL"
        file_name = Path(result['file']).name
        return (f"[{status}] {file_name} ({result['language']}) - "
                f"{result['summary']['errorCount']} errors, "
                f"{result['summary']['warningCount']} warnings")


if __name__ == "__main__":
    create_cli_script(ValidateScriptSyntaxScript)
