#!/usr/bin/env python3
"""Tests for analyzers/frontend_analyzer.py: React/Vue/Angular extraction and scenario generation."""

from pathlib import Path

import pytest

from analyzers.frontend_analyzer import FrontendAnalyzer
from bba.models import EntryPoint, EntryPointType, Language, Parameter, ProjectInfo, ProjectType


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _info(root: Path, *types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.TYPESCRIPT,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=str(root),
        project_types=list(types),
        primary_type=types[0] if types else ProjectType.UNKNOWN,
    )


def _by_name(entry_points: list[EntryPoint]) -> dict[str, EntryPoint]:
    return {ep.name: ep for ep in entry_points}


# ── can_analyze ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "project_type",
    [ProjectType.FRONTEND_REACT, ProjectType.FRONTEND_VUE, ProjectType.FRONTEND_ANGULAR],
)
def test_can_analyze_accepts_every_frontend_type(tmp_path, project_type):
    assert FrontendAnalyzer().can_analyze(_info(tmp_path, project_type))


def test_can_analyze_rejects_backend_project(tmp_path):
    assert not FrontendAnalyzer().can_analyze(_info(tmp_path, ProjectType.REST_API))


# ── React ─────────────────────────────────────────────────────────────────────


def test_react_function_component_reads_props_interface(tmp_path):
    _write(
        tmp_path,
        "src/Button.tsx",
        "interface ButtonProps {\n  label: string;\n  disabled?: boolean;\n}\n"
        "export default function Button(props: ButtonProps) {\n  return <button>{props.label}</button>;\n}\n",
    )

    eps = _by_name(FrontendAnalyzer().extract_entry_points(tmp_path))

    button = eps["Button"]
    assert button.type == EntryPointType.COMPONENT
    assert button.metadata == {"component_type": "function"}
    assert button.line_number == 5
    assert [(p.name, p.data_type, p.param_type) for p in button.params] == [
        ("label", "string", "prop"),
        ("disabled", "boolean", "prop"),
    ]


def test_react_arrow_function_returning_jsx_is_a_component(tmp_path):
    _write(tmp_path, "src/Card.jsx", "export const Card = () => {\n  return (\n    <div>card</div>\n  );\n};\n")

    eps = _by_name(FrontendAnalyzer().extract_entry_points(tmp_path))

    assert eps["Card"].metadata == {"component_type": "arrow"}
    assert eps["Card"].framework == "react"


def test_react_arrow_function_without_jsx_is_not_a_component(tmp_path):
    _write(tmp_path, "src/math.tsx", "const add = (a, b) => {\n  return a + b;\n};\n")

    assert FrontendAnalyzer().extract_entry_points(tmp_path) == []


def test_react_custom_hook_is_reported_as_hook(tmp_path):
    _write(tmp_path, "src/useAuth.tsx", "export function useAuth() {\n  return null;\n}\n")

    eps = FrontendAnalyzer().extract_entry_points(tmp_path)

    hooks = [ep for ep in eps if ep.type == EntryPointType.HOOK]
    assert [h.name for h in hooks] == ["useAuth"]
    assert hooks[0].metadata == {"hook_type": "custom"}


def test_react_router_routes_are_extracted(tmp_path):
    _write(
        tmp_path,
        "src/App.tsx",
        "<Routes>\n  <Route path=\"/users/:id\" element={<User />} />\n  <Route path='/home' />\n</Routes>\n",
    )

    routes = [ep for ep in FrontendAnalyzer().extract_entry_points(tmp_path) if ep.type == EntryPointType.ROUTE]

    assert [(r.name, r.line_number, r.framework) for r in routes] == [
        ("/users/:id", 2, "react-router"),
        ("/home", 3, "react-router"),
    ]


def test_empty_frontend_files_yield_nothing(tmp_path):
    for name in ("a.tsx", "b.jsx", "c.vue", "composables/d.ts"):
        _write(tmp_path, name, "")

    assert FrontendAnalyzer().extract_entry_points(tmp_path) == []


# ── Vue ───────────────────────────────────────────────────────────────────────


