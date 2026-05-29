#!/usr/bin/env python3
"""Pytest fixtures for black-box-analyzer tests.

Provides:
- Sample project fixtures (Go, TypeScript, C#, Python)
- Temporary directories
- Mock data generators
"""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_go_project(temp_dir):
    """Create sample Go project with gin framework."""
    project_dir = temp_dir / "go-project"
    project_dir.mkdir()

    # go.mod
    (project_dir / "go.mod").write_text(
        """module example.com/api

go 1.21

require github.com/gin-gonic/gin v1.9.1
"""
    )

    # main.go with endpoints
    (project_dir / "main.go").write_text(
        """package main

import "github.com/gin-gonic/gin"

func main() {
    router := gin.Default()

    router.GET("/users/:id", getUser)
    router.POST("/users", createUser)
    router.PUT("/users/:id", updateUser)
    router.DELETE("/users/:id", deleteUser)

    router.Run(":8080")
}

func getUser(c *gin.Context) {}
func createUser(c *gin.Context) {}
func updateUser(c *gin.Context) {}
func deleteUser(c *gin.Context) {}
"""
    )

    # handler_test.go with tests
    (project_dir / "handler_test.go").write_text(
        """package main

import "testing"

func TestGetUser(t *testing.T) {
    // Test GET /users/:id
}

func TestCreateUser(t *testing.T) {
    // Test POST /users
}

func TestCreateUserInvalidInput(t *testing.T) {
    // Test POST /users with invalid data
}
"""
    )

    return project_dir


@pytest.fixture
def sample_typescript_project(temp_dir):
    """Create sample TypeScript project with Express."""
    project_dir = temp_dir / "ts-project"
    project_dir.mkdir()

    # package.json
    (project_dir / "package.json").write_text(
        json.dumps(
            {
                "name": "api",
                "version": "1.0.0",
                "dependencies": {"express": "^4.18.0"},
                "devDependencies": {"jest": "^29.0.0"},
            }
        )
    )

    # tsconfig.json
    (project_dir / "tsconfig.json").write_text(json.dumps({"compilerOptions": {}}))

    # src/routes.ts with endpoints
    src_dir = project_dir / "src"
    src_dir.mkdir()

    (src_dir / "routes.ts").write_text(
        """import express from 'express';

const app = express();

app.get('/api/posts/:id', (req, res) => {
    // Get post by ID
});

app.post('/api/posts', (req, res) => {
    // Create post
});

app.delete('/api/posts/:id', (req, res) => {
    // Delete post
});
"""
    )

    # tests/routes.test.ts
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()

    (tests_dir / "routes.test.ts").write_text(
        """import request from 'supertest';

describe('POST /api/posts', () => {
    it('should create a post with valid data', async () => {
        // Test happy path
    });

    it('should return 400 when title is missing', async () => {
        // Test missing required field
    });
});

describe('GET /api/posts/:id', () => {
    it('should return post when exists', async () => {
        // Test success
    });

    it('should return 404 when not found', async () => {
        // Test error
    });
});
"""
    )

    return project_dir


@pytest.fixture
def sample_csharp_project(temp_dir):
    """Create sample C# project with ASP.NET."""
    project_dir = temp_dir / "csharp-project"
    project_dir.mkdir()

    # Api.csproj
    (project_dir / "Api.csproj").write_text(
        """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="8.0.0" />
  </ItemGroup>
</Project>
"""
    )

    # Controllers/UsersController.cs
    controllers_dir = project_dir / "Controllers"
    controllers_dir.mkdir()

    (controllers_dir / "UsersController.cs").write_text(
        """using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    [HttpGet("{id}")]
    public IActionResult GetUser(int id)
    {
        return Ok();
    }

    [HttpPost]
    public IActionResult CreateUser([FromBody] CreateUserRequest request)
    {
        return Created();
    }

    [HttpPut("{id}")]
    public IActionResult UpdateUser(int id, [FromBody] UpdateUserRequest request)
    {
        return NoContent();
    }

    [HttpDelete("{id}")]
    public IActionResult DeleteUser(int id)
    {
        return NoContent();
    }
}
"""
    )

    # Tests/UsersControllerTests.cs
    tests_dir = project_dir / "Tests"
    tests_dir.mkdir()

    (tests_dir / "UsersControllerTests.cs").write_text(
        """using Xunit;

public class UsersControllerTests
{
    [Fact]
    public void GetUser_ReturnsUser_WhenExists()
    {
        // Test success
    }

    [Fact]
    public void GetUser_Returns404_WhenNotFound()
    {
        // Test error
    }

    [Fact]
    public void CreateUser_ReturnsCreated_WithValidData()
    {
        // Test happy path
    }

    [Fact]
    public void CreateUser_ReturnsBadRequest_WithInvalidData()
    {
        // Test validation
    }
}
"""
    )

    return project_dir


