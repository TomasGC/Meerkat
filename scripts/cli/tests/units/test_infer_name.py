"""Tests for infer_name.py — intelligent name inference for skills/scripts/agents."""

import json
from pathlib import Path

import pytest

from cli.infer_name import InferNameScript

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def script():
    return InferNameScript()

# ---------------------------------------------------------------------------
# Unit: verb detection
# ---------------------------------------------------------------------------

def test_detect_verbs_analyze(script):
    verbs = script._detect_verbs("Analyze git commits")
    assert "analyze" in verbs

def test_detect_verbs_generate(script):
    verbs = script._detect_verbs("Generate test scaffold")
    assert "generate" in verbs

def test_detect_verbs_validate(script):
    verbs = script._detect_verbs("Validate code quality")
    assert "validate" in verbs

def test_detect_verbs_check(script):
    verbs = script._detect_verbs("Check code coverage")
    assert "check" in verbs

def test_detect_verbs_multiple(script):
    verbs = script._detect_verbs("Analyze and validate code")
    assert len(verbs) >= 2

def test_detect_verbs_fallback_get(script):
    # "list" is in VERB_MAPPINGS and appears in the phrase — detected directly
    verbs = script._detect_verbs("Get the list of files")
    assert "list" in verbs

def test_detect_verbs_fallback_show(script):
    verbs = script._detect_verbs("Show all repositories")
    assert "list" in verbs

def test_detect_verbs_fallback_setup(script):
    verbs = script._detect_verbs("Setup the project environment")
    assert "configure" in verbs

def test_detect_verbs_unknown_falls_back_to_process(script):
    verbs = script._detect_verbs("Something completely unknown xyz")
    assert "process" in verbs

# ---------------------------------------------------------------------------
# Unit: noun detection
# ---------------------------------------------------------------------------

def test_detect_nouns_commit(script):
    nouns = script._detect_nouns("Analyze git commits")
    assert "commit" in nouns

def test_detect_nouns_code(script):
    nouns = script._detect_nouns("Format code files")
    assert "code" in nouns

def test_detect_nouns_test(script):
    nouns = script._detect_nouns("Generate test scaffold")
    assert "test" in nouns

def test_detect_nouns_project(script):
    nouns = script._detect_nouns("Initialize project structure")
    assert "project" in nouns

def test_detect_nouns_security(script):
    nouns = script._detect_nouns("Check security vulnerabilities")
    assert "security" in nouns

def test_detect_nouns_branch(script):
    nouns = script._detect_nouns("Get current branch info")
    assert "branch" in nouns

def test_detect_nouns_fallback_extracts_words(script):
    nouns = script._detect_nouns("Something completely unknown")
    assert isinstance(nouns, list)

def test_detect_nouns_max_three(script):
    nouns = script._detect_nouns("Analyze commits code tests security documentation")
    assert len(nouns) <= 3

# ---------------------------------------------------------------------------
# Unit: name inference
# ---------------------------------------------------------------------------

def test_infer_names_returns_list(script):
    suggestions = script._infer_names("Analyze git commits", "script", 3)
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0

def test_infer_names_count_respected(script):
    suggestions = script._infer_names("Analyze git commits", "script", 2)
    assert len(suggestions) <= 2

def test_infer_names_no_duplicates(script):
    suggestions = script._infer_names("Analyze git commits", "script", 10)
    names = [s.name for s in suggestions]
    assert len(names) == len(set(names))

def test_infer_names_sorted_by_confidence(script):
    suggestions = script._infer_names("Analyze git commits", "script", 5)
    confidences = [s.confidence for s in suggestions]
    assert confidences == sorted(confidences, reverse=True)

def test_infer_names_has_verb_noun_pattern(script):
    suggestions = script._infer_names("Analyze commits", "script", 5)
    patterns = [s.pattern for s in suggestions]
    assert "verb-noun" in patterns

def test_infer_names_has_noun_verb_pattern(script):
    suggestions = script._infer_names("Analyze commits", "script", 5)
    patterns = [s.pattern for s in suggestions]
    assert "noun-verb" in patterns

def test_infer_names_compound_when_multiple_nouns(script):
    suggestions = script._infer_names("Analyze commit security", "script", 10)
    patterns = [s.pattern for s in suggestions]
    assert "compound" in patterns

# ---------------------------------------------------------------------------
# Unit: suggestion to dict
# ---------------------------------------------------------------------------

def test_suggestion_to_dict_structure(script):
    suggestions = script._infer_names("Analyze commits", "script", 1)
    d = script._suggestion_to_dict(suggestions[0])
    assert "name" in d
    assert "reasoning" in d
    assert "pattern" in d
    assert "confidence" in d

# ---------------------------------------------------------------------------
# Unit: format methods
# ---------------------------------------------------------------------------

def test_format_text_output(script):
    result = {
        "purpose": "Analyze commits",
        "type": "script",
        "suggestions": [
            {"name": "analyze-commit", "pattern": "verb-noun", "reasoning": "test", "confidence": 1.0}
        ]
    }
    text = script.format_text(result)
    assert "analyze-commit" in text
    assert "Analyze commits" in text

def test_format_summary_output(script):
    result = {
        "purpose": "Analyze commits",
        "type": "script",
        "suggestions": [
            {"name": "analyze-commit", "pattern": "verb-noun", "reasoning": "test", "confidence": 1.0}
        ]
    }
    summary = script.format_summary(result)
    assert "analyze-commit" in summary

def test_format_summary_empty_suggestions(script):
    result = {"purpose": "test", "type": "script", "suggestions": []}
    summary = script.format_summary(result)
    assert "N/A" in summary

# ---------------------------------------------------------------------------
# Integration: CLI run
# ---------------------------------------------------------------------------

def test_run_json_output(capsys):
    script = InferNameScript()
    exit_code = script.run(["--purpose", "Analyze git commits", "--type", "script", "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0

def test_run_text_output(capsys):
    script = InferNameScript()
    exit_code = script.run(["--purpose", "Validate code quality", "--type", "skill", "--format", "text"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Suggestions for" in captured.out

def test_run_summary_output(capsys):
    script = InferNameScript()
    exit_code = script.run(["--purpose", "Generate test scaffold", "--format", "summary"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Suggested:" in captured.out

def test_run_agent_type(capsys):
    script = InferNameScript()
    exit_code = script.run(["--purpose", "Monitor background tasks", "--type", "agent", "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["type"] == "agent"

def test_run_count_parameter(capsys):
    script = InferNameScript()
    exit_code = script.run(["--purpose", "Analyze commit quality", "--count", "2", "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data["suggestions"]) <= 2

def test_run_missing_purpose_fails():
    script = InferNameScript()
    with pytest.raises(SystemExit):
        script.run([])
