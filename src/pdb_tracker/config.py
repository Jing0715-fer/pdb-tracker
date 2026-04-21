"""PDB Tracker configuration — loaded from environment variables with sensible defaults.

Priority: explicit env vars > .env file > hardcoded defaults
"""

import os
import shutil
from pathlib import Path
from typing import Optional

# ─── Base directories ──────────────────────────────────────────────────────────

def _get_data_dir() -> Path:
    """Top-level data directory. Can be overridden via PDB_DATA_DIR env var."""
    if os.getenv("PDB_DATA_DIR"):
        return Path(os.getenv("PDB_DATA_DIR"))
    # Fallback to ~/.pdb-tracker/ (install.sh default)
    return Path.home() / ".pdb-tracker"


DATA_DIR: Path = _get_data_dir()

# ─── Database ─────────────────────────────────────────────────────────────────

DB_NAME: str = os.getenv("PDB_DB_NAME", "pdb_tracker.db")


def get_db_path() -> Path:
    """Path to the main SQLite database."""
    db_dir = Path(os.getenv("PDB_DB_DIR", str(DATA_DIR / "data")))
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / DB_NAME


# ─── Weekly reports ───────────────────────────────────────────────────────────

def get_weekly_reports_dir() -> Path:
    """Directory where weekly .md report files are stored."""
    return Path(os.getenv("PDB_WEEKLY_DIR", str(DATA_DIR / "weekly_reports")))


def get_weekly_summaries_dir() -> Path:
    """Directory where weekly summary .md files are stored (for migration)."""
    return Path(os.getenv("PDB_WEEKLY_SUMMARIES_DIR", str(DATA_DIR / "weekly_reports" / "summaries")))


# ─── Evaluation data ─────────────────────────────────────────────────────────

def get_evaluations_dir() -> Path:
    """Directory where evaluation JSON and .md report files are stored."""
    return Path(os.getenv("PDB_EVAL_DIR", str(DATA_DIR / "evaluations")))


# ─── Web UI runtime ─────────────────────────────────────────────────────────

def get_script_dir() -> Path:
    """Runtime directory for the Web UI's generated JS and copied HTML.

    Uses a persistent location under DATA_DIR so files survive restarts.
    """
    script_dir = Path(os.getenv("PDB_SCRIPT_DIR", str(DATA_DIR / "web_scripts")))
    script_dir.mkdir(parents=True, exist_ok=True)
    return script_dir


# ─── Web server ─────────────────────────────────────────────────────────────

WEB_HOST: str = os.getenv("PDB_WEB_HOST", "0.0.0.0")
WEB_PORT: int = int(os.getenv("PDB_WEB_PORT", "5555"))
WEB_DEBUG: bool = os.getenv("PDB_WEB_DEBUG", "").lower() in ("1", "true", "yes")


# ─── Cache ───────────────────────────────────────────────────────────────────

CACHE_DIR: Path = DATA_DIR / "cache"
PDB_CACHE_DIR: Path = CACHE_DIR / "pdb"
UNIPROT_CACHE_DIR: Path = CACHE_DIR / "uniprot"


def ensure_dirs() -> None:
    """Create all required directories. Called once at startup."""
    for d in [DATA_DIR, PDB_CACHE_DIR, UNIPROT_CACHE_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    get_weekly_reports_dir().mkdir(parents=True, exist_ok=True)
    get_evaluations_dir().mkdir(parents=True, exist_ok=True)
    get_script_dir().mkdir(parents=True, exist_ok=True)
