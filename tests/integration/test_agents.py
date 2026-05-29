#!/usr/bin/env python3
"""Integration tests for agents"""

import subprocess
import pytest
from pathlib import Path


class TestAgents:
    """Integration tests for specialized agents."""

    def test_agents_exist(self):
        """Test all agents are created."""
        agents_dir = Path.home() / ".claude" / "agents"

        expected_agents = [
            "task-delegator",
            "test-runner",
            "code-reviewer",
            "git-helper",
            "ollama-router"
        ]

        for agent in expected_agents:
            agent_file = agents_dir / agent / "AGENT.md"
            assert agent_file.exists(), f"Agent {agent} not found"

    def test_agent_structure(self):
        """Test agents have proper YAML frontmatter."""
        agents_dir = Path.home() / ".claude" / "agents"

        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            agent_file = agent_dir / "AGENT.md"
            if not agent_file.exists():
                continue

            content = agent_file.read_text(encoding="utf-8")

            # Check frontmatter
            assert content.startswith("---"), f"Agent {agent_dir.name} missing frontmatter"
            assert "name:" in content, f"Agent {agent_dir.name} missing name"
            assert "description:" in content, f"Agent {agent_dir.name} missing description"
            assert "tools:" in content, f"Agent {agent_dir.name} missing tools"
            assert "model:" in content, f"Agent {agent_dir.name} missing model"

    def test_task_delegator_agent(self):
        """Test task-delegator agent structure."""
        agent_file = Path.home() / ".claude" / "agents" / "task-delegator" / "AGENT.md"
        content = agent_file.read_text(encoding="utf-8")

        # Should have routing logic
        assert "auto_delegate" in content.lower() or "delegate" in content.lower()
        assert "routing" in content.lower() or "route" in content.lower()

        # Should mention Ollama
        assert "ollama" in content.lower()

        # Should have model: haiku (fast routing)
        assert "model: haiku" in content

    def test_code_reviewer_agent(self):
        """Test code-reviewer agent structure."""
        agent_file = Path.home() / ".claude" / "agents" / "code-reviewer" / "AGENT.md"
        content = agent_file.read_text(encoding="utf-8")

        # Should use Ollama models
        assert "qwen2.5-coder" in content.lower()

        # Should mention review types
        assert "quick" in content.lower() or "deep" in content.lower()

    def test_git_helper_agent(self):
        """Test git-helper agent structure."""
        agent_file = Path.home() / ".claude" / "agents" / "git-helper" / "AGENT.md"
        content = agent_file.read_text(encoding="utf-8")

        # Should have git operations
        assert "git diff" in content.lower()
        assert "git log" in content.lower()

        # Should output JSON
        assert "json" in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
