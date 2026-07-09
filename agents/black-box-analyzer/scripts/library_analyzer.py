#!/usr/bin/env python3
"""
LibraryAnalyzer — white-box analyzer for library/SDK projects (any language).

Activated when analyze_project_structure detects 0 HTTP endpoints.
Delegates to analyze_library_branches.py (Ollama) for branch extraction
and scan_tdd_refactoring.py (Ollama) for testability analysis.
"""

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common.models import (
    AnalysisResult,
    CoverageGap,
    CoverageMatrix,
    EntryPoint,
    EntryPointType,
    ProjectType,
    RiskAssessment,
    RiskScore,
    Scenario,
    TestCase,
)

_SCRIPTS_DIR = Path(__file__).parent


def _run_script(script: str, *args: str) -> dict | list | None:
    """Run a sibling script and parse its JSON stdout."""
    cmd = [sys.executable, str(_SCRIPTS_DIR / script), *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"[WARN] {script} exited {result.returncode}: {result.stderr[:300]}", file=sys.stderr)
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"[WARN] {script} failed: {exc}", file=sys.stderr)
        return None


def _branch_to_scenario(method: dict, branch: dict, index: int) -> Scenario:
    """Convert a branch extracted by analyze_library_branches into a Scenario."""
    # Reuse Scenario dataclass — repurpose fields for library context
    from common.models import HTTPMethod
    return Scenario(
        endpoint=method.get("method", "unknown"),
        method=HTTPMethod.GET,           # sentinel — not HTTP, but field is required
        input_combination={"condition": branch.get("condition", "")},
        expected_output=0,               # sentinel — not an HTTP code
        scenario_type=_infer_scenario_type(branch),
        description=branch.get("test_scenario", branch.get("condition", "")),
    )


def _infer_scenario_type(branch: dict) -> str:
    condition = branch.get("condition", "").lower()
    outcome = branch.get("outcome", "").lower()
    if any(k in outcome for k in ("throw", "raise", "panic", "exception", "error")):
        return "error"
    if any(k in condition for k in ("null", "none", "nil", "empty", "zero", "negative", "max", "min")):
        return "edge_case"
    return "happy_path"


def _risk_for_scenario(scenario: Scenario) -> RiskAssessment:
    """Simple heuristic risk scoring for library branch scenarios."""
    impact = 3
    tech_risk = 3
    prob = 3

    if scenario.scenario_type == "error":
        tech_risk = 4
        prob = 4
    elif scenario.scenario_type == "edge_case":
        tech_risk = 3
        prob = 3
    else:
        tech_risk = 2
        prob = 2

    score: RiskScore = impact * tech_risk * prob
    level = RiskAssessment.calculate_risk_level(score)

    gap = CoverageGap(scenario=scenario, is_tested=False)
    return RiskAssessment(
        gap=gap,
        business_impact=impact,
        technical_risk=tech_risk,
        failure_probability=prob,
        risk_score=score,
        risk_level=level,
        reasoning=f"Library branch: {scenario.description[:120]}",
    )


class LibraryAnalyzer:
    """Analyzer for library/SDK projects — white-box, any language."""

    def can_analyze(self, project_info) -> bool:
        """Activate when project has 0 HTTP endpoints."""
        return project_info.metadata.get("is_library", False) or project_info.endpoint_count == 0

    def analyze(self, project_path: Path, project_info, agents: int = 1,
                typed_agents: bool = False, include_e2e: bool = False) -> AnalysisResult:
        src_candidates = [
            project_path / "src",
            project_path / "lib",
            project_path / "source",
            project_path,
        ]
        src_path = next((p for p in src_candidates if p.is_dir()), project_path)

        language = project_info.language.value
        if language == "unknown":
            language = "auto"

        agents_args = ["--agents", str(agents)] if agents > 1 else []
        typed_args = ["--typed-agents"] if typed_agents else []
        e2e_args = ["--e2e"] if include_e2e else []

        # Phase 1 + Phase 4b run in parallel — no data dependency between them
        def _phase1():
            return _run_script(
                "analyze_library_branches.py",
                str(src_path), "--language", language, *agents_args, *typed_args, *e2e_args,
            )

        def _phase4b():
            return _run_script(
                "scan_tdd_refactoring.py",
                str(src_path), "--language", language, *agents_args,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_phase1)
            f4b = pool.submit(_phase4b)
            branch_data = f1.result()
            refactoring_data = f4b.result()

        methods = branch_data.get("methods", []) if branch_data else []
        self._refactoring_data = refactoring_data  # stored for caller access

        # Build entry_points + scenarios from branch data
        entry_points: list[EntryPoint] = []
        scenarios: list[Scenario] = []
        risk_assessment: list[RiskAssessment] = []

        for method in methods:
            ep = EntryPoint(
                type=EntryPointType.UNKNOWN,
                name=method.get("method", "unknown"),
                params=[],
                file_path=method.get("source_file", ""),
                line_number=0,
                metadata={"signature": method.get("signature", "")},
            )
            entry_points.append(ep)

            for i, branch in enumerate(method.get("branches", [])):
                scenario = _branch_to_scenario(method, branch, i)
                scenarios.append(scenario)
                risk_assessment.append(_risk_for_scenario(scenario))

        # Phase 2 — match against existing tests (reuse parse_test_files output if available)
        tests_file = project_path / ".claude" / "bbanalysis-last-tests.json"
        test_cases: list[TestCase] = []
        covered_descriptions: set[str] = set()

        if tests_file.exists():
            try:
                tests_data = json.loads(tests_file.read_text())
                from common.models import TestFramework
                for t in tests_data.get("tests", []):
                    try:
                        fw = TestFramework(t.get("framework", "unknown"))
                    except ValueError:
                        fw = TestFramework.UNKNOWN
                    tc = TestCase(
                        name=t["name"],
                        file_path=t.get("file_path", ""),
                        line_number=t.get("line_number", 0),
                        framework=fw,
                    )
                    test_cases.append(tc)
                    covered_descriptions.add(t["name"].lower())
            except Exception:
                pass

        # Mark scenarios as tested if a test name contains key words from scenario description
        gaps: list[CoverageGap] = []
        for scenario in scenarios:
            desc_words = set(scenario.description.lower().split())
            is_tested = any(
                len(desc_words & set(name.lower().split())) >= 2
                for name in covered_descriptions
            )
            gaps.append(CoverageGap(scenario=scenario, is_tested=is_tested))

        tested = sum(1 for g in gaps if g.is_tested)
        total = len(gaps)
        matrix = CoverageMatrix(
            total_scenarios=total,
            tested_scenarios=tested,
            untested_scenarios=total - tested,
            coverage_percent=(tested / total * 100) if total else 0.0,
            gaps=gaps,
            by_endpoint={},
        )

        tdd_blockers = refactoring_data.get("blockers", []) if refactoring_data else []

        return AnalysisResult(
            project_type=ProjectType.LIBRARY,
            entry_points=entry_points,
            test_cases=test_cases,
            scenarios=scenarios,
            coverage_matrix=matrix,
            risk_assessment=risk_assessment,
            metadata={
                "mode": "library_whitebox",
                "language": language,
                "src_path": str(src_path),
                "branch_count": sum(len(m.get("branches", [])) for m in methods),
                "tdd_blockers": tdd_blockers,
                "tdd_blocker_count": len(tdd_blockers),
            },
        )
