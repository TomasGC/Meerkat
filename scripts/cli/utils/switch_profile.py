#!/usr/bin/env python3
"""
Switch integration profile.

Switch between different integration profiles.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cli.base import BaseCLIScript
from common.integrations import list_profiles, load_integrations, switch_profile


class SwitchProfileScript(BaseCLIScript):
    """Switch integration profile."""

    def setup_parser(self, parser):
        """Add script-specific arguments."""
        parser.add_argument(
            "profile",
            nargs="?",
            help="Profile to switch to (leave empty to show current)"
        )
        parser.add_argument(
            "--list",
            "-l",
            action="store_true",
            help="List available profiles"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute profile switch."""
        integrations_dir = Path.home() / ".claude" / "integrations"

        if not integrations_dir.exists():
            return {
                "success": False,
                "error": "integrations/ directory not found in ~/.claude/"
            }

        # List profiles
        if args.list:
            import json

            profiles_list = list_profiles()
            current = load_integrations()

            profile_details = []
            for profile_name in profiles_list:
                try:
                    profile_config = load_integrations(profile=profile_name)
                    profile_details.append({
                        "name": profile_name,
                        "description": profile_name,
                        "vcs": profile_config.vcs_provider,
                        "ci": profile_config.ci_provider,
                        "docs": profile_config.docs_provider,
                        "issues": profile_config.issues_provider,
                        "is_active": profile_name == current.profile_name
                    })
                except Exception:
                    continue

            return {
                "success": True,
                "active_profile": current.profile_name,
                "profiles": profile_details
            }

        # Show current profile
        if not args.profile:
            current = load_integrations()

            return {
                "success": True,
                "active_profile": current.profile_name,
                "vcs_provider": current.vcs_provider,
                "ci_provider": current.ci_provider,
                "docs_provider": current.docs_provider,
                "issues_provider": current.issues_provider
            }

        # Switch profile
        try:
            switch_profile(args.profile)

            return {
                "success": True,
                "message": f"Switched to profile: {args.profile}",
                "active_profile": args.profile
            }

        except (ValueError, FileNotFoundError) as e:
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """CLI entry point."""
    from common.cli.base import create_cli_script
    create_cli_script(SwitchProfileScript)


if __name__ == "__main__":
    main()
