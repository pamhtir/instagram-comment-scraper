import pytest

from src.config import Settings


def test_loads_valid_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("IG_PROFILE_DIR", str(tmp_path))
    monkeypatch.setenv("STABLE_ROUNDS", "3")
    assert Settings.from_env().stable_rounds == 3


def test_rejects_inverted_pause_range(monkeypatch):
    monkeypatch.setenv("PAUSE_MIN_SECONDS", "2")
    monkeypatch.setenv("PAUSE_MAX_SECONDS", "1")
    with pytest.raises(ValueError, match="cannot exceed"):
        Settings.from_env()


def test_rejects_invalid_wait(monkeypatch):
    monkeypatch.setenv("SELENIUM_WAIT_SECONDS", "fast")
    with pytest.raises(ValueError, match="must be an integer"):
        Settings.from_env()


def test_fast_default_load_timeout(monkeypatch):
    monkeypatch.delenv("LOAD_TIMEOUT_SECONDS", raising=False)
    assert Settings.from_env().load_timeout_seconds == 4
