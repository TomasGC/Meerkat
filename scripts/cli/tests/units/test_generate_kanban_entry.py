#!/usr/bin/env python3
"""Tests for generate_kanban_entry.py"""

from pathlib import Path

import pytest

from cli.generate_kanban_entry import generate_descriptions

def test_generate_descriptions_testing_professional():
    """Test generating testing description in professional style."""
    categories = {"testing": 10}
    descriptions = generate_descriptions(categories, "professional")

    assert len(descriptions) == 1
    assert "test suite" in descriptions[0].lower()
    assert "10 test files" in descriptions[0]
    assert "100% passing" in descriptions[0]

def test_generate_descriptions_testing_detailed():
    """Test generating testing description in detailed style."""
    categories = {"testing": 10}
    descriptions = generate_descriptions(categories, "detailed")

    assert len(descriptions) == 1
    assert "10 comprehensive tests" in descriptions[0]
    assert "fixtures" in descriptions[0]

def test_generate_descriptions_testing_concise():
    """Test generating testing description in concise style."""
    categories = {"testing": 10}
    descriptions = generate_descriptions(categories, "concise")

    assert len(descriptions) == 1
    assert "Test suite (10 tests)" in descriptions[0]

def test_generate_descriptions_scripts_professional():
    """Test generating scripts description in professional style."""
    categories = {"scripts": 5}
    descriptions = generate_descriptions(categories, "professional")

    assert len(descriptions) == 1
    assert "5 cross-platform" in descriptions[0]
    assert "automation" in descriptions[0]

def test_generate_descriptions_scripts_detailed():
    """Test generating scripts description in detailed style."""
    categories = {"scripts": 5}
    descriptions = generate_descriptions(categories, "detailed")

    assert len(descriptions) == 1
    assert "5 cross-platform" in descriptions[0]
    assert "workflow optimization" in descriptions[0]

def test_generate_descriptions_scripts_concise():
    """Test generating scripts description in concise style."""
    categories = {"scripts": 5}
    descriptions = generate_descriptions(categories, "concise")

    assert len(descriptions) == 1
    assert "5 utility scripts" in descriptions[0]

def test_generate_descriptions_standards_professional():
    """Test generating standards description in professional style."""
    categories = {"standards": 3}
    descriptions = generate_descriptions(categories, "professional")

    assert len(descriptions) == 1
    assert "coding standards" in descriptions[0].lower()
    assert "15+" in descriptions[0]

def test_generate_descriptions_standards_concise():
    """Test generating standards description in concise style."""
    categories = {"standards": 3}
    descriptions = generate_descriptions(categories, "concise")

    assert len(descriptions) == 1
    assert "Coding standards defined" in descriptions[0]

def test_generate_descriptions_documentation_professional():
    """Test generating documentation description in professional style."""
    categories = {"documentation": 6}
    descriptions = generate_descriptions(categories, "professional")

    assert len(descriptions) == 1
    assert "documentation" in descriptions[0].lower()
    assert "6 files" in descriptions[0]

def test_generate_descriptions_infrastructure_professional():
    """Test generating infrastructure description."""
    categories = {"infrastructure": 2, "skills": 3}
    descriptions = generate_descriptions(categories, "professional")

    # Should have infrastructure as first description
    assert any("infrastructure" in d.lower() for d in descriptions)

def test_generate_descriptions_configuration():
    """Test generating configuration description."""
    categories = {"configuration": 4}
    descriptions = generate_descriptions(categories, "professional")

    assert len(descriptions) == 1
    assert "environment" in descriptions[0].lower()
    assert "Git" in descriptions[0]

def test_generate_descriptions_code_fallback():
    """Test code fallback when no specific patterns."""
    categories = {"code": 15}
    descriptions = generate_descriptions(categories, "professional")

    assert len(descriptions) == 1
    assert "core functionality" in descriptions[0].lower()
    assert "15 files" in descriptions[0]

def test_generate_descriptions_multiple_categories():
    """Test generating descriptions with multiple categories."""
    categories = {
        "testing": 10,
        "scripts": 5,
        "standards": 3,
        "documentation": 6
    }
    descriptions = generate_descriptions(categories, "professional")

    # Should have multiple descriptions
    assert len(descriptions) >= 3
    assert any("test" in d.lower() for d in descriptions)
    assert any("script" in d.lower() for d in descriptions)

def test_generate_descriptions_empty():
    """Test generating descriptions with no categories."""
    categories = {}
    descriptions = generate_descriptions(categories, "professional")

    assert descriptions == []

def test_generate_descriptions_order():
    """Test that infrastructure comes first."""
    categories = {
        "code": 10,
        "infrastructure": 2,
        "testing": 5
    }
    descriptions = generate_descriptions(categories, "professional")

    # Infrastructure should be first
    assert "infrastructure" in descriptions[0].lower()

def test_generate_descriptions_all_styles():
    """Test all styles produce different output."""
    categories = {"testing": 10, "scripts": 5}

    prof = generate_descriptions(categories, "professional")
    detailed = generate_descriptions(categories, "detailed")
    concise = generate_descriptions(categories, "concise")

    # Professional and detailed should have more words than concise
    assert len(" ".join(prof)) > len(" ".join(concise))
    assert len(" ".join(detailed)) > len(" ".join(concise))

def test_generate_descriptions_skills_agents():
    """Test that skills and agents contribute to infrastructure count."""
    categories = {
        "skills": 3,
        "agents": 2,
        "infrastructure": 1
    }
    descriptions = generate_descriptions(categories, "professional")

    # Should have infrastructure description
    assert any("infrastructure" in d.lower() for d in descriptions)
