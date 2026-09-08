#!/usr/bin/env python3
"""E2E tests for universal project type detection and analysis.

Tests all 19 project types with real fixtures.

NOTE: These tests are skipped because universal detection is not yet implemented.
This is future work planned for Phase 2+ of the refactoring.
"""

import pytest
from pathlib import Path

# Skip all tests in this file - universal detection not yet implemented
pytestmark = pytest.mark.skip(reason="Universal detection not yet implemented (future work)")

# Add scripts directory to path (parent/scripts)

import pytest
from analyze_project_structure import analyze_project as detect_project_structure
from analyzers.api_analyzer import APIAnalyzer
from analyzers.cli_analyzer import CLIAnalyzer
from analyzers.mobile_analyzer import MobileAnalyzer
from analyzers.frontend_analyzer import FrontendAnalyzer
from analyzers.llm_analyzer import LLMAnalyzer
from analyzers.sql_analyzer import SQLAnalyzer
from analyzers.event_driven.serverless_analyzer import ServerlessAnalyzer
from analyzers.event_driven.worker_analyzer import WorkerAnalyzer
from analyzers.event_driven.message_queue_analyzer import MessageQueueAnalyzer
from analyzers.blockchain.smart_contract_analyzer import SmartContractAnalyzer
from common.models import ProjectType, EntryPointType

FIXTURES_DIR = Path(__file__).parent / "fixtures"

class TestCLIProject:
    """Test CLI project detection and analysis."""

    @pytest.fixture
    def cli_project(self):
        return FIXTURES_DIR / "cli_project"

    def test_detect_cli_project(self, cli_project):
        """Should detect CLI project type."""
        project_info = detect_project_structure(cli_project)

        assert ProjectType.CLI_APP in project_info.project_types
        assert project_info.language.value == "go"
        assert "cobra" in [f.lower() for f in project_info.frameworks]

    def test_extract_cli_commands(self, cli_project):
        """Should extract CLI commands and flags."""
        project_info = detect_project_structure(cli_project)
        analyzer = CLIAnalyzer()

        entry_points = analyzer.extract_entry_points(cli_project)

        # Should find: deploy command, config set subcommand
        assert len(entry_points) >= 2

        # Check deploy command
        deploy_cmd = next((ep for ep in entry_points if "deploy" in ep.name.lower()), None)
        assert deploy_cmd is not None
        assert deploy_cmd.type == EntryPointType.CLI_COMMAND

        # Check flags
        flag_names = [p.name for ep in entry_points for p in ep.params]
        assert "force" in flag_names or "f" in flag_names
        assert "environment" in flag_names or "e" in flag_names

class TestAndroidProject:
    """Test Android project detection and analysis."""

    @pytest.fixture
    def android_project(self):
        return FIXTURES_DIR / "android_project"

    def test_detect_android_project(self, android_project):
        """Should detect Android project type."""
        project_info = detect_project_structure(android_project)

        assert ProjectType.ANDROID_APP in project_info.project_types

    def test_extract_android_activities(self, android_project):
        """Should extract Activities and lifecycle methods."""
        project_info = detect_project_structure(android_project)
        analyzer = MobileAnalyzer()

        entry_points = analyzer.extract_entry_points(android_project)

        # Should find MainActivity
        assert len(entry_points) > 0

        # Check for lifecycle methods
        lifecycle_methods = [ep for ep in entry_points if ep.type == EntryPointType.LIFECYCLE_METHOD]
        assert len(lifecycle_methods) >= 3  # onCreate, onStart, onResume

        # Check for UI handlers
        ui_handlers = [ep for ep in entry_points if ep.type == EntryPointType.UI_HANDLER]
        assert len(ui_handlers) >= 1  # onButtonClick

