"""Locate the kanban.md of the repository being worked on."""

from pathlib import Path

# Searched in every directory from the start up to the repository root.
_PROJECT_KANBAN = Path(".claude") / "contexts" / "kanban.md"
# Searched at the repository root only: Meerkat's layout, whose checkout is the .claude directory itself.
_ROOT_KANBAN = Path("contexts") / "kanban.md"

NOT_FOUND = "kanban.md not found in this repository (.claude/contexts/kanban.md, or contexts/kanban.md at its root)"


def _is_repository_root(directory: Path) -> bool:
    """True when git would treat ``directory`` as a work tree root: a ``.git`` directory holding ``HEAD``, or a
    worktree's ``.git`` file. A stray ``.git`` folder (some Windows tools leave one in the home directory) is not."""
    git = directory / ".git"
    if git.is_dir():
        return (git / "HEAD").exists()
    if git.is_file():
        return git.read_text(encoding="utf-8", errors="replace").startswith("gitdir:")
    return False


def find_kanban_file(start: Path | None = None) -> Path | None:
    """Return the kanban.md of the repository containing ``start`` (default: the current directory), or None.

    The search never leaves the repository: it stops at the repository root, so a project without a kanban cannot
    pick up an enclosing directory's, such as ``~/.claude``. Outside any repository, only ``start`` itself is searched.
    """
    start = (start or Path.cwd()).absolute()
    chain = [start, *start.parents]
    root = next((d for d in chain if _is_repository_root(d)), None)
    searched = chain[: chain.index(root) + 1] if root else [start]
    for directory in searched:
        candidate = directory / _PROJECT_KANBAN
        if candidate.exists():
            return candidate
    if root and (root / _ROOT_KANBAN).exists():
        return root / _ROOT_KANBAN
    return None
