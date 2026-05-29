#!/usr/bin/env python3
"""
Infer intelligent names for skills/scripts/agents based on purpose.

Analyzes purpose keywords and proposes naming options with reasoning.
"""

import re
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript, create_cli_script
from common.models import NameSuggestion

# Verb/Noun mappings
VERB_MAPPINGS = {
    "analyze": ["analyze", "parse", "inspect", "examine", "scan"],
    "generate": ["generate", "create", "build", "produce", "make"],
    "validate": ["validate", "verify", "check", "test", "confirm"],
    "update": ["update", "modify", "change", "refresh", "sync"],
    "process": ["process", "handle", "transform", "convert", "parse"],
    "check": ["check", "verify", "validate", "test", "inspect"],
    "monitor": ["monitor", "watch", "track", "observe", "follow"],
    "review": ["review", "audit", "examine", "inspect", "evaluate"],
    "create": ["create", "generate", "build", "make", "scaffold"],
    "extract": ["extract", "parse", "retrieve", "fetch", "get"],
    "format": ["format", "style", "beautify", "prettify", "normalize"],
    "search": ["search", "find", "lookup", "query", "locate"],
    "detect": ["detect", "identify", "find", "discover", "locate"],
    "list": ["list", "show", "display", "enumerate", "get"],
    "configure": ["configure", "setup", "initialize", "prepare", "set"],
}

NOUN_MAPPINGS = {
    "commit": ["commits", "commit", "changes", "revisions"],
    "code": ["code", "source", "files", "codebase"],
    "test": ["tests", "test", "specs", "unit-tests"],
    "file": ["files", "file", "documents", "data"],
    "configuration": ["config", "configuration", "settings", "options"],
    "dependency": ["dependencies", "deps", "packages", "modules"],
    "documentation": ["docs", "documentation", "readme", "guides"],
    "quality": ["quality", "standards", "metrics", "checks"],
    "security": ["security", "vulnerabilities", "threats", "issues"],
    "structure": ["structure", "layout", "organization", "architecture"],
    "pattern": ["patterns", "pattern", "templates", "conventions"],
    "project": ["project", "repository", "repo", "workspace"],
    "issue": ["issues", "issue", "tickets", "ticket", "tasks", "task", "us", "user-stories", "user-story", "user stories", "user story"],
    "branch": ["branches", "branch", "refs", "heads"],
    "pull request": ["pull-request", "pr", "merge-request", "mr"],
}


class InferNameScript(BaseCLIScript):
    """Infer intelligent names based on purpose."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "--purpose",
            "-p",
            required=True,
            help="Purpose description (e.g., 'Analyze git commits')"
        )
        parser.add_argument(
            "--type",
            "-t",
            choices=["skill", "script", "agent"],
            default="script",
            help="Component type (default: script)"
        )
        parser.add_argument(
            "--count",
            "-c",
            type=int,
            default=3,
            help="Number of suggestions (default: 3)"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute name inference."""
        # Generate suggestions
        suggestions = self._infer_names(args.purpose, args.type, args.count)

        # Track metrics
        self.metrics.track("infer_name", {
            "type": args.type,
            "suggestions_count": len(suggestions)
        })

        return {
            "purpose": args.purpose,
            "type": args.type,
            "suggestions": [self._suggestion_to_dict(s) for s in suggestions]
        }

    def _infer_names(self, purpose: str, component_type: str, count: int) -> list[NameSuggestion]:
        """Infer name suggestions."""
        verbs = self._detect_verbs(purpose)
        nouns = self._detect_nouns(purpose)

        suggestions = []

        # Pattern 1: verb-noun (analyze-commits)
        for verb in verbs[:2]:
            for noun in nouns[:2]:
                name = f"{verb}-{noun}"
                reasoning = f"'{verb}' captures action, '{noun}' describes target"
                suggestions.append(NameSuggestion(name, reasoning, "verb-noun", 1.0))

        # Pattern 2: noun-verb (commit-analyzer)
        for noun in nouns[:2]:
            for verb in verbs[:2]:
                name = f"{noun}-{verb}er"
                reasoning = f"'{noun}' is focus, '{verb}er' indicates role"
                suggestions.append(NameSuggestion(name, reasoning, "noun-verb", 0.9))

        # Pattern 3: compound (git-commit-analyzer)
        if len(nouns) > 1:
            compound = f"{nouns[0]}-{nouns[1]}-{verbs[0]}er" if verbs else f"{nouns[0]}-{nouns[1]}"
            reasoning = "Compound name with multiple context words"
            suggestions.append(NameSuggestion(compound, reasoning, "compound", 0.8))

        # Deduplicate and sort by confidence
        seen = set()
        unique = []
        for s in suggestions:
            if s.name not in seen:
                seen.add(s.name)
                unique.append(s)

        unique.sort(key=lambda x: x.confidence, reverse=True)
        return unique[:count]

    def _detect_verbs(self, purpose: str) -> list[str]:
        """Detect action verbs."""
        purpose_lower = purpose.lower()
        detected = []

        for verb in VERB_MAPPINGS:
            if re.search(rf"\b{verb}\b", purpose_lower):
                detected.append(verb)

        if not detected:
            if re.search(r"\b(get|fetch|retrieve)\b", purpose_lower):
                detected.append("extract")
            elif re.search(r"\b(show|display|list)\b", purpose_lower):
                detected.append("list")
            elif re.search(r"\b(setup|init|initialize)\b", purpose_lower):
                detected.append("configure")
            else:
                detected.append("process")

        return detected

    def _detect_nouns(self, purpose: str) -> list[str]:
        """Detect subject nouns."""
        purpose_lower = purpose.lower()
        detected = []

        for noun, patterns in NOUN_MAPPINGS.items():
            for pattern in patterns:
                if re.search(rf"\b{pattern}\b", purpose_lower):
                    detected.append(noun.replace(" ", "-"))
                    break

        if not detected:
            words = re.findall(r'\b[a-z]+\b', purpose_lower)
            detected = [w for w in words if len(w) > 3 and w not in VERB_MAPPINGS][:2]

        return detected[:3]

    def _suggestion_to_dict(self, suggestion: NameSuggestion) -> dict:
        """Convert NameSuggestion to dict."""
        return {
            "name": suggestion.name,
            "reasoning": suggestion.reasoning,
            "pattern": suggestion.pattern,
            "confidence": suggestion.confidence
        }

    def format_text(self, result: dict) -> str:
        """Format as human-readable text."""
        lines = [
            f"Name Suggestions for: {result['purpose']}",
            f"Type: {result['type']}",
            ""
        ]

        for i, suggestion in enumerate(result['suggestions'], 1):
            lines.append(f"{i}. {suggestion['name']}")
            lines.append(f"   Pattern: {suggestion['pattern']}")
            lines.append(f"   Reasoning: {suggestion['reasoning']}")
            lines.append(f"   Confidence: {suggestion['confidence']:.1%}")
            lines.append("")

        return "\n".join(lines)

    def format_summary(self, result: dict) -> str:
        """Format as brief summary."""
        top = result['suggestions'][0] if result['suggestions'] else {"name": "N/A"}
        return f"Suggested: {top['name']} ({len(result['suggestions'])} options)"


if __name__ == "__main__":
    create_cli_script(InferNameScript)