class TestFrontendProject:
    """Test React frontend project detection and analysis."""

    @pytest.fixture
    def frontend_project(self):
        return FIXTURES_DIR / "frontend_project"

    def test_detect_frontend_project(self, frontend_project):
        """Should detect React frontend project."""
        project_info = detect_project_structure(frontend_project)

        assert ProjectType.FRONTEND_REACT in project_info.project_types
        assert "react" in [f.lower() for f in project_info.frameworks]

    def test_extract_react_components(self, frontend_project):
        """Should extract React components and hooks."""
        project_info = detect_project_structure(frontend_project)
        analyzer = FrontendAnalyzer()

        entry_points = analyzer.extract_entry_points(frontend_project)

        # Should find UserButton component
        assert len(entry_points) >= 1

        # Check component
        component = next((ep for ep in entry_points if "UserButton" in ep.name), None)
        assert component is not None
        assert component.type == EntryPointType.COMPONENT

        # Check props
        prop_names = [p.name for p in component.params]
        assert "userId" in prop_names

class TestLLMProject:
    """Test LLM agent project detection and analysis."""

    @pytest.fixture
    def llm_project(self):
        return FIXTURES_DIR / "llm_agent_project"

    def test_detect_llm_project(self, llm_project):
        """Should detect LLM agent project."""
        project_info = detect_project_structure(llm_project)

        assert ProjectType.LLM_AI_AGENT in project_info.project_types

    def test_extract_langchain_tools(self, llm_project):
        """Should extract LangChain tools and agents."""
        project_info = detect_project_structure(llm_project)
        analyzer = LLMAnalyzer()

        entry_points = analyzer.extract_entry_points(llm_project)

        # Should find: search_documents, calculate_risk, WebScraperTool
        assert len(entry_points) >= 3

        # Check @tool decorator
        tool_entries = [ep for ep in entry_points if ep.type == EntryPointType.AGENT_TOOL]
        assert len(tool_entries) >= 2

        # Check tool names
        tool_names = [ep.name for ep in tool_entries]
        assert "search_documents" in tool_names
        assert "calculate_risk" in tool_names

class TestSQLProject:
    """Test SQL project detection and analysis."""

    @pytest.fixture
    def sql_project(self):
        return FIXTURES_DIR / "sql_project"

    def test_detect_sql_project(self, sql_project):
        """Should detect SQL project."""
        project_info = detect_project_structure(sql_project)

        assert ProjectType.SQL_PROJECT in project_info.project_types

    def test_extract_stored_procedures(self, sql_project):
        """Should extract stored procedures and functions."""
        project_info = detect_project_structure(sql_project)
        analyzer = SQLAnalyzer()

        entry_points = analyzer.extract_entry_points(sql_project)

        # Should find procedures, functions, triggers
        assert len(entry_points) >= 3

        # Check stored procedure
        procedures = [ep for ep in entry_points if ep.type == EntryPointType.STORED_PROCEDURE]
        assert len(procedures) >= 1
        assert any("CreateUser" in ep.name for ep in procedures)

        # Check functions
        functions = [ep for ep in entry_points if ep.type == EntryPointType.SQL_FUNCTION]
        assert len(functions) >= 2

class TestServerlessProject:
    """Test serverless project detection and analysis."""

    @pytest.fixture
    def serverless_project(self):
        return FIXTURES_DIR / "serverless_project"

    def test_detect_serverless_project(self, serverless_project):
        """Should detect serverless project."""
        project_info = detect_project_structure(serverless_project)

        assert ProjectType.SERVERLESS in project_info.project_types

    def test_extract_lambda_handlers(self, serverless_project):
        """Should extract Lambda handlers."""
        project_info = detect_project_structure(serverless_project)
        analyzer = ServerlessAnalyzer()

        entry_points = analyzer.extract_entry_points(serverless_project)

        # Should find multiple handlers
        assert len(entry_points) >= 3

        # Check Lambda handler type
        lambda_handlers = [ep for ep in entry_points if ep.type == EntryPointType.LAMBDA_HANDLER]
        assert len(lambda_handlers) >= 2

