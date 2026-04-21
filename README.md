# PDB Tracker

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PDB Tracker 是一个综合性的蛋白质结构数据管理与评估平台，专为结构生物学研究设计。它集成了 PDB 数据获取、周报生成、靶点评估和可视化 Web UI。

## ✨ 核心功能

### 1. 📊 PDB 周报生成
- 自动获取 RCSB PDB 最新结构数据
- 按方法分类 (Cryo-EM, X-ray, NMR)
- 生成 LLM 增强的结构分析报告
- 支持时间序列数据追踪

### 2. 🎯 靶点评估
- UniProt 数据自动获取
- PDB 结构覆盖度分析
- 结构可行性评分 (Cryo-EM / X-ray / NMR)
- 生成详细的结构可行性评估报告

### 3. 🌐 可视化 Web UI
- 双模式界面（周报模式 / 评估模式）
- 交互式 PDB 结构表格
- 实时搜索和筛选
- 报告预览和导出

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/Jing0715-fer/pdb-tracker.git
cd pdb-tracker
pip install -e ".[dev,web,llm]"
```

### 生成周报

```bash
python -m pdb_tracker.weekly.generator
```

### 评估靶点

```bash
python -m pdb_tracker.evaluation.evaluator P04637   # TP53 示例
```

### 启动 Web UI

```bash
python -m pdb_tracker.web
# 打开 http://localhost:5555
```

### 一键安装（OpenClaw / Claude Code）

```bash
./install.sh
```

---

## ⚙️ 配置

所有数据路径均可通过环境变量覆盖，默认存储在 `~/.pdb-tracker/`。

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
python -m pdb_tracker.web
```

**方式二：`.env` 文件**（参考 `.env.example`）

```bash
cp .env.example ~/.pdb-tracker/.env
# 编辑 ~/.pdb-tracker/.env
python -m pdb_tracker.web
```

---

## 📁 项目结构

```
pdb-tracker/
├── src/
│   └── pdb_tracker/
│       ├── __init__.py
│       ├── config.py              # 统一路径配置（环境变量优先）
│       ├── core/                  # 核心数据获取
│       │   ├── pdb_fetcher.py
│       │   ├── uniprot_fetcher.py
│       │   └── database.py
│       ├── weekly/               # 周报生成
│       │   ├── generator.py
│       │   └── llm_reporter.py
│       ├── evaluation/            # 靶点评估
│       │   ├── evaluator.py
│       │   └── llm_reporter.py
│       └── web/                   # Web UI
│           ├── __main__.py        # python -m pdb_tracker.web 入口
│           ├── app.py             # Flask 应用
│           └── templates/
│               └── pdb_index.html
├── skills/                       # Agent Skills
├── .env.example                   # 配置模板
├── install.sh                     # 一键安装脚本
└── pyproject.toml
```

---

## 📖 详细文档

- [快速开始指南](docs/quickstart.md)
- [API 文档](docs/api.md)
- [配置说明](docs/configuration.md)

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出新功能建议！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- RCSB PDB 提供结构数据
- UniProt 提供蛋白序列信息
- OpenClaw / Claude Code 提供 Agent 框架支持
