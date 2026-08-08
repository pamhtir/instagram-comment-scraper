"""Beginner-friendly environment check; does not contact Instagram."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main() -> int:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    supported = (3, 11) <= sys.version_info[:2] < (3, 14)
    required = ("pandas", "selenium", "openpyxl", "dotenv", "pytest")
    missing = [name for name in required if importlib.util.find_spec(name) is None]

    print(f"Python: {version}")
    print(f"Executable: {Path(sys.executable)}")
    print(f"Virtual environment: {'yes' if in_venv else 'NO'}")
    print(f"Supported Python: {'yes' if supported else 'NO (requires 3.11-3.13)'}")
    print(f"Dependencies: {'ready' if not missing else 'missing ' + ', '.join(missing)}")
    if supported and in_venv and not missing:
        print("Environment ready: scraping and tests can run.")
        return 0
    print("Fix: py -3.13 -m venv .venv")
    print("Then in Git Bash: source .venv/Scripts/activate")
    print("Then: python -m pip install -r requirements.txt")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