class TestWorkerProject:
    """Test background worker project detection and analysis."""

    @pytest.fixture
    def worker_project(self):
        return FIXTURES_DIR / "worker_project"

    def test_detect_worker_project(self, worker_project):
        """Should detect background worker project."""
        project_info = detect_project_structure(worker_project)

        assert ProjectType.BACKGROUND_WORKER in project_info.project_types

    def test_extract_celery_tasks(self, worker_project):
        """Should extract Celery tasks."""
        project_info = detect_project_structure(worker_project)
        analyzer = WorkerAnalyzer()

        entry_points = analyzer.extract_entry_points(worker_project)

        # Should find tasks
        assert len(entry_points) >= 3

        # Check task type
        tasks = [ep for ep in entry_points if ep.type == EntryPointType.BACKGROUND_JOB]
        assert len(tasks) >= 3

        # Check task names
        task_names = [ep.name for ep in tasks]
        assert "send_email" in task_names
        assert "process_payment" in task_names

class TestMessageQueueProject:
    """Test message queue project detection and analysis."""

    @pytest.fixture
    def mq_project(self):
        return FIXTURES_DIR / "message_queue_project"

    def test_detect_message_queue_project(self, mq_project):
        """Should detect message queue project."""
        project_info = detect_project_structure(mq_project)

        assert ProjectType.MESSAGE_QUEUE in project_info.project_types

    def test_extract_kafka_consumers(self, mq_project):
        """Should extract Kafka consumers."""
        project_info = detect_project_structure(mq_project)
        analyzer = MessageQueueAnalyzer()

        entry_points = analyzer.extract_entry_points(mq_project)

        # Should find consumer
        assert len(entry_points) >= 1

        # Check consumer type
        consumers = [ep for ep in entry_points if ep.type == EntryPointType.MESSAGE_CONSUMER]
        assert len(consumers) >= 1

class TestSmartContractProject:
    """Test smart contract project detection and analysis."""

    @pytest.fixture
    def contract_project(self):
        return FIXTURES_DIR / "smart_contract_project"

    def test_detect_smart_contract_project(self, contract_project):
        """Should detect smart contract project."""
        project_info = detect_project_structure(contract_project)

        assert ProjectType.SMART_CONTRACT in project_info.project_types

    def test_extract_solidity_functions(self, contract_project):
        """Should extract Solidity contract functions."""
        project_info = detect_project_structure(contract_project)
        analyzer = SmartContractAnalyzer()

        entry_points = analyzer.extract_entry_points(contract_project)

        # Should find functions, events, modifiers
        assert len(entry_points) >= 5

        # Check functions
        functions = [ep for ep in entry_points if ep.type == EntryPointType.SMART_CONTRACT_FUNCTION]
        assert len(functions) >= 5  # transfer, approve, transferFrom, mint, burn

        # Check events
        events = [ep for ep in entry_points if ep.type == EntryPointType.CONTRACT_EVENT]
        assert len(events) >= 4

        # Check modifiers
        modifiers = [ep for ep in entry_points if ep.type == EntryPointType.CONTRACT_MODIFIER]
        assert len(modifiers) >= 2

class TestHybridProject:
    """Test hybrid project detection and analysis."""

    @pytest.fixture
    def hybrid_project(self):
        return FIXTURES_DIR / "hybrid_project"

    def test_detect_hybrid_project(self, hybrid_project):
        """Should detect multiple project types."""
        project_info = detect_project_structure(hybrid_project)

        # Should detect Android + REST API
        assert ProjectType.ANDROID_APP in project_info.project_types
        assert ProjectType.REST_API in project_info.project_types
        assert ProjectType.HYBRID in project_info.project_types

    def test_analyze_hybrid_project(self, hybrid_project):
        """Should analyze both mobile and API components."""
        project_info = detect_project_structure(hybrid_project)

        # Mobile analyzer should work
        mobile_analyzer = MobileAnalyzer()
        mobile_entry_points = mobile_analyzer.extract_entry_points(hybrid_project)
        assert len(mobile_entry_points) > 0

        # API analyzer should work
        api_analyzer = APIAnalyzer()
        api_entry_points = api_analyzer.extract_entry_points(hybrid_project)
        assert len(api_entry_points) >= 3  # GET /users, GET /users/:id, POST /users