def test_vue_script_setup_component_reads_define_props(tmp_path):
    _write(
        tmp_path,
        "src/UserCard.vue",
        '<template><div/></template>\n<script setup lang="ts">\n'
        "defineProps<{ name: string; age?: number }>()\n</script>\n",
    )

    eps = _by_name(FrontendAnalyzer().extract_entry_points(tmp_path))

    card = eps["UserCard"]
    assert card.framework == "vue"
    assert card.metadata == {"component_type": "sfc", "setup": True}
    assert [(p.name, p.data_type) for p in card.params] == [("name", "string"), ("age", "number")]


def test_vue_options_api_component_is_not_reported(tmp_path):
    _write(tmp_path, "src/Legacy.vue", "<template><div/></template>\n<script>\nexport default {}\n</script>\n")

    assert FrontendAnalyzer().extract_entry_points(tmp_path) == []


def _composables(root: Path) -> list[tuple[str, int]]:
    eps = FrontendAnalyzer().extract_entry_points(root)
    return [(ep.name, ep.line_number) for ep in eps if ep.type == EntryPointType.COMPOSABLE]


def test_vue_use_functions_count_only_under_their_dedicated_dir(tmp_path):
    _write(tmp_path, "src/composables/useCounter.ts", "\nexport function useCounter() {}\n")
    _write(tmp_path, "src/utils/useHelper.js", "export function useHelper() {}\n")

    assert _composables(tmp_path) == [("useCounter", 2)]


@pytest.mark.xfail(
    strict=True,
    reason="bug (#50): the composables-dir check matches the absolute path, so a parent dir named composables counts",
)
def test_vue_composable_dir_check_ignores_directories_above_the_project(tmp_path):
    project = tmp_path / "composables-demo"
    _write(project, "src/utils/useHelper.js", "export function useHelper() {}\n")

    assert _composables(project) == []


# ── Angular ───────────────────────────────────────────────────────────────────


def test_angular_component_reports_selector_and_inputs(tmp_path):
    _write(
        tmp_path,
        "src/app/hero.component.ts",
        "@Component({\n  selector: 'app-hero',\n  templateUrl: './hero.html'\n})\n"
        "export class HeroComponent {\n  @Input() hero: Hero;\n  @Input() size: number;\n}\n",
    )

    eps = _by_name(FrontendAnalyzer().extract_entry_points(tmp_path))

    hero = eps["app-hero"]
    assert hero.framework == "angular"
    assert [(p.name, p.data_type, p.param_type, p.required) for p in hero.params] == [
        ("hero", "hero", "input", False),
        ("size", "number", "input", False),
    ]


def test_parse_tests_returns_no_tests(tmp_path):
    assert FrontendAnalyzer().parse_tests(tmp_path) == []


# ── generate_scenarios ────────────────────────────────────────────────────────


def test_component_with_required_prop_gets_error_scenario():
    ep = EntryPoint(EntryPointType.COMPONENT, "Button", [Parameter("label", "prop", "string", True)], "B.tsx", 1)

    scenarios = FrontendAnalyzer().generate_scenarios([ep])

    assert [s.scenario_type for s in scenarios] == ["happy_path", "edge_case", "error"]
    assert scenarios[0].input_combination == {"props": {"label": "valid_value"}}
    assert scenarios[2].expected_output == 1
    assert all(s.method_name == "RENDER" for s in scenarios)


def test_component_with_only_optional_props_gets_no_error_scenario():
    ep = EntryPoint(EntryPointType.COMPONENT, "Icon", [Parameter("size", "prop", "number", False)], "I.tsx", 1)

    types = [s.scenario_type for s in FrontendAnalyzer().generate_scenarios([ep])]

    assert types == ["happy_path", "edge_case"]


def test_route_gets_navigation_scenarios_and_hook_gets_none():
    route = EntryPoint(EntryPointType.ROUTE, "/home", [], "App.tsx", 1)
    hook = EntryPoint(EntryPointType.HOOK, "useAuth", [], "useAuth.tsx", 1)

    scenarios = FrontendAnalyzer().generate_scenarios([route, hook])

    assert [(s.endpoint, s.method_name, s.scenario_type, s.expected_output) for s in scenarios] == [
        ("/home", "NAVIGATE", "happy_path", 0),
        ("/home", "NAVIGATE", "error", 1),
    ]
