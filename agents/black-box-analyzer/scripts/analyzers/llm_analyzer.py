#!/usr/bin/env python3
"""LLM/AI Agent Analyzer for LangChain, CrewAI, AutoGPT applications.

Handles detection and analysis of LLM agent systems:
- LangChain: Tools, chains, agents, prompts
- CrewAI: Agents, tasks, crews
- AutoGPT: Agent tools and workflows
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.constants import LLM_PATTERNS
from common.models import (
    EntryPoint,
    EntryPointType,
    Parameter,
    ProjectInfo,
    ProjectType,
    Scenario,
    TestCase,
)
from common.utils import (
    format_path_relative,
    read_file_safe,
    walk_files,
)

from .base_analyzer import BaseAnalyzer


class LLMAnalyzer(BaseAnalyzer):
    """Analyzer for LLM/AI agent systems."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle LLM projects."""
        return ProjectType.LLM_AI_AGENT in project_info.project_types

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract LLM agent entry points.

        Returns:
            List of agent tools, workflows, prompts
        """
        entry_points = []

        # LangChain tools
        entry_points.extend(self._extract_langchain_tools(project_path))

        # CrewAI agents and tasks
        entry_points.extend(self._extract_crewai_entry_points(project_path))

        return entry_points

    def _extract_langchain_tools(self, project_path: Path) -> list[EntryPoint]:
        """Extract LangChain tools and chains."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # @tool decorator
            tool_pattern = re.compile(r"@tool\s+def\s+(\w+)\s*\(([^)]*)\)")
            for match in tool_pattern.finditer(content):
                tool_name = match.group(1)
                params_str = match.group(2)
                line_num = content[: match.start()].count("\n") + 1

                # Parse parameters
                params = self._parse_python_params(params_str)

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.AGENT_TOOL,
                        name=tool_name,
                        params=params,
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="langchain",
                        metadata={"tool_type": "function"},
                    )
                )

            # BaseTool classes
            basetool_pattern = re.compile(r"class\s+(\w+)\s*\(\s*BaseTool\s*\)")
            for match in basetool_pattern.finditer(content):
                tool_class = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.AGENT_TOOL,
                        name=tool_class,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="langchain",
                        metadata={"tool_type": "class"},
                    )
                )

            # AgentExecutor
            agent_pattern = re.compile(r"AgentExecutor\s*\(\s*agent\s*=\s*(\w+)")
            for match in agent_pattern.finditer(content):
                agent_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.AGENT_WORKFLOW,
                        name=agent_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="langchain",
                        metadata={"workflow_type": "agent_executor"},
                    )
                )

            # PromptTemplate
            prompt_pattern = re.compile(r'PromptTemplate\s*\([^)]*template\s*=\s*["\']([^"\']+)["\']')
            for match in prompt_pattern.finditer(content):
                prompt_content = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Extract template name from variable assignment
                var_pattern = re.compile(r"(\w+)\s*=\s*PromptTemplate")
                var_match = var_pattern.search(content[max(0, match.start() - 100) : match.start()])
                template_name = var_match.group(1) if var_match else "prompt_template"

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.PROMPT_TEMPLATE,
                        name=template_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="langchain",
                        metadata={"template_content": prompt_content[:100]},
                    )
                )

        return entry_points

    def _extract_crewai_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract CrewAI agents and tasks."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # @agent decorator
            agent_pattern = re.compile(r"@agent\s+def\s+(\w+)\s*\(")
            for match in agent_pattern.finditer(content):
                agent_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.AGENT_WORKFLOW,
                        name=agent_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="crewai",
                        metadata={"component_type": "agent"},
                    )
                )

            # @task decorator
            task_pattern = re.compile(r"@task\s+def\s+(\w+)\s*\(")
            for match in task_pattern.finditer(content):
                task_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.AGENT_WORKFLOW,
                        name=task_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="crewai",
                        metadata={"component_type": "task"},
                    )
                )

        return entry_points

    def _parse_python_params(self, params_str: str) -> list[Parameter]:
        """Parse Python function parameters."""
        params = []

        if not params_str.strip():
            return params

        # Split by comma (simple parsing)
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue

            # Parse name: type = default
            parts = re.match(r"(\w+)(?::\s*(\w+))?(?:\s*=\s*(.+))?", param)
            if parts:
                name = parts.group(1)
                param_type = parts.group(2) or "any"
                default = parts.group(3)

                params.append(
                    Parameter(
                        name=name,
                        param_type="arg",
                        data_type=param_type.lower(),
                        required=default is None,
                        default_value=default,
                    )
                )

        return params

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse LLM agent test files.

        LLM tests typically:
        - Mock LLM responses
        - Test tool input/output schemas
        - Validate prompt templates
        Note: LLM test parsing tracked in #3
        """
        return []

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate LLM agent test scenarios.

        For LLM agents, scenarios include:
        - Tools: Valid input schema, invalid schema, edge cases
        - Workflows: Tool chaining, error handling, retries
        - Prompts: Variable substitution, token limits
        - Agents: Goal achievement, tool selection
        """
        scenarios = []

        for entry_point in entry_points:
            if entry_point.type == EntryPointType.AGENT_TOOL:
                # Happy path: Valid tool input
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="TOOL",
                        input_combination={
                            "params": {p.name: "valid_value" for p in entry_point.params}
                        },
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Valid input to tool {entry_point.name}",
                    )
                )

                # Error: Invalid schema
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="TOOL",
                        input_combination={"params": {"invalid": "schema"}},
                        expected_output=1,
                        scenario_type="error",
                        description=f"Invalid schema for tool {entry_point.name}",
                    )
                )

                # Edge case: Missing optional params
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="TOOL",
                        input_combination={"params": {}},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Tool {entry_point.name} without optional params",
                    )
                )

            elif entry_point.type == EntryPointType.AGENT_WORKFLOW:
                # Workflow execution scenarios
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="WORKFLOW",
                        input_combination={"goal": "valid_goal"},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Execute workflow {entry_point.name}",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="WORKFLOW",
                        input_combination={"goal": "impossible_goal"},
                        expected_output=1,
                        scenario_type="error",
                        description=f"Workflow {entry_point.name} with impossible goal",
                    )
                )

            elif entry_point.type == EntryPointType.PROMPT_TEMPLATE:
                # Prompt template scenarios
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="PROMPT",
                        input_combination={"variables": {"var": "value"}},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Render prompt template {entry_point.name}",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="PROMPT",
                        input_combination={"variables": {}},
                        expected_output=1,
                        scenario_type="error",
                        description=f"Missing variables for template {entry_point.name}",
                    )
                )

        return scenarios
