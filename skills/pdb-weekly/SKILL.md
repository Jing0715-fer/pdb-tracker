---
name: pdb-weekly
version: 2.0.0
description: Generate weekly PDB structure reports (Cryo-EM + X-ray). Full protocol at skills/pdb-weekly/PROTOCOL.md. Triggers on: "PDB周报", "weekly PDB", "结构周报", "PDB report", "generate PDB report", "抓取PDB数据", "PDB weekly"
---

# PDB Weekly Skill

Generate weekly PDB structure reports with automated data fetching, ligand analysis, and LLM-enhanced markdown output in 8 sections (A–H).

## ⚠️ 执行前必读

**完整正确流程见 `PROTOCOL.md`**。以下为快速参考。

---

## 快速参考（cron 执行用）

### 关键规则

| 规则 | 说明 |
|------|------|
| **RCSB API end_date +1 天** | 查询 4/29 数据需用 `to: 2026-04-30`，否则返回 0 条 |
| **week_id 用 `date.isocalendar()[1]`** | 禁止用 `strftime('%Y-W%W')`，从周一开始计数会错 |
| **数据库路径** | 必须用 `PDB_DATA_DIR=/Users/lijing/Documents/my_note/LLM-Wiki/data` |
| **Section H** | 文献列表（按 IF 从高到低），不是结构列表 |

### 日期计算公式

```python
from datetime import date, timedelta
today = date.today()
week_id = f"2026-W{today.isocalendar()[1]:02d}"    # ISO week
start_date = (today - timedelta(days=6)).strftime('%Y-%m-%d')  # today-6
end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')    # today+1 ← +1天！
```

### Step 1: Fetch 数据

```bash
PDB_DATA_DIR=/Users/lijing/Documents/my_note/LLM-Wiki/data \
  /usr/bin/python3 /Users/lijing/.openclaw/workspace/pdb_tracker_db.py \
  --fetch 2026-04-23 2026-04-30
```

### Step 2: 验证 week_id（fetch 后立即检查）

```python
# 如果 week_id 错误（显示 W17 而不是 W18），立即修正
cursor.execute('UPDATE pdb_structures SET week_id = "2026-W18" WHERE release_date = "2026-04-29"')
```

### Step 3-4: 生成报告（8 章节 A-H）

报告路径：
```
/Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/冷冻电镜结构周报-W{week_id}-{report_date}.md
/Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/X射线晶体学结构周报-W{week_id}-{report_date}.md
```

### Step 5: 同步到 data/weekly_reports/

```bash
cp /Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/*-W{week_id}-*.md \
   /Users/lijing/Documents/my_note/LLM-Wiki/data/weekly_reports/
```

### Step 6: 插入 weekly_reports 表（Web UI 显示用）

```python
# 对每个报告文件执行
cursor.execute('''
    INSERT OR REPLACE INTO weekly_reports (week_id, title, filename, report_type, content, created_at)
    VALUES (?, ?, ?, ?, ?, datetime('now'))
''', (report_date, title, filename, rtype, content))
# week_id 字段 = 报告日期 YYYY-MM-DD（如 "2026-04-29"），不是 ISO 周次
```

### Step 7: 插入 weekly_snapshots（如缺失）

### Step 8: 更新 index.md 和 log.md

---

## 数据库路径

| 用途 | 路径 |
|------|------|
| **主数据库** | `/Users/lijing/Documents/my_note/LLM-Wiki/data/pdb_tracker.db` |
| pdb_tracker_db.py | `/Users/lijing/.openclaw/workspace/pdb_tracker_db.py` |
| 报告输出（wiki） | `/Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/` |
| 报告同步（Web UI） | `/Users/lijing/Documents/my_note/LLM-Wiki/data/weekly_reports/` |
| Web UI | `http://localhost:5555` |

---

## Report Output Format

命名：`{type}-结构周报-W{week}-{YYYY-MM-DD}.md`

**必须 8 章节 A–H：**
- A. 期刊发表趋势分析
- B. 技术突破分析
- C. 研究趋势与热点
- D. 方法学创新与挑战
- E. 重要结构列表（Top 20，按分辨率）
- F. 总结与展望
- G. 整体影响与领域动态
- **H. 附录：本周完整文献列表（按影响因子从高到低排列，每条关联对应 PDB ID）**

---

## Web UI 可见性验证

```bash
curl http://localhost:5555/api/reports/list | python3 -c \
  "import sys,json; [print(r['file']) for r in json.load(sys.stdin) if 'W18' in r.get('name','')]"
```
