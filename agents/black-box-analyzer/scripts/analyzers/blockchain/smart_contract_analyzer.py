#!/usr/bin/env python3
"""Smart Contract Analyzer for blockchain platforms.

Handles detection and analysis of smart contracts:
- Solidity (Ethereum)
- Rust (Solana)
- Move (Aptos/Sui)
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.constants import BLOCKCHAIN_PATTERNS
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

from ..base_analyzer import BaseAnalyzer


class SmartContractAnalyzer(BaseAnalyzer):
    """Analyzer for smart contracts (Solidity, Rust/Solana, Move)."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle smart contract projects."""
        return ProjectType.SMART_CONTRACT in project_info.project_types

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract smart contract entry points.

        Returns:
            List of contract functions, events, modifiers
        """
        entry_points = []

        # Solidity contracts (Ethereum)
        entry_points.extend(self._extract_solidity_contracts(project_path))

        # Rust contracts (Solana)
        entry_points.extend(self._extract_solana_contracts(project_path))

        # Move contracts (Aptos/Sui)
        entry_points.extend(self._extract_move_contracts(project_path))

        return entry_points

    def _extract_solidity_contracts(self, project_path: Path) -> list[EntryPoint]:
        """Extract Solidity contract functions."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.sol"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Extract contract name
            contract_pattern = BLOCKCHAIN_PATTERNS["solidity_contract"]
            contract_matches = list(contract_pattern.finditer(content))
            if not contract_matches:
                continue

            for i, contract_match in enumerate(contract_matches):
                contract_name = contract_match.group(1)
                # Bound search to this contract's body — stop at the next contract
                search_end = contract_matches[i + 1].start() if i + 1 < len(contract_matches) else len(content)
                search_area = content[contract_match.end():search_end]

                # Extract functions
                func_pattern = BLOCKCHAIN_PATTERNS["solidity_function"]
                for match in func_pattern.finditer(search_area):
                    func_name = match.group(1)
                    abs_pos = contract_match.end() + match.start()
                    line_num = content[:abs_pos].count("\n") + 1

                    # Parse function signature to extract parameters
                    func_sig = match.group(0)
                    params = self._parse_solidity_params(func_sig)

                    # Determine correct Solidity visibility (public/external/internal/private)
                    if "public" in func_sig:
                        visibility = "public"
                    elif "external" in func_sig:
                        visibility = "external"
                    elif "private" in func_sig:
                        visibility = "private"
                    else:
                        visibility = "internal"

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.SMART_CONTRACT_FUNCTION,
                            name=f"{contract_name}.{func_name}",
                            params=params,
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="solidity",
                            metadata={
                                "contract": contract_name,
                                "visibility": visibility,
                            },
                        )
                    )

                # Extract events
                event_pattern = BLOCKCHAIN_PATTERNS["solidity_event"]
                for match in event_pattern.finditer(search_area):
                    event_name = match.group(1)
                    abs_pos = contract_match.end() + match.start()
                    line_num = content[:abs_pos].count("\n") + 1

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.CONTRACT_EVENT,
                            name=f"{contract_name}.{event_name}",
                            params=[],
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="solidity",
                            metadata={"contract": contract_name, "event_type": "log"},
                        )
                    )

                # Extract modifiers (bounded to this contract's search_area)
                modifier_pattern = BLOCKCHAIN_PATTERNS["solidity_modifier"]
                for match in modifier_pattern.finditer(search_area):
                    modifier_name = match.group(1)
                    abs_pos = contract_match.end() + match.start()
                    line_num = content[:abs_pos].count("\n") + 1

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.CONTRACT_MODIFIER,
                            name=f"{contract_name}.{modifier_name}",
                            params=[],
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="solidity",
                            metadata={
                                "contract": contract_name,
                                "modifier_type": "access_control",
                            },
                        )
                    )

        return entry_points

    def _extract_solana_contracts(self, project_path: Path) -> list[EntryPoint]:
        """Extract Rust/Solana program instructions."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.rs"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: pub fn instruction_name(ctx: Context<...>)
            solana_instruction_pattern = BLOCKCHAIN_PATTERNS["solana_instruction"]
            for match in solana_instruction_pattern.finditer(content):
                func_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Extract Context type
                ctx_pattern = re.compile(r"Context<(\w+)>")
                ctx_match = ctx_pattern.search(match.group(0))
                ctx_type = ctx_match.group(1) if ctx_match else "Unknown"

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.SMART_CONTRACT_FUNCTION,
                        name=func_name,
                        params=[
                            Parameter(
                                name="ctx",
                                param_type="context",
                                data_type=f"Context<{ctx_type}>",
                                required=True,
                            )
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="solana",
                        metadata={"platform": "solana", "context": ctx_type},
                    )
                )

        return entry_points

    def _extract_move_contracts(self, project_path: Path) -> list[EntryPoint]:
        """Extract Move module functions."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.move"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Extract module name
            module_pattern = re.compile(r"module\s+\w+::(\w+)")
            module_matches = list(module_pattern.finditer(content))
            if not module_matches:
                continue

            for i, module_match in enumerate(module_matches):
                module_name = module_match.group(1)
                # Bound search to this module — stop at next module declaration
                module_end = module_matches[i + 1].start() if i + 1 < len(module_matches) else len(content)
                module_area = content[module_match.end():module_end]

                # Pattern: public entry fun function_name(...)
                move_function_pattern = BLOCKCHAIN_PATTERNS["move_function"]
                for match in move_function_pattern.finditer(module_area):
                    func_name = match.group(1)
                    abs_pos = module_match.end() + match.start()
                    line_num = content[:abs_pos].count("\n") + 1

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.SMART_CONTRACT_FUNCTION,
                            name=f"{module_name}::{func_name}",
                            params=[],
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="move",
                            metadata={"module": module_name, "visibility": "public"},
                        )
                    )

        return entry_points

    def _parse_solidity_params(self, func_sig: str) -> list[Parameter]:
        """Parse Solidity function parameters."""
        params = []

        # Extract parameter list between parentheses
        param_match = re.search(r"\(([^)]*)\)", func_sig)
        if not param_match:
            return params

        param_str = param_match.group(1).strip()
        if not param_str:
            return params

        # Split by comma (simple parsing)
        for param in param_str.split(","):
            param = param.strip()
            if not param:
                continue

            # Parse: type name or type memory name
            parts = param.split()
            if len(parts) >= 2:
                param_type = parts[0]
                param_name = parts[-1]

                params.append(
                    Parameter(
                        name=param_name,
                        param_type="solidity_param",
                        data_type=param_type,
                        required=True,
                    )
                )

        return params

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse smart contract test files.

        Smart contract tests typically:
        - Test function calls with different parameters
        - Validate state changes
        - Check access control (modifiers)
        - Test edge cases (overflow, underflow)
        Note: smart contract test parsing tracked in #3
        """
        return []

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate smart contract test scenarios.

        For smart contracts, scenarios include:
        - Functions: Valid params, invalid params, access control
        - Events: Emission validation
        - Modifiers: Authorization checks
        - Edge cases: Overflow, underflow, reentrancy
        - Security: Reentrancy, front-running, integer overflow
        """
        scenarios = []

        for entry_point in entry_points:
            if entry_point.type == EntryPointType.SMART_CONTRACT_FUNCTION:
                # Happy path: Valid function call
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="CALL",
                        input_combination={
                            "params": {p.name: "valid_value" for p in entry_point.params}
                        },
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Call {entry_point.name} with valid params",
                    )
                )

                # Error: Unauthorized caller
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="CALL",
                        input_combination={
                            "caller": "unauthorized_address",
                            "params": {p.name: "valid_value" for p in entry_point.params},
                        },
                        expected_output=1,
                        scenario_type="error",
                        description=f"{entry_point.name} called by unauthorized address",
                    )
                )

                # Edge case: Integer overflow
                int_params = [p for p in entry_point.params if "int" in p.data_type.lower()]
                for param in int_params:
                    scenarios.append(
                        Scenario(
                            endpoint=entry_point.name,
                            method="CALL",
                            input_combination={
                                "params": {param.name: 2**256 - 1}  # Max uint256
                            },
                            expected_output=0,
                            scenario_type="edge_case",
                            description=f"{entry_point.name} with max {param.name}",
                        )
                    )

                # Security: Reentrancy attack
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="CALL",
                        input_combination={
                            "params": {p.name: "valid_value" for p in entry_point.params},
                            "attack": "reentrancy",
                        },
                        expected_output=1,
                        scenario_type="security",
                        description=f"{entry_point.name} reentrancy protection",
                    )
                )

            elif entry_point.type == EntryPointType.CONTRACT_EVENT:
                # Event emission validation
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="EMIT",
                        input_combination={"event_data": {"field": "value"}},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Emit {entry_point.name} event",
                    )
                )

            elif entry_point.type == EntryPointType.CONTRACT_MODIFIER:
                # Modifier validation
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="VALIDATE",
                        input_combination={"caller": "authorized_address"},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Modifier {entry_point.name} allows authorized",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="VALIDATE",
                        input_combination={"caller": "unauthorized_address"},
                        expected_output=1,
                        scenario_type="error",
                        description=f"Modifier {entry_point.name} blocks unauthorized",
                    )
                )

        return scenarios
