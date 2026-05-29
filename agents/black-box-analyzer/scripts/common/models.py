#!/usr/bin/env python3
"""Shared data models for black-box-analyzer scripts.

Python 3.12+ features:
- Type aliases (PEP 695)
- Dataclasses with field defaults
- Enum for type safety
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# Python 3.12+ type aliases
type EndpointList = list["Endpoint"]
type TestCaseList = list["TestCase"]
type ScenarioList = list["Scenario"]
type RiskScore = int  # 1-125


class Language(Enum):
    """Supported programming languages."""

    GO = "go"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    CSHARP = "csharp"
    PYTHON = "python"
    JAVA = "java"
    RUBY = "ruby"
    PHP = "php"
    UNKNOWN = "unknown"


class HTTPMethod(Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"
    TRACE = "TRACE"
    CONNECT = "CONNECT"


class TestFramework(Enum):
    """Supported test frameworks."""

    # Go
    GO_TESTING = "testing"

    # JavaScript/TypeScript
    JEST = "jest"
    VITEST = "vitest"
    MOCHA = "mocha"
    JASMINE = "jasmine"

    # Python
    PYTEST = "pytest"
    UNITTEST = "unittest"

    # C#
    XUNIT = "xunit"
    NUNIT = "nunit"
    MSTEST = "mstest"

    # Java
    JUNIT = "junit"
    TESTNG = "testng"

    # Ruby
    RSPEC = "rspec"
    MINITEST = "minitest"

    UNKNOWN = "unknown"


class ProjectType(Enum):
    """Universal project types (supports multiple types per project)."""

    # API Types
    REST_API = "rest_api"
    GRAPHQL_API = "graphql_api"
    GRPC_API = "grpc_api"

    # Application Types
    CLI_APP = "cli_app"
    ANDROID_APP = "android_app"
    IOS_APP = "ios_app"
    DESKTOP_WINDOWS = "desktop_windows"
    DESKTOP_MAC = "desktop_mac"
    DESKTOP_LINUX = "desktop_linux"

    # Web Types
    FRONTEND_REACT = "frontend_react"
    FRONTEND_VUE = "frontend_vue"
    FRONTEND_ANGULAR = "frontend_angular"
    FULLSTACK = "fullstack"

    # AI/Data Types
    LLM_AI_AGENT = "llm_ai_agent"
    SQL_PROJECT = "sql_project"

    # Event-Driven / Async Types
    SERVERLESS = "serverless"
    BACKGROUND_WORKER = "background_worker"
    MESSAGE_QUEUE = "message_queue"

    # Blockchain Types
    SMART_CONTRACT = "smart_contract"

    # Meta Types
    HYBRID = "hybrid"  # Multiple types in one project
    UNKNOWN = "unknown"


class EntryPointType(Enum):
    """Universal entry point types (replaces HTTP-only focus)."""

    # API Entry Points
    HTTP_ENDPOINT = "http_endpoint"  # REST/GraphQL/gRPC
    GRAPHQL_QUERY = "graphql_query"
    GRAPHQL_MUTATION = "graphql_mutation"
    GRPC_METHOD = "grpc_method"

    # CLI Entry Points
    CLI_COMMAND = "cli_command"  # Main commands
    CLI_SUBCOMMAND = "cli_subcommand"  # Subcommands
    CLI_FLAG = "cli_flag"  # Flags/options

    # Mobile Entry Points
    ACTIVITY = "activity"  # Android Activity
    FRAGMENT = "fragment"  # Android Fragment
    VIEW_CONTROLLER = "view_controller"  # iOS ViewController
    SWIFTUI_VIEW = "swiftui_view"  # iOS SwiftUI View
    LIFECYCLE_METHOD = "lifecycle_method"  # onCreate, viewDidLoad, etc.
    UI_HANDLER = "ui_handler"  # Button clicks, gestures

    # Desktop Entry Points
    WINDOW = "window"  # WPF Window, Qt MainWindow
    DIALOG = "dialog"  # Dialog boxes
    EVENT_HANDLER = "event_handler"  # Click handlers, menu actions

    # Frontend Entry Points
    COMPONENT = "component"  # React/Vue/Angular components
    HOOK = "hook"  # React hooks
    COMPOSABLE = "composable"  # Vue composables
    ROUTE = "route"  # Frontend routes

    # AI/Agent Entry Points
    AGENT_TOOL = "agent_tool"  # LangChain/CrewAI tools
    AGENT_WORKFLOW = "agent_workflow"  # Agent workflows
    PROMPT_TEMPLATE = "prompt_template"  # Prompt templates

    # SQL Entry Points
    STORED_PROCEDURE = "stored_procedure"
    SQL_FUNCTION = "sql_function"
    SQL_TRIGGER = "sql_trigger"

    # Event-Driven Entry Points
    LAMBDA_HANDLER = "lambda_handler"              # AWS Lambda
    FUNCTION_HANDLER = "function_handler"          # Azure Functions, Cloud Functions
    BACKGROUND_JOB = "background_job"              # Celery, Sidekiq, Bull
    MESSAGE_CONSUMER = "message_consumer"          # Kafka, RabbitMQ, SQS
    EVENT_SUBSCRIBER = "event_subscriber"          # Event bus subscribers

    # Blockchain Entry Points
    SMART_CONTRACT_FUNCTION = "smart_contract_function"
    CONTRACT_EVENT = "contract_event"
    CONTRACT_MODIFIER = "contract_modifier"

    UNKNOWN = "unknown"


@dataclass
class ProjectInfo:
    """Project structure and metadata (universal multi-type support)."""

    language: Language
    frameworks: list[str]
    endpoint_count: int
    test_file_count: int
    root_path: str
    test_framework: TestFramework = TestFramework.UNKNOWN
    detected_patterns: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Universal multi-type support (can detect multiple types)
    project_types: list[ProjectType] = field(default_factory=list)
    primary_type: ProjectType = ProjectType.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "language": self.language.value,
            "frameworks": self.frameworks,
            "endpoint_count": self.endpoint_count,
            "test_file_count": self.test_file_count,
            "root_path": self.root_path,
            "test_framework": self.test_framework.value,
            "detected_patterns": self.detected_patterns,
            "metadata": self.metadata,
            "project_types": [pt.value for pt in self.project_types],
            "primary_type": self.primary_type.value,
        }


@dataclass
class Parameter:
    """Universal parameter definition (API/CLI/UI/etc.)."""

    name: str
    param_type: str  # "path", "query", "body", "header", "flag", "arg", "prop", "input"
    data_type: str  # "string", "integer", "boolean", "object", "array"
    required: bool = True
    default_value: Any = None
    constraints: dict[str, Any] = field(default_factory=dict)  # min, max, pattern, etc.

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "param_type": self.param_type,
            "data_type": self.data_type,
            "required": self.required,
            "default_value": self.default_value,
            "constraints": self.constraints,
        }


@dataclass
class EntryPoint:
    """Universal entry point (replaces API-only Endpoint).

    Represents any testable entry point in a codebase:
    - HTTP endpoints (REST/GraphQL/gRPC)
    - CLI commands and flags
    - Mobile UI handlers (Activity, ViewController)
    - Desktop UI handlers (Window, Dialog)
    - Frontend components (React, Vue, Angular)
    - LLM agent tools
    - SQL stored procedures
    """

    type: EntryPointType
    name: str  # "/users/:id", "deploy --force", "MainActivity.onCreate", "UserButton"
    params: list[Parameter]
    file_path: str
    line_number: int
    framework: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)  # Type-specific data

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "name": self.name,
            "params": [p.to_dict() for p in self.params],
            "file_path": self.file_path,
            "line_number": self.line_number,
            "framework": self.framework,
            "metadata": self.metadata,
        }


@dataclass
class Endpoint:
    """API endpoint definition (kept for backward compatibility with existing code)."""

    path: str
    method: HTTPMethod
    params: list[Parameter]
    response_codes: list[int]
    file_path: str
    line_number: int
    framework: Optional[str] = None
    handler_name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "method": self.method.value,
            "params": [
                {
                    "name": p.name,
                    "param_type": p.param_type,
                    "data_type": p.data_type,
                    "required": p.required,
                    "default_value": p.default_value,
                    "constraints": p.constraints,
                }
                for p in self.params
            ],
            "response_codes": self.response_codes,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "framework": self.framework,
            "handler_name": self.handler_name,
        }


@dataclass
class TestCase:
    """Test case definition."""

    name: str
    file_path: str
    line_number: int
    framework: TestFramework
    tested_endpoint: Optional[str] = None
    tested_method: Optional[HTTPMethod] = None
    tested_inputs: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    test_type: str = "unknown"  # "unit", "integration", "e2e"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "framework": self.framework.value,
            "tested_endpoint": self.tested_endpoint,
            "tested_method": self.tested_method.value if self.tested_method else None,
            "tested_inputs": self.tested_inputs,
            "expected_outputs": self.expected_outputs,
            "test_type": self.test_type,
        }


@dataclass
class Scenario:
    """Test scenario (input/output combination)."""

    endpoint: str
    method: HTTPMethod
    input_combination: dict[str, Any]
    expected_output: int  # HTTP status code
    scenario_type: str  # "happy_path", "edge_case", "error", "security"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "endpoint": self.endpoint,
            "method": self.method.value,
            "input_combination": self.input_combination,
            "expected_output": self.expected_output,
            "scenario_type": self.scenario_type,
            "description": self.description,
        }


@dataclass
class CoverageGap:
    """Missing test scenario."""

    scenario: Scenario
    is_tested: bool
    related_tests: list[TestCase] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario": self.scenario.to_dict(),
            "is_tested": self.is_tested,
            "related_tests": [t.to_dict() for t in self.related_tests],
        }


@dataclass
class RiskAssessment:
    """Risk scoring for missing test."""

    gap: CoverageGap
    business_impact: int  # 1-5
    technical_risk: int  # 1-5
    failure_probability: int  # 1-5
    risk_score: RiskScore  # impact × technical × probability (1-125)
    risk_level: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "gap": self.gap.to_dict(),
            "business_impact": self.business_impact,
            "technical_risk": self.technical_risk,
            "failure_probability": self.failure_probability,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "reasoning": self.reasoning,
        }

    @staticmethod
    def calculate_risk_level(score: RiskScore) -> str:
        """Calculate risk level from score."""
        if score >= 60:
            return "CRITICAL"
        elif score >= 40:
            return "HIGH"
        elif score >= 20:
            return "MEDIUM"
        else:
            return "LOW"


@dataclass
class CoverageMatrix:
    """Coverage matrix result."""

    total_scenarios: int
    tested_scenarios: int
    untested_scenarios: int
    coverage_percent: float
    gaps: list[CoverageGap]
    by_endpoint: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_scenarios": self.total_scenarios,
            "tested_scenarios": self.tested_scenarios,
            "untested_scenarios": self.untested_scenarios,
            "coverage_percent": round(self.coverage_percent, 2),
            "gaps": [gap.to_dict() for gap in self.gaps],
            "by_endpoint": self.by_endpoint,
        }


@dataclass
class AnalysisResult:
    """Universal analysis result format (output from any analyzer).

    Used by all analyzers (API, CLI, Mobile, Desktop, Frontend, LLM, SQL).
    """

    project_type: ProjectType
    entry_points: list[EntryPoint]
    test_cases: list[TestCase]
    scenarios: list[Scenario]
    coverage_matrix: CoverageMatrix
    risk_assessment: list[RiskAssessment]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_type": self.project_type.value,
            "entry_points": [ep.to_dict() for ep in self.entry_points],
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "scenarios": [s.to_dict() for s in self.scenarios],
            "coverage_matrix": self.coverage_matrix.to_dict(),
            "risk_assessment": [ra.to_dict() for ra in self.risk_assessment],
            "metadata": self.metadata,
        }
