#!/usr/bin/env python3
"""
Switch integration profile.

Switch between different integration profiles.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from common.cli.base import BaseCLIScript
from common.integrations import (
    get_profile_detection_info,
    list_profiles,
    load_integrations,
    switch_profile,
    validate_profile
)


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
        parser.add_argument(
            "--status",
            "-s",
            action="store_true",
            help="Show detailed status (profile, detection source, providers)"
        )
        parser.add_argument(
            "--create",
            "-c",
            metavar="NAME",
            help="Create a new profile interactively"
        )
        parser.add_argument(
            "--validate",
            "-v",
            metavar="NAME",
            help="Validate a profile JSON file"
        )

    def execute(self, args) -> dict[str, Any]:
        """Execute profile switch."""
        integrations_dir = Path.home() / ".claude" / "integrations"

        if not integrations_dir.exists():
            return {
                "success": False,
                "error": "integrations/ directory not found in ~/.claude/"
            }

        # Validate profile
        if args.validate:
            profile_path = integrations_dir / f"{args.validate}.json"
            errors = validate_profile(profile_path)

            if errors:
                return {
                    "success": False,
                    "profile": args.validate,
                    "errors": errors
                }
            else:
                return {
                    "success": True,
                    "profile": args.validate,
                    "message": "Profile is valid"
                }

        # Create profile
        if args.create:
            profile_name = args.create
            profile_path = integrations_dir / f"{profile_name}.json"

            if profile_path.exists():
                return {
                    "success": False,
                    "error": f"Profile '{profile_name}' already exists"
                }

            # Interactive creation (basic template)
            template = {
                "name": f"{profile_name.capitalize()} Profile",
                "vcs": {
                    "provider": "github",
                    "url": "https://github.com",
                    "api_url": "https://api.github.com"
                },
                "ci": {
                    "provider": "github-actions"
                },
                "docs": {
                    "provider": "github-pages"
                },
                "issues": {
                    "provider": "github",
                    "issue_format": r"#(\d+)"
                }
            }

            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2)

            return {
                "success": True,
                "profile": profile_name,
                "path": str(profile_path),
                "message": f"Created profile template at {profile_path}. Edit it to customize."
            }

        # List profiles
        if args.list:
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

        # Show detailed status
        if args.status:
            detection_info = get_profile_detection_info()
            current = load_integrations()

            return {
                "success": True,
                "active_profile": current.profile_name,
                "detection_source": detection_info["detection_source"],
                "detection_details": detection_info["details"],
                "cwd": detection_info["cwd"],
                "vcs_provider": current.vcs_provider,
                "vcs_url": current.vcs_url,
                "ci_provider": current.ci_provider,
                "docs_provider": current.docs_provider,
                "issues_provider": current.issues_provider,
                "issue_format": current.issue_format
            }

        # Show current profile (brief)
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
