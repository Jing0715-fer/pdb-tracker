# PDB Weekly Skill

Generate weekly PDB structure reports with automated data fetching and LLM-enhanced analysis.

## Installation

```bash
openclaw skill add pdb-weekly
```

## Usage

### Generate Weekly Report

```bash
# Generate report for current week
pdb-weekly generate

# Generate report for specific week
pdb-weekly generate --week 2024-W01

# Force refresh (re-fetch data)
pdb-weekly generate --week 2024-W01 --force
```

### List Available Reports

```bash
pdb-weekly list
```

### Get Report Summary

```bash
pdb-weekly summary --week 2024-W01
```

## Configuration

Create `~/.pdb-tracker/config.yaml`:

```yaml
# Database path
db_path: ~/.pdb-tracker/pdb_tracker.db

# Report output directory
output_dir: ~/Documents/PDB_Reports

# Cache settings
cache_dir: ~/.pdb-tracker/cache
cache_ttl_days: 7

# LLM integration (optional)
llm:
  provider: openai  # or anthropic, local
  model: gpt-4
  api_key: ${OPENAI_API_KEY}
```

## Output

Reports are generated in Markdown format with:
- Weekly structure statistics (Cryo-EM, X-ray, NMR)
- High-resolution structure highlights
- Journal impact analysis
- Method distribution charts
- LLM-generated insights

## API Usage

```python
from pdb_tracker.weekly import WeeklyReportGenerator

generator = WeeklyReportGenerator(
    db_path=Path("pdb_tracker.db"),
    output_dir=Path("reports")
)

# Generate current week report
report_path = generator.generate_report()

# Generate specific week
report_path = generator.generate_report("2024-W15")
```

## Dependencies

- Python 3.8+
- requests
- sqlite3
- pandas (optional, for advanced analysis)
- matplotlib (optional, for charts)

## Data Sources

- RCSB PDB REST API (https://data.rcsb.org/)
- RCSB PDB Search API (https://search.rcsb.org/)

## License

MIT License
