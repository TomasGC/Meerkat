#!/usr/bin/env python3
"""
Propose fixes for CI errors using Ollama for mechanical fixes.

Delegates mechanical error analysis to Ollama (qwen2.5-coder:7b) to minimize
Claude token usage. Escalates complex errors back to Claude.

Used by ci-fix-proposer agent and analyze-github-ci skill.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.cli.base import BaseCLIScript
from common.utils import run_command


@dataclass
class ErrorInput:
    """CI error input."""
    error_id: str
    error_type: str  # compilation, test, lint, build
    error_message: str
    file_path: str | None = None
    line_number: int | None = None
    context_lines: list[str] = field(default_factory=list)


@dataclass
class FixProposal:
    """Fix proposal from Ollama."""
    error_id: str
    fix_type: str
    file_path: str
    line_number: int | None
    original_code: str | None
    fixed_code: str
    reasoning: str
    confidence: str  # high, medium, low
    ollama_latency_ms: int


@dataclass
class EscalatedError:
    """Error escalated to Claude."""
    error_id: str
    error_type: str
    reason: str
    requires_claude: bool = True


def should_delegate_to_ollama(error: ErrorInput) -> bool:
    """
    Determine if error should be delegated to Ollama or escalated to Claude.

    Args:
        error: Error input

    Returns:
        True if delegable to Ollama (mechanical fix), False if escalate to Claude
    """
    # Patterns that are mechanical and delegable
    mechanical_patterns = [
        r"unresolved reference",
        r"cannot find symbol",
        r"missing import",
        r"expected.*but was",  # Test assertion
        r"lint.*suppress",
        r"unused.*variable",
    ]

    # Patterns that require Claude (complex)
    complex_patterns = [
        r"circular dependency",
        r"design pattern",
        r"architecture",
        r"refactor",
        r"multiple files",
    ]

    message_lower = error.error_message.lower()

    # Check if complex
    for pattern in complex_patterns:
        if re.search(pattern, message_lower):
            return False

    # Check if mechanical
    for pattern in mechanical_patterns:
        if re.search(pattern, message_lower):
            return True

    # Default: delegate simple compilation/test/lint errors
    if error.error_type in ["compilation", "test", "lint"]:
        return True

    # Default: escalate build/infrastructure errors
    return False


def extract_context(error: ErrorInput, repo_path: Path) -> dict[str, Any]:
    """
    Extract context for error using grep and file reading.

    Args:
        error: Error input
        repo_path: Repository path

    Returns:
        Context dictionary
    """
    context = {
        "file_content": None,
        "dependencies": [],
        "related_files": []
    }

    if not error.file_path:
        return context

    file_path = repo_path / error.file_path

    # Read file context (10 lines before/after error)
    if file_path.exists() and error.line_number:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                start = max(0, error.line_number - 6)
                end = min(len(lines), error.line_number + 5)
                context["file_content"] = "".join(lines[start:end])
        except Exception:
            pass

    # For import errors, search for class in dependencies
    if "unresolved reference" in error.error_message.lower():
        # Extract class name
        match = re.search(r"unresolved reference: (\w+)", error.error_message, re.IGNORECASE)
        if match:
            class_name = match.group(1)
            # Search in build files
            build_files = ["build.gradle", "build.gradle.kts", "package.json", "go.mod"]
            for build_file in build_files:
                build_path = repo_path / build_file
                if build_path.exists():
                    returncode, stdout, _ = run_command(
                        ["grep", "-i", class_name, str(build_path)],
                        timeout=5
                    )
                    if returncode == 0 and stdout.strip():
                        context["dependencies"].append({
                            "file": build_file,
                            "match": stdout.strip()
                        })

    return context


def invoke_ollama_for_fix(error: ErrorInput, context: dict) -> dict | None:
    """
    Invoke Ollama to propose a fix.

    Args:
        error: Error input
        context: Context from extract_context()

    Returns:
        Fix proposal dict or None on failure
    """
    # Build prompt
    prompt = f"""Task: Propose a fix for this CI error.

Error Type: {error.error_type}
Error Message: {error.error_message}
File: {error.file_path}:{error.line_number if error.line_number else "unknown"}

Context:
{context.get("file_content", "No context available")}

