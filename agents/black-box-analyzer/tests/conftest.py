#!/usr/bin/env python3
"""Pytest fixtures for black-box-analyzer tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import json
import tempfile

import pytest


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_go_project(temp_dir):
    project_dir = temp_dir / "go-project"
    project_dir.mkdir()

    (project_dir / "go.mod").write_text(
        "module example.com/api\n\ngo 1.21\n\nrequire github.com/gin-gonic/gin v1.9.1\n"
    )
    (project_dir / "main.go").write_text(
        'package main\n\nimport "github.com/gin-gonic/gin"\n\nfunc main() {\n'
        '    router := gin.Default()\n'
        '    router.GET("/users/:id", getUser)\n'
        '    router.POST("/users", createUser)\n'
        '    router.PUT("/users/:id", updateUser)\n'
        '    router.DELETE("/users/:id", deleteUser)\n'
        '    router.Run(":8080")\n}\n\n'
        'func getUser(c *gin.Context) {}\n'
        'func createUser(c *gin.Context) {}\n'
        'func updateUser(c *gin.Context) {}\n'
        'func deleteUser(c *gin.Context) {}\n'
    )
    (project_dir / "handler_test.go").write_text(
        'package main\n\nimport "testing"\n\n'
        'func TestGetUser(t *testing.T) {}\n'
        'func TestCreateUser(t *testing.T) {}\n'
        'func TestCreateUserInvalidInput(t *testing.T) {}\n'
    )
    return project_dir


@pytest.fixture
def sample_typescript_project(temp_dir):
    project_dir = temp_dir / "ts-project"
    project_dir.mkdir()

    (project_dir / "package.json").write_text(
        json.dumps({
            "name": "api", "version": "1.0.0",
            "dependencies": {"express": "^4.18.0"},
            "devDependencies": {"jest": "^29.0.0"},
        })
    )
    (project_dir / "tsconfig.json").write_text(json.dumps({"compilerOptions": {}}))

    src_dir = project_dir / "src"
    src_dir.mkdir()
    (src_dir / "routes.ts").write_text(
        "import express from 'express';\nconst app = express();\n"
        "app.get('/api/posts/:id', (req, res) => {});\n"
        "app.post('/api/posts', (req, res) => {});\n"
        "app.delete('/api/posts/:id', (req, res) => {});\n"
    )

    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "routes.test.ts").write_text(
        "import request from 'supertest';\n"
        "describe('POST /api/posts', () => {\n"
        "    it('should create a post with valid data', async () => {});\n"
        "    it('should return 400 when title is missing', async () => {});\n"
        "});\n"
        "describe('GET /api/posts/:id', () => {\n"
        "    it('should return post when exists', async () => {});\n"
        "    it('should return 404 when not found', async () => {});\n"
        "});\n"
    )
    return project_dir


@pytest.fixture
def sample_csharp_project(temp_dir):
    project_dir = temp_dir / "csharp-project"
    project_dir.mkdir()

    (project_dir / "Api.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk.Web">\n'
        '  <PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>\n'
        '  <ItemGroup><PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="8.0.0" /></ItemGroup>\n'
        '</Project>\n'
    )

    controllers_dir = project_dir / "Controllers"
    controllers_dir.mkdir()
    (controllers_dir / "UsersController.cs").write_text(
        "using Microsoft.AspNetCore.Mvc;\n\n"
        '[ApiController]\n[Route("api/[controller]")]\n'
        "public class UsersController : ControllerBase\n{\n"
        '    [HttpGet("{id}")] public IActionResult GetUser(int id) => Ok();\n'
        '    [HttpPost] public IActionResult CreateUser([FromBody] CreateUserRequest r) => Created();\n'
        '    [HttpPut("{id}")] public IActionResult UpdateUser(int id, [FromBody] UpdateUserRequest r) => NoContent();\n'
        '    [HttpDelete("{id}")] public IActionResult DeleteUser(int id) => NoContent();\n'
        "}\n"
    )

    tests_dir = project_dir / "Tests"
    tests_dir.mkdir()
    (tests_dir / "UsersControllerTests.cs").write_text(
        "using Xunit;\n\npublic class UsersControllerTests\n{\n"
        "    [Fact] public void GetUser_ReturnsUser_WhenExists() {}\n"
        "    [Fact] public void GetUser_Returns404_WhenNotFound() {}\n"
        "    [Fact] public void CreateUser_ReturnsCreated_WithValidData() {}\n"
        "    [Fact] public void CreateUser_ReturnsBadRequest_WithInvalidData() {}\n"
        "}\n"
    )
    return project_dir


@pytest.fixture
def sample_python_project(temp_dir):
    project_dir = temp_dir / "python-project"
    project_dir.mkdir()

    (project_dir / "requirements.txt").write_text("fastapi==0.109.0\nuvicorn==0.27.0\npytest==8.0.0\n")
    (project_dir / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n\n"
        "@app.get('/items/{item_id}')\nasync def get_item(item_id: int): return {'item_id': item_id}\n\n"
        "@app.post('/items')\nasync def create_item(item: dict): return {'id': 1}\n\n"
        "@app.put('/items/{item_id}')\nasync def update_item(item_id: int, item: dict): return {'updated': True}\n\n"
        "@app.delete('/items/{item_id}')\nasync def delete_item(item_id: int): return {'deleted': True}\n"
    )

    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text(
        "import pytest\n\n"
        "def test_get_item_success(): pass\n"
        "def test_get_item_not_found(): pass\n"
        "def test_create_item_success(): pass\n"
        "def test_create_item_invalid_data(): pass\n"
    )
    return project_dir


@pytest.fixture
def sample_endpoints_json(temp_dir):
    data = {
        "endpoint_count": 3,
        "endpoints": [
            {"path": "/users/:id", "method": "GET",
             "params": [{"name": "id", "param_type": "path", "data_type": "string",
                         "required": True, "default_value": None, "constraints": {}}],
             "response_codes": [200, 400, 401, 403, 404, 500],
             "file_path": "handlers/users.go", "line_number": 10,
             "framework": "gin", "handler_name": "getUser"},
            {"path": "/users", "method": "POST",
             "params": [
                 {"name": "email", "param_type": "body", "data_type": "string",
                  "required": True, "default_value": None, "constraints": {}},
                 {"name": "name", "param_type": "body", "data_type": "string",
                  "required": True, "default_value": None, "constraints": {}},
             ],
             "response_codes": [201, 400, 401, 403, 409, 422, 500],
             "file_path": "handlers/users.go", "line_number": 20,
             "framework": "gin", "handler_name": "createUser"},
            {"path": "/users/:id", "method": "DELETE",
             "params": [{"name": "id", "param_type": "path", "data_type": "string",
                         "required": True, "default_value": None, "constraints": {}}],
             "response_codes": [204, 400, 401, 403, 404, 500],
             "file_path": "handlers/users.go", "line_number": 30,
             "framework": "gin", "handler_name": "deleteUser"},
        ],
    }
    f = temp_dir / "endpoints.json"
    f.write_text(json.dumps(data, indent=2))
    return f


@pytest.fixture
def sample_tests_json(temp_dir):
    data = {
        "test_count": 4,
        "tests": [
            {"name": "TestGetUser", "file_path": "handlers/users_test.go", "line_number": 10,
             "framework": "testing", "tested_endpoint": "/users/:id", "tested_method": "GET",
             "tested_inputs": ["id"], "expected_outputs": ["200"], "test_type": "unit"},
            {"name": "TestCreateUser", "file_path": "handlers/users_test.go", "line_number": 20,
             "framework": "testing", "tested_endpoint": "/users", "tested_method": "POST",
             "tested_inputs": ["email", "name"], "expected_outputs": ["201"], "test_type": "unit"},
            {"name": "TestCreateUserInvalidEmail", "file_path": "handlers/users_test.go", "line_number": 30,
             "framework": "testing", "tested_endpoint": "/users", "tested_method": "POST",
             "tested_inputs": ["invalid_email"], "expected_outputs": ["400"], "test_type": "unit"},
            {"name": "TestDeleteUser", "file_path": "handlers/users_test.go", "line_number": 40,
             "framework": "testing", "tested_endpoint": "/users/:id", "tested_method": "DELETE",
             "tested_inputs": ["id"], "expected_outputs": ["204"], "test_type": "unit"},
        ],
    }
    f = temp_dir / "tests.json"
    f.write_text(json.dumps(data, indent=2))
    return f


@pytest.fixture
def sample_scenarios_json(temp_dir):
    data = {
        "scenario_count": 10,
        "scenarios": [
            {"endpoint": "/users/:id", "method": "GET", "input_combination": {"id": "test"},
             "expected_output": 200, "scenario_type": "happy_path",
             "description": "Valid request to GET /users/:id"},
            {"endpoint": "/users/:id", "method": "GET", "input_combination": {"id": None},
             "expected_output": 400, "scenario_type": "error", "description": "Edge case: id=None"},
            {"endpoint": "/users/:id", "method": "GET",
             "input_combination": {"id": "<script>alert('xss')</script>"},
             "expected_output": 400, "scenario_type": "security", "description": "Security test: xss_script"},
            {"endpoint": "/users", "method": "POST",
             "input_combination": {"email": "test@example.com", "name": "Test User"},
             "expected_output": 201, "scenario_type": "happy_path",
             "description": "Valid request to POST /users"},
            {"endpoint": "/users", "method": "POST", "input_combination": {"name": "Test User"},
             "expected_output": 400, "scenario_type": "error",
             "description": "Missing required parameter: email"},
        ],
        "breakdown": {"happy_path": 2, "edge_case": 1, "error": 2, "security": 1},
    }
    f = temp_dir / "scenarios.json"
    f.write_text(json.dumps(data, indent=2))
    return f


@pytest.fixture
def minimal_lcov_file(temp_dir):
    content = "SF:src/main.py\nDA:1,1\nDA:2,0\nDA:3,1\nend_of_record\n"
    p = temp_dir / "coverage_unit.lcov"
    p.write_text(content)
    return p


@pytest.fixture
def minimal_go_cover_file(temp_dir):
    content = (
        "mode: atomic\n"
        "example.com/api/handlers.go:10.25,12.2 1 3\n"
        "example.com/api/handlers.go:15.10,17.2 2 0\n"
    )
    p = temp_dir / "coverage_unit.out"
    p.write_text(content)
    return p


@pytest.fixture
def minimal_project_info_json(temp_dir):
    data = {
        "language": "python", "frameworks": ["fastapi"], "test_framework": "pytest",
        "root_path": str(temp_dir), "endpoint_count": 4, "test_file_count": 2,
    }
    p = temp_dir / "project_info.json"
    p.write_text(json.dumps(data, indent=2))
    return p


@pytest.fixture
def sample_kotlin_project(temp_dir):
    project_dir = temp_dir / "kotlin-project"
    project_dir.mkdir()
    (project_dir / "build.gradle.kts").write_text(
        'plugins { kotlin("jvm") version "1.9.0"\n'
        '  id("org.springframework.boot") version "3.2.0" }\n'
        'dependencies {\n'
        '  implementation("org.springframework.boot:spring-boot-starter-web")\n'
        '  testImplementation("org.springframework.boot:spring-boot-starter-test") }\n'
    )
    src = project_dir / "src" / "main" / "kotlin" / "com" / "example"
    src.mkdir(parents=True)
    (src / "UserController.kt").write_text(
        "package com.example\nimport org.springframework.web.bind.annotation.*\n"
        "@RestController\n@RequestMapping(\"/api/users\")\nclass UserController {\n"
        "    @GetMapping(\"/{id}\") fun getUser() = Unit\n"
        "    @PostMapping(\"/\") fun createUser() = Unit\n"
        "    @DeleteMapping(\"/{id}\") fun deleteUser() = Unit\n}\n"
    )
    test = project_dir / "src" / "test" / "kotlin" / "com" / "example"
    test.mkdir(parents=True)
    (test / "UserControllerTest.kt").write_text(
        "package com.example\nimport org.junit.jupiter.api.Test\n"
        "class UserControllerTest {\n    @Test fun test1() {}\n}\n"
    )
    return project_dir


@pytest.fixture
def sample_rust_project(temp_dir):
    project_dir = temp_dir / "rust-project"
    project_dir.mkdir()
    (project_dir / "Cargo.toml").write_text(
        "[package]\nname = \"my-api\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n"
        "[dependencies]\nactix-web = \"4\"\n"
    )
    src = project_dir / "src"
    src.mkdir()
    (src / "main.rs").write_text(
        'use actix_web::{get, post, delete, web, App, HttpServer, Responder};\n'
        '#[get("/users/{id}")] async fn get_user() -> impl Responder { "ok" }\n'
        '#[post("/users")] async fn create_user() -> impl Responder { "ok" }\n'
        '#[delete("/users/{id}")] async fn delete_user() -> impl Responder { "ok" }\n'
        '#[cfg(test)] mod tests {\n    #[test] fn test_get() {}\n    #[test] fn test_create() {}\n}\n'
    )
    return project_dir


@pytest.fixture
def sample_matrix_json(temp_dir, sample_scenarios_json, sample_tests_json):
    data = {
        "coverage_stats": {
            "total_scenarios": 5, "tested_scenarios": 3, "untested_scenarios": 2,
            "coverage_percent": 60.0,
            "by_endpoint": {
                "GET /users/:id": {"total": 3, "tested": 2, "untested": 1, "coverage_percent": 66.67},
                "POST /users": {"total": 2, "tested": 1, "untested": 1, "coverage_percent": 50.0},
            },
            "by_type": {
                "happy_path": {"total": 2, "tested": 2, "untested": 0, "coverage_percent": 100.0},
                "edge_case": {"total": 1, "tested": 0, "untested": 1, "coverage_percent": 0.0},
                "error": {"total": 2, "tested": 1, "untested": 1, "coverage_percent": 50.0},
            },
        },
        "gaps": [
            {"scenario": {"endpoint": "/users/:id", "method": "GET",
                          "input_combination": {"id": "test"}, "expected_output": 200,
                          "scenario_type": "happy_path", "description": "Valid request to GET /users/:id"},
             "is_tested": True,
             "related_tests": [{"name": "TestGetUser", "file_path": "handlers/users_test.go",
                                "line_number": 10, "framework": "testing",
                                "tested_endpoint": "/users/:id", "tested_method": "GET",
                                "tested_inputs": [], "expected_outputs": [], "test_type": "unit"}]},
            {"scenario": {"endpoint": "/users/:id", "method": "GET",
                          "input_combination": {"id": None}, "expected_output": 400,
                          "scenario_type": "error", "description": "Edge case: id=None"},
             "is_tested": False, "related_tests": []},
        ],
    }
    f = temp_dir / "matrix.json"
    f.write_text(json.dumps(data, indent=2))
    return f
