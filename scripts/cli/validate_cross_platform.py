#!/usr/bin/env python3
"""
Validate scripts for cross-platform compatibility (Windows, Linux, macOS).

Replaces: validate-cross-platform.ps1

Deep analysis of PowerShell scripts to ensure cross-platform compatibility:
- Check for hardcoded paths (Windows/Unix specific)
- Verify use of System.IO.Path methods
- Detect platform-specific cmdlets
- Validate shebang and file permissions
- Check file naming conventions
- Identify encoding issues
"""

import sys
from pathlib import Path
from typing import Any
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript


def check_hardcoded_paths(content: str, errors: list, warnings: list) -> None:
    """Check for hardcoded Windows/Unix paths."""
    # Windows hardcoded paths
    if re.search(r'C:\\', content):
        errors.append("Hardcoded Windows path detected (C:\\)")

    if re.search(r'[A-Z]:\\(?!\\)', content):
        errors.append("Hardcoded drive letter path detected")

    # Unix hardcoded paths
    if re.search(r'(?<![a-zA-Z])/home/[a-zA-Z0-9_-]+', content):
        warnings.append("Hardcoded Unix home path detected (/home/username)")

    if re.search(r'(?<![a-zA-Z])/usr/(?:local/)?bin', content):
        warnings.append("Hardcoded Unix system path detected (/usr/bin)")

    # Backslash in path strings
    if re.search(r'".*\\.*"|\'.*\\.*\'', content):
        warnings.append("Backslashes in path strings (use [System.IO.Path] methods)")


def check_path_api_usage(content: str, warnings: list, info: list) -> None:
    """Check for proper path API usage."""
    # Count path API usage
    path_combine = len(re.findall(r'\[System\.IO\.Path\]::Combine\(', content))
    path_join = len(re.findall(r'\[System\.IO\.Path\]::Join\(', content))
    join_path = len(re.findall(r'Join-Path', content))

    path_api_count = path_combine + path_join + join_path

    if path_api_count > 0:
        info.append(f"Using cross-platform path methods ({path_api_count} occurrences)")
    else:
        warnings.append("No cross-platform path methods detected (consider using [System.IO.Path]::Combine())")

    # Detect string concatenation for paths
    if re.search(r'\$\w+\s*\+\s*["\'][/\\]', content) or re.search(r'["\'][/\\].*["\']\s*\+\s*\$', content):
        warnings.append("Path string concatenation detected (use [System.IO.Path]::Combine() instead)")


def check_platform_specific_cmdlets(content: str, warnings: list, info: list) -> None:
    """Check for platform-specific PowerShell cmdlets."""
    windows_only_cmdlets = [
        'Get-WmiObject',
        'Get-CimInstance',
        'Get-EventLog',
        'Get-WindowsFeature',
        'Get-Service',
        'Set-ExecutionPolicy',
        'Get-Acl',
        'Set-Acl'
    ]

    for cmdlet in windows_only_cmdlets:
        if re.search(rf'\b{cmdlet}\b', content):
            warnings.append(f"Platform-specific cmdlet detected: {cmdlet} (may not work on Linux/macOS)")

    # Check for platform detection
    if re.search(r'\$Is(Windows|Linux|MacOS)', content):
        info.append("Platform detection found (good for cross-platform compatibility)")


def check_shebang_and_encoding(file_path: Path, warnings: list, info: list) -> None:
    """Check shebang and file encoding."""
    # Read first line
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
    except Exception:
        first_line = ""

    # Check shebang
    if first_line.startswith('#!/usr/bin/env pwsh'):
        info.append("Correct shebang for PowerShell 7+")
    elif first_line.startswith('#!/usr/bin/env powershell'):
        warnings.append("Shebang uses 'powershell' instead of 'pwsh' (PowerShell 7+)")
    elif first_line.startswith('#!'):
        warnings.append("Non-standard shebang detected")
    else:
        warnings.append("Missing shebang (#!/usr/bin/env pwsh) for Unix compatibility")

    # Check file encoding
    try:
        with open(file_path, 'rb') as f:
            bom = f.read(3)

        if len(bom) >= 3 and bom[0] == 0xEF and bom[1] == 0xBB and bom[2] == 0xBF:
            info.append("UTF-8 with BOM encoding (generally compatible)")
        elif len(bom) >= 2 and bom[0] == 0xFF and bom[1] == 0xFE:
            warnings.append("UTF-16 LE encoding detected (may cause issues on Unix)")
        else:
            info.append("UTF-8 encoding (best for cross-platform)")
    except Exception:
        pass


