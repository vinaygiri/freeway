from __future__ import annotations

from api.data_governor import DataGovernor
from config.settings import Settings


def test_inactive_by_default_allows_everything():
    governor = DataGovernor()
    assert governor.active is False
    assert governor.allowed("gemini") is True
    assert governor.reason("gemini") is None


def test_require_local_only_blocks_non_local():
    governor = DataGovernor(require_local_only=True)
    assert governor.active is True
    assert governor.allowed("ollama") is True  # local
    assert governor.reason("nvidia_nim") == "local_only"


def test_require_no_training_blocks_trainers_and_unknowns():
    governor = DataGovernor(require_no_training=True)
    assert governor.reason("gemini") == "training"  # known trainer
    assert governor.reason("nvidia_nim") == "training"  # unknown -> conservative
    assert governor.allowed("lmstudio") is True  # local -> trains=False


def test_allowed_regions_blocks_unknown_and_mismatched():
    governor = DataGovernor(allowed_regions=["local"])
    assert governor.allowed("ollama") is True  # region "local"
    assert governor.reason("nvidia_nim") == "region"  # unknown region
    assert governor.reason("gemini") == "region"  # region "global" not allowed


def test_from_settings_reads_flags():
    settings = Settings()
    settings.require_local_only = True
    governor = DataGovernor.from_settings(settings)
    assert governor.active is True
    assert governor.reason("nvidia_nim") == "local_only"
