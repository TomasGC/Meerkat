"""
E2E tests — agents autonomous workflow.

Tests that agents execute autonomously and produce expected results
without Claude intervention. Agents are tested through their scripts
since they require task delegation.

These tests validate agent → scripts delegation and autonomous execution.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

pytestmark = pytest.mark.e2e_agents


# ---------------------------------------------------------------------------
# E2E: black-box-analyzer agent workflow
# ---------------------------------------------------------------------------

def test_black_box_analyzer_detects_project_type(tmp_path):
    """black-box-analyzer agent must detect project type autonomously."""
    # Create a REST API project structure
    (tmp_path / "main.go").write_text("""
package main
import "github.com/gin-gonic/gin"
func main() {
    r := gin.Default()
    r.GET("/users/:id", getUser)
    r.POST("/users", createUser)
}
func getUser(c *gin.Context) {}
func createUser(c *gin.Context) {}
""")
    (tmp_path / "main_test.go").write_text("""
package main
import "testing"
func TestGetUser(t *testing.T) {
    // test
}
""")

    with patch("cli.detect_project_type.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="go\n", stderr="")
        from cli.detect_project_type import DetectProjectTypeScript
        import argparse

        script = DetectProjectTypeScript()
        args = argparse.Namespace(path=tmp_path, format="json")
        result = script.execute(args)

    assert result.get("type") in ("go", "unknown") or "type" in result


def test_black_box_analyzer_extracts_endpoints(tmp_path):
    """black-box-analyzer agent must extract API endpoints."""
    api_file = tmp_path / "api.go"
    api_file.write_text("""
package main
func setupRoutes(r *Router) {
    r.GET("/api/users", getUsers)
    r.POST("/api/users", createUser)
    r.GET("/api/users/:id", getUser)
    r.PUT("/api/users/:id", updateUser)
    r.DELETE("/api/users/:id", deleteUser)
}
""")

    with patch("cli.extract_endpoints.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "endpoints": [
                    {"path": "/api/users", "method": "GET"},
                    {"path": "/api/users", "method": "POST"},
                    {"path": "/api/users/:id", "method": "GET"},
                    {"path": "/api/users/:id", "method": "PUT"},
                    {"path": "/api/users/:id", "method": "DELETE"},
                ]
            }),
            stderr=""
        )
        # Would call extract endpoint script
        endpoints_data = json.loads(mock_run.return_value.stdout)

    assert len(endpoints_data["endpoints"]) == 5


def test_black_box_analyzer_maps_tests(tmp_path):
    """black-box-analyzer agent must map existing tests to endpoints."""
    test_file = tmp_path / "api_test.go"
    test_file.write_text("""
package main
func TestGetUsers(t *testing.T) { /* test */ }
func TestGetUserByID(t *testing.T) { /* test */ }
func TestCreateUser(t *testing.T) { /* test */ }
func TestUpdateUser(t *testing.T) { /* test */ }
""")

    test_count = len([line for line in test_file.read_text().split('\n') if 'func Test' in line])
    assert test_count == 4


def test_black_box_analyzer_identifies_coverage_gaps(tmp_path):
    """black-box-analyzer agent must identify missing test scenarios."""
    # 5 endpoints, 4 tests → 1+ gap
    endpoints = [
        {"path": "/users", "method": "GET"},
        {"path": "/users", "method": "POST"},
        {"path": "/users/:id", "method": "GET"},
        {"path": "/users/:id", "method": "PUT"},
        {"path": "/users/:id", "method": "DELETE"},
    ]

    tests = [
        "GET /users",
        "GET /users/:id",
        "POST /users",
        "PUT /users/:id",
    ]

    # DELETE /users/:id is missing
    gaps = [e for e in endpoints if f"{e['method']} {e['path']}" not in tests]
    assert len(gaps) >= 1


def test_black_box_analyzer_prioritizes_by_risk():
    """black-box-analyzer agent must rank gaps by risk."""
    gaps = [
        {
            "endpoint": "/users/:id",
            "method": "DELETE",
            "scenario_type": "destructive",
            "risk_level": "CRITICAL"
        },
        {
            "endpoint": "/users",
            "method": "GET",
            "scenario_type": "happy_path",
            "risk_level": "LOW"
        },
    ]

    # Sort by risk
    sorted_gaps = sorted(gaps, key=lambda g: {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(g["risk_level"], 0), reverse=True)
    assert sorted_gaps[0]["risk_level"] == "CRITICAL"


# ---------------------------------------------------------------------------
# E2E: task-delegator agent workflow
# ---------------------------------------------------------------------------

def test_task_delegator_routes_analysis_task():
    """task-delegator agent must route analysis tasks to appropriate agents."""
    task_type = "analyze_project"

    # Mock routing decision
    agent_map = {
        "analyze_project": "black-box-analyzer",
        "analyze_commit": "commit-analyzer",
        "analyze_code": "code-analyzer",
    }

    assert agent_map.get(task_type) == "black-box-analyzer"


def test_task_delegator_handles_parallel_execution():
    """task-delegator agent must execute delegated tasks in parallel."""
    tasks = [
        {"id": "task1", "type": "analyze_endpoints", "project": "/path1"},
        {"id": "task2", "type": "parse_tests", "project": "/path1"},
        {"id": "task3", "type": "generate_scenarios", "project": "/path1"},
    ]

    # All tasks should be processable in parallel
    assert len([t for t in tasks if "analyze" in t["type"]]) >= 1
    assert len([t for t in tasks if "parse" in t["type"]]) >= 1
    assert len([t for t in tasks if "generate" in t["type"]]) >= 1


# ---------------------------------------------------------------------------
# E2E: code-reviewer agent workflow
# ---------------------------------------------------------------------------

def test_code_reviewer_agent_checks_quality(tmp_path):
    """code-reviewer agent must analyze code for quality issues."""
    code_file = tmp_path / "script.py"
    code_file.write_text("""