def check_file_naming_conventions(file_name: str, warnings: list, info: list) -> None:
    """Check file naming conventions."""
    # Check for spaces
    if ' ' in file_name:
        warnings.append("Filename contains spaces (may cause issues in scripts)")

    # Check for special characters
    if re.search(r'[<>:"|?*]', file_name):
        warnings.append("Filename contains special characters that may be invalid on some platforms")

    # Check for mixed case
    if re.search(r'[A-Z]', file_name) and re.search(r'[a-z]', file_name):
        info.append("Filename has mixed case (remember Unix filesystems are case-sensitive)")


def check_environment_variables(content: str, warnings: list, info: list) -> None:
    """Check environment variable usage."""
    # Windows-specific environment variables
    if re.search(r'\$env:USERPROFILE|\$env:APPDATA|\$env:TEMP(?![_A-Z])|\$env:PROGRAMFILES', content):
        warnings.append("Windows-specific environment variable detected (consider cross-platform alternatives)")

    # Check for portable HOME
    if re.search(r'\$env:HOME', content):
        info.append("Using portable HOME environment variable")

    # Check for proper TEMP usage
    if re.search(r'\[System\.IO\.Path\]::GetTempPath\(\)', content):
        info.append("Using cross-platform temp directory method")


def check_line_endings(file_path: Path, warnings: list, info: list) -> None:
    """Check line endings."""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        content_str = content.decode('utf-8', errors='ignore')

        # Count line ending types
        crlf_count = content_str.count('\r\n')
        lf_count = content_str.count('\n') - crlf_count  # Subtract CRLF newlines

        if crlf_count > 0 and lf_count > 0:
            warnings.append("Mixed line endings detected (CRLF and LF)")
        elif crlf_count > 0:
            info.append("Using CRLF line endings (Windows style)")
        elif lf_count > 0:
            info.append("Using LF line endings (Unix style, preferred for cross-platform)")

    except Exception:
        pass


