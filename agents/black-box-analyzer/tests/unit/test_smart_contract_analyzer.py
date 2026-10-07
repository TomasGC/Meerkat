#!/usr/bin/env python3
"""Tests for analyzers/blockchain/smart_contract_analyzer.py: Solidity/Solana/Move extraction and scenarios."""

from pathlib import Path

from analyzers.blockchain.smart_contract_analyzer import SmartContractAnalyzer
from bba.models import EntryPoint, EntryPointType, Language, Parameter, ProjectInfo, ProjectType


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _info(root: Path, *types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.SOLIDITY,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=str(root),
        project_types=list(types),
        primary_type=types[0] if types else ProjectType.UNKNOWN,
    )


def _by_name(entry_points: list[EntryPoint]) -> dict[str, EntryPoint]:
    return {ep.name: ep for ep in entry_points}


def test_can_analyze_accepts_only_smart_contracts(tmp_path):
    assert SmartContractAnalyzer().can_analyze(_info(tmp_path, ProjectType.SMART_CONTRACT))
    assert not SmartContractAnalyzer().can_analyze(_info(tmp_path, ProjectType.REST_API))


# ── Solidity ──────────────────────────────────────────────────────────────────


def test_solidity_functions_are_scoped_to_their_contract(tmp_path):
    _write(
        tmp_path,
        "contracts/Tokens.sol",
        "contract Token {\n"
        "    function transfer(address to, uint256 amount) public returns (bool) {}\n"
        "    function mint(uint256 amount) external {}\n"
        "}\n"
        "contract Vault {\n"
        "    function withdraw() public {}\n"
        "}\n",
    )

    eps = _by_name(SmartContractAnalyzer().extract_entry_points(tmp_path))

    transfer = eps["Token.transfer"]
    assert transfer.type == EntryPointType.SMART_CONTRACT_FUNCTION
    assert transfer.line_number == 2
    assert transfer.metadata == {"contract": "Token", "visibility": "public"}
    assert [(p.name, p.data_type) for p in transfer.params] == [("to", "address"), ("amount", "uint256")]
    assert eps["Token.mint"].metadata["visibility"] == "external"
    assert eps["Vault.withdraw"].metadata["contract"] == "Vault"
    assert eps["Vault.withdraw"].params == []
    assert "Token.withdraw" not in eps


def test_solidity_visibility_ignores_parameter_names(tmp_path):
    _write(tmp_path, "Sig.sol", "contract Sig {\n    function verify(bytes32 publicKey) external {}\n}\n")

    eps = _by_name(SmartContractAnalyzer().extract_entry_points(tmp_path))

    assert eps["Sig.verify"].metadata["visibility"] == "external"


def test_solidity_events_and_modifiers_are_extracted(tmp_path):
    _write(
        tmp_path,
        "Owned.sol",
        "contract Owned {\n    event Transfer(address from);\n    modifier onlyOwner() { _; }\n}\n",
    )

    eps = _by_name(SmartContractAnalyzer().extract_entry_points(tmp_path))

    assert eps["Owned.Transfer"].type == EntryPointType.CONTRACT_EVENT
    assert eps["Owned.Transfer"].line_number == 2
    assert eps["Owned.onlyOwner"].type == EntryPointType.CONTRACT_MODIFIER
    assert eps["Owned.onlyOwner"].metadata == {"contract": "Owned", "modifier_type": "access_control"}


def test_solidity_file_without_contract_or_content_is_skipped(tmp_path):
    _write(tmp_path, "Lib.sol", "pragma solidity ^0.8.0;\n")
    _write(tmp_path, "Empty.sol", "")
    _write(tmp_path, "Empty.rs", "")
    _write(tmp_path, "Empty.move", "")
    _write(tmp_path, "NoModule.move", "script { fun main() {} }\n")

    assert SmartContractAnalyzer().extract_entry_points(tmp_path) == []


def test_parse_solidity_params_handles_memory_keyword_and_empty_lists():
    analyzer = SmartContractAnalyzer()

    params = analyzer._parse_solidity_params("function set(string memory name, uint8 ) public")

    assert [(p.name, p.data_type) for p in params] == [("name", "string")]
    assert analyzer._parse_solidity_params("function f() public") == []
    assert analyzer._parse_solidity_params("no parens") == []
    assert analyzer._parse_solidity_params("function f(uint a,, uint b)") == [
        Parameter("a", "solidity_param", "uint", True),
        Parameter("b", "solidity_param", "uint", True),
    ]


