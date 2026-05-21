"""Runtime configuration for the Zenlo audit harness."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# NHANES XPT directory — override with ZENLO_AUDIT_DATA env var.
DATA_DIR: Path = Path(
    os.environ.get("ZENLO_AUDIT_DATA", PROJECT_ROOT / "data" / "nhanes")
).expanduser().resolve()

OUTPUT_DIR: Path = Path(
    os.environ.get("ZENLO_AUDIT_OUTPUT", PROJECT_ROOT / "output")
).expanduser().resolve()

# Ensure output directory exists at import (safe for CLI).
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
