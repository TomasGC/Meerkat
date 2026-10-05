#!/usr/bin/env python3
"""Tests for aggregate_results module."""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import aggregate_results as aggregate_module
import pytest
from aggregate_results import aggregate_results, calculate_rank_score, format_markdown
from search_tech.models import ResultType, SearchResult, Source


class TestRankScoreCalculation:
    """Test rank score calculation algorithm."""

    def test_base_score(self):
        """Test base score without bonuses."""
        result = SearchResult(
            source=Source.STACKOVERFLOW,
            result_type=ResultType.QUESTION,
            title="Test",
            url="https://test.com",
            score=100,
            excerpt="Test excerpt",
        )

        rank_score = calculate_rank_score(result)
        assert rank_score == 100.0

    def test_accepted_answer_bonus(self):
        """Test accepted answer adds +50 bonus."""
        result = SearchResult(
            source=Source.STACKOVERFLOW,
            result_type=ResultType.QUESTION,
            title="Test",
            url="https://test.com",
            score=100,
            excerpt="Test excerpt",
            accepted=True,
        )

        rank_score = calculate_rank_score(result)
        assert rank_score == 150.0  # 100 + 50

    def test_recency_bonus(self):
        """Test recency bonus for recent results."""
        recent_date = datetime.now()
        result = SearchResult(
            source=Source.STACKOVERFLOW,
            result_type=ResultType.QUESTION,
            title="Test",
            url="https://test.com",
            score=100,
            excerpt="Test excerpt",
            created_date=recent_date,
        )

        rank_score = calculate_rank_score(result)
        # Should have recency bonus (up to +18 for last 6 months)
        assert rank_score > 100.0
        assert rank_score <= 118.0  # 100 + 18 max

    def test_old_date_no_recency_bonus(self):
        """Test no recency bonus for old results."""
        from datetime import timedelta

        old_date = datetime.now() - timedelta(days=365)
        result = SearchResult(
            source=Source.STACKOVERFLOW,
            result_type=ResultType.QUESTION,
            title="Test",
            url="https://test.com",
            score=100,
            excerpt="Test excerpt",
            created_date=old_date,
        )

        rank_score = calculate_rank_score(result)
        assert rank_score == 100.0  # No recency bonus

    def test_engagement_bonus(self):
        """Test engagement bonus (comments + answers × 2)."""
        result = SearchResult(
            source=Source.STACKOVERFLOW,
            result_type=ResultType.QUESTION,
            title="Test",
            url="https://test.com",
            score=100,
            excerpt="Test excerpt",
            comments=5,
            answer_count=3,
        )

        rank_score = calculate_rank_score(result)
        # Engagement: (5 + 3) × 2 = 16
        assert rank_score == 116.0  # 100 + 16

    def test_all_bonuses_combined(self):
        """Test all bonuses combined."""
        recent_date = datetime.now()
        result = SearchResult(
            source=Source.STACKOVERFLOW,
            result_type=ResultType.QUESTION,
            title="Test",
            url="https://test.com",
            score=100,
            excerpt="Test excerpt",
            accepted=True,
            created_date=recent_date,
            comments=5,
            answer_count=3,
        )

        rank_score = calculate_rank_score(result)
        # Base: 100
        # Accepted: +50
        # Engagement: +16
        # Recency: ~+18 (max)
        assert rank_score >= 166.0  # 100 + 50 + 16
        assert rank_score <= 184.0  # 100 + 50 + 16 + 18


