#!/usr/bin/env python3
"""Regenerate golden expected files for the fixture projects under replay.

Runs the agent's real pipeline over fixtures/projects/<project> of this checkout, with
every model call served from fixtures/golden/<project>/ai_responses/<agent>/,
and writes the result to fixtures/golden/<project>/expected/<agent>.json.

The script puts the chosen agent's scripts dir on sys.path itself, so it can
be launched from any directory, e.g.:

    cd ~/.claude/agents/clean-code-analyzer/scripts
    python ../../../scripts/cli/update_golden.py --agent cca

    cd ~/.claude/agents/security-safety-analyzer/scripts
    python ../../../scripts/cli/update_golden.py --agent ssa --project go_project

The output is a snapshot of whatever the code does today: read every record
before committing and confirm it is an issue the fixture deliberately contains.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.testing import golden  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", required=True, choices=sorted(golden.AGENTS))
    parser.add_argument("--project", default=None, help="Fixture project name (default: all)")
    args = parser.parse_args(argv)

    projects = [args.project] if args.project else golden.project_names()
    for project in projects:
        with tempfile.TemporaryDirectory() as cache:
            report = golden.run_agent(project, args.agent, cache_dir=Path(cache))
        record = golden.expected_record(project, args.agent, report)
        target = golden.expected_path(project, args.agent)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"[OK] {target}: {len(record['violations'])} violations, " f"reconciliation {record['reconciliation']}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
