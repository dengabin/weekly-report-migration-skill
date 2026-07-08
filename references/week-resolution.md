# 周次解析与部门表列匹配

## 1. 默认规则（用户未指定周次）

**不要 AskQuestion 问「要哪一周」。**

1. 读取组内 otl 全部 `# YYYY-MM-DD` 区块（`extract_otl_weekly.py` 内 `pick_week_section` 逻辑）
2. 取 **日期 ≤ 今天** 中**最新**的一期作为本次 `week`
3. 写入 `config.json` 的 `week` 字段
4. 部门表表头、补丁计划、提取脚本**全部使用该同一 `week`**

用户只说「周报迁移」「同步周报」即走此默认。

---

## 2. 用户指定周次

### 2.1 绝对日期

| 用户输入示例 | 解析为 |
|--------------|--------|
| `week 是 2026-07-02` | `2026-07-02` |
| `粘贴 6.26-7.2 的` | 在 otl 表头/区块中模糊匹配含 `6.26-7.2` 或 `7.2` 的列 |
| `7月2日那一列` | 匹配部门表头 `7月2日` + `config.week_aliases` |

### 2.2 相对周次（需系统当前日期）

以 Agent 执行时的**系统日期**为「今天」。

| 用户输入 | 行为 |
|----------|------|
| 本周 / 这周 | 同 §1 默认（最新 ≤ 今天） |
| 上周 / 上一周 / 前一周 | 在 otl 日期区块列表（降序）中，取默认周次的**下一档**（时间更早的一期） |
| 上上周 | 再往前一档 |

实现要点：

1. 先 `parse_sections` 得到所有 `(date, label, body)`
2. 默认周 = `pick_week_section(sections, week=None)`
3. 「上一周」= 在 `dated` 列表中，找默认周的 index+1（若按时间降序排列）

若相对周次超出 otl 已有区块：列出可用日期，AskQuestion 让用户选。

---

## 3. 组内 ↔ 部门 日期对齐

| 字段 | 必须一致 |
|------|----------|
| otl `# 日期` 区块 | `extracted.json` → `week_section` |
| `config.week` | 部门表表头 `col_match.equals` |
| 每人姓名 | otl `## 姓名` = 部门 B 列 = `config.members[].name` |

**禁止**：组内取 A 周、部门写 B 周。

---

## 4. 部门表周列检测

从 `.cache/dept-content.json` 目标子表表头行读取列标题（KDC JSON 优先于 Markdown）。

匹配逻辑（`sheet_utils.week_matches`）：

- `config.week` 与表头**相等、包含、或被包含**
- 或命中 `config.week_aliases` 任一项

### 4.1 列已存在

- `plan_sheet_patches.py` 定位到该列
- 仅覆盖该列内容格（如 C 列）；历史列不动

### 4.2 列不存在 — 插入新列

**场景**：组内已写本周报，部门表尚未开列（常见）。

**要求**：

1. 根据本周日期，在表头**时间序正确位置**插入一列（新周一般在**最左数据列**或紧邻最新历史周左侧，与现有表风格一致）
2. 表头单元格文案参考相邻列，例如：  
   `7月2日` + 换行 + `周期：6.26-7.2`（周期从 otl 区块或组内习惯推断）
3. D 列同步复制「📄组内周报」占位结构（若该组行有文件链接列）
4. **仅**新增列相关 XML/结构；**不得**修改其它列单元格内容
5. 插入完成后重新 `preflight` / `plan_sheet_patches`，再 patch

**若列已存在但为空**：视为覆盖写入，同 §4.1。

---

## 5. config 中的 week 字段

```json
{
  "week": "2026-07-02",
  "week_aliases": ["7.2", "7月2日", "6.26-7.2", "周期：6.26-7.2"]
}
```

Agent 在解析用户口语后应**自动更新** `week` 与必要时补充 `week_aliases`，无需用户手改 JSON。

---

## 6. 命令行覆盖

```bash
python scripts/extract/extract_otl_weekly.py --week 2026-07-02 ...
python scripts/workflow/run_preview.py --week 2026-07-02
```

`run_preview` / `apply_migration` 在更新 `config.week` 后应使用同一 `--week` 参数。
