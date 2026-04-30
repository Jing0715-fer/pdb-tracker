# PDB Weekly Report — 正确执行流程

> 本文档记录 PDB 周报自动生成任务的完整正确流程，涵盖所有已发现的坑和关键配置。
> 上次错误教训（2026-04-29）：API 日期范围未 +1 天、week_id 计算错误、数据库路径不一致、Section H 格式错误。

---

## 一、关键规则（必读）

### ⚠️ RCSB API 日期范围：end_date 必须 +1 天

RCSB Search API 的 `range` 查询中，`to` 参数需要**目标日期 +1 天**才能包含当天数据。

```
# 错误 ❌ — 查询 Apr 23-29，返回 0 条
{"attribute": "rcsb_accession_info.initial_release_date", "operator": "range", "value": {"from": "2026-04-23", "to": "2026-04-29"}}

# 正确 ✅ — 查询 Apr 23-30，才能拿到 Apr 29 的数据
{"attribute": "rcsb_accession_info.initial_release_date", "operator": "range", "value": {"from": "2026-04-23", "to": "2026-04-30"}}
```

**规则：** `end_date = 报告日期 + 1 天`，即 RCSB 查询的 to 参数 = 实际想要包含的最后一天 + 1。

### ⚠️ week_id 以报告生成日期为准，不用 release_date

week_id 使用**生成日（today）的 ISO 周次**，不是数据 release_date 所在的周次。

```
报告生成日期：2026-04-29（周三）→ week_id = 2026-W18（ISO week 18）
报告日期范围：2026-04-23 至 2026-04-29（上周三到这周三）
```

**计算方式：** 使用 Python `date.isocalendar()[1]`（或 `isocalendar().week`）获取 ISO 周次：
```python
from datetime import date
today = date(2026, 4, 29)
week_num = today.isocalendar()[1]  # = 18
week_id = f"2026-W{week_num:02d}"   # = "2026-W18"
```

**禁止使用** `strftime('%Y-W%W')` — 这个从周一开始计数，周三当天返回的值可能与 ISO 不一致（尤其在年末/年初跨年时）。

### ⚠️ 数据库路径：必须用 LLM-Wiki 下的路径

```
正确路径：/Users/lijing/Documents/my_note/LLM-Wiki/data/pdb_tracker.db
```

cron 任务中必须设置：
```bash
PDB_DATA_DIR=/Users/lijing/Documents/my_note/LLM-Wiki/data /usr/bin/python3 pdb_tracker_db.py --fetch ...
```

### ⚠️ Section H 格式：文献列表（按 IF 从高到低），非结构列表

Section H 不是完整 PDB 结构罗列，而是**按影响因子从高到低排列的文献列表**，每条关联对应 PDB ID：

```
| IF | 期刊名称 | 结构数 | PDB IDs |
|---:|----------|-------:|---------|
| 56.9 | Science | 6 | 9Z6Y, 9Z6Z, 9VC6, 9VC9, 9VCB, 9VCF |
| 17.7 | Nat Commun | 12 | 9XKO, 10RX, 9W23... |
| N/A | To Be Published | 60 | 9NZU, 9WP6... |
```

---

## 二、完整执行流程（Step-by-Step）

### Step 1：计算日期参数

**在报告生成日当天执行（周三 8:00 AM）：**

```python
from datetime import date, timedelta

today = date.today()                              # e.g. 2026-04-29
report_date = today.strftime('%Y-%m-%d')          # "2026-04-29"
week_num = today.isocalendar()[1]                 # 18
week_id = f"2026-W{week_num:02d}"                 # "2026-W18"
start_date = (today - timedelta(days=6)).strftime('%Y-%m-%d')  # "2026-04-23"
end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')    # "2026-04-30"  ← +1天！
```

### Step 2：获取 RCSB 数据

```bash
PDB_DATA_DIR=/Users/lijing/Documents/my_note/LLM-Wiki/data \
  /usr/bin/python3 /Users/lijing/.openclaw/workspace/pdb_tracker_db.py \
  --fetch 2026-04-23 2026-04-30   # 注意 end_date +1
```

**数据写入：** `/Users/lijing/Documents/my_note/LLM-Wiki/data/pdb_tracker.db`

