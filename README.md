# PDB Tracker

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PDB Tracker 是一个综合性的蛋白质结构数据管理与评估平台，专为结构生物学研究设计。它集成了 PDB 数据获取、周报生成、靶点评估和可视化 Web UI。

## 核心功能

### 1. PDB 周报生成
- 自动获取 RCSB PDB 最新结构数据（按方法分类 Cryo-EM / X-ray / NMR）
- ISO 周ID命名（YYYY-Www 格式）
- 配体信息回填（GraphQL API，含药物/辅因子/底物过滤）
- 生成 LLM 增强的结构分析报告（8 章节 A–H）
- 支持 cron 自动化（建议 timeout ≥ 3600s）

### 2. 靶点评估
- UniProt ID 追踪（添加靶点 → 自动关联 PDB 结构）
- PDB 结构覆盖度分析（链级映射）
- 结构可行性评分（Cryo-EM / X-ray / NMR 各 0–10 分）
- 生成详细的结构可行性评估报告

### 3. 可视化 Web UI
- 双模式界面（周报模式 / 评估模式）
- 交互式 PDB 结构表格，实时搜索和筛选
- 报告预览和导出

---

## 快速开始

### 方式一：直接使用脚本（推荐，无需安装）

```bash
# 克隆到本地
git clone https://github.com/Jing0715-fer/pdb-tracker.git
cd pdb-tracker

# 初始化数据库
python3 skills/pdb-weekly/scripts/pdb_tracker_db.py --init

# 抓取一周数据
python3 skills/pdb-weekly/scripts/pdb_tracker_db.py --fetch 2026-04-16 2026-04-23

# 回填所有历史结构的配体信息
python3 skills/pdb-weekly/scripts/pdb_tracker_db.py --backfill-ligands

# 启动 Web UI（靶点评估模式）
python3 skills/target-evaluation/scripts/pdb_web_ui.py
# 打开 http://localhost:5555
```

### 方式二：pip 安装（用于 python -m 方式）

```bash
git clone https://github.com/Jing0715-fer/pdb-tracker.git
cd pdb-tracker
pip install -e ".[dev,web,llm]"

python -m pdb_tracker.weekly.generator
python -m pdb_tracker.evaluation.evaluator P04637
python -m pdb_tracker.web
```

### OpenClaw / Claude Code Agent Skill

Skill 位于 `skills/` 目录，包含两个独立 skill：

```
skills/
├── pdb-weekly/              # PDB 周报生成
│   ├── SKILL.md            # 触发条件 + 使用说明
│   └── scripts/
│       └── pdb_tracker_db.py   # 核心脚本（616 行）
└── target-evaluation/      # 靶点评估
    ├── SKILL.md            # 触发条件 + 使用说明
    └── scripts/
        └── pdb_web_ui.py   # Flask Web UI（1456 行）
```

**触发关键词：**
- PDB 周报：`PDB周报`、`weekly PDB`、`结构周报`、`PDB report`、`抓取PDB数据`
- 靶点评估：`靶点评估`、`target evaluation`、`structure feasibility`、`PDB coverage`

---

## 项目结构

```
pdb-tracker/
├── src/
│   └── pdb_tracker/
│       ├── __init__.py
│       ├── config.py              # 统一路径配置（环境变量优先）
│       ├── weekly/               # 周报生成模块
│       │   └── generator.py
│       ├── evaluation/           # 靶点评估模块
│       │   └── evaluator.py
│       └── web/                  # Web UI
│           ├── __main__.py
│           ├── app.py
│           ├── static/pdb_app.js
│           └── templates/pdb_index.html
├── skills/                       # Agent Skills（独立工作流）
│   ├── SKILL_SPEC.yaml
│   ├── pdb-weekly/
│   └── target-evaluation/
├── .env.example                   # 配置模板
├── install.sh                     # 一键安装脚本
└── pyproject.toml
```

---

## 配置

所有路径均可通过环境变量覆盖。

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `PDB_DATA_DIR` | 数据根目录 | `~/.pdb-tracker/` |
| `PDB_DB_NAME` | SQLite 数据库文件名 | `pdb_tracker.db` |
| `PDB_WEEKLY_DIR` | 周报 .md 文件目录 | `~/.pdb-tracker/weekly_reports/` |
| `PDB_EVAL_DIR` | 评估报告目录 | `~/.pdb-tracker/evaluations/` |
| `PDB_WEB_HOST` | Web UI 监听地址 | `0.0.0.0` |
| `PDB_WEB_PORT` | Web UI 端口 | `5555` |

**方式一：环境变量**

```bash
export PDB_DATA_DIR=/mnt/data/pdb-tracker
export PDB_WEB_PORT=8080
python3 skills/target-evaluation/scripts/pdb_web_ui.py
```

**方式二：`.env` 文件**

```bash
cp .env.example ~/.pdb-tracker/.env
# 编辑 ~/.pdb-tracker/.env
python3 skills/target-evaluation/scripts/pdb_web_ui.py
```

---

## 数据库 Schema

### pdb_structures（主表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `pdb_id` | TEXT | RCSB ID，主键 |
| `method` | TEXT | Cryo-EM / X-RAY / NMR |
| `release_date` | TEXT | YYYY-MM-DD |
| `resolution` | REAL | Å |
| `title, doi, journal, journal_if, authors, organisms` | | 元数据 |
| `ligands` | TEXT | 有意义配体（ABBR:FullName，pipe 分隔） |
| `ligand_info` | TEXT | 所有配体（含金属/水/缓冲液） |
| `fetch_date` | TEXT | 抓取日期 |
| `week_id` | TEXT | ISO 周 ID（YYYY-Www） |

生成列：`is_cryoem`, `is_xray`, `if_tier`（top/high/mid/low）

### weekly_snapshots（周报聚合）

week_id, week_start, week_end, total/cryoem/xray/nmr counts, avg_resolution, top_journals 等

### target_tracking / target_structures（靶点追踪）

UniProt acc → PDB 结构关联，支持靶点新增结构提醒

---

## 致谢

- RCSB PDB（结构数据 + GraphQL API）
- UniProt（蛋白序列信息）
- OpenClaw / Claude Code（Agent 框架支持）

---

MIT License - 详见 [LICENSE](LICENSE) 文件