Respond with JSON only (no markdown):
{{
  "fix_type": "add_import|change_value|suppress_lint|fix_syntax",
  "fixed_code": "the fix code",
  "reasoning": "why this fix resolves the error",
  "confidence": "high|medium|low"
}}
"""

    try:
        # Invoke Ollama
        import time
        start = time.time()

        result = subprocess.run(
            ["ollama", "run", "qwen2.5-coder:7b", prompt],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace"
        )

        latency_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        # Try to extract JSON (Ollama might wrap in markdown)
        json_match = re.search(r'\{[^}]+\}', output, re.DOTALL)
        if json_match:
            output = json_match.group(0)

        response = json.loads(output)

        # Validate response
        required_keys = ["fix_type", "fixed_code", "reasoning", "confidence"]
        if not all(key in response for key in required_keys):
            return None

        response["latency_ms"] = latency_ms
        return response

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


class ProposeCIFixesScript(BaseCLIScript):
    """Propose CI fixes using Ollama."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--errors-json",
            type=Path,
            required=True,
            help="Path to errors JSON file from analyze_ci_failure.py"
        )
        parser.add_argument(
            "--repo-path",
            type=Path,
            default=Path.cwd(),
            help="Repository path (default: current directory)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute fix proposal."""
        import time
        start_time = time.time()

        # Check Ollama availability
        returncode, _, _ = run_command(["ollama", "ps"], timeout=5)
        if returncode != 0:
            self.logger.warning("Ollama not available - escalating all errors to Claude")
            return {
                "success": False,
                "error": "Ollama service unavailable",
                "fallback": "escalate_all_to_claude"
            }

        # Load errors
        if not args.errors_json.exists():
            return {
                "success": False,
                "error": f"Errors file not found: {args.errors_json}"
            }

        with open(args.errors_json, "r", encoding="utf-8") as f:
            errors_data = json.load(f)

        errors = []
        for idx, err in enumerate(errors_data.get("errors", [])):
            errors.append(ErrorInput(
                error_id=err.get("id", f"error_{idx}"),
                error_type=err.get("type", "unknown"),
                error_message=err.get("message", ""),
                file_path=err.get("file"),
                line_number=err.get("line"),
                context_lines=err.get("context", [])
            ))

        self.logger.info(f"Analyzing {len(errors)} errors")

        # Process errors
        proposals = []
        escalated = []
        delegated_count = 0
        escalated_count = 0

        for error in errors:
            # Determine strategy
            if should_delegate_to_ollama(error):
                delegated_count += 1
                self.logger.debug(f"Delegating {error.error_id} to Ollama")

                # Extract context
                context = extract_context(error, args.repo_path)

                # Invoke Ollama
                fix_response = invoke_ollama_for_fix(error, context)

                if fix_response:
                    proposals.append(FixProposal(
                        error_id=error.error_id,
                        fix_type=fix_response["fix_type"],
                        file_path=error.file_path or "unknown",
                        line_number=error.line_number,
                        original_code=context.get("file_content"),
                        fixed_code=fix_response["fixed_code"],
                        reasoning=fix_response["reasoning"],
                        confidence=fix_response["confidence"],
                        ollama_latency_ms=fix_response["latency_ms"]
                    ))
                else:
                    # Ollama failed, escalate
                    escalated_count += 1
                    escalated.append(EscalatedError(
                        error_id=error.error_id,
                        error_type=error.error_type,
                        reason="Ollama failed to propose fix"
                    ))
            else:
                escalated_count += 1
                self.logger.debug(f"Escalating {error.error_id} to Claude")
                escalated.append(EscalatedError(
                    error_id=error.error_id,
                    error_type=error.error_type,
                    reason="Complex error requiring Claude analysis"
                ))

        # Calculate token savings
        # Estimate: 8K tokens saved per Ollama-handled error
        estimated_token_savings = len(proposals) * 8000
        claude_tokens_needed = len(escalated) * 3000

        analysis_time_ms = int((time.time() - start_time) * 1000)

        result = {
            "success": True,
            "analysis_time_ms": analysis_time_ms,
            "total_errors_analyzed": len(errors),
            "delegated_to_ollama": delegated_count,
            "escalated_to_claude": escalated_count,
            "fix_proposals": [
                {
                    "error_id": p.error_id,
                    "fix_type": p.fix_type,
                    "file_path": p.file_path,
                    "line_number": p.line_number,
                    "fixed_code": p.fixed_code,
                    "reasoning": p.reasoning,
                    "confidence": p.confidence,
                    "ollama_latency_ms": p.ollama_latency_ms
                }
                for p in proposals
            ],
            "escalated_errors": [
                {
                    "error_id": e.error_id,
                    "error_type": e.error_type,
                    "reason": e.reason,
                    "requires_claude": e.requires_claude
                }
                for e in escalated
            ],
            "estimated_token_savings": estimated_token_savings,
            "claude_tokens_needed": claude_tokens_needed
        }

        self.metrics.track("propose_ci_fixes", {
            "total_errors": len(errors),
            "delegated": delegated_count,
            "escalated": escalated_count,
            "token_savings": estimated_token_savings
        })

        return result


def main():
    """CLI entry point."""
    from common.cli.base import create_cli_script
    create_cli_script(ProposeCIFixesScript)


if __name__ == "__main__":
    main()