### Step 3：验证数据入库

```python
# 检查是否写入正确数据库
import sqlite3
conn = sqlite3.connect('/Users/lijing/Documents/my_note/LLM-Wiki/data/pdb_tracker.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*), release_date FROM pdb_structures WHERE release_date = "2026-04-29" GROUP BY release_date')
print(cursor.fetchone())  # 期望: (365, '2026-04-29')

# 检查 week_id 是否正确（必须是报告生成日的 ISO 周次）
cursor.execute('SELECT DISTINCT week_id FROM pdb_structures WHERE release_date = "2026-04-29"')
print(cursor.fetchone())  # 期望: ('2026-W18',)
```

**⚠️ week_id 验证：** 如果发现 week_id 不对（如显示 W17），立即修正：
```python
cursor.execute('UPDATE pdb_structures SET week_id = "2026-W18" WHERE release_date = "2026-04-29"')
```

### Step 4：插入 weekly_snapshots（如缺失）

```python
cursor.execute('''
    INSERT OR REPLACE INTO weekly_snapshots
    (week_id, week_start, week_end, total_structures, cryoem_count, xray_count, nmr_count, other_count,
     cryoem_res_dist, xray_res_dist, cryoem_avg_res, xray_avg_res, top_journals, if_dist, raw_json_path, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
''', ('2026-W18', '2026-04-23', '2026-04-29', 365, 196, 159, 5, 5,
      json.dumps({'<=2.0':3,'2.0-3.0':84,'3.0-4.0':82,'>4.0':27}),
      json.dumps({'<=1.0':2,'1.0-1.5':8,'1.5-2.0':95,'>2.0':54}),
      3.480, 2.00,
      json.dumps([('To Be Published', 60), ('Biorxiv', 23), ('Science Advances', 18)]),
      json.dumps({'top':0,'high':0,'mid':0,'low':0,'unknown':365}), ''))
```

### Step 5：生成报告（MD 文件）

报告路径：
```
/Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/冷冻电镜结构周报-W18-2026-04-29.md
/Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/X射线晶体学结构周报-W18-2026-04-29.md
```

命名规范：`{类型}-结构周报-W{week_id}-{YYYY-MM-DD}.md`

必须包含全部 8 个章节 A-H。

### Step 6：同步到 data/weekly_reports/（Web UI 所需）

```bash
# Web UI 从 data/weekly_reports/ 迁移报告到数据库
cp /Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/*-W{week_id}-*.md \
   /Users/lijing/Documents/my_note/LLM-Wiki/data/weekly_reports/
```

### Step 7：插入 weekly_reports 表（Web UI 显示报告的关键）

```python
# 每个报告文件都要插入 weekly_reports 表，Web UI 才能显示
for filename, rtype, title in [
    ('冷冻电镜结构周报-W18-2026-04-29.md', 'cryoem', '冷冻电镜（Cryo-EM）结构周报'),
    ('X射线晶体学结构周报-W18-2026-04-29.md', 'xray', 'X射线晶体学（X-ray Crystallography）结构周报'),
]:
    path = f'/Users/lijing/Documents/my_note/LLM-Wiki/data/weekly_reports/{filename}'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    cursor.execute('''
        INSERT OR REPLACE INTO weekly_reports (week_id, title, filename, report_type, content, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    ''', ('2026-04-29', title, filename, rtype, content))
```

### Step 8：更新 index.md 和 log.md

- `index.md`：在 PDB Weekly Reports 下添加 W18 条目
- `log.md`：追加本次执行记录

---

## 三、cron 任务配置（jobs.json）

