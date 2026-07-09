# 组名解析（部门表多组场景）

部门周报表格通常**一张子表内包含多个小组**，每个小组有组标题行，其下为成员姓名行。迁移时**只能写入其中一个小组**对应区块，不得误写到其它组。

---

## 1. 核心原则

| 情况 | Agent 行为 |
|------|------------|
| 组内 otl 的 `## 姓名` 能在部门表**唯一对应**到同一组区块 | **不问用户**，自动解析 `team_name` 并迁移 |
| 无法从姓名唯一确定组（跨组、重名、全找不到） | **必须 AskQuestion** 询问「要迁移哪个组」 |
| 用户未提供组名且无法自动确定 | **禁止**猜测或随意选组写回 |

**成员名单**仍从 otl 自动解析，不向用户索要；**组名**仅在无法自动确定时才问。

---

## 2. 自动解析逻辑

预检并提取 otl 后，Agent 执行：

```bash
python scripts/plan/resolve_team_name.py
```

脚本读取 `.cache/extracted.json` 成员姓名 + `.cache/dept-content.json` 目标子表，对每个成员：

1. 在部门表姓名列（默认 B 列）查找含该姓名的行
2. 向上回溯到最近的**组标题行**（该行文本不含任何 otl 成员姓名）
3. 若全部成员落在**同一组** → `status: resolved`，自动写入 `config.team_name` 与 `options.team_row_marker`
4. 否则 → `status: ambiguous` / `need_team_name` / `not_found`，退出码 **3**

输出：`.cache/team-resolve.json`

---

## 3. 需要用户指定组名时

当 `resolve_team_name.py` 退出码为 3，或 `team-resolve.json` 的 `status` 为 `ambiguous` / `need_team_name` / `not_found`：

1. 向用户说明：**部门表中有多个组，当前无法从姓名唯一确定要写入哪一组**
2. 列出 `candidates`（若能推断出部分候选组名）或请用户给出部门表中的**组标题行文字**
3. AskQuestion 等待用户回复组名
4. 收到后执行：
   ```bash
   python scripts/plan/resolve_team_name.py --team-name "<用户给的组名>"
   python scripts/workflow/run_preview.py
   ```
5. **禁止**在未明确组名前继续 `plan_sheet_patches` / 写回

### Agent 话术示例

> 部门周报表里有多个小组。你贴的组内周报里虽然有成员姓名，但在部门表里对应到了多个组（或找不到对应行），我无法自动判断要写入哪一组。  
> 请告诉我**部门表中你们组的组名**（就是成员姓名上方那一行的组标题，例如「示例小组名」）。

---

## 4. 用户直接粘贴组内周报

用户可在对话中**直接粘贴** otl Markdown（含 `# 日期` + `## 姓名`），不必只给链接。

Agent 将粘贴内容写入 `.cache/team-report.md`，再走 `extract_otl_weekly.py` → `resolve_team_name.py`。

若粘贴内容含成员姓名且能在部门表唯一匹配 → 同样**不问组名**。

---

## 5. 平铺姓名子表（无组标题行）

部分部门子表**没有**组标题行分区，结构为：`工号 | 姓名 | 周列…`，成员按姓名直接平铺。

`resolve_team_name.py` 检测到此类布局时返回 `status: flat_sheet`：

- **不设置** `team_row_marker`（留空）
- 可选记录 `options.link_column`（含 📄 的链接列，若存在）
- `plan_sheet_patches` 在**全表**按姓名 + 周次表头定位单元格

此场景**不问用户组名**。仅当表内有多组且无法从姓名唯一对应时才 AskQuestion。

---

## 6. 与 `team_name` / `team_row_marker` 的关系

自动解析成功后写入：

```json
{
  "team_name": "你的组名",
  "options": {
    "team_row_marker": "你的组名",
    "use_team_name_as_marker": true
  }
}
```

此后 `plan_sheet_patches.py` 的 `find_cell_in_rows` 仅在**该组区块内**匹配成员行，避免写到其它组同名行。

若 `config.json` 已有有效 `team_name` 且全部成员可在该组内定位，脚本返回 `already_set`，跳过重算。

---

## 7. 禁止行为

- ❌ 在 `ambiguous` 时默认选第一个组
- ❌ 用 `fourth_dept_name` 代替小组 `team_name`（前者是子表 tab，后者是表内组标题行）
- ❌ 未设置 `team_row_marker` 就在多组子表里全局搜姓名（可能误匹配它组）

---

## 8. 相关命令

```bash
# 自动解析（run_preview 内已调用）
python scripts/plan/resolve_team_name.py

# 用户指定组名后
python scripts/plan/resolve_team_name.py --team-name "你的组名"
```

详见 [mapping-rules.md](mapping-rules.md) §行匹配增强。
