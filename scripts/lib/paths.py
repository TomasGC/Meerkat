#!/usr/bin/env python3
"""Where this checkout lives, resolved from this file instead of ~/.claude (#2).

Two roots, one rule:
- CHECKOUT holds code and test data (scripts, agents, committed config templates, fixtures). It is always the
  checkout this module was imported from, so a clone, a worktree or a CI runner uses its own files.
- user_root() holds the user's own data: local configs, integration profiles, agent caches. It is CHECKOUT
  unless MEERKAT_HOME points elsewhere, e.g. a second clone sharing the configs of the main install.
  Read on every call, so a test or subprocess can set it after import.
"""

import os
from pathlib import Path

ENV_VAR = "MEERKAT_HOME"

CHECKOUT = Path(__file__).resolve().parents[2]
SCRIPTS = CHECKOUT / "scripts"
AGENTS = CHECKOUT / "agents"
FIXTURES = CHECKOUT / "fixtures"
CONFIGS = CHECKOUT / "configs"


def user_root() -> Path:
    """Root of the user's data: MEERKAT_HOME if set, else the checkout."""
    override = os.environ.get(ENV_VAR)
    return Path(override).expanduser().resolve() if override else CHECKOUT


def user_configs() -> Path:
    return user_root() / "configs"
