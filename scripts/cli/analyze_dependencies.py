#!/usr/bin/env python3
"""
Analyze project dependencies from package files (cross-platform).

Replaces: analyze-dependencies.ps1

Parses package manager files (package.json, requirements.txt, Cargo.toml,
go.mod, etc.) to extract language, framework, dependencies, and build info.
Used for project type detection and template generation.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript


def analyze_package_json(content: str, top_n: int) -> dict:
    """Analyze Node.js package.json file."""
    data = json.loads(content)

    result = {
        "language": "javascript",
        "framework": None,
        "packageManager": "npm",
        "dependencies": [],
        "devDependencies": [],
        "scripts": {}
    }

    # Extract dependencies
    if "dependencies" in data:
        result["dependencies"] = [
            {"name": name, "version": version}
            for name, version in list(data["dependencies"].items())[:top_n]
        ]

    if "devDependencies" in data:
        result["devDependencies"] = [
            {"name": name, "version": version}
            for name, version in list(data["devDependencies"].items())[:top_n]
        ]

    # Detect framework
    all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

    if "react" in all_deps or "next" in all_deps:
        result["framework"] = "react"
        if "next" in all_deps:
            result["framework"] = "next.js"
    elif "vue" in all_deps or "nuxt" in all_deps:
        result["framework"] = "vue"
        if "nuxt" in all_deps:
            result["framework"] = "nuxt"
    elif "@angular/core" in all_deps:
        result["framework"] = "angular"
    elif "express" in all_deps:
        result["framework"] = "express"

    # Detect package manager
    if "workspaces" in data:
        result["packageManager"] = "yarn" if data.get("packageManager", "").startswith("yarn") else "npm"

    # Extract scripts
    if "scripts" in data:
        result["scripts"] = data["scripts"]

    return result


def analyze_requirements_txt(content: str, top_n: int) -> dict:
    """Analyze Python requirements.txt file."""
    result = {
        "language": "python",
        "framework": None,
        "packageManager": "pip",
        "dependencies": [],
        "devDependencies": [],
        "scripts": {}
    }

    # Parse requirements
    for line in content.splitlines()[:top_n]:
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue

        # Extract package name and version
        match = re.match(r"([a-zA-Z0-9_-]+)([>=<~!]=?)?([\d.]+)?", line)
        if match:
            name = match.group(1)
            operator = match.group(2) if match.group(2) else ""
            version_num = match.group(3) if match.group(3) else ""
            version = f"{operator}{version_num}" if version_num else "any"
            result["dependencies"].append({"name": name, "version": version})

            # Detect framework (priority: django > fastapi > flask)
            if name == "django" and not result["framework"]:
                result["framework"] = "django"
            elif name == "fastapi" and result["framework"] not in ["django"]:
                result["framework"] = "fastapi"
            elif name == "flask" and not result["framework"]:
                result["framework"] = "flask"

    return result


def analyze_cargo_toml(content: str, top_n: int) -> dict:
    """Analyze Rust Cargo.toml file."""
    result = {
        "language": "rust",
        "framework": None,
        "packageManager": "cargo",
        "dependencies": [],
        "devDependencies": [],
        "scripts": {}
    }

    # Simple TOML parsing (dependencies section)
    in_dependencies = False
    in_dev_dependencies = False
    count = 0

    for line in content.splitlines():
        line = line.strip()

        # Section headers
        if line == "[dependencies]":
            in_dependencies = True
            in_dev_dependencies = False
            continue
        elif line == "[dev-dependencies]":
            in_dependencies = False
            in_dev_dependencies = True
            continue
        elif line.startswith("["):
            in_dependencies = False
            in_dev_dependencies = False
            continue

        # Parse dependency lines
        if (in_dependencies or in_dev_dependencies) and "=" in line and count < top_n:
            # Simple format: name = "version"
            match = re.match(r'([a-z0-9_-]+)\s*=\s*"([^"]+)"', line)
            if match:
                name = match.group(1)
                version = match.group(2)
            else:
                # Complex format: name = { version = "version", features = [...] }
                match = re.match(r'([a-z0-9_-]+)\s*=\s*\{\s*version\s*=\s*"([^"]+)"', line)
                if match:
                    name = match.group(1)
                    version = match.group(2)
                else:
                    continue

            dep = {"name": name, "version": version}

            if in_dependencies:
                result["dependencies"].append(dep)
            else:
                result["devDependencies"].append(dep)

            count += 1

            # Detect framework
            if name == "actix-web":
                result["framework"] = "actix-web"
            elif name == "rocket":
                result["framework"] = "rocket"

    return result


def analyze_go_mod(content: str, top_n: int) -> dict:
    """Analyze Go go.mod file."""
    result = {
        "language": "go",
        "framework": None,
        "packageManager": "go",
        "dependencies": [],
        "devDependencies": [],
        "scripts": {}
    }

    # Parse require block
    for line in content.splitlines():
        line = line.strip()

        if line.startswith("require "):
            # Single-line require
            match = re.match(r"require\s+([^\s]+)\s+([^\s]+)", line)
            if match and len(result["dependencies"]) < top_n:
                result["dependencies"].append({
                    "name": match.group(1),
                    "version": match.group(2)
                })
        elif not line.startswith(("module", "go ", ")", "//")):
            # Multi-line require block
            match = re.match(r"([^\s]+)\s+([^\s]+)", line)
            if match and len(result["dependencies"]) < top_n:
                name = match.group(1)
                version = match.group(2)

                result["dependencies"].append({"name": name, "version": version})

                # Detect framework
                if "gin-gonic/gin" in name:
                    result["framework"] = "gin"
                elif "labstack/echo" in name:
                    result["framework"] = "echo"
                elif "gofiber/fiber" in name:
                    result["framework"] = "fiber"
                elif "gorilla/mux" in name:
                    result["framework"] = "gorilla/mux"

    return result


def analyze_pom_xml(content: str, top_n: int) -> dict:
    """Analyze Java pom.xml file."""
    result = {
        "language": "java",
        "framework": None,
        "packageManager": "maven",
        "dependencies": [],
        "devDependencies": [],
        "scripts": {}
    }

    # Simple XML parsing (dependencies)
    dependencies = re.findall(r"<dependency>(.*?)</dependency>", content, re.DOTALL)

    for dep in dependencies[:top_n]:
        group_match = re.search(r"<groupId>([^<]+)</groupId>", dep)
        artifact_match = re.search(r"<artifactId>([^<]+)</artifactId>", dep)
        version_match = re.search(r"<version>([^<]+)</version>", dep)

        if artifact_match:
            group = group_match.group(1) if group_match else ""
            artifact = artifact_match.group(1)
            name = f"{group}:{artifact}" if group else artifact
            version = version_match.group(1) if version_match else "latest"

            result["dependencies"].append({"name": name, "version": version})

            # Detect framework
            if "spring-boot" in artifact or "spring" in group:
                result["framework"] = "spring"

    return result


def analyze_dependencies(file_path: Path, top_n: int = 10) -> dict:
    """
    Analyze dependencies from package file.

    Args:
        file_path: Path to package file
        top_n: Number of top dependencies to return

    Returns:
        Dictionary with language, framework, dependencies, etc.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    filename = file_path.name

    # Dispatch based on filename
    if filename == "package.json":
        analysis = analyze_package_json(content, top_n)
    elif filename == "requirements.txt":
        analysis = analyze_requirements_txt(content, top_n)
    elif filename == "Cargo.toml":
        analysis = analyze_cargo_toml(content, top_n)
    elif filename == "go.mod":
        analysis = analyze_go_mod(content, top_n)
    elif filename == "pom.xml":
        analysis = analyze_pom_xml(content, top_n)
    else:
        raise ValueError(f"Unsupported package file: {filename}")

    # Add file path
    analysis["file"] = str(file_path)

    return analysis


