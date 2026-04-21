#!/bin/bash
# PDB Tracker Installation Script
# Compatible with OpenClaw and Claude Code

set -e

echo "========================================"
echo "     PDB Tracker Installation"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ─── Python check ──────────────────────────────────────────────────────────────
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python 3.8+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# ─── Clone / cd ─────────────────────────────────────────────────────────────────
if [ ! -f "pyproject.toml" ]; then
    echo ""
    echo "Cloning repository..."
    git clone https://github.com/Jing0715-fer/pdb-tracker.git
    cd pdb-tracker
fi

# ─── Install package ───────────────────────────────────────────────────────────
echo ""
echo "Installing PDB Tracker..."
pip install -e ".[dev,web,llm]"

# ─── Create .env from example ──────────────────────────────────────────────────
CONFIG_DIR="${PDB_DATA_DIR:-$HOME/.pdb-tracker}"
ENV_FILE="$CONFIG_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    mkdir -p "$CONFIG_DIR"
    if [ -f ".env.example" ]; then
        cp .env.example "$ENV_FILE"
        echo -e "${GREEN}✓ Copied .env.example → $ENV_FILE${NC}"
    else
        cat > "$ENV_FILE" << 'ENV'
# PDB Tracker environment configuration
# All paths default to ~/.pdb-tracker/
# Override any variable below to customise locations

# Top-level data directory (default: ~/.pdb-tracker/)
# PDB_DATA_DIR=/custom/path

# SQLite database file name (default: pdb_tracker.db)
# PDB_DB_NAME=pdb_tracker.db

# Web UI host/port
# PDB_WEB_HOST=0.0.0.0
# PDB_WEB_PORT=5555
# PDB_WEB_DEBUG=false
ENV
        echo -e "${GREEN}✓ Created default .env at $ENV_FILE${NC}"
    fi
else
    echo -e "${YELLOW}⚠  .env already exists at $ENV_FILE — skipping${NC}"
fi

# ─── Initialize database ───────────────────────────────────────────────────────
echo ""
echo "Initializing database..."
python3 -c "
from pdb_tracker import config
config.ensure_dirs()

# Trigger table creation via the CLI entry points
from pdb_tracker.weekly.generator import WeeklyReportGenerator
from pdb_tracker.evaluation.evaluator import TargetEvaluator

gen = WeeklyReportGenerator(
    db_path=config.get_db_path(),
    output_dir=config.get_weekly_reports_dir(),
)
evaluator = TargetEvaluator(
    db_path=config.get_db_path(),
    output_dir=config.get_evaluations_dir(),
)
print(f'Database ready: {config.get_db_path()}')
"

# ─── OpenClaw skills ───────────────────────────────────────────────────────────
if command -v openclaw &> /dev/null; then
    echo ""
    echo "Installing OpenClaw skills..."
    OPENCLAW_SKILLS_DIR="$HOME/.openclaw/skills"
    mkdir -p "$OPENCLAW_SKILLS_DIR"
    ln -sf "$(pwd)/skills/pdb-weekly" "$OPENCLAW_SKILLS_DIR/pdb-weekly"
    ln -sf "$(pwd)/skills/target-evaluation" "$OPENCLAW_SKILLS_DIR/target-evaluation"
    echo -e "${GREEN}✓ OpenClaw skills installed${NC}"
fi

# ─── Claude Code skills ───────────────────────────────────────────────────────
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
if [ -d "$CLAUDE_SKILLS_DIR" ]; then
    echo ""
    echo "Installing Claude Code skills..."
    ln -sf "$(pwd)/skills/pdb-weekly" "$CLAUDE_SKILLS_DIR/pdb-weekly"
    ln -sf "$(pwd)/skills/target-evaluation" "$CLAUDE_SKILLS_DIR/target-evaluation"
    echo -e "${GREEN}✓ Claude Code skills installed${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "========================================"
echo ""
echo "Quick Start:"
echo "  1. Generate weekly report:"
echo "     python -m pdb_tracker.weekly.generator"
echo ""
echo "  2. Evaluate a target:"
echo "     python -m pdb_tracker.evaluation.evaluator P04637"
echo ""
echo "  3. Start Web UI:"
echo "     python -m pdb_tracker.web"
echo "     Then open http://localhost:5555"
echo ""
echo "All data lives under: ${PDB_DATA_DIR:-$HOME/.pdb-tracker/}"
echo "Customise locations via $ENV_FILE"
echo ""
echo "Documentation: https://github.com/Jing0715-fer/pdb-tracker"
echo ""
