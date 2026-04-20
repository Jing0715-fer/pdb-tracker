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
- 结构可行性评分 (Cryo-EM/X-ray/NMR)
- 生成详细的结构可行性评估报告

### 3. 🌐 可视化 Web UI
- 双模式界面 (周报模式/评估模式)
- 交互式 PDB 结构表格
- 实时搜索和筛选
- 报告预览和导出

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Jing0715-fer/pdb-tracker.git
cd pdb-tracker

# 安装依赖
pip install -r requirements.txt

# 启动 Web UI
python -m pdb_tracker.web_ui
```

### OpenClaw/Claude Code 一键安装

```bash
# 使用 OpenClaw skill 安装
openclaw skill add pdb-tracker

# 或使用 Claude Code
claude skill install pdb-tracker
```

## 📁 项目结构

```
pdb-tracker/
├── src/
│   └── pdb_tracker/
│       ├── __init__.py
│       ├── core/              # 核心数据获取模块
│       │   ├── pdb_fetcher.py
│       │   ├── uniprot_fetcher.py
│       │   └── database.py
│       ├── weekly/            # 周报生成模块
│       │   ├── generator.py
│       │   └── llm_reporter.py
│       ├── evaluation/        # 靶点评估模块
│       │   ├── evaluator.py
│       │   └── llm_reporter.py
│       └── web/               # Web UI
│           ├── app.py
│           └── static/
├── skills/                    # OpenClaw/Claude Code Skills
│   ├── pdb-weekly/
│   └── target-evaluation/
├── templates/                 # 报告模板
│   ├── weekly_report.md
│   └── evaluation_report.md
├── docs/                      # 文档
└── tests/                     # 测试
```

## 🛠️ Skills 使用

### PDB 周报 Skill

```yaml
# .openclaw/skills/pdb-weekly.yaml
name: pdb-weekly
description: 生成 PDB 结构周报
commands:
  generate:
    description: 生成本周 PDB 结构报告
    usage: pdb-weekly generate --week 2024-W01
```

### 靶点评估 Skill

```yaml
# .openclaw/skills/target-evaluation.yaml
name: target-evaluation
description: 评估蛋白靶点的结构可行性
commands:
  evaluate:
    description: 评估指定 UniProt ID
    usage: target-evaluation evaluate P04637
```

## 📖 详细文档

- [快速开始指南](docs/quickstart.md)
- [API 文档](docs/api.md)
- [Skill 开发指南](docs/skill-development.md)
- [配置说明](docs/configuration.md)

## 🤝 贡献

欢迎贡献代码、报告问题或提出新功能建议！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- RCSB PDB 提供结构数据
- UniProt 提供蛋白序列信息
- OpenClaw/Claude Code 提供 Agent 框架支持