@pytest.fixture
def sample_python_project(temp_dir):
    """Create sample Python project with FastAPI."""
    project_dir = temp_dir / "python-project"
    project_dir.mkdir()

    # requirements.txt
    (project_dir / "requirements.txt").write_text(
        """fastapi==0.109.0
uvicorn==0.27.0
pytest==8.0.0
"""
    )

    # main.py with endpoints
    (project_dir / "main.py").write_text(
        """from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"item_id": item_id}

@app.post("/items")
async def create_item(item: dict):
    return {"id": 1}

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: dict):
    return {"updated": True}

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    return {"deleted": True}
"""
    )

    # tests/test_main.py
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_main.py").write_text(
        """import pytest

def test_get_item_success():
    # Test GET /items/{item_id} with valid ID
    pass

def test_get_item_not_found():
    # Test GET /items/{item_id} with non-existent ID
    pass

def test_create_item_success():
    # Test POST /items with valid data
    pass

def test_create_item_invalid_data():
    # Test POST /items with invalid data
    pass
"""
    )

    return project_dir


@pytest.fixture
def sample_endpoints_json(temp_dir):
    """Create sample endpoints.json file."""
    endpoints_data = {
        "endpoint_count": 3,
        "endpoints": [
            {
                "path": "/users/:id",
                "method": "GET",
                "params": [
                    {
                        "name": "id",
                        "param_type": "path",
                        "data_type": "string",
                        "required": True,
                        "default_value": None,
                        "constraints": {},
                    }
                ],
                "response_codes": [200, 400, 401, 403, 404, 500],
                "file_path": "handlers/users.go",
                "line_number": 10,
                "framework": "gin",
                "handler_name": "getUser",
            },
            {
                "path": "/users",
                "method": "POST",
                "params": [
                    {
                        "name": "email",
                        "param_type": "body",
                        "data_type": "string",
                        "required": True,
                        "default_value": None,
                        "constraints": {},
                    },
                    {
                        "name": "name",
                        "param_type": "body",
                        "data_type": "string",
                        "required": True,
                        "default_value": None,
                        "constraints": {},
                    },
                ],
                "response_codes": [201, 400, 401, 403, 409, 422, 500],
                "file_path": "handlers/users.go",
                "line_number": 20,
                "framework": "gin",
                "handler_name": "createUser",
            },
            {
                "path": "/users/:id",
                "method": "DELETE",
                "params": [
                    {
                        "name": "id",
                        "param_type": "path",
                        "data_type": "string",
                        "required": True,
                        "default_value": None,
                        "constraints": {},
                    }
                ],
                "response_codes": [204, 400, 401, 403, 404, 500],
                "file_path": "handlers/users.go",
                "line_number": 30,
                "framework": "gin",
                "handler_name": "deleteUser",
            },
        ],
    }

    endpoints_file = temp_dir / "endpoints.json"
    endpoints_file.write_text(json.dumps(endpoints_data, indent=2))
    return endpoints_file


@pytest.fixture
def sample_tests_json(temp_dir):
    """Create sample tests.json file."""
    tests_data = {
        "test_count": 4,
        "tests": [
            {
                "name": "TestGetUser",
                "file_path": "handlers/users_test.go",
                "line_number": 10,
                "framework": "testing",
                "tested_endpoint": "/users/:id",
                "tested_method": "GET",
                "tested_inputs": ["id"],
                "expected_outputs": ["200"],
                "test_type": "unit",
            },
            {
                "name": "TestCreateUser",
                "file_path": "handlers/users_test.go",
                "line_number": 20,
                "framework": "testing",
                "tested_endpoint": "/users",
                "tested_method": "POST",
                "tested_inputs": ["email", "name"],
                "expected_outputs": ["201"],
                "test_type": "unit",
            },
            {
                "name": "TestCreateUserInvalidEmail",
                "file_path": "handlers/users_test.go",
                "line_number": 30,
                "framework": "testing",
                "tested_endpoint": "/users",
                "tested_method": "POST",
                "tested_inputs": ["invalid_email"],
                "expected_outputs": ["400"],
                "test_type": "unit",
            },
            {
                "name": "TestDeleteUser",
                "file_path": "handlers/users_test.go",
                "line_number": 40,
                "framework": "testing",
                "tested_endpoint": "/users/:id",
                "tested_method": "DELETE",
                "tested_inputs": ["id"],
                "expected_outputs": ["204"],
                "test_type": "unit",
            },
        ],
    }

    tests_file = temp_dir / "tests.json"
    tests_file.write_text(json.dumps(tests_data, indent=2))
    return tests_file