# ── Solana ────────────────────────────────────────────────────────────────────


_SOLANA_DEPOSIT = "pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> { Ok(()) }\n"


def test_solana_instruction_becomes_a_contract_function_with_ctx_param(tmp_path):
    _write(tmp_path, "programs/vault/src/lib.rs", _SOLANA_DEPOSIT)

    eps = _by_name(SmartContractAnalyzer().extract_entry_points(tmp_path))

    deposit = eps["deposit"]
    assert deposit.type == EntryPointType.SMART_CONTRACT_FUNCTION
    assert deposit.framework == "solana"
    assert deposit.line_number == 1
    assert [(p.name, p.param_type) for p in deposit.params] == [("ctx", "context")]


def test_solana_instruction_records_its_context_type(tmp_path):
    _write(tmp_path, "lib.rs", _SOLANA_DEPOSIT)

    deposit = _by_name(SmartContractAnalyzer().extract_entry_points(tmp_path))["deposit"]

    assert deposit.metadata == {"platform": "solana", "context": "Deposit"}


def test_anchor_program_attribute_does_not_become_a_nameless_entry_point(tmp_path):
    _write(
        tmp_path,
        "lib.rs",
        "#[program]\npub mod vault {\n    pub fn deposit(ctx: Context<Deposit>) -> Result<()> { Ok(()) }\n}\n",
    )

    names = [ep.name for ep in SmartContractAnalyzer().extract_entry_points(tmp_path)]

    assert names == ["deposit"]


# ── Move ──────────────────────────────────────────────────────────────────────


def test_move_entry_functions_are_scoped_per_module(tmp_path):
    _write(
        tmp_path,
        "sources/coins.move",
        "module 0x1::coin {\n    public entry fun mint() {}\n}\nmodule 0x1::bank {\n    public entry fun pay() {}\n}\n",
    )

    eps = _by_name(SmartContractAnalyzer().extract_entry_points(tmp_path))

    assert set(eps) == {"coin::mint", "bank::pay"}
    assert eps["bank::pay"].line_number == 5
    assert eps["coin::mint"].metadata == {"module": "coin", "visibility": "public"}


def test_parse_tests_returns_no_tests(tmp_path):
    assert SmartContractAnalyzer().parse_tests(tmp_path) == []


# ── generate_scenarios ────────────────────────────────────────────────────────


def test_function_scenarios_add_overflow_case_per_integer_param():
    ep = EntryPoint(
        EntryPointType.SMART_CONTRACT_FUNCTION,
        "Token.transfer",
        [Parameter("to", "solidity_param", "address"), Parameter("amount", "solidity_param", "uint256")],
        "T.sol",
        1,
    )

    scenarios = SmartContractAnalyzer().generate_scenarios([ep])

    assert [s.scenario_type for s in scenarios] == ["happy_path", "error", "edge_case", "security"]
    assert scenarios[1].input_combination["caller"] == "unauthorized_address"
    assert scenarios[2].input_combination == {"params": {"amount": 2**256 - 1}}
    assert scenarios[3].input_combination["attack"] == "reentrancy"


def test_event_and_modifier_scenarios():
    eps = [
        EntryPoint(EntryPointType.CONTRACT_EVENT, "Token.Transfer", [], "T.sol", 1),
        EntryPoint(EntryPointType.CONTRACT_MODIFIER, "Token.onlyOwner", [], "T.sol", 2),
        EntryPoint(EntryPointType.UNKNOWN, "ignored", [], "T.sol", 3),
    ]

    scenarios = SmartContractAnalyzer().generate_scenarios(eps)

    assert [(s.endpoint, s.method_name, s.scenario_type, s.expected_output) for s in scenarios] == [
        ("Token.Transfer", "EMIT", "happy_path", 0),
        ("Token.onlyOwner", "VALIDATE", "happy_path", 0),
        ("Token.onlyOwner", "VALIDATE", "error", 1),
    ]
