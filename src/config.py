"""Validated runtime settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _number(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class Settings:
    profile_dir: Path
    wait_seconds: int = 20
    pause_min_seconds: float = 0.4
    pause_max_seconds: float = 0.9
    stable_rounds: int = 4
    load_timeout_seconds: int = 4
    surface_recovery_attempts: int = 3

    @classmethod
    def from_env(cls) -> "Settings":
        default_profile = Path.home() / "selenium_instagram_profile"
        pause_min = _number("PAUSE_MIN_SECONDS", 0.4, 0.0, 30.0)
        pause_max = _number("PAUSE_MAX_SECONDS", 0.9, 0.0, 30.0)
        if pause_min > pause_max:
            raise ValueError("PAUSE_MIN_SECONDS cannot exceed PAUSE_MAX_SECONDS")
        return cls(
            profile_dir=Path(os.getenv("IG_PROFILE_DIR", str(default_profile))).expanduser(),
            wait_seconds=_integer("SELENIUM_WAIT_SECONDS", 20, 5, 120),
            pause_min_seconds=pause_min,
            pause_max_seconds=pause_max,
            stable_rounds=_integer("STABLE_ROUNDS", 4, 1, 20),
            load_timeout_seconds=_integer("LOAD_TIMEOUT_SECONDS", 4, 1, 30),
            surface_recovery_attempts=_integer("SURFACE_RECOVERY_ATTEMPTS", 3, 1, 10),
        )
