# 组名解析（部门表多组场景）

部门周报表格通常**一张子表内包含多个小组**，每个小组有组标题行，其下为成员姓名行。迁移时**只能写入其中一个小组**对应区块，不得误写到其它组。

---

## 1. 核心原则

### 1.1 定位确定性（防误写，强制）

**宁可多问一次，不可写错它组。** 只有**百分百确定**目标时，才允许不问用户直接写回。

| 定位对象 | 视为「百分百确定」、可不问 | 不确定 → **必须 AskQuestion** |
|----------|---------------------------|--------------------------------|
| **部门子表 tab** | `config.dept_sheet.sheet_name` 与云端子表列表**精确一致**；或模糊规则**仅命中唯一**一页 | `sheet_name` 已失效；**多个**子表名同时匹配；预检 `resolved_sheet: null` |
| **页内组名** | otl 成员在目标子表内**唯一**落在同一组标题区块（`resolve_team_name` → `resolved`） | `ambiguous` / `need_team_name` / `not_found`（退出码 3） |
| **平铺子表** | `flat_sheet` 且本次 otl 成员**全部**能在该子表姓名列找到 | 部分成员找不到、或子表本身不确定 |

**禁止**（即使「看起来差不多」）：

- ❌ 多个子表候选时**默认选第一个**
- ❌ 用组内 otl **文档标题**模糊猜子表 tab
- ❌ 用 `contains` 模糊匹配到多页仍自动写入
- ❌ `ambiguous` 时选第一个候选组
- ❌ 未通过预览向用户展示**子表名 + 周次 + 人数**就上传

用户通过 AskQuestion **明确点选**的子表/组名，写入前预览须再次展示该子表名供核对；用户取消则不上传。

### 1.2 组名（页内多组）

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

### 每次迁移都会重算组名（不依赖旧缓存）

- 写回成功后默认清空 `.cache/`，**下次 preflight 会从云端重新下载**部门表与组内 otl，不靠上次中间文件。
- `config.json` 会保留文档链接与上次的 `team_name`，但 **`resolve_team_name.py` 每次都会用本次部门表 + 本次 otl 成员重新反推**；若部门调整了组标题，会自动更新 `config.team_name`（`team-resolve.json` 可能出现 `team_name_changed`）。
- **只有**自动反推失败（`ambiguous` / `not_found` / `need_team_name`，退出码 3）时，才 **AskQuestion** 向用户要组名；**不需要**因组名变更而重新要文档链接。
- 若用户换了部门文档或四级子表，可说「更新周报迁移的文档链接」或删除 `config.json` 后重来。

若自动反推失败、且 config 旧组名仍能在**本次**部门表定位全部成员，脚本返回 `already_set` 暂沿用旧组名。

---

## 7. 禁止行为

- ❌ 在 `ambiguous` 时默认选第一个组
- ❌ 用 `fourth_dept_name` 代替小组 `team_name`（前者是子表 tab，后者是表内组标题行）
- ❌ 未设置 `team_row_marker` 就在多组子表里全局搜姓名（可能误匹配它组）
- ❌ 子表 tab 或组名**任一**存在多个候选时自动写入（须 AskQuestion）
- ❌ 用 otl 文档标题、旧 config、模糊字符串「猜」子表或组名

---

## 8. 相关命令

```bash
# 自动解析（run_preview 内已调用）
python scripts/plan/resolve_team_name.py

# 用户指定组名后
python scripts/plan/resolve_team_name.py --team-name "你的组名"
```

详见 [mapping-rules.md](mapping-rules.md) §行匹配增强。
