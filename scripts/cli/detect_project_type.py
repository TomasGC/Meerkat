#!/usr/bin/env python3
"""
Detect project type and return build/test commands (cross-platform).

Replaces: detect-project-type.ps1

Analyzes project files to determine type (Node, Go, .NET, Vue, Cypress, etc.)
and returns appropriate build and test commands.
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript


def detect_project_type(project_path: Path) -> dict:
    """
    Detect project type and return build/test commands.

    Args:
        project_path: Path to project root

    Returns:
        Dict with type, technology, build, and test commands
    """
    result = {
        "type": "unknown",
        "technology": "Unknown",
        "build": "(To be configured)",
        "test": "(To be configured)"
    }

    # Detect Cypress (check package.json for cypress dependency)
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                pkg = json.load(f)

            # Check for Cypress
            dependencies = pkg.get("dependencies", {})
            dev_dependencies = pkg.get("devDependencies", {})
            has_cypress = "cypress" in dependencies or "cypress" in dev_dependencies

            if has_cypress:
                result["type"] = "cypress"
                result["technology"] = "Cypress E2E Testing"
                result["build"] = "npm install"
                result["test"] = "npx cypress run"
            # Check for Vue
            elif "vue" in dependencies or \
                 (project_path / "vite.config.js").exists() or \
                 (project_path / "vite.config.ts").exists():
                result["type"] = "vuejs"
                result["technology"] = "Vue.js 3"
                result["build"] = "npm run build"
                result["test"] = "npm run test:unit"
            # Check for React
            elif "react" in dependencies:
                result["type"] = "node"
                result["technology"] = "React"
                result["build"] = "npm run build"
                result["test"] = "npm test"
            # Generic Node.js
            else:
                result["type"] = "node"
                result["technology"] = "Node.js"
                result["build"] = "npm install"
                result["test"] = "npm test"

        except (json.JSONDecodeError, Exception):
            # Fallback to generic Node
            result["type"] = "node"
            result["technology"] = "Node.js"
            result["build"] = "npm install"
            result["test"] = "npm test"

    # Detect Go
    elif (project_path / "go.mod").exists():
        result["type"] = "go"
        result["technology"] = "Go"
        result["build"] = "go build"
        result["test"] = "go test ./..."

    # Detect .NET (csproj or sln)
    elif list(project_path.glob("*.csproj")) or list(project_path.glob("*.sln")):
        # Check for Razor/CSHTML
        has_cshtml = bool(list(project_path.rglob("*.cshtml")))

        if has_cshtml:
            result["type"] = "cshtml"
            result["technology"] = "ASP.NET MVC"
            result["build"] = "dotnet build"
            result["test"] = "dotnet test"
        else:
            result["type"] = "dotnet"
            result["technology"] = ".NET"
            result["build"] = "dotnet build"
            result["test"] = "dotnet test"

    # Detect Python
    elif (project_path / "requirements.txt").exists() or \
         (project_path / "setup.py").exists() or \
         (project_path / "pyproject.toml").exists():
        result["type"] = "python"
        result["technology"] = "Python"
        result["build"] = "pip install -r requirements.txt"
        result["test"] = "pytest"

    # Detect Rust
    elif (project_path / "Cargo.toml").exists():
        result["type"] = "rust"
        result["technology"] = "Rust"
        result["build"] = "cargo build"
        result["test"] = "cargo test"

    return result


def format_env(result: dict) -> str:
    """Format result as environment variables."""
    lines = [
        f"PROJECT_TYPE={result['type']}",
        f"PROJECT_TECHNOLOGY={result['technology']}",
        f"BUILD_COMMAND={result['build']}",
        f"TEST_COMMAND={result['test']}"
    ]
    return "\n".join(lines)


class DetectProjectTypeScript(BaseCLIScript):
    """Detect project type and return build/test commands."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--path",
            "-p",
            default=".",
            help="Path to project root (defaults to current directory)"
        )
        # Override format to include 'env' option
        parser.add_argument(
            "--format-env",
            action="store_true",
            help="Output as environment variables (alternative to --format)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute project type detection."""
        try:
            # Resolve path
            project_path = Path(args.path).resolve()

            if not project_path.exists():
                self.logger.error(f"Path does not exist: {project_path}")
                return {
                    "success": False,
                    "error": f"Path does not exist: {project_path}"
                }

            if not project_path.is_dir():
                self.logger.error(f"Path is not a directory: {project_path}")
                return {
                    "success": False,
                    "error": f"Path is not a directory: {project_path}"
                }

            # Detect project type
            result = detect_project_type(project_path)

            self.metrics.track("detect_project_type", {
                "type": result["type"]
            })

            return {
                "success": True,
                **result,
                "format_env": args.format_env if hasattr(args, 'format_env') else False
            }

        except Exception as e:
            self.logger.error(f"Failed to detect project type: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = [
            f"Type: {result['type']}",
            f"Technology: {result['technology']}",
            f"Build: {result['build']}",
            f"Test: {result['test']}"
        ]
        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        return f"{result['technology']} project (type: {result['type']})"

    def output(self, result: dict, format: str) -> None:
        """Override output to support env format."""
        if result.get("format_env"):
            print(format_env(result))
        else:
            super().output(result, format)


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(DetectProjectTypeScript)
