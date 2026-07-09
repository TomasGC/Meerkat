#!/usr/bin/env python3
"""Tests for validate_skill_structure.py"""

from pathlib import Path
from textwrap import dedent

import pytest

from cli.validate_skill_structure import (
    StructureValidationResult,
    detect_type,
    validate_structure)
from common.utils import write_file_safe

def test_detect_type_skill():
    """Test type detection for skill file."""
    file_path = Path("SKILL.md")
    component_type = detect_type(file_path)
    assert component_type == "skill"

def test_detect_type_agent():
    """Test type detection for agent file."""
    file_path = Path("~/.claude/agents/my-agent.md")
    component_type = detect_type(file_path)
    assert component_type == "agent"

def test_detect_type_default():
    """Test type detection defaults to skill."""
    file_path = Path("unknown.md")
    component_type = detect_type(file_path)
    assert component_type == "skill"

def test_validate_skill_valid(tmp_path):
    """Test validation with valid skill structure."""
    skill = tmp_path / "SKILL.md"
    content = dedent("""
        ---
        name: analyze-code
        description: Use this skill when you need to analyze code quality
        ---

        # Analyze Code Skill

        ## What This Skill Does
        Analyzes code for quality issues.

        ## Persona Definition
        You are a principal software developer.

        ## Tools
        - Read
        - Grep

        ## Model
        sonnet

        ## Hard Constraints
        - Always validate syntax
        - Never modify code

        ## Operational Guidelines
        Follow these steps.

        ## Self-Verification Checklist
        - [ ] Code analyzed
        - [ ] Issues reported

        ## Communication Style
        Be concise.
    """)
    write_file_safe(skill, content)

    result = validate_structure(skill, component_type="skill")

    assert result.valid is True
    assert result.type == "skill"
    assert result.error_count == 0

def test_validate_skill_missing_frontmatter(tmp_path):
    """Test validation with missing YAML frontmatter."""
    skill = tmp_path / "SKILL.md"
    content = "# No frontmatter here"
    write_file_safe(skill, content)

    result = validate_structure(skill, component_type="skill")

    assert result.valid is False
    assert any("frontmatter" in e.lower() for e in result.errors)

def test_validate_skill_missing_name(tmp_path):
    """Test validation with missing name field."""
    skill = tmp_path / "SKILL.md"
    content = dedent("""
        ---
        description: A skill without name
        ---

        # Skill
    """)
    write_file_safe(skill, content)

    result = validate_structure(skill, component_type="skill")

    assert result.valid is False
    assert any("name" in e.lower() for e in result.errors)

def test_validate_skill_invalid_name_format(tmp_path):
    """Test validation with invalid name format."""
    skill = tmp_path / "SKILL.md"
    content = dedent("""
        ---
        name: InvalidName_WithUnderscore
        description: Invalid name format
        ---

        # Skill
    """)
    write_file_safe(skill, content)

    result = validate_structure(skill, component_type="skill")

    assert result.valid is False
    assert any("lowercase-with-dashes" in e for e in result.errors)

def test_validate_skill_missing_sections(tmp_path):
    """Test validation with missing required sections."""
    skill = tmp_path / "SKILL.md"
    content = dedent("""
        ---
        name: incomplete-skill
        description: Missing required sections
        ---

        # Incomplete Skill

        ## Persona Definition
        A developer.
    """)
    write_file_safe(skill, content)

    result = validate_structure(skill, component_type="skill")

    assert result.valid is False
    assert any("missing required sections" in e.lower() for e in result.errors)

def test_validate_skill_placeholders(tmp_path):
    """Test validation detects placeholders."""
    skill = tmp_path / "SKILL.md"
    content = dedent("""
        ---
        name: placeholder-skill
        description: Has placeholders
        ---

        # Skill

        [TODO] Add content here
    """)
    write_file_safe(skill, content)

    result = validate_structure(skill, component_type="skill")

    assert result.valid is False
    assert any("todo" in e.lower() or "placeholder" in e.lower() for e in result.errors)

def test_validate_skill_non_english(tmp_path):
    """Test validation detects non-English content."""
    skill = tmp_path / "SKILL.md"
    content = dedent("""
        ---
        name: french-skill
        description: Has French accents
        ---

        # Skill

        Ceci est du français avec des accents: é, è, à
    """)
    write_file_safe(skill, content)

    result = validate_structure(skill, component_type="skill")

    assert result.valid is False
    assert any("non-english" in e.lower() or "french" in e.lower() for e in result.errors)

def test_validate_skill_generic_persona(tmp_path):
    """Test validation warns about generic persona."""
    skill = tmp_path / "SKILL.md"
    content = dedent("""
        ---
        name: generic-skill
        description: Generic persona
        ---

        ## Persona Definition
        You are a developer.

        ## Tools
        Read

        ## Model
        sonnet

        ## Hard Constraints
        None

        ## Operational Guidelines
        Follow steps

        ## Self-Verification Checklist
        - [ ] Done

        ## Communication Style
        Be clear
    """)
    write_file_safe(skill, content)

    result = validate_structure(skill, component_type="skill")

    assert any("generic" in w.lower() for w in result.warnings)

def test_validate_skill_strict_mode(tmp_path):
    """Test strict mode treats warnings as errors."""
    skill = tmp_path / "SKILL.md"
    content = dedent("""
        ---
        name: warning-skill
        description: Has warnings
        ---

        ## Persona Definition
        A developer.

        ## Tools
        Read

        ## Model
        sonnet

        ## Hard Constraints
        None

        ## Operational Guidelines
        Follow steps

        ## Self-Verification Checklist
        - [ ] Done

        ## Communication Style
        Be clear
    """)
    write_file_safe(skill, content)

    # Non-strict: valid (warnings OK)
    result_non_strict = validate_structure(skill, component_type="skill", strict=False)
    assert result_non_strict.valid is True

    # Strict: invalid (warnings = errors)
    result_strict = validate_structure(skill, component_type="skill", strict=True)
    assert result_strict.valid is False

def test_validate_agent_valid(tmp_path):
    """Test validation with valid agent structure."""
    agent = tmp_path / "agent.md"
    content = dedent("""
        ---
        name: code-reviewer
        description: Reviews code changes
        tools: Read, Grep
        model: sonnet
        ---

        # Code Reviewer Agent

        ## Core Responsibilities
        - Review code
        - Check quality

        ## Hard Constraints
        - Never modify code
        - Always check tests
    """)
    write_file_safe(agent, content)

    result = validate_structure(agent, component_type="agent")

    assert result.valid is True
    assert result.type == "agent"

def test_validate_nonexistent_file():
    """Test validation with nonexistent file."""
    with pytest.raises(FileNotFoundError):
        validate_structure(Path("/nonexistent/skill.md"))