```json
{
  "id": "7c26ab96-bd27-401f-9d8e-7dd142797450",
  "schedule": "0 8 * * 3",
  "tz": "Asia/Shanghai",
  "payload": {
    "message": "Task: Generate PDB weekly reports for the current week (Cryo-EM + X-ray) and write to database.\n\n## Week ID Calculation (CRITICAL)\nweek_id = today's ISO week using date.isocalendar()[1], NOT strftime('%Y-W%W')\nExample: if today is 2026-04-29 (Wednesday), week_id = 2026-W18\n\n## Date Range (CRITICAL)\n- start_date = today - 6 days\n- end_date = today + 1 day (RCSB API requires +1 to include target date!)\nExample for 2026-04-29: start=2026-04-23, end=2026-04-30\n\n## Step 1: Fetch\nPDB_DATA_DIR=/Users/lijing/Documents/my_note/LLM-Wiki/data /usr/bin/python3 /Users/lijing/.openclaw/workspace/pdb_tracker_db.py --fetch [start_date] [end_date]\nExample: --fetch 2026-04-23 2026-04-30\n\n## Step 2: Verify week_id in DB\nAfter fetch, verify: SELECT DISTINCT week_id FROM pdb_structures WHERE release_date = [report_date]\nIf wrong, fix: UPDATE pdb_structures SET week_id = [week_id] WHERE release_date = [report_date]\n\n## Step 3-4: Generate reports (8 sections A-H)\n- Cryo-EM: /Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/冷冻电镜结构周报-W{week_id}-{report_date}.md\n- X-ray: /Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/X射线晶体学结构周报-W{week_id}-{report_date}.md\n- Section H: Literature list (by IF desc), NOT structure list\n\n## Step 5: Sync to data/weekly_reports/\ncp *.md /Users/lijing/Documents/my_note/LLM-Wiki/data/weekly_reports/\n\n## Step 6: Insert into weekly_reports table (for Web UI)\nInsert each report's filename, week_id (as report_date YYYY-MM-DD), title, type, content into weekly_reports table\n\n## Step 7: Insert weekly_snapshots if missing\n\n## Step 8: Update index.md and log.md"
  }
}
```

---

## 四、数据库路径配置

| 用途 | 路径 |
|------|------|
| **主数据库** | `/Users/lijing/Documents/my_note/LLM-Wiki/data/pdb_tracker.db` |
| pdb_tracker_db.py 脚本 | `/Users/lijing/.openclaw/workspace/pdb_tracker_db.py` |
| 报告输出（wiki） | `/Users/lijing/Documents/my_note/LLM-Wiki/wiki/pdb_weekly_report/` |
| 报告同步（Web UI） | `/Users/lijing/Documents/my_note/LLM-Wiki/data/weekly_reports/` |
| Web UI | `http://localhost:5555`（`/Users/lijing/Documents/my_note/LLM-Wiki/data/pdb_web_ui.py`）|

**环境变量：** `PDB_DATA_DIR=/Users/lijing/Documents/my_note/LLM-Wiki/data`

---

## 五、Web UI 报告可见性检查清单

报告在 Web UI 中显示需要满足：

1. ✅ MD 文件存在于 `data/weekly_reports/`
2. ✅ 对应记录插入 `weekly_reports` 表（字段：week_id, title, filename, report_type, content）
3. ✅ `week_id` 字段设为**报告日期**（YYYY-MM-DD 格式），不是 ISO 周次
4. ✅ `weekly_snapshots` 表有对应周次的快照记录

**验证命令：**
```bash
# API 层面验证
curl http://localhost:5555/api/reports/list | python3 -c "import sys,json; [print(r['file']) for r in json.load(sys.stdin) if 'W18' in r.get('name','')]"

# 数据库层面验证
sqlite3 /Users/lijing/Documents/my_note/LLM-Wiki/data/pdb_tracker.db \
  "SELECT week_id, filename, report_type FROM weekly_reports ORDER BY week_id DESC"
```

---

## 六、上次错误记录（2026-04-29）

| 错误 | 后果 | 修正 |
|------|------|------|
| RCSB API end_date 未 +1 天 | API 返回 0 条，误以为数据不存在 | 改为 `end_date = today + 1` |
| week_id 用 `strftime('%Y-W%W')` 计算 | April 29 错误标记为 W17 | 改用 `date.isocalendar()[1]` |
| 数据库写入 `~/.pdb-tracker/` 而非 LLM-Wiki | Web UI 看不到数据 | 设 `PDB_DATA_DIR` 环境变量 |
| 报告只写到 wiki/ 未同步到 data/weekly_reports/ | Web UI 无法迁移报告 | 两处都写 |
| weekly_reports 表未手动插入 W18 记录 | Web UI 不显示 W18 报告 | 手动 INSERT |
| Section H 用结构列表而非文献列表 | 格式不符合规范 | 改为按 IF 排序的文献列表 |