def validate_script_cross_platform(script_path: Path) -> dict:
    """
    Validate script for cross-platform compatibility.

    Args:
        script_path: Path to script file

    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []
    info = []

    # Read file content
    try:
        content = script_path.read_text(encoding='utf-8')
    except Exception as e:
        return {
            "file": str(script_path),
            "valid": False,
            "errors": [f"Failed to read file: {e}"],
            "warnings": [],
            "info": [],
            "summary": {
                "errorCount": 1,
                "warningCount": 0,
                "infoCount": 0
            }
        }

    file_name = script_path.name

    # Run all checks
    check_hardcoded_paths(content, errors, warnings)
    check_path_api_usage(content, warnings, info)
    check_platform_specific_cmdlets(content, warnings, info)
    check_shebang_and_encoding(script_path, warnings, info)
    check_file_naming_conventions(file_name, warnings, info)
    check_environment_variables(content, warnings, info)
    check_line_endings(script_path, warnings, info)

    return {
        "file": str(script_path),
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "summary": {
            "errorCount": len(errors),
            "warningCount": len(warnings),
            "infoCount": len(info)
        }
    }


class ValidateCrossPlatformScript(BaseCLIScript):
    """Validate scripts for cross-platform compatibility."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--file",
            help="Path to script file to validate (for single file analysis)"
        )
        parser.add_argument(
            "--path",
            "-p",
            default=".",
            help="Path to directory containing scripts (default: current directory)"
        )
        parser.add_argument(
            "--recursive",
            "-r",
            action="store_true",
            help="Search subdirectories recursively"
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Enable strict mode (warnings become errors)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute validation logic."""
        if args.file:
            # Single file validation
            file_path = Path(args.file)

            if not file_path.exists():
                self.logger.error(f"File not found: {args.file}")
                return {
                    "success": False,
                    "error": f"File not found: {args.file}"
                }

            result = validate_script_cross_platform(file_path)

            # Apply strict mode
            if args.strict and result["warnings"]:
                result["valid"] = False

            self.metrics.track("validate_cross_platform_single", {
                "valid": result["valid"],
                "errors": result["summary"]["errorCount"],
                "warnings": result["summary"]["warningCount"]
            })

            return result

        else:
            # Directory validation
            path = Path(args.path)

            if not path.exists():
                self.logger.error(f"Path not found: {args.path}")
                return {
                    "success": False,
                    "error": f"Path not found: {args.path}"
                }

            # Get all PowerShell scripts
            if args.recursive:
                scripts = list(path.rglob("*.ps1"))
            else:
                scripts = list(path.glob("*.ps1"))

            # Exclude test files
            scripts = [s for s in scripts if not s.name.endswith(".Tests.ps1")]

            if not scripts:
                self.logger.warning(f"No PowerShell scripts found in {args.path}")
                return {
                    "success": True,
                    "path": str(path),
                    "recursive": args.recursive,
                    "scripts": [],
                    "summary": {
                        "totalScripts": 0,
                        "validScripts": 0,
                        "scriptsWithIssues": 0,
                        "totalErrors": 0,
                        "totalWarnings": 0
                    }
                }

            # Validate each script
            results = []
            total_errors = 0
            total_warnings = 0

            for script_path in scripts:
                result = validate_script_cross_platform(script_path)

                # Apply strict mode
                if args.strict and result["warnings"]:
                    result["valid"] = False

                total_errors += result["summary"]["errorCount"]
                total_warnings += result["summary"]["warningCount"]

                results.append(result)

            # Build summary
            valid_scripts = sum(1 for r in results if r["valid"])
            scripts_with_issues = len(results) - valid_scripts

            self.metrics.track("validate_cross_platform_multiple", {
                "total_scripts": len(results),
                "valid_scripts": valid_scripts,
                "scripts_with_issues": scripts_with_issues
            })

            return {
                "success": scripts_with_issues == 0,
                "path": str(path),
                "recursive": args.recursive,
                "scripts": results,
                "summary": {
                    "totalScripts": len(results),
                    "validScripts": valid_scripts,
                    "scriptsWithIssues": scripts_with_issues,
                    "totalErrors": total_errors,
                    "totalWarnings": total_warnings
                }
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if "file" in result:
            # Single file
            lines = [
                f"Cross-Platform Validation: {result['file']}",
                ""
            ]

            if result["errors"]:
                lines.append("ERRORS:")
                for error in result["errors"]:
                    lines.append(f"  [X] {error}")
                lines.append("")

            if result["warnings"]:
                lines.append("WARNINGS:")
                for warning in result["warnings"]:
                    lines.append(f"  [!] {warning}")
                lines.append("")

            if result["info"]:
                lines.append("INFO:")
                for i in result["info"]:
                    lines.append(f"  [i] {i}")
                lines.append("")

            status = "[OK]" if result["valid"] else "[FAIL]"
            lines.append(f"{status} Script is {'cross-platform compatible' if result['valid'] else 'has compatibility issues'}")

            return "\n".join(lines)
        else:
            # Multiple files
            lines = [
                "Cross-Platform Validation Report",
                f"Path: {result['path']}",
                f"Recursive: {result['recursive']}",
                "",
                "Summary:",
                f"  Total scripts: {result['summary']['totalScripts']}",
                f"  Valid: {result['summary']['validScripts']}",
                f"  With issues: {result['summary']['scriptsWithIssues']}",
                f"  Total errors: {result['summary']['totalErrors']}",
                f"  Total warnings: {result['summary']['totalWarnings']}",
                ""
            ]

            for script in result["scripts"]:
                status = "[OK]" if script["valid"] else "[FAIL]"
                lines.append(f"{status} {script['file']}")

                if script["errors"]:
                    lines.append("  ERRORS:")
                    for error in script["errors"]:
                        lines.append(f"    [X] {error}")

                if script["warnings"]:
                    lines.append("  WARNINGS:")
                    for warning in script["warnings"]:
                        lines.append(f"    [!] {warning}")

                lines.append("")

            if result["summary"]["scriptsWithIssues"] == 0:
                lines.append("[OK] All scripts are cross-platform compatible")
            else:
                lines.append(f"[FAIL] {result['summary']['scriptsWithIssues']} script(s) have compatibility issues")

            return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if "file" in result:
            # Single file
            status = "[OK]" if result["valid"] else "[FAIL]"
            file_name = Path(result["file"]).name
            return (f"{status} {file_name} "
                    f"({result['summary']['errorCount']} errors, "
                    f"{result['summary']['warningCount']} warnings)")
        else:
            # Multiple files
            status = "[OK]" if result["summary"]["scriptsWithIssues"] == 0 else "[FAIL]"
            return (f"{status} Cross-platform: {result['summary']['validScripts']}/"
                    f"{result['summary']['totalScripts']} compatible "
                    f"({result['summary']['totalErrors']} errors, "
                    f"{result['summary']['totalWarnings']} warnings)")


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(ValidateCrossPlatformScript)
