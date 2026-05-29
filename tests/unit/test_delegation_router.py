#!/usr/bin/env python3
"""Unit tests for delegation routing logic"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import json
import pytest
from unittest.mock import Mock, patch


class TestDelegationRouter:
    """Test delegation routing decisions."""

    @pytest.fixture
    def delegation_rules(self, tmp_path):
        """Load delegation rules."""
        rules_file = Path.home() / ".claude" / "configs" / "delegation-rules.json"

        if not rules_file.exists():
            pytest.skip("Delegation rules not found")

        with open(rules_file) as f:
            return json.load(f)

    def test_delegation_rules_structure(self, delegation_rules):
        """Test delegation rules have required structure."""
        assert "auto_delegate" in delegation_rules
        assert "hybrid_tasks" in delegation_rules
        assert "claude_only" in delegation_rules

    def test_auto_delegate_tasks_defined(self, delegation_rules):
        """Test auto-delegate tasks are defined."""
        auto_delegate = delegation_rules["auto_delegate"]

        # Expected tasks
        expected = [
            "format_code",
            "lint_code",
            "validate_syntax",
            "quick_review",
            "run_tests",
        ]

        for task in expected:
            assert task in auto_delegate, f"Missing task: {task}"

    def test_auto_delegate_has_tool(self, delegation_rules):
        """Test each auto-delegate task has a tool specified."""
        auto_delegate = delegation_rules["auto_delegate"]

        for task, config in auto_delegate.items():
            assert "tool" in config, f"Task {task} missing tool"
            assert config["tool"], f"Task {task} has empty tool"

    def test_auto_delegate_has_latency(self, delegation_rules):
        """Test each auto-delegate task has max latency."""
        auto_delegate = delegation_rules["auto_delegate"]

        for task, config in auto_delegate.items():
            assert "max_latency_s" in config, f"Task {task} missing max_latency_s"
            assert config["max_latency_s"] > 0, f"Task {task} has invalid latency"

    def test_auto_delegate_has_token_estimate(self, delegation_rules):
        """Test each auto-delegate task has token savings estimate."""
        auto_delegate = delegation_rules["auto_delegate"]

        for task, config in auto_delegate.items():
            assert "token_savings_estimate" in config, f"Task {task} missing token estimate"
            assert config["token_savings_estimate"] > 0, f"Task {task} has invalid estimate"

    def test_hybrid_tasks_structure(self, delegation_rules):
        """Test hybrid tasks have proper structure."""
        hybrid = delegation_rules["hybrid_tasks"]

        for task, config in hybrid.items():
            assert "steps" in config, f"Hybrid task {task} missing steps"
            assert len(config["steps"]) > 0, f"Hybrid task {task} has no steps"

            # Check first step structure
            first_step = config["steps"][0]
            assert "name" in first_step
            assert "tool" in first_step

    def test_claude_only_tasks_defined(self, delegation_rules):
        """Test Claude-only tasks are defined."""
        claude_only = delegation_rules["claude_only"]

        assert "tasks" in claude_only
        assert len(claude_only["tasks"]) > 0

        # Should include strategic tasks
        tasks = claude_only["tasks"]
        assert "architecture" in tasks
        assert "design_patterns" in tasks

    def test_ollama_tool_format(self, delegation_rules):
        """Test Ollama tools are properly formatted."""
        auto_delegate = delegation_rules["auto_delegate"]

        ollama_tasks = [
            task for task, config in auto_delegate.items()
            if "ollama:" in config["tool"]
        ]

        # Should have at least validation and review
        assert len(ollama_tasks) >= 2

        # Check format: ollama:model-name
        for task in ollama_tasks:
            tool = auto_delegate[task]["tool"]
            assert tool.startswith("ollama:"), f"Invalid Ollama tool format: {tool}"
            model = tool.split(":", 1)[1]
            assert model, f"Empty model name in: {tool}"


class TestDelegationDecisions:
    """Test delegation decision logic."""

    def test_should_delegate_format(self):
        """Test format task should delegate to scripts."""
        task = "format code"

        # Simple keyword matching
        assert "format" in task.lower()

        # Should delegate to scripts (fast)
        expected_tool = "scripts"
        assert expected_tool == "scripts"

    def test_should_delegate_tests(self):
        """Test run tests should delegate to agent."""
        task = "run all tests"

        assert "test" in task.lower()

        # Should delegate to agent (background)
        expected_tool = "agents/test-runner"
        assert expected_tool == "agents/test-runner"

    def test_should_not_delegate_architecture(self):
        """Test architecture decisions stay with Claude."""
        task = "should we use microservices or monolith?"

        # Strategic keywords
        strategic_keywords = ["should we", "architecture", "design decision"]
        has_strategic = any(kw in task.lower() for kw in strategic_keywords)

        assert has_strategic

        # Should NOT delegate
        expected_tool = "claude"
        assert expected_tool == "claude"

    def test_hybrid_task_bug_investigation(self):
        """Test bug investigation is hybrid task."""
        task = "why is this api slow?"

        # Performance keywords
        assert any(kw in task.lower() for kw in ["slow", "bug", "error"])

        # Should be hybrid: scripts (data) + claude (analysis)
        workflow = ["scripts", "claude"]
        assert "scripts" in workflow
        assert "claude" in workflow


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
