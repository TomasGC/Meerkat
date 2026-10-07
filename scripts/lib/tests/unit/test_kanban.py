"""Tests for lib.kanban: the kanban lookup never leaves the current repository."""

from pathlib import Path

from lib.kanban import find_kanban_file


def _repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir()
    (path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    return path


def _kanban(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# KANBAN\n", encoding="utf-8")
    return path


def test_finds_project_kanban_in_the_start_directory(tmp_path):
    repo = _repo(tmp_path / "repo")
    kanban = _kanban(repo / ".claude" / "contexts" / "kanban.md")
    assert find_kanban_file(repo) == kanban


def test_finds_project_kanban_from_a_subdirectory(tmp_path):
    repo = _repo(tmp_path / "repo")
    kanban = _kanban(repo / ".claude" / "contexts" / "kanban.md")
    sub = repo / "src" / "deep"
    sub.mkdir(parents=True)
    assert find_kanban_file(sub) == kanban


def test_finds_contexts_kanban_at_the_repository_root(tmp_path):
    """Meerkat's layout: the checkout is the .claude directory, so contexts/ sits at its root."""
    repo = _repo(tmp_path / "meerkat")
    kanban = _kanban(repo / "contexts" / "kanban.md")
    sub = repo / "scripts"
    sub.mkdir()
    assert find_kanban_file(sub) == kanban


def test_project_layout_wins_over_the_root_layout(tmp_path):
    repo = _repo(tmp_path / "repo")
    _kanban(repo / "contexts" / "kanban.md")
    project = _kanban(repo / ".claude" / "contexts" / "kanban.md")
    assert find_kanban_file(repo) == project


def test_stops_at_the_repository_root(tmp_path):
    """A repository without a kanban must not pick up an enclosing directory's (e.g. ~/.claude's)."""
    _kanban(tmp_path / ".claude" / "contexts" / "kanban.md")
    inner = _repo(tmp_path / "projects" / "other")
    assert find_kanban_file(inner) is None


def test_a_worktree_git_file_marks_the_root(tmp_path):
    _kanban(tmp_path / ".claude" / "contexts" / "kanban.md")
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: /elsewhere/.git/worktrees/w\n", encoding="utf-8")
    assert find_kanban_file(worktree) is None


def test_outside_a_repository_only_the_start_directory_is_searched(tmp_path):
    kanban = _kanban(tmp_path / ".claude" / "contexts" / "kanban.md")
    sub = tmp_path / "sub"
    sub.mkdir()
    assert find_kanban_file(tmp_path) == kanban
    assert find_kanban_file(sub) is None


def test_a_stray_git_folder_is_not_a_repository_root(tmp_path):
    """A .git folder without HEAD (left by some Windows tools in the home directory) does not stop the search."""
    repo = _repo(tmp_path / "repo")
    kanban = _kanban(repo / ".claude" / "contexts" / "kanban.md")
    stray = repo / "home"
    (stray / ".git" / "info").mkdir(parents=True)
    assert find_kanban_file(stray) == kanban


def test_ignores_the_legacy_flat_layout(tmp_path):
    repo = _repo(tmp_path / "repo")
    _kanban(repo / ".claude" / "KANBAN.md")
    assert find_kanban_file(repo) is None


def test_defaults_to_the_current_directory(tmp_path, monkeypatch):
    repo = _repo(tmp_path / "repo")
    kanban = _kanban(repo / ".claude" / "contexts" / "kanban.md")
    monkeypatch.chdir(repo)
    assert find_kanban_file() == kanban
