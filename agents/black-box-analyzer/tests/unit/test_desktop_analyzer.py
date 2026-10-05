#!/usr/bin/env python3
"""Tests for analyzers/desktop_analyzer.py: window and event-handler extraction per toolkit."""

import pytest
from analyzers.desktop_analyzer import DesktopAnalyzer
from bba.models import EntryPoint, EntryPointType, Language, ProjectInfo, ProjectType


def _info(*types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.UNKNOWN,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=".",
        project_types=list(types),
    )


def _write(root, name: str, content: str):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _summary(entry_points):
    return sorted((ep.type.value, ep.name, ep.framework, ep.line_number) for ep in entry_points)


@pytest.mark.parametrize(
    "project_type", [ProjectType.DESKTOP_WINDOWS, ProjectType.DESKTOP_MAC, ProjectType.DESKTOP_LINUX]
)
def test_can_analyze_accepts_every_desktop_platform(project_type):
    assert DesktopAnalyzer().can_analyze(_info(project_type))


def test_can_analyze_rejects_non_desktop_project():
    assert not DesktopAnalyzer().can_analyze(_info(ProjectType.REST_API))


def test_extracts_wpf_windows_click_handlers_and_winforms_forms(tmp_path):
    _write(
        tmp_path,
        "MainWindow.xaml",
        '<Window x:Class="Shop.Views.MainWindow"\n        Title="Main">\n</Window>\n',
    )
    _write(tmp_path, "Empty.xaml", "")
    _write(
        tmp_path,
        "MainWindow.xaml.cs",
        "public partial class MainWindow {\n    private void Save_Click(object s, EventArgs e) {}\n}\n"
        "public class SettingsForm : Form {}\n",
    )
    _write(tmp_path, "Empty.cs", "")

    entry_points = DesktopAnalyzer().extract_entry_points(tmp_path)

    assert _summary(entry_points) == [
        ("event_handler", "Save_Click", "wpf", 2),
        ("window", "MainWindow", "wpf", 1),
        ("window", "SettingsForm", "winforms", 4),
    ]
    window = next(ep for ep in entry_points if ep.framework == "wpf" and ep.type == EntryPointType.WINDOW)
    assert window.metadata == {"class": "Shop.Views.MainWindow"}
    assert window.file_path == "MainWindow.xaml"


def test_extracts_appkit_window_controllers_and_ibactions(tmp_path):
    _write(
        tmp_path,
        "PrefsWindow.swift",
        "import Cocoa\nclass PrefsWindow: NSWindowController {\n    @IBAction func savePressed(_ s: Any) {}\n}\n",
    )
    _write(tmp_path, "empty.m", "")

    entry_points = DesktopAnalyzer().extract_entry_points(tmp_path)

    assert _summary(entry_points) == [
        ("event_handler", "savePressed", "appkit", 3),
        ("window", "PrefsWindow", "appkit", 2),
    ]


def test_extracts_qt_main_window_and_only_methods_declared_after_slots(tmp_path):
    _write(
        tmp_path,
        "mainwindow.h",
        "class MainWindow : public QMainWindow {\n"
        "public:\n    void helper();\n"
        "private slots:\n    void onOpen();\n};\n",
    )
    _write(tmp_path, "empty.cpp", "")

    entry_points = DesktopAnalyzer().extract_entry_points(tmp_path)

    assert _summary(entry_points) == [
        ("event_handler", "onOpen", "qt", 5),
        ("window", "MainWindow", "qt", 1),
    ]


def test_extracts_gtk_windows_from_python(tmp_path):
    _write(tmp_path, "app.py", "import gi\n\nclass AppWindow(Gtk.Window):\n    pass\n")
    _write(tmp_path, "empty.py", "")

    entry_points = DesktopAnalyzer().extract_entry_points(tmp_path)

    assert _summary(entry_points) == [("window", "AppWindow", "gtk", 3)]


def test_project_without_desktop_code_has_no_entry_points(tmp_path):
    _write(tmp_path, "README.md", "hello\n")

    assert DesktopAnalyzer().extract_entry_points(tmp_path) == []


def test_parse_tests_returns_no_tests(tmp_path):
    assert DesktopAnalyzer().parse_tests(tmp_path) == []


def _entry(entry_type: EntryPointType, name: str) -> EntryPoint:
    return EntryPoint(type=entry_type, name=name, params=[], file_path="f", line_number=1)


def test_window_gets_four_lifecycle_scenarios():
    scenarios = DesktopAnalyzer().generate_scenarios([_entry(EntryPointType.WINDOW, "Main")])

    assert [(s.input_combination["action"], s.scenario_type) for s in scenarios] == [
        ("open", "happy_path"),
        ("close", "happy_path"),
        ("minimize", "edge_case"),
        ("maximize", "edge_case"),
    ]
    assert {(s.endpoint, s.method) for s in scenarios} == {("Main", "WINDOW")}


def test_event_handler_gets_three_trigger_scenarios():
    scenarios = DesktopAnalyzer().generate_scenarios([_entry(EntryPointType.EVENT_HANDLER, "Save_Click")])

    assert [(s.input_combination["trigger"], s.scenario_type) for s in scenarios] == [
        ("click", "happy_path"),
        ("double_click", "edge_case"),
        ("rapid_clicks", "edge_case"),
    ]
    assert scenarios[2].description == "Rapid clicks on Save_Click"


def test_other_entry_point_types_get_no_scenarios():
    assert DesktopAnalyzer().generate_scenarios([_entry(EntryPointType.COMPONENT, "Button")]) == []
