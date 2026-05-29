#!/usr/bin/env python3
"""
Refactor sys.path.insert to relative imports for proper Python package structure.

Eliminates 14 occurrences of sys.path.insert(0, ...) and converts to relative imports.
"""

import re
from pathlib import Path


def refactor_analyzer(file_path: Path) -> bool:
    """
    Refactor analyzer file to use relative imports.

    Changes:
    - Remove sys.path.insert boilerplate
    - Convert 'from common.X import Y' to 'from ..common.X import Y'

    Args:
        file_path: Path to analyzer file

    Returns:
        True if file was modified
    """
    content = file_path.read_text(encoding='utf-8')
    original = content

    # Pattern 1: Remove sys.path.insert block
    sys_path_pattern = r"""import sys
from pathlib import Path

# Add parent directory to path
sys\.path\.insert\(0, str\(Path\(__file__\)\.parent\.parent\)\)

"""
    content = re.sub(sys_path_pattern, "", content)

    # Alternative pattern (without exact comments)
    sys_path_pattern2 = r"""import sys.*?sys\.path\.insert\([^)]+\)\n+"""
    content = re.sub(sys_path_pattern2, "", content, flags=re.DOTALL)

    # Pattern 2: Convert absolute imports to relative
    content = re.sub(r"^from common\.", "from ..common.", content, flags=re.MULTILINE)

    # Pattern 3: Convert analyzer imports (for fullstack_analyzer.py)
    content = re.sub(r"^from analyzers\.", "from .", content, flags=re.MULTILINE)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return True
    return False


def refactor_subdirectory_analyzer(file_path: Path) -> bool:
    """
    Refactor analyzer in subdirectory (blockchain/, event_driven/).

    Changes:
    - Remove sys.path.insert boilerplate
    - Convert 'from common.X' to 'from ...common.X' (three levels up)
    - Convert 'from analyzers.Y' to 'from ..Y' (two levels up)

    Args:
        file_path: Path to analyzer file in subdirectory

    Returns:
        True if file was modified
    """
    content = file_path.read_text(encoding='utf-8')
    original = content

    # Pattern 1: Remove sys.path.insert block (parent.parent.parent for subdirs)
    sys_path_pattern = r"""import sys.*?sys\.path\.insert\([^)]+\)\n+"""
    content = re.sub(sys_path_pattern, "", content, flags=re.DOTALL)

    # Pattern 2: Convert common imports (three levels up)
    content = re.sub(r"^from common\.", "from ...common.", content, flags=re.MULTILINE)

    # Pattern 3: Convert analyzer imports (two levels up)
    content = re.sub(r"^from analyzers\.base_analyzer", "from ..base_analyzer", content, flags=re.MULTILINE)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return True
    return False


def main():
    """Main entry point."""
    scripts_dir = Path(__file__).parent
    analyzers_dir = scripts_dir / "analyzers"

    refactored = 0

    # Refactor main analyzers
    main_analyzers = [
        "base_analyzer.py",
        "api_analyzer.py",
        "cli_analyzer.py",
        "desktop_analyzer.py",
        "frontend_analyzer.py",
        "fullstack_analyzer.py",
        "llm_analyzer.py",
        "mobile_analyzer.py",
        "sql_analyzer.py",
    ]

    print("Refactoring main analyzers...")
    for filename in main_analyzers:
        file_path = analyzers_dir / filename
        if file_path.exists():
            if refactor_analyzer(file_path):
                print(f"  OK {filename}")
                refactored += 1

    # Refactor blockchain subdirectory
    blockchain_dir = analyzers_dir / "blockchain"
    print("\nRefactoring blockchain analyzers...")
    for file_path in blockchain_dir.glob("*.py"):
        if file_path.name != "__init__.py":
            if refactor_subdirectory_analyzer(file_path):
                print(f"  OK blockchain/{file_path.name}")
                refactored += 1

    # Refactor event_driven subdirectory
    event_driven_dir = analyzers_dir / "event_driven"
    print("\nRefactoring event_driven analyzers...")
    for file_path in event_driven_dir.glob("*.py"):
        if file_path.name != "__init__.py":
            if refactor_subdirectory_analyzer(file_path):
                print(f"  OK event_driven/{file_path.name}")
                refactored += 1

    print(f"\nRefactored {refactored} files")
    print("\nRemoved sys.path.insert from all analyzers")


if __name__ == "__main__":
    main()
