#!/usr/bin/env python3
"""Tests for analyzers/mobile_analyzer.py: Android/iOS extraction and scenario generation."""

from pathlib import Path

from analyzers.mobile_analyzer import MobileAnalyzer
from bba.models import EntryPoint, EntryPointType, Language, ProjectInfo, ProjectType


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _info(root: Path, *types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.SWIFT,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=str(root),
        project_types=list(types),
        primary_type=types[0] if types else ProjectType.UNKNOWN,
    )


def _by_type(entry_points: list[EntryPoint], ep_type: EntryPointType) -> list[str]:
    return [ep.name for ep in entry_points if ep.type == ep_type]


# ── can_analyze ───────────────────────────────────────────────────────────────


def test_can_analyze_accepts_android_and_ios(tmp_path):
    analyzer = MobileAnalyzer()

    assert analyzer.can_analyze(_info(tmp_path, ProjectType.ANDROID_APP))
    assert analyzer.can_analyze(_info(tmp_path, ProjectType.IOS_APP))
    assert not analyzer.can_analyze(_info(tmp_path, ProjectType.CLI_APP))


# ── Android ───────────────────────────────────────────────────────────────────


def test_android_fragment_and_composable_are_extracted(tmp_path):
    _write(
        tmp_path,
        "app/Home.kt",
        "class HomeFragment : Fragment() {}\n\n@Composable fun Greeting(name: String) {}\n",
    )

    eps = MobileAnalyzer().extract_entry_points(tmp_path)

    assert _by_type(eps, EntryPointType.FRAGMENT) == ["HomeFragment"]
    composable = next(ep for ep in eps if ep.type == EntryPointType.COMPONENT)
    assert (composable.name, composable.framework, composable.line_number) == ("Greeting", "compose", 3)


def test_android_lifecycle_methods_stay_within_their_activity(tmp_path):
    _write(
        tmp_path,
        "app/Main.kt",
        "class MainActivity : AppCompatActivity() {\n"
        "    override fun onCreate(b: Bundle?) {}\n"
        "    override fun onPause() {}\n"
        "}\n"
        "class Other {\n"
        "    override fun onDestroy() {}\n"
        "}\n",
    )

    eps = MobileAnalyzer().extract_entry_points(tmp_path)

    lifecycle = [ep for ep in eps if ep.type == EntryPointType.LIFECYCLE_METHOD]
    assert [(ep.name, ep.line_number) for ep in lifecycle] == [
        ("MainActivity.onCreate", 2),
        ("MainActivity.onPause", 3),
    ]
    assert lifecycle[0].metadata == {"parent": "MainActivity", "lifecycle_stage": "onCreate"}


def test_android_click_handlers_become_ui_handlers(tmp_path):
    _write(
        tmp_path,
        "app/Main.kt",
        "fun onSaveClicked(view: View) {}\nsaveButton.setOnClickListener { save() }\n",
    )

    handlers = [ep for ep in MobileAnalyzer().extract_entry_points(tmp_path) if ep.type == EntryPointType.UI_HANDLER]

    assert [(h.name, h.line_number, h.metadata["handler_type"]) for h in handlers] == [
        ("onSaveClicked", 1, "on_click_attribute"),
        ("saveButton", 2, "click_listener"),
    ]
    assert [(p.name, p.data_type) for p in handlers[0].params] == [("view", "View")]


def test_empty_mobile_sources_are_skipped(tmp_path):
    for name in ("A.kt", "B.java", "C.swift", "D.m"):
        _write(tmp_path, name, "")

    assert MobileAnalyzer().extract_entry_points(tmp_path) == []


# ── iOS ───────────────────────────────────────────────────────────────────────


def test_ios_view_controller_with_lifecycle_and_ibaction(tmp_path):
    _write(
        tmp_path,
        "App/LoginViewController.swift",
        "class LoginViewController: UIViewController {\n"
        "    override func viewDidLoad() {}\n"
        "    override func viewWillAppear(_ animated: Bool) {}\n"
        "    @IBAction func loginTapped(_ sender: Any) {}\n"
        "}\n"
        "class Helper {\n"
        "    override func viewDidDisappear() {}\n"
        "}\n",
    )

    eps = MobileAnalyzer().extract_entry_points(tmp_path)

    assert _by_type(eps, EntryPointType.VIEW_CONTROLLER) == ["LoginViewController"]
    assert _by_type(eps, EntryPointType.LIFECYCLE_METHOD) == [
        "LoginViewController.viewDidLoad",
        "LoginViewController.viewWillAppear",
    ]
    action = next(ep for ep in eps if ep.type == EntryPointType.UI_HANDLER)
    assert (action.name, action.framework, action.line_number) == ("loginTapped", "uikit", 4)
    assert action.metadata == {"handler_type": "ibaction"}


def test_swiftui_view_is_extracted(tmp_path):
    _write(tmp_path, "App/ContentView.swift", "import SwiftUI\n\nstruct ContentView: View {\n}\n")

    eps = MobileAnalyzer().extract_entry_points(tmp_path)

    view = next(ep for ep in eps if ep.type == EntryPointType.SWIFTUI_VIEW)
    assert (view.name, view.framework, view.line_number) == ("ContentView", "swiftui", 3)


def test_parse_tests_returns_no_tests(tmp_path):
    assert MobileAnalyzer().parse_tests(tmp_path) == []


# ── generate_scenarios ────────────────────────────────────────────────────────


def test_lifecycle_method_gets_normal_and_rapid_transition_scenarios():
    ep = EntryPoint(
        EntryPointType.LIFECYCLE_METHOD, "Main.onResume", [], "M.kt", 1, metadata={"lifecycle_stage": "onResume"}
    )

    scenarios = MobileAnalyzer().generate_scenarios([ep])

    assert [(s.scenario_type, s.input_combination) for s in scenarios] == [
        ("happy_path", {"state": "onResume"}),
        ("edge_case", {"state": "onResume_rapid"}),
    ]


def test_lifecycle_method_without_stage_metadata_uses_unknown():
    ep = EntryPoint(EntryPointType.LIFECYCLE_METHOD, "Main.x", [], "M.kt", 1)

    scenarios = MobileAnalyzer().generate_scenarios([ep])

    assert scenarios[0].input_combination == {"state": "unknown"}


def test_screen_entry_points_get_init_and_restore_scenarios():
    eps = [
        EntryPoint(t, f"S{i}", [], "S.kt", 1)
        for i, t in enumerate(
            [
                EntryPointType.ACTIVITY,
                EntryPointType.FRAGMENT,
                EntryPointType.VIEW_CONTROLLER,
                EntryPointType.SWIFTUI_VIEW,
            ]
        )
    ]

    scenarios = MobileAnalyzer().generate_scenarios(eps)

    assert len(scenarios) == 8
    assert {s.method_name for s in scenarios} == {"INIT"}
    assert [s.input_combination["init_type"] for s in scenarios[:2]] == ["normal", "restore_state"]


def test_ui_handler_gets_three_gesture_scenarios_and_component_gets_none():
    handler = EntryPoint(EntryPointType.UI_HANDLER, "onSave", [], "M.kt", 1)
    composable = EntryPoint(EntryPointType.COMPONENT, "Greeting", [], "M.kt", 2)

    scenarios = MobileAnalyzer().generate_scenarios([handler, composable])

    assert [s.input_combination["gesture"] for s in scenarios] == ["tap", "long_press", "double_tap"]
    assert {s.endpoint for s in scenarios} == {"onSave"}
