---
name: target-evaluation
version: 1.0.0
description: Evaluate protein target structure feasibility with PDB coverage analysis, feasibility scoring (Cryo-EM/X-ray/NMR), and LLM-enhanced reports. Triggers on: "靶点评估", "target evaluation", "structure feasibility", "PDB coverage", "UniProt ID", "evaluate target"
---

# Target Evaluation Skill

Evaluate protein target structure feasibility using existing PDB data with UniProt ID lookup, PDB chain mapping, feasibility scoring, and markdown report generation.

## Database Schema

**`pdb_structures`** — same as pdb-weekly skill (see above)

**`target_tracking`** — user-tracked targets
- `id, uniprot_acc, gene_name, protein_name, disease_area, target_notes, is_active, created_at, updated_at`

**`target_structures`** — PDB structures linked to targets
- `id, target_id, pdb_id, method, release_date, resolution, journal, journal_if, is_new, first_seen_at`

**`pdb_chains`** — PDB↔UniProt mapping
- `id, pdb_id, asym_id, entity_id, uniprot_accession, uniprot_id, gene_name, organism_tax_id, organism_name, sequence, start_residue, end_residue`

## Key Paths (Configurable via Environment Variables)

```
# Default locations (~/.pdb-tracker/)
DB:     $PDB_DATA_DIR/data/pdb_tracker.db
Output: $PDB_DATA_DIR/weekly_reports/

# Override with environment variables:
export PDB_DATA_DIR=/custom/path
export PDB_DB_DIR=/custom/db/path
export PDB_WEEKLY_DIR=/custom/output/path
export PDB_WEB_PORT=8080
```

## Core Script

```bash
python3 skills/target-evaluation/scripts/pdb_web_ui.py
# Runs on http://localhost:5555
```

## API Endpoints

```
GET /api/snapshots          — list weekly snapshots
GET /api/entries?week=      — entries for a week
GET /api/reports/list       — available .md reports
GET /api/evaluations        — all evaluated targets
GET /api/evaluations/<uniprot_id>  — specific target data
GET /api/evaluation/reports/list    — evaluation report files
```

## Feasibility Scoring

Score 0–10 per method based on:
- **Cryo-EM**: size (optimal 500–2000 aa), existing structures, resolution (≤3.5Å good), complexity
- **X-ray**: size (optimal 100–500 aa), resolution (≤2.5Å good), flexibility
- **NMR**: size (<350 aa), solubility, dynamics complexity

Assessment: 0–3 "困难", 4–6 "可行", 7–10 "推荐"

## Target Operations

```bash
# Add target
python3 pdb_tracker_db.py --add-target <uniprot_acc>

# List targets
python3 pdb_tracker_db.py --list-targets

# Query new structures for target
python3 pdb_tracker_db.py --query new
```

## Report Output

Evaluation reports in markdown with:
1. Executive Summary (feasibility scores per method)
2. Protein Background (function, domain architecture, disease)
3. Structure Analysis (existing PDBs, resolution/method distribution)
4. Feasibility Assessment
5. Experimental Recommendations (construct design, timeline)