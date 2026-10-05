"""lib.paths — the checkout root, and the guarantee that nothing is imported from another checkout (#2)."""

import sys
from pathlib import Path

from lib import paths
from lib.config import language_config, model_config
from lib.testing import golden

# Top-level packages this repository owns; any of them loaded from elsewhere means a second checkout leaked in.
_OWN_PACKAGES = ("lib", "cli", "cca", "ssa", "bba", "search_tech")


def test_checkout_is_the_repo_holding_this_module():
    assert (paths.CHECKOUT / "scripts" / "lib" / "paths.py").samefile(paths.__file__)
    assert (paths.CHECKOUT / "pytest.ini").is_file()


def test_named_roots_sit_in_the_checkout():
    for root in (paths.SCRIPTS, paths.AGENTS, paths.FIXTURES, paths.CONFIGS):
        assert root.parent == paths.CHECKOUT
        assert root.is_dir()


def test_user_root_defaults_to_the_checkout(monkeypatch):
    monkeypatch.delenv(paths.ENV_VAR, raising=False)
    assert paths.user_root() == paths.CHECKOUT
    assert paths.user_configs() == paths.CHECKOUT / "configs"


def test_user_root_follows_meerkat_home_on_every_call(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.ENV_VAR, str(tmp_path))
    assert paths.user_root() == tmp_path.resolve()
    monkeypatch.setenv(paths.ENV_VAR, str(tmp_path / "other"))
    assert paths.user_configs() == (tmp_path / "other").resolve() / "configs"


def test_config_templates_and_golden_fixtures_come_from_the_checkout():
    assert language_config._TEMPLATE_PATH.parent == paths.CONFIGS
    assert model_config._TEMPLATE_PATH.parent == paths.CONFIGS
    assert golden.projects_root() == paths.FIXTURES / "projects"
    assert golden.agent_scripts_dir("cca") == paths.AGENTS / "clean-code-analyzer" / "scripts"


def test_no_own_package_is_loaded_from_another_checkout():
    """Every loaded module of this repository's packages lives under CHECKOUT.

    Before #2, agents put ~/.claude/scripts on sys.path, so a clone imported the installed lib instead of
    its own. In a full run every suite's modules are loaded by collection time, so this sees all of them.
    """
    checkout = paths.CHECKOUT.resolve()
    foreign = []
    for name, module in list(sys.modules.items()):
        if name.split(".")[0] not in _OWN_PACKAGES:
            continue
        origin = getattr(module, "__file__", None)
        if origin and not Path(origin).resolve().is_relative_to(checkout):
            foreign.append(f"{name}: {origin}")
    assert not foreign, "imported from outside this checkout:\n" + "\n".join(foreign)