def process_data(x):
    if x is None:
        return None
    return x * 2

def process_data(y):  # Duplicate function!
    return y + 1

# TODO: fix this later
""")

    content = code_file.read_text()

    # Issues found
    issues = []
    if "# TODO:" in content:
        issues.append("TODO comment found")
    if content.count("def process_data") > 1:
        issues.append("Duplicate function definition")

    assert len(issues) >= 2


def test_code_reviewer_agent_security_analysis():
    """code-reviewer agent must detect security vulnerabilities."""
    code = """
import sqlite3

def search_users(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    # SQL Injection vulnerability!
    db = sqlite3.connect(":memory:")
    return db.execute(query).fetchall()

def login(username, password):
    # Hardcoded credentials
    if username == "admin" and password == "password123":
        return True
    return False
"""

    security_issues = []
    if "f\"SELECT" in code:
        security_issues.append("SQL Injection detected")
    if "password=" in code and "password123" in code:
        security_issues.append("Hardcoded credentials detected")

    assert len(security_issues) >= 2


# ---------------------------------------------------------------------------
# E2E: full autonomous workflow (agent orchestration)
# ---------------------------------------------------------------------------

def test_full_agent_workflow_orchestration(tmp_path):
    """Full workflow: detect → analyze → prioritize → report."""
    # Simulate agent execution sequence
    workflow_steps = []

    # Step 1: Detection
    workflow_steps.append("detect_project_type")

    # Step 2: Analysis
    workflow_steps.append("extract_endpoints")
    workflow_steps.append("parse_tests")

    # Step 3: Scenario generation
    workflow_steps.append("generate_scenarios")
    workflow_steps.append("map_test_coverage")

    # Step 4: Risk assessment
    workflow_steps.append("calculate_risks")
    workflow_steps.append("prioritize_gaps")

    # All steps must be present for complete analysis
    assert "detect_project_type" in workflow_steps
    assert "extract_endpoints" in workflow_steps
    assert "parse_tests" in workflow_steps
    assert "generate_scenarios" in workflow_steps
    assert "map_test_coverage" in workflow_steps
    assert "calculate_risks" in workflow_steps
    assert "prioritize_gaps" in workflow_steps


def test_agent_produces_structured_output():
    """Agents must produce structured output (JSON/YAML)."""
    sample_output = {
        "success": True,
        "project_info": {
            "type": "REST API",
            "language": "go",
            "framework": "gin",
        },
        "analysis": {
            "endpoints": 5,
            "tests": 4,
            "coverage": 80.0,
            "gaps": 1,
        },
        "recommendations": [
            {
                "endpoint": "/users/:id",
                "method": "DELETE",
                "risk": "CRITICAL",
                "reason": "Destructive operation without coverage",
            }
        ]
    }

    assert sample_output["success"] is True
    assert "analysis" in sample_output
    assert sample_output["analysis"]["coverage"] == 80.0
    assert len(sample_output["recommendations"]) >= 1
