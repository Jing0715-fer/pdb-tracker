"""PDB Tracker - Protein Structure Data Management and Evaluation Platform

A comprehensive platform for managing protein structure data, generating weekly reports,
and evaluating target feasibility for structural biology projects.

Main Components:
    - weekly: Weekly PDB structure report generation
    - evaluation: Protein target structure feasibility evaluation
    - web: Interactive Web UI for data visualization
    - core: Core data fetching and database management

Example:
    >>> from pdb_tracker.weekly import WeeklyReportGenerator
    >>> from pdb_tracker.evaluation import TargetEvaluator
    >>> 
    >>> # Generate weekly report
    >>> generator = WeeklyReportGenerator(db_path="pdb.db", output_dir="reports")
    >>> report = generator.generate_report("2024-W01")
    >>>
    >>> # Evaluate target
    >>> evaluator = TargetEvaluator(db_path="pdb.db", output_dir="evaluations")
    >>> report = evaluator.evaluate("P04637")

See Also:
    GitHub: https://github.com/Jing0715-fer/pdb-tracker
    Documentation: https://github.com/Jing0715-fer/pdb-tracker#readme
"""

__version__ = "1.0.0"
__author__ = "Jing0715"
__email__ = "your.email@example.com"
__license__ = "MIT"

from pathlib import Path

# Package paths
PACKAGE_ROOT = Path(__file__).parent.parent
DEFAULT_DB_PATH = Path.home() / ".pdb-tracker" / "pdb_tracker.db"
DEFAULT_CACHE_DIR = Path.home() / ".pdb-tracker" / "cache"
DEFAULT_OUTPUT_DIR = Path.home() / "Documents" / "PDB_Tracker"

# Ensure directories exist
DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

__all__ = [
    "__version__",
    "PACKAGE_ROOT",
    "DEFAULT_DB_PATH",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_OUTPUT_DIR",
]