@pytest.fixture
def sample_scenarios_json(temp_dir):
    """Create sample scenarios.json file."""
    scenarios_data = {
        "scenario_count": 10,
        "scenarios": [
            {
                "endpoint": "/users/:id",
                "method": "GET",
                "input_combination": {"id": "test"},
                "expected_output": 200,
                "scenario_type": "happy_path",
                "description": "Valid request to GET /users/:id",
            },
            {
                "endpoint": "/users/:id",
                "method": "GET",
                "input_combination": {"id": None},
                "expected_output": 400,
                "scenario_type": "error",
                "description": "Edge case: id=None",
            },
            {
                "endpoint": "/users/:id",
                "method": "GET",
                "input_combination": {"id": "<script>alert('xss')</script>"},
                "expected_output": 400,
                "scenario_type": "security",
                "description": "Security test: xss_script",
            },
            {
                "endpoint": "/users",
                "method": "POST",
                "input_combination": {"email": "test@example.com", "name": "Test User"},
                "expected_output": 201,
                "scenario_type": "happy_path",
                "description": "Valid request to POST /users",
            },
            {
                "endpoint": "/users",
                "method": "POST",
                "input_combination": {"name": "Test User"},
                "expected_output": 400,
                "scenario_type": "error",
                "description": "Missing required parameter: email",
            },
        ],
        "breakdown": {
            "happy_path": 2,
            "edge_case": 1,
            "error": 2,
            "security": 1,
        },
    }

    scenarios_file = temp_dir / "scenarios.json"
    scenarios_file.write_text(json.dumps(scenarios_data, indent=2))
    return scenarios_file


@pytest.fixture
def sample_matrix_json(temp_dir, sample_scenarios_json, sample_tests_json):
    """Create sample matrix.json file."""
    matrix_data = {
        "coverage_stats": {
            "total_scenarios": 5,
            "tested_scenarios": 3,
            "untested_scenarios": 2,
            "coverage_percent": 60.0,
            "by_endpoint": {
                "GET /users/:id": {
                    "total": 3,
                    "tested": 2,
                    "untested": 1,
                    "coverage_percent": 66.67,
                },
                "POST /users": {
                    "total": 2,
                    "tested": 1,
                    "untested": 1,
                    "coverage_percent": 50.0,
                },
            },
            "by_type": {
                "happy_path": {"total": 2, "tested": 2, "untested": 0, "coverage_percent": 100.0},
                "edge_case": {"total": 1, "tested": 0, "untested": 1, "coverage_percent": 0.0},
                "error": {"total": 2, "tested": 1, "untested": 1, "coverage_percent": 50.0},
            },
        },
        "gaps": [
            {
                "scenario": {
                    "endpoint": "/users/:id",
                    "method": "GET",
                    "input_combination": {"id": "test"},
                    "expected_output": 200,
                    "scenario_type": "happy_path",
                    "description": "Valid request to GET /users/:id",
                },
                "is_tested": True,
                "related_tests": [
                    {
                        "name": "TestGetUser",
                        "file_path": "handlers/users_test.go",
                        "line_number": 10,
                        "framework": "testing",
                        "tested_endpoint": "/users/:id",
                        "tested_method": "GET",
                        "tested_inputs": [],
                        "expected_outputs": [],
                        "test_type": "unit",
                    }
                ],
            },
            {
                "scenario": {
                    "endpoint": "/users/:id",
                    "method": "GET",
                    "input_combination": {"id": None},
                    "expected_output": 400,
                    "scenario_type": "error",
                    "description": "Edge case: id=None",
                },
                "is_tested": False,
                "related_tests": [],
            },
        ],
    }

    matrix_file = temp_dir / "matrix.json"
    matrix_file.write_text(json.dumps(matrix_data, indent=2))
    return matrix_file