class TestAggregateResults:
    """Test result aggregation."""

    def test_aggregate_single_file(self):
        """Test aggregation from single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.json"
            data = {
                "success": True,
                "results": [
                    {
                        "source": "stackoverflow",
                        "type": "question",
                        "title": "Test 1",
                        "url": "https://test.com/1",
                        "score": 100,
                        "excerpt": "Test",
                    },
                    {
                        "source": "stackoverflow",
                        "type": "question",
                        "title": "Test 2",
                        "url": "https://test.com/2",
                        "score": 50,
                        "excerpt": "Test",
                    },
                ],
            }
            with open(test_file, "w") as f:
                json.dump(data, f)

            # Aggregate
            results = aggregate_results([str(test_file)])

            assert len(results) == 2
            # Should be sorted by score (descending)
            assert results[0].score == 100
            assert results[1].score == 50

    def test_aggregate_multiple_files(self):
        """Test aggregation from multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = Path(tmpdir) / "file1.json"
            file2 = Path(tmpdir) / "file2.json"

            data1 = {
                "success": True,
                "results": [
                    {
                        "source": "stackoverflow",
                        "type": "question",
                        "title": "Test 1",
                        "url": "https://test.com/1",
                        "score": 100,
                        "excerpt": "Test",
                    }
                ],
            }
            data2 = {
                "success": True,
                "results": [
                    {
                        "source": "github_issue",
                        "type": "issue",
                        "title": "Test 2",
                        "url": "https://github.com/test",
                        "score": 50,
                        "excerpt": "Test",
                    }
                ],
            }

            with open(file1, "w") as f:
                json.dump(data1, f)
            with open(file2, "w") as f:
                json.dump(data2, f)

            # Aggregate
            results = aggregate_results([str(file1), str(file2)])

            assert len(results) == 2
            assert results[0].source == Source.STACKOVERFLOW
            assert results[1].source == Source.GITHUB_ISSUE

    def test_max_results_limit(self):
        """Test max_results parameter limits output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"
            data = {
                "success": True,
                "results": [
                    {
                        "source": "stackoverflow",
                        "type": "question",
                        "title": f"Test {i}",
                        "url": f"https://test.com/{i}",
                        "score": 100 - i,
                        "excerpt": "Test",
                    }
                    for i in range(20)
                ],
            }
            with open(test_file, "w") as f:
                json.dump(data, f)

            # Aggregate with max_results=5
            results = aggregate_results([str(test_file)], max_results=5)

            assert len(results) == 5
            # Should be top 5 by score
            assert results[0].score == 100
            assert results[4].score == 96

    def test_ranking_by_score(self):
        """Test results are ranked by calculated score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"
            data = {
                "success": True,
                "results": [
                    {
                        "source": "stackoverflow",
                        "type": "question",
                        "title": "Low score",
                        "url": "https://test.com/1",
                        "score": 10,
                        "excerpt": "Test",
                    },
                    {
                        "source": "stackoverflow",
                        "type": "question",
                        "title": "High score accepted",
                        "url": "https://test.com/2",
                        "score": 50,
                        "accepted": True,  # +50 bonus
                        "excerpt": "Test",
                    },
                    {
                        "source": "stackoverflow",
                        "type": "question",
                        "title": "Medium score",
                        "url": "https://test.com/3",
                        "score": 30,
                        "excerpt": "Test",
                    },
                ],
            }
            with open(test_file, "w") as f:
                json.dump(data, f)

            results = aggregate_results([str(test_file)])

            # Order should be: High score accepted (100), Medium (30), Low (10)
            assert results[0].title == "High score accepted"
            assert results[1].title == "Medium score"
            assert results[2].title == "Low score"

    def test_skip_failed_files(self):
        """Test aggregation skips failed sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            success_file = Path(tmpdir) / "success.json"
            failed_file = Path(tmpdir) / "failed.json"

            data_success = {
                "success": True,
                "results": [
                    {
                        "source": "stackoverflow",
                        "type": "question",
                        "title": "Test",
                        "url": "https://test.com",
                        "score": 100,
                        "excerpt": "Test",
                    }
                ],
            }
            data_failed = {"success": False, "error": "Rate limit exceeded"}

            with open(success_file, "w") as f:
                json.dump(data_success, f)
            with open(failed_file, "w") as f:
                json.dump(data_failed, f)

            # Should only get results from success file
            results = aggregate_results([str(success_file), str(failed_file)])

            assert len(results) == 1
            assert results[0].title == "Test"

    def test_handle_missing_files(self):
        """Test aggregation handles missing files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_file = Path(tmpdir) / "exists.json"
            missing_file = Path(tmpdir) / "missing.json"

            data = {
                "success": True,
                "results": [
                    {
                        "source": "stackoverflow",
                        "type": "question",
                        "title": "Test",
                        "url": "https://test.com",
                        "score": 100,
                        "excerpt": "Test",
                    }
                ],
            }
            with open(existing_file, "w") as f:
                json.dump(data, f)

            # Should only get results from existing file
            results = aggregate_results([str(existing_file), str(missing_file)])

            assert len(results) == 1

    def test_handle_invalid_json(self):
        """Test aggregation handles invalid JSON gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_file = Path(tmpdir) / "invalid.json"

            # Write invalid JSON
            with open(invalid_file, "w") as f:
                f.write("{ invalid json }")

            # Should return empty list
            results = aggregate_results([str(invalid_file)])

            assert len(results) == 0

    def test_empty_results(self):
        """Test aggregation with no results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "empty.json"
            data = {"success": True, "results": []}
            with open(test_file, "w") as f:
                json.dump(data, f)

            results = aggregate_results([str(test_file)])

            assert len(results) == 0


