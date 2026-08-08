from pathlib import Path

import pytest

from src.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(profile_dir=tmp_path, pause_min_seconds=0, pause_max_seconds=0)
