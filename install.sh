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

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo -e "${RED}Error: Python 3.8+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Clone repository if not already in it
if [ ! -f "pyproject.toml" ]; then
    echo "Cloning repository..."
    git clone https://github.com/Jing0715-fer/pdb-tracker.git
    cd pdb-tracker
fi

# Install package
echo ""
echo "Installing PDB Tracker..."
pip install -e ".[dev,web,llm]"

# Create config directory
echo ""
echo "Creating configuration..."
CONFIG_DIR="$HOME/.pdb-tracker"
mkdir -p "$CONFIG_DIR/cache/pdb"
mkdir -p "$CONFIG_DIR/cache/uniprot"
mkdir -p "$CONFIG_DIR/logs"

# Create default config
cat > "$CONFIG_DIR/config.yaml" << CONFIG
# PDB Tracker Configuration
# Documentation: https://github.com/Jing0715-fer/pdb-tracker

# Database settings
database:
  path: $CONFIG_DIR/pdb_tracker.db

# Cache settings
cache:
  directory: $CONFIG_DIR/cache
  ttl_days: 7

# Output directories
output:
  weekly: $HOME/Documents/PDB_Reports/Weekly
  evaluations: $HOME/Documents/PDB_Reports/Evaluations

# Web UI settings
web:
  host: 0.0.0.0
  port: 5555
  debug: false

# LLM integration (optional)
# Uncomment and configure if using LLM features
# llm:
#   provider: openai  # or anthropic
#   model: gpt-4
#   api_key: \${OPENAI_API_KEY}
CONFIG

echo -e "${GREEN}✓ Configuration created at $CONFIG_DIR/config.yaml${NC}"

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'src')
from pdb_tracker.weekly.generator import WeeklyReportGenerator
from pdb_tracker.evaluation.evaluator import TargetEvaluator

db_path = Path.home() / '.pdb-tracker' / 'pdb_tracker.db'
db_path.parent.mkdir(parents=True, exist_ok=True)

# Initialize tables
gen = WeeklyReportGenerator(db_path=db_path, output_dir=Path.home() / 'Documents' / 'PDB_Reports' / 'Weekly')
evaluator = TargetEvaluator(db_path=db_path, output_dir=Path.home() / 'Documents' / 'PDB_Reports' / 'Evaluations')

print('Database initialized successfully!')
"

# Create OpenClaw skill symlink (if OpenClaw is installed)
if command -v openclaw &> /dev/null; then
    echo ""
    echo "Installing OpenClaw skills..."
    
    OPENCLAW_SKILLS_DIR="$HOME/.openclaw/skills"
    mkdir -p "$OPENCLAW_SKILLS_DIR"
    
    # Create skill symlinks
    ln -sf "$(pwd)/skills/pdb-weekly" "$OPENCLAW_SKILLS_DIR/pdb-weekly"
    ln -sf "$(pwd)/skills/target-evaluation" "$OPENCLAW_SKILLS_DIR/target-evaluation"
    
    echo -e "${GREEN}✓ OpenClaw skills installed${NC}"
fi

# Create Claude Code skill directory
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
if [ -d "$CLAUDE_SKILLS_DIR" ]; then
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
echo "     pdb-weekly generate"
echo ""
echo "  2. Evaluate a target:"
echo "     target-evaluation evaluate P04637"
echo ""
echo "  3. Start Web UI:"
echo "     python -m pdb_tracker.web"
echo "     Then open http://localhost:5555"
echo ""
echo "Documentation: https://github.com/Jing0715-fer/pdb-tracker"
echo ""
