# Target Evaluation Skill

Evaluate protein target structure feasibility with comprehensive PDB coverage analysis.

## Installation

```bash
openclaw skill add target-evaluation
```

## Usage

### Evaluate Single Target

```bash
# Basic evaluation
target-evaluation evaluate P04637

# With force refresh
target-evaluation evaluate P04637 --force

# Specify output format
target-evaluation evaluate P04637 --format markdown
```

### Batch Evaluation

```bash
# Evaluate multiple targets from file
target-evaluation batch --file targets.txt

# Evaluate with specific method focus
target-evaluation batch --file targets.txt --method cryoem
```

### List Evaluations

```bash
# List all evaluated targets
target-evaluation list

# List with filters
target-evaluation list --method xray --min-score 7
```

### Compare Targets

```bash
# Compare multiple targets
target-evaluation compare P04637 P00533 Q9GZU1
```

## Report Template

Generated reports follow a standardized template including:

1. **Executive Summary**
   - Protein function overview
   - Feasibility scores (Cryo-EM/X-ray/NMR)
   - Recommendation summary

2. **Protein Background**
   - Function and biology
   - Domain architecture
   - Disease associations

3. **Structure Analysis**
   - Existing PDB structures
   - Resolution distribution
   - Method distribution
   - Coverage analysis

4. **Feasibility Assessment**
   - Method comparison
   - Complexity analysis
   - Scoring rationale

5. **Experimental Recommendations**
   - Construct design
   - Expression strategy
   - Purification workflow
   - Structure determination approach
   - Timeline estimate

## Configuration

Create `~/.pdb-tracker/config.yaml`:

```yaml
# Database settings
db_path: ~/.pdb-tracker/pdb_tracker.db

# Report output
output_dir: ~/Documents/Target_Evaluations

# Journal IF data
journal_if_file: ~/.pdb-tracker/journal_if.json

# Evaluation criteria
scoring:
  cryoem:
    size_optimal: [500, 2000]  # aa range
    resolution_threshold: 3.5
  xray:
    size_optimal: [100, 500]
    resolution_threshold: 2.5
  nmr:
    size_max: 350
```

## API Usage

```python
from pdb_tracker.evaluation import TargetEvaluator

evaluator = TargetEvaluator(
    db_path=Path("pdb_tracker.db"),
    output_dir=Path("evaluations")
)

# Evaluate single target
report_path = evaluator.evaluate("P04637")

# Force refresh
report_path = evaluator.evaluate("P04637", force_refresh=True)

# Get evaluation data
data = evaluator.get_evaluation("P04637")
```

## Output Formats

### Markdown (default)
Human-readable report with tables and formatting.

### JSON
Structured data for programmatic access:

```json
{
  "uniprot_id": "P04637",
  "protein_name": "Cellular tumor antigen p53",
  "scores": {
    "Cryo-EM": {"score": 6, "assessment": "可行"},
    "X-ray": {"score": 10, "assessment": "推荐"},
    "NMR": {"score": 6, "assessment": "可行"}
  },
  "structures": 50,
  "coverage": 100.0,
  "recommendation": "X-ray crystallography recommended"
}
```

## Feasibility Scoring

### Criteria

**Cryo-EM Score (0-10):**
- Protein size (optimal: 500-2000 aa)
- Existing structures
- Resolution of existing structures
- Complexity (membrane protein, etc.)

**X-ray Score (0-10):**
- Protein size (optimal: 100-500 aa)
- Existing structures
- Resolution of existing structures
- Flexibility/disorder prediction

**NMR Score (0-10):**
- Protein size (< 350 aa required)
- Existing structures
- Solubility prediction
- Dynamics complexity

## Dependencies

- Python 3.8+
- requests
- sqlite3
- biopython (optional, for sequence analysis)

## Data Sources

- UniProt REST API (https://rest.uniprot.org/)
- RCSB PDB APIs
- Journal Impact Factor data (optional)

## License

MIT License
