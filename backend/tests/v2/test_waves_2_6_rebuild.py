"""Contract tests for the Waves 2-6 module rebuild.

Each rebuilt module must: register, expose a Pydantic output_schema, have a playbook that
loads, and declare only `composes` deps that are themselves registered. Add a module's name
to REBUILT as it's built. Structural contract only — no live calls, no fabricated data.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from core.playbook import PlaybookLoader
from core.registry import V2_MODULE_REGISTRY, register_all_v2_modules

register_all_v2_modules()

# Rebuilt Waves 2-6 modules — extended as each is built.
REBUILT = [
    "synth-business-case",  # W5
    "synth-sales-plays",  # W5
    "campaign-abx",  # W5
    "audit-report",  # W6
]


@pytest.mark.parametrize("name", REBUILT)
def test_module_registered(name: str) -> None:
    assert name in V2_MODULE_REGISTRY, f"{name} not registered"


@pytest.mark.parametrize("name", REBUILT)
def test_output_schema_is_pydantic_model(name: str) -> None:
    handle = V2_MODULE_REGISTRY[name]
    assert isinstance(handle.output_schema, type)
    assert issubclass(handle.output_schema, BaseModel)


@pytest.mark.parametrize("name", REBUILT)
def test_playbook_loads(name: str) -> None:
    handle = V2_MODULE_REGISTRY[name]
    assert handle.playbook_path.exists(), f"{name} playbook missing"
    meta, body = PlaybookLoader().load(handle.playbook_path)
    assert meta.name == name
    assert body.strip()


@pytest.mark.parametrize("name", REBUILT)
def test_composes_reference_registered_modules(name: str) -> None:
    handle = V2_MODULE_REGISTRY[name]
    for dep in handle.config.composes:
        assert dep in V2_MODULE_REGISTRY, f"{name} composes unknown module: {dep}"


@pytest.mark.parametrize("name", REBUILT)
def test_playbook_upstream_tokens_use_underscores(name: str) -> None:
    """Guard the latent bug: {upstream_x-y} (hyphen) never substitutes — only \\w matches."""
    import re

    handle = V2_MODULE_REGISTRY[name]
    _, body = PlaybookLoader().load(handle.playbook_path)
    broken = re.findall(r"\{upstream_[a-z]+-[a-z-]+\}", body)
    assert not broken, f"{name} playbook has non-substituting hyphen upstream tokens: {broken}"
