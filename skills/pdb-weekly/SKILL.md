---
name: pdb-weekly
version: 1.0.0
description: Generate weekly PDB structure reports (Cryo-EM + X-ray) with ligand analysis, ISO week IDs, and 8-section markdown output. Triggers on: "PDB周报", "weekly PDB", "结构周报", "PDB report", "generate PDB report", "抓取PDB数据", "PDB weekly"
---

# PDB Weekly Skill

Generate weekly PDB structure reports with automated data fetching, ligand analysis, and LLM-enhanced markdown output in 8 sections (A–H).

## Quick Start

```bash
python3 skills/pdb-weekly/scripts/pdb_tracker_db.py --init           # Init DB
python3 skills/pdb-weekly/scripts/pdb_tracker_db.py --fetch 2026-04-16 2026-04-23  # Fetch week
python3 skills/pdb-weekly/scripts/pdb_tracker_db.py --backfill-ligands          # Ligand backfill
```

## Database Schema

**Main table: `pdb_structures`**
- `pdb_id TEXT PRIMARY KEY` — RCSB ID (e.g. 9UJF)
- `method TEXT` — Cryo-EM / X-RAY / NMR
- `release_date TEXT` — YYYY-MM-DD
- `resolution REAL` — Å
- `title, doi, journal, journal_if, authors, organisms` — metadata
- `ligands TEXT` — meaningful ligands only (ABBR:FullName, pipe-separated)
- `ligand_names TEXT` — same as ligands
- `ligand_info TEXT` — ALL ligands (incl. metals/water/buffers)
- `fetch_date TEXT` — when record was fetched
- `week_id TEXT` — ISO week (YYYY-Www format, e.g. 2026-W17)

**Generated columns:** `is_cryoem`, `is_xray`, `if_tier` (top/high/mid/low)

**Snapshots: `weekly_snapshots`** — week_id, week_start, week_end, counts, avg_res, etc.

## Key Paths (Configurable via Environment Variables)

```
# Default locations (~/.pdb-tracker/)
DB:     $PDB_DATA_DIR/data/pdb_tracker.db
Output: $PDB_DATA_DIR/weekly_reports/
Raw:    $PDB_DATA_DIR/raw/

# Override with environment variables:
export PDB_DATA_DIR=/custom/path
export PDB_DB_DIR=/custom/db/path
export PDB_WEEKLY_DIR=/custom/output/path
```

## Report Generation Workflow

1. **Fetch** — `python3 pdb_tracker_db.py --fetch <week_start> <week_end>`
   - Fetches PDB IDs from RCSB Search API (range query on release_date)
   - Deduplicates against existing DB records (only fetch missing)
   - Concurrent detail fetch (10 workers) with ligand GraphQL query
   - Writes to DB + raw JSON + weekly_snapshots

2. **Ligand backfill** — `python3 pdb_tracker_db.py --backfill-ligands`
   - Uses RCSB GraphQL: `entry(entry_id: "XXX") { nonpolymer_entities {...} }`
   - Filters: metals (MG/ZN/CA/FE etc.), water (HOH/DOD/WAT), buffers (GOL/EDO/MES etc.), single-letter amino acids
   - Format: `ABBR:FullName` (e.g. `GDP:GUANOSINE-5'-DIPHOSPHATE`)

3. **Week ID logic** — `week_id()` uses `datetime.strftime('%Y-W%W')` on release_date
   - **Important**: For cron-triggered reports, use today's ISO week (generation date), not release date range

## Report Output Format

Output: `{type}-结构周报-W{week}-{YYYY-MM-DD}.md` in `pdb_weekly_report/`

**Required 8 sections (A–H):**
- A. 期刊发表趋势分析
- B. 技术突破分析（/药物设计）
- C. 研究趋势与热点（/高影响力工作深度解读）
- D. 方法学创新与挑战（/本周数据统计）
- E. 重要结构列表（Top 20，按分辨率排序）**with ligands**
- F. 总结与展望（核心洞察 + 前沿展望）
- G. 整体影响与领域动态
- H. 附录：本周完整结构列表

## Ligand Display Format (Section E)

Top 20 structures show ligand info like:
```
9UJF | 2.01 Å | GTP cyclohydrolase | GDP:GUANOSINE-5'-DIPHOSPHATE | Cryo-EM
```

## Configuration

```python
RCSB_SEARCH_API = "https://search.rcsb.org/rcsbsearch/v2/query"
RCSB_DATA_API   = "https://data.rcsb.org/rest/v1/core/entry/"
RCSB_GRAPHQL    = "https://data.rcsb.org/graphql"

METAL_IONS = {'MG','ZN','NA','CL','K','CA','FE','CU','MN','CO','NI','CD','HG','PB','BA','SR','AL','GA','MO','W','V','CR','TI','ZR','LI','CS'}
WATER      = {'HOH','DOD','WAT','H2O','D2O'}
COMMON_BUFFERS = {'ACT','ACN','DMSO','GOL','EDO','MES','TRIS','HEPES','PBS','PIPES','BME','EDTA','EGTA','SPERMID','PUT','TMAO','GLC','MAN','NAG','FLC','CIT'}
```

## Cron Jobs (Wiki Maintenance)

PDB weekly cron `7c26ab96-bd27-401f-9d8e-7dd142797450`:
- Date range: `today-6 days` to `today+1 day` (dynamic, calculated at runtime)
- Week ID: ISO week of **generation date** (today), not release date range
- Timeout: 3600s
- Output: `pdb_weekly_report/`

Wiki daily maintenance `89e71c48-747f-44fe-9421-18dcb5e02312`:
- Timeout: ≥300s