class AnalyzeDependenciesScript(BaseCLIScript):
    """Analyze project dependencies from package files."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--file",
            required=True,
            help="Path to package file (auto-detects type from filename)"
        )
        parser.add_argument(
            "--top-n",
            "-n",
            type=int,
            default=10,
            help="Number of top dependencies to return (default: 10)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute dependency analysis."""
        try:
            # Resolve path
            file_path = Path(args.file)

            # Analyze dependencies
            result = analyze_dependencies(file_path, args.top_n)

            self.metrics.track("analyze_dependencies", {
                "file": result["file"],
                "language": result["language"],
                "framework": result["framework"],
                "dependencyCount": len(result["dependencies"])
            })

            return {
                "success": True,
                **result
            }

        except FileNotFoundError as e:
            self.logger.error(str(e))
            return {
                "success": False,
                "error": str(e)
            }
        except ValueError as e:
            self.logger.error(str(e))
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            self.logger.error(f"Failed to analyze dependencies: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        lines = [
            f"Dependency Analysis: {result['file']}",
            "",
            f"Language: {result['language']}",
            f"Framework: {result['framework'] or 'None detected'}",
            f"Package Manager: {result['packageManager']}",
            ""
        ]

        if result['dependencies']:
            lines.append(f"Dependencies ({len(result['dependencies'])}):")
            for dep in result['dependencies']:
                lines.append(f"  - {dep['name']} ({dep['version']})")
            lines.append("")

        if result['devDependencies']:
            lines.append(f"Dev Dependencies ({len(result['devDependencies'])}):")
            for dep in result['devDependencies']:
                lines.append(f"  - {dep['name']} ({dep['version']})")
            lines.append("")

        if result['scripts']:
            lines.append(f"Scripts ({len(result['scripts'])}):")
            for name, cmd in list(result['scripts'].items())[:5]:
                lines.append(f"  - {name}: {cmd}")
            lines.append("")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        if not result.get("success"):
            return f"[ERROR] {result.get('error', 'Unknown error')}"

        framework = result['framework'] or result['language']
        return (f"{framework} project with {len(result['dependencies'])} dependencies "
                f"({result['packageManager']})")


if __name__ == "__main__":
    from common.cli.base import create_cli_script
    create_cli_script(AnalyzeDependenciesScript)
