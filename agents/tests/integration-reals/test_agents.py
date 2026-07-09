#!/usr/bin/env python3
"""Integration tests for agents — reads real AGENT.md files on disk"""

import pytest
from pathlib import Path


class TestAgents:

    def test_agents_exist(self):
        agents_dir = Path.home() / ".claude" / "agents"
        for agent in ["task-delegator", "test-runner", "code-reviewer", "git-helper", "ollama-router"]:
            assert (agents_dir / agent / "AGENT.md").exists(), f"Agent {agent} not found"

    def test_agent_structure(self):
        agents_dir = Path.home() / ".claude" / "agents"
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            agent_file = agent_dir / "AGENT.md"
            if not agent_file.exists():
                continue
            content = agent_file.read_text(encoding="utf-8")
            assert content.startswith("---"), f"Agent {agent_dir.name} missing frontmatter"
            assert "name:" in content
            assert "description:" in content
            assert "tools:" in content
            assert "model:" in content

    def test_task_delegator_agent(self):
        content = (Path.home() / ".claude" / "agents" / "task-delegator" / "AGENT.md").read_text(encoding="utf-8")
        assert "delegate" in content.lower()
        assert "routing" in content.lower() or "route" in content.lower()
        assert "ollama" in content.lower()
        assert "model: haiku" in content

    def test_code_reviewer_agent(self):
        content = (Path.home() / ".claude" / "agents" / "code-reviewer" / "AGENT.md").read_text(encoding="utf-8")
        assert "qwen2.5-coder" in content.lower()
        assert "quick" in content.lower() or "deep" in content.lower()

    def test_git_helper_agent(self):
        content = (Path.home() / ".claude" / "agents" / "git-helper" / "AGENT.md").read_text(encoding="utf-8")
        assert "git diff" in content.lower()
        assert "git log" in content.lower()
        assert "json" in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
