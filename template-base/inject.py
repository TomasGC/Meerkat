#!/usr/bin/env python3
"""Inject template variables into output files."""

import argparse
from datetime import date
from pathlib import Path

LANGUAGE_VARS: dict[str, dict[str, str]] = {
    "go": {
        "PROJECT_TYPE": "Go Service",
        "LANGUAGE": "Go",
        "BUILD_PERMISSION": "Bash:go build",
        "TEST_PERMISSION": "Bash:go test",
    },
    "node": {
        "PROJECT_TYPE": "Node.js Service",
        "LANGUAGE": "TypeScript",
        "BUILD_PERMISSION": "Bash:npm run build",
        "TEST_PERMISSION": "Bash:npm test",
    },
    "vuejs": {
        "PROJECT_TYPE": "Vue.js 3 Application",
        "LANGUAGE": "Vue 3",
        "BUILD_PERMISSION": "Bash:npm run build",
        "TEST_PERMISSION": "Bash:npm run test:unit",
    },
    "dotnet": {
        "PROJECT_TYPE": ".NET Service",
        "LANGUAGE": "C#",
        "BUILD_PERMISSION": "Bash:dotnet build",
        "TEST_PERMISSION": "Bash:dotnet test",
    },
    "cshtml": {
        "PROJECT_TYPE": "ASP.NET MVC Application",
        "LANGUAGE": "C#",
        "BUILD_PERMISSION": "Bash:dotnet build",
        "TEST_PERMISSION": "Bash:dotnet test",
    },
    "kotlin": {
        "PROJECT_TYPE": "Kotlin/Android Application",
        "LANGUAGE": "Kotlin",
        "BUILD_PERMISSION": "Bash:./gradlew build",
        "TEST_PERMISSION": "Bash:./gradlew test",
    },
    "python": {
        "PROJECT_TYPE": "Python Application",
        "LANGUAGE": "Python 3.12+",
        "BUILD_PERMISSION": "Bash:python -m build",
        "TEST_PERMISSION": "Bash:python -m pytest",
    },
    "bash": {
        "PROJECT_TYPE": "Bash Script Collection",
        "LANGUAGE": "Bash",
        "BUILD_PERMISSION": "Bash:shellcheck",
        "TEST_PERMISSION": "Bash:bats",
    },
    "powershell": {
        "PROJECT_TYPE": "PowerShell Module",
        "LANGUAGE": "PowerShell 7+",
        "BUILD_PERMISSION": "Bash:pwsh -Command Invoke-Build",
        "TEST_PERMISSION": "Bash:pwsh -Command Invoke-Pester",
    },
}

_BASE_DIR = Path(__file__).parent


def _replace_content_vars(template: str, content_dir: Path) -> str:
    if not content_dir.exists():
        return template
    for content_file in sorted(content_dir.glob("*.md")):
        var_name = content_file.stem.upper().replace("-", "_")
        template = template.replace(f"{{{{{var_name}}}}}", content_file.read_text(encoding="utf-8"))
    return template


def cmd_template(args: argparse.Namespace) -> None:
    """Inject template variables into a file."""
    template_file: Path = args.template_file
    output_file: Path = args.output_file
    language: str = args.language

    content_dir = _BASE_DIR / "content" / language
    template = template_file.read_text(encoding="utf-8")
    template = template.replace("{{DATE}}", date.today().isoformat())
    template = _replace_content_vars(template, content_dir)

    for var, value in LANGUAGE_VARS[language].items():
        template = template.replace(f"{{{{{var}}}}}", value)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(template, encoding="utf-8")
    print(f"Template injected: {output_file}")


def cmd_conventions(args: argparse.Namespace) -> None:
    """Generate contexts/conventions.md: base + language-specific + Python (always).

    Python conventions are appended to every project because all projects
    include Python automation scripts. For Python projects, they are not
    duplicated.
    """
    language: str = args.language
    output_file: Path = args.output_file

    common_file = _BASE_DIR / "common" / ".claude" / "contexts" / "conventions.md"
    lang_file = _BASE_DIR / "content" / language / "conventions.md"
    python_file = _BASE_DIR / "content" / "python" / "conventions.md"

    parts: list[str] = []

    if common_file.exists():
        parts.append(common_file.read_text(encoding="utf-8").rstrip())

    if lang_file.exists():
        parts.append(lang_file.read_text(encoding="utf-8").rstrip())

    if language != "python" and python_file.exists():
        parts.append(python_file.read_text(encoding="utf-8").rstrip())

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"Conventions created: {output_file}")


def cmd_commands(args: argparse.Namespace) -> None:
    """Generate contexts/commands.md: header + language-specific commands."""
    language: str = args.language
    output_file: Path = args.output_file

    common_file = _BASE_DIR / "common" / ".claude" / "contexts" / "commands.md"
    lang_file = _BASE_DIR / "content" / language / "commands.md"

    parts: list[str] = []

    if common_file.exists():
        parts.append(common_file.read_text(encoding="utf-8").rstrip())

    if lang_file.exists():
        parts.append(lang_file.read_text(encoding="utf-8").rstrip())

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"Commands created: {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject template variables")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tmpl = subparsers.add_parser("template", help="Inject template variables into a file")
    tmpl.add_argument("template_file", type=Path)
    tmpl.add_argument("output_file", type=Path)
    tmpl.add_argument("language", choices=list(LANGUAGE_VARS))

    conv = subparsers.add_parser("conventions", help="Generate conventions.md (base + language + Python)")
    conv.add_argument("output_file", type=Path)
    conv.add_argument("language", choices=list(LANGUAGE_VARS))

    cmds = subparsers.add_parser("commands", help="Generate commands.md (header + language-specific)")
    cmds.add_argument("output_file", type=Path)
    cmds.add_argument("language", choices=list(LANGUAGE_VARS))

    args = parser.parse_args()

    if args.command == "template":
        cmd_template(args)
    elif args.command == "conventions":
        cmd_conventions(args)
    elif args.command == "commands":
        cmd_commands(args)


if __name__ == "__main__":
    main()
