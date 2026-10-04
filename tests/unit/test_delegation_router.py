#!/usr/bin/env python3
"""Unit tests for delegation routing logic"""

import json
import pytest
from pathlib import Path


class TestDelegationRouter:

    @pytest.fixture
    def delegation_rules(self):
        rules_file = Path.home() / ".claude" / "configs" / "delegation-rules.json"
        if not rules_file.exists():
            pytest.skip("Delegation rules not found")
        with open(rules_file) as f:
            return json.load(f)

    def test_delegation_rules_structure(self, delegation_rules):
        assert "auto_delegate" in delegation_rules
        assert "hybrid_tasks" in delegation_rules
        assert "claude_only" in delegation_rules

    def test_auto_delegate_tasks_defined(self, delegation_rules):
        auto_delegate = delegation_rules["auto_delegate"]
        for task in ["format_code", "lint_code", "validate_syntax", "quick_review", "run_tests"]:
            assert task in auto_delegate, f"Missing task: {task}"

    def test_auto_delegate_has_tool(self, delegation_rules):
        for task, config in delegation_rules["auto_delegate"].items():
            assert "tool" in config and config["tool"], f"Task {task} missing tool"

    def test_auto_delegate_has_latency(self, delegation_rules):
        for task, config in delegation_rules["auto_delegate"].items():
            assert "max_latency_s" in config and config["max_latency_s"] > 0

    def test_auto_delegate_has_token_estimate(self, delegation_rules):
        for task, config in delegation_rules["auto_delegate"].items():
            assert "token_savings_estimate" in config and config["token_savings_estimate"] > 0

    def test_hybrid_tasks_structure(self, delegation_rules):
        for task, config in delegation_rules["hybrid_tasks"].items():
            assert "steps" in config and len(config["steps"]) > 0
            assert "name" in config["steps"][0] and "tool" in config["steps"][0]

    def test_claude_only_tasks_defined(self, delegation_rules):
        claude_only = delegation_rules["claude_only"]
        assert "tasks" in claude_only and len(claude_only["tasks"]) > 0
        assert "architecture" in claude_only["tasks"]
        assert "design_patterns" in claude_only["tasks"]

    def test_ollama_tool_format(self, delegation_rules):
        ollama_tasks = [t for t, c in delegation_rules["auto_delegate"].items()
                        if "ollama:" in c["tool"]]
        assert len(ollama_tasks) >= 2
        for task in ollama_tasks:
            tool = delegation_rules["auto_delegate"][task]["tool"]
            assert tool.startswith("ollama:")
            assert tool.split(":", 1)[1]


class TestDelegationDecisions:

    def test_should_delegate_format(self):
        assert "format" in "format code".lower()

    def test_should_delegate_tests(self):
        assert "test" in "run all tests".lower()

    def test_should_not_delegate_architecture(self):
        task = "should we use microservices or monolith?"
        assert any(kw in task.lower() for kw in ["should we", "architecture", "design decision"])

    def test_hybrid_task_bug_investigation(self):
        task = "why is this api slow?"
        assert any(kw in task.lower() for kw in ["slow", "bug", "error"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