class TestMarkdownFormatting:
    """Test markdown output formatting."""

    def test_format_single_result(self):
        """Test markdown formatting with single result."""
        result = SearchResult(
            source=Source.STACKOVERFLOW,
            result_type=ResultType.QUESTION,
            title="How to handle async errors?",
            url="https://stackoverflow.com/q/12345",
            score=245,
            excerpt="This is a test excerpt",
            tags=["typescript", "async"],
        )

        markdown = format_markdown([result], "async error handling")

        assert "## 🔍 Technical Search Results" in markdown
        assert "How to handle async errors?" in markdown
        assert "245 👍" in markdown
        assert "stackoverflow.com/q/12345" in markdown
        assert "typescript, async" in markdown

    def test_format_no_results(self):
        """Test markdown formatting with no results."""
        markdown = format_markdown([], "nonexistent query")

        assert "No results found" in markdown
        assert "Try:" in markdown

    def test_format_accepted_answer_badge(self):
        """Test accepted answer badge in markdown."""
        result = SearchResult(
            source=Source.STACKOVERFLOW,
            result_type=ResultType.QUESTION,
            title="Test",
            url="https://test.com",
            score=100,
            excerpt="Test",
            accepted=True,
        )

        markdown = format_markdown([result], "test")

        assert "✅ Accepted" in markdown

    def test_format_source_icons(self):
        """Test correct icons for different sources."""
        results = [
            SearchResult(
                source=Source.STACKOVERFLOW,
                result_type=ResultType.QUESTION,
                title="SO",
                url="https://so.com",
                score=1,
                excerpt="Test",
            ),
            SearchResult(
                source=Source.REDDIT,
                result_type=ResultType.DISCUSSION,
                title="Reddit",
                url="https://reddit.com",
                score=1,
                excerpt="Test",
            ),
            SearchResult(
                source=Source.DEVTO,
                result_type=ResultType.QUESTION,
                title="DevTo",
                url="https://dev.to",
                score=1,
                excerpt="Test",
            ),
        ]

        markdown = format_markdown(results, "test")

        assert "⭐" in markdown  # StackOverflow
        assert "🔴" in markdown  # Reddit
        assert "📰" in markdown  # Dev.to


# ── main() and remaining branches ────────────────────────────────────────────


def _result(**kwargs):
    fields = dict(
        source=Source.GITHUB_ISSUE, result_type=ResultType.ISSUE, title="T", url="https://x/1", score=3, excerpt="e"
    )
    fields.update(kwargs)
    return SearchResult(**fields)


def _write(path, results, success=True):
    path.write_text(json.dumps({"success": success, "results": [r.to_dict() for r in results]}), encoding="utf-8")
    return str(path)


def _main(argv):
    with patch.object(sys, "argv", ["aggregate_results.py", *argv]):
        aggregate_module.main()


def test_unreadable_result_record_counts_as_failed_file(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"success": True, "results": [{"title": "missing fields"}]}), encoding="utf-8")
    assert aggregate_results([str(bad)]) == []


def test_format_markdown_closed_issue_with_repository():
    markdown = format_markdown([_result(status="closed", repository="o/r", tags=list("abcdef"))], "q")
    assert "| Github Issue | Closed" in markdown
    assert "Repository: o/r" in markdown
    assert "Tags: a, b, c, d, e" in markdown


def test_main_writes_json_and_markdown(tmp_path):
    so = _write(tmp_path / "so.json", [_result(source=Source.STACKOVERFLOW, result_type=ResultType.QUESTION)])
    gh = _write(tmp_path / "gh.json", [_result(score=9), _result(score=1)])
    out, md = tmp_path / "out" / "agg.json", tmp_path / "out" / "agg.md"

    _main([so, gh, "--output", str(out), "--markdown", str(md), "--query", "leak", "--max-results", "2", "--verbose"])

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["success"] is True
    assert data["total_results"] == 2
    assert [r["score"] for r in data["results"]] == [9, 3]
    assert data["sources"] == {"github_issue": 1, "stackoverflow": 1}
    assert md.read_text(encoding="utf-8").startswith('## 🔍 Technical Search Results for "leak"')


def test_main_without_results_writes_failure_and_exits(tmp_path):
    failed = _write(tmp_path / "f.json", [], success=False)
    out = tmp_path / "agg.json"

    with pytest.raises(SystemExit) as exc:
        _main([failed, str(tmp_path / "missing.json"), "--output", str(out)])

    assert exc.value.code == 1
    assert json.loads(out.read_text(encoding="utf-8")) == {
        "success": False,
        "error": "No results found in any input file",
        "total_results": 0,
        "results": [],
        "sources": {},
    }


def test_main_exits_when_json_output_cannot_be_written(tmp_path):
    source = _write(tmp_path / "gh.json", [_result()])
    with pytest.raises(SystemExit) as exc:
        _main([source, "--output", str(tmp_path)])  # a directory, not a file
    assert exc.value.code == 1


def test_main_exits_when_markdown_cannot_be_written(tmp_path):
    source = _write(tmp_path / "gh.json", [_result()])
    with pytest.raises(SystemExit) as exc:
        _main([source, "--output", str(tmp_path / "a.json"), "--markdown", str(tmp_path)])
    assert exc.value.code == 1
    assert json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))["success"] is True
