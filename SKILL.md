---
name: weekly-report-migration
description: >-
  将小组周报中每位成员的本周内容，自动填入三级部门周报中对应位置。
  仅修改目标单元格/段落，不重写整份文档。Agent 必读 references/workflow/INDEX.md 按步骤1-8执行。
  用户指南见 README.md。支持金山文档（kdocs.cn）智能文档 .otl、表格 .xlsx/.et、文字 .docx。
  触发词：周报迁移、填部门周报、同步周报、weekly report migration、复制周报到部门、周报汇总。
---

---

## ⛔ Agent 必读（加载 Skill 后第一件事）

**在跑任何脚本之前**，必须先阅读 **[references/workflow/INDEX.md](references/workflow/INDEX.md)**，再**按步骤 1 → 8 依次**阅读并执行各步 MD：

1. `01-原则与用户边界.md` → 2. `02-首次配置` → 3. `03-环境预检` → 4. `04-周次与部门列` → 5. `05-提取与计划` → 6. `06-预览确认` → 7. `07-写回` → 8. `08-校验汇报`

用户使用说明见 **[README.md](README.md)**。Cursor 规则：`.cursor/rules/report-migration-agent.mdc`

---

## ⛔ Skill 加载后第一步（自动预检，必须执行）

用户触发本 Skill 后，**在读取云文档或迁移之前**，必须先在本 Skill 根目录执行：

```bash
pip install -r requirements.txt
python scripts/workflow/preflight.py
```

或一键预览（预检 + 提取 + 计划）：

```bash
python scripts/workflow/run_preview.py
```

### Agent 自动处理规则（用户不跑脚本）

**硬性规定**（详见 [agent-behavior.md](references/agent-behavior.md)）：

- ❌ **禁止**让用户自己运行 `python scripts/...`、pip、或任何终端命令
- ❌ **禁止**让用户手动配置环境、下载/上传云文档、编辑 config
- ❌ **禁止**向用户索要组成员名单（必须从组内 otl 自动解析）
- ❌ **禁止**在用户未指定周次时询问「要哪一周」（默认最新一期）
- ✅ **所有**脚本必须由 Agent 通过 Shell 工具执行
- ✅ 用户唯一可能需要做的事：在对话里**粘贴** `wps_sid`（缺凭证时）；Agent 须**详细引导 + 原地等待 + 自动续跑**

流程：

1. **静默执行** `pip install -r requirements.txt`（若缺依赖）→ `python scripts/workflow/preflight.py` → 读 `.cache/preflight-report.json`
2. 若 `config.json` 缺文档链接 → **AskQuestion** 依次收集：组内周报链接 → 部门周报链接（**不问成员**）→ Agent 写入 config
3. **解析周次**（见 [week-resolution.md](references/week-resolution.md)）：用户未指定则用 otl 最新周；「上周」等按系统日期回溯
4. **检查部门表是否有本周列**：无列则先插入再迁移；有列则仅覆盖该列
5. 根据 `status` 分支：
   | status | Agent 动作（全自动，不停下让用户跑命令） |
   |--------|----------------------------------------|
   | `ready` | 立即执行 `python scripts/workflow/run_preview.py`，展示迁移预览，AskQuestion 确认是否写回 |
   | `need_wps_sid` | 按 [wps-sid-guide.md](references/wps-sid-guide.md) **逐步引导** → AskQuestion 等待用户**下一条消息**粘贴 `wps_sid` → Agent 执行 `setup_wps_sid.py` → 重跑 preflight → **自动续跑** run_preview，不中断 |
   | `need_deps` | Agent 执行 `pip install -r requirements.txt` → 重跑 preflight |
   | `need_wps365_read` | Agent 尝试在常见路径发现；失败则 AskQuestion 要 wps365-read 目录路径，写入 config 后重跑 |
   | `need_config` | AskQuestion 收集组内/部门文档链接（**不问成员、不问周次**）→ `build_config_from_extracted.py` |
   | `dept_read_failed` | 按 wps-sid-guide 引导用户粘贴新 `wps_sid` → 更新并重跑全流程 |
6. **不得**在 preflight `ready` 之前用 MCP `extract_yundoc_content` 读 ksheet。
7. 小组 otl 若 preflight 未拉取，Agent 用 MCP 提取并写入 `.cache/team-report.md`，再 `extract_otl_weekly.py` → **`build_config_from_extracted.py` 自动填充 members**。

### WPS_SID 存放位置（方案 A 已内置）

本 Skill 目录：`assets/config/auth.yaml`（从 `auth.yaml.template` 复制）

```yaml
wps:
  sid: "你的wps_sid"
  api_base: "https://api.wps.cn"
```

Agent 收集到用户粘贴的 sid 后：

```bash
python scripts/workflow/setup_wps_sid.py "<wps_sid>"
python scripts/workflow/preflight.py
```

凭证说明见 [references/ksheet-mcp-limitation.md](references/ksheet-mcp-limitation.md)。

---

## 快速开始（你怎么用）

### 一次性准备（用户零命令）

1. 确保 `config.json` 已存在（AI应用组 示例已就绪）。
2. 用户只说 **「周报迁移」**。
3. Agent 自动跑完全部脚本；**仅当缺 `wps_sid`** 时，请用户在**下一条聊天消息**粘贴 Cookie 值（不是让用户跑脚本）。
4. 粘贴后 Agent 自动配置、预检、预览，用户只需最后点确认写回。

### 每周使用（用户一句话即可）

在 Cursor 对话里说：

> 周报迁移

或指定周次：

> 周报迁移，粘贴上一周的

或：

> 用周报迁移 skill，week 是 2026-07-02

**周次规则**：

- 用户**没说**哪一周 → Agent **不问**，自动取组内 otl **最新一期**
- 用户说「上周」「上一周」→ 按**系统当前日期**在 otl 中取上一期
- 部门表必须与组内周报**同一周次、同一批人名**写入

Agent 会：读小组文档 → 自动解析成员 → 检查/插入部门表周列 → 预览 → **等你确认** → 只改对应格子写回。

### 你会看到什么

1. **子表解析结果**：例如 `resolved_sheet: "PDF业务部"`，`resolve_reason: 子表名 contains 匹配`
2. **迁移预览表**：成员 | 目标子表 | 单元格（如 `C5`）| 内容摘要
3. **确认后**才写入；其它子表、其它组、其它周列**不会被改动**

---

## 目标

从**小组周报**提取本周每位成员的内容，写入**部门周报**中由「人名 + 周次/日期 + 小组」决定的对应位置。**只改内容区，不改文档结构、标题、合并单元格或排版。**

## 前置依赖

| 能力 | 用途 | 获取方式 |
|------|------|----------|
| `user-wps365` MCP | 读/写云文档 | 配置 `smart-kmcp`（见 `smart-kmcp` skill） |
| 本目录 `config.json` | 成员映射与文档定位 | 首次使用从 `config.template.json` 复制并填写 |

⛔ **云文档约束**：输入含 `kdocs.cn` / `365.kdocs.cn` 链接时，**禁止** WebFetch / curl。必须通过 MCP：`kso_yundoc_get_file_meta` → `kso_yundoc_extract_yundoc_content`。

⚠️ **格式差异（重要）**：

| 格式 | MCP `extract_yundoc_content` | 读表/写表推荐方式 |
|------|------------------------------|-------------------|
| `.otl` 智能文档 | ✅ | MCP 即可 |
| `.ksheet` / `.xlsx` / `.et` 表格 | ❌ 常返回 `400008018` | **wps365-read** + `WPS_SID` → `get-file-content` / `download` / `update` |

详见 [references/ksheet-mcp-limitation.md](references/ksheet-mcp-limitation.md)。

## 配置文件

路径：**本 SKILL.md 同级** `config.json`。不存在时复制 `config.template.json` 并引导用户填写。

关键字段：

- `team_report` / `dept_report`：云文档 `link_id` 或完整 URL
- `week`：本次周次（如 `2026-W27` 或 `2026-07-07`），用于在部门表中定位列/区块
- `team_name`：小组名，用于在部门表中定位行/区块
- `dept_sheet`：**四级部门子表定位**（见下节，部门周报为多 sheet 时必填）
- `members[]`：每人 `name`、可选 `aliases`、`extract`（小组文档中的定位规则）、`target`（部门文档中的定位规则）

### 部门多子表（四级部门）

部门周报通常是**一个 xlsx/et 文件、多个 sheet**，每个 sheet 对应一个四级部门（或类似划分）。迁移时**只打开属于你们四级部门的那张子表**，再在该表内按「组名 + 人名 + 周次」定位单元格。

在 `config.json` 中配置 `dept_sheet`：

```json
"dept_sheet": {
  "fourth_dept_name": "PDF业务部",
  "aliases": ["PDF业务", "业务部-PDF"],
  "match": "contains",
  "fallback_scan": true
}
```

| 字段 | 含义 |
|------|------|
| `fourth_dept_name` | 四级部门名，与子表 tab 名模糊匹配 |
| `aliases` | 子表名的其它写法 |
| `match` | `contains`（默认）/ `equals` / `regex` |
| `sheet_name` | 若已知精确子表名，直接写此项（优先级最高） |
| `fallback_scan` | 为 true 时，再用 `team_name` 在子表名中兜底搜索 |

**解析顺序**：`sheet_name` 精确命中 → `fourth_dept_name` + `aliases` 匹配子表 tab → `team_name` 出现在子表名中。

步骤 2 必须先执行 `scripts/plan/list_dept_sheets.py` 或等价逻辑，**向用户展示** `resolved_sheet`；若未命中，列出全部子表名请用户指定 `dept_sheet.sheet_name`。

定位规则语法见 [references/mapping-rules.md](references/mapping-rules.md)。

## 工作流（必须按序执行）

```
任务进度：
- [ ] -1. 自动预检（preflight.py / run_preview.py）
- [ ] 0. 加载配置，解析文档元信息
- [ ] 1. 读取小组周报，按成员提取内容
- [ ] 2. 读取部门周报，解析目标位置
- [ ] 3. 生成迁移计划（预览），用户确认
- [ ] 4. 执行局部写入
- [ ] 5. 校验并汇报结果
```

### 步骤 -1：自动预检（wps365-read 方案 A）

在 Skill 根目录执行：

```bash
python scripts/workflow/preflight.py
```

预检内容：

| 检查项 | 说明 |
|--------|------|
| Python 依赖 | openpyxl、pyyaml 等 |
| wps365-read | 自动发现路径 |
| WPS_SID | `assets/config/auth.yaml` 或环境变量 |
| 部门表可读 | `get-file-content` 拉取 ksheet → `.cache/dept-report.md` |
| 子表解析 | 列出全部 sheet，匹配 `dept_sheet` → `resolved_sheet` |
| 小组 otl | 拉取到 `.cache/team-report.md` |
| 部门表下载 | `download` 到 `.cache/`（供后续 update 回写） |

输出：`.cache/preflight-report.json`（Agent 必读）。

一键到预览计划：

```bash
python scripts/workflow/run_preview.py
```

### 步骤 0：加载配置

1. 读取 `config.json`；缺失或 `members` 为空 → 用 `AskQuestion` 收集：小组/部门文档链接、本周日期、成员名单。
2. 对 `team_report`、`dept_report` 各调用一次 `kso_yundoc_get_file_meta`，记录 `file_id`、`drive_id`、`name`、扩展名（`.otl` / `.xlsx` / `.et` / `.docx`）。
3. 若小组与部门文档格式组合不在支持列表，告知用户并停止。

**支持格式**

| 小组源 | 部门目标 | 写入方式 |
|--------|----------|----------|
| `.otl` | `.otl` | Markdown 段落级局部替换 + `kso_airpage_import_markdown_data` 全量写回（基于原文 patch，非重建） |
| `.otl` / `.docx` | `.ksheet` | 下载部门表 → 解析子表 → 单元格 patch → `update` 回传（**MCP 无法直接读 ksheet，需 wps365-read 或本地下载**，见 [references/ai-app-group.md](references/ai-app-group.md)） |
| `.otl` / `.docx` | `.docx` | 下载 → `scripts/patch/patch_docx.py` 改段落/表格单元格 → `update` 回传 |

### 步骤 1：提取小组周报

1. 若 `.cache/team-report.md` 已由 preflight 生成，**直接使用**；否则 MCP `kso_yundoc_extract_yundoc_content` 获取 otl Markdown 并保存。
2. **otl 按日期区块**：`python scripts/extract/extract_otl_weekly.py --markdown .cache/team-report.md --output .cache/extracted.json`
3. 检查 `extracted.json`：每人 `content` 非空；空则列出名单请用户补充。

### 步骤 2：解析部门周报目标位置

按 `dept_report` 扩展名分支：

**表格（`.ksheet` / `.xlsx` / `.et`）— 推荐流程（多子表）**

1. 使用 preflight 已生成的 `.cache/dept-report.md` 与 `preflight-report.json` 中的 `resolved_sheet`。
2. 若子表未命中，根据 `all_sheets` 列表请用户指定 `dept_sheet.sheet_name` 后重跑 preflight。
3. 生成补丁计划：  
   `python scripts/plan/plan_sheet_patches.py --config config.json --dept-kdc-json .cache/dept-content.json --extracted .cache/extracted.json --output .cache/patch-plan.json`
4. 或使用一键：`python scripts/workflow/run_preview.py`

本地 xlsx 备选：`--input-xlsx .cache/dept-report.xlsx` + `scripts/plan/list_dept_sheets.py`。

**智能文档（`.otl`）**

1. 在 Markdown 中按 `target.heading_path` 或 `target.anchor_text` 定位每人内容块（标题与小组/姓名/周次标签）。
2. 仅替换该标题下正文，**保留**标题、上级结构、表格骨架与其它成员区块。

**文字文档（`.docx`）**

1. 下载原文：`download` 到 `.cache/dept-report.docx`。
2. `scripts/plan/plan_docx_patches.py` 按表格行/段落样式定位。

### 步骤 3：预览与确认（强制）

向用户展示迁移计划表格：

| 成员 | 源字数 | 目标位置 | 原内容摘要（前 80 字） | 新内容摘要（前 80 字） |
|------|--------|----------|------------------------|------------------------|

- 使用 `AskQuestion`：**确认执行** / **取消** / **仅迁移指定成员（列出姓名）**。
- 未确认前**不得**写回云文档。

### 步骤 4：执行局部写入

**表格（`.ksheet`）** — 必须用 ZIP/XML 级补丁，**禁止 openpyxl save**：

```bash
python scripts/patch/patch_ksheet_zip.py --config config.json --input .cache/<部门表>.ksheet --plan .cache/patch-plan.json --extracted .cache/extracted.json --output .cache/dept-report-patched.ksheet
```

或一键：`python scripts/workflow/apply_migration.py --upload`

**表格（`.xlsx` / `.et`）**：

```bash
python scripts/patch/patch_sheet.py --config config.json --input .cache/dept-report.xlsx --plan .cache/patch-plan.json --output .cache/dept-report-patched.xlsx
```

然后通过 **wps365-read**（预检已配置 WPS_SID）：

```bash
cd <wps365-read-root>
python skills/drive/run.py update <dept_link_id> <patched-file> --confirm
```

**必须用 wps365-read 的 `update`**，不要用 MCP `write` 写表格。

**智能文档**：

1. 在内存中对步骤 1 读到的**完整 Markdown** 做字符串/块级替换（每人一处）。
2. `kso_airpage_import_markdown_data(file_id=data.id, markdown_content=patched_full_markdown)`。
3. 写回前对比：除目标块外，其余段落哈希/行数应与原文一致（脚本 `scripts/patch/verify_otl_patch.py` 可辅助）。

**文字文档**：`patch_docx.py` 后 `update` 回传。

### 步骤 5：校验与汇报

1. 再次读取部门文档，核对每位成员目标位置内容是否与 `extracted.json` 一致。
2. 输出：成功 N 人、跳过 M 人、失败列表及原因。
3. 若有失败，**不要**重复全量覆盖；仅对失败成员重试步骤 4。

## 不变式（Anti-patterns）

**写死规则（违反即失败）** — 完整版见 [agent-behavior.md](references/agent-behavior.md) §6：

- ❌ **禁止修改非目标单元格**：未列入 `patch-plan.json` 的格子、列、子表，一个字节都不能动
- ❌ **禁止用 openpyxl `save()` 写回 `.ksheet`**：会丢失 `customXml` 超链接
- ❌ **禁止改正文内容**：`content_raw` 为真源；格式化**仅**允许列表符、缩进、续行缩进、单元格样式（从同行历史列复制）
- ❌ **禁止修改用户未指定周次的列**：只粘贴/覆盖**本次 `config.week`** 对应列
- ✅ **部门表无本周列时**：按 [week-resolution.md](references/week-resolution.md) **插入新列**后再写入；有列则仅覆盖该列内容格
- ✅ **仅目标内容列写入**；D 列文件链接、E 列历史周报原样保留
- ✅ **`.ksheet` 必须用** `scripts/patch/patch_ksheet_zip.py`；写回后校验 `hypersublink` 数量不变

其它反模式：

- ❌ 用 `kso_airpage_import_markdown_data` **重建**部门文档（会丢格式）
- ❌ 用 `update` 覆盖 `.otl` / `.dbt`
- ❌ 用 `write` 写 `.xlsx` / `.et`
- ❌ 未读原文档就生成新 Markdown 上传
- ✅ 始终：**先读全量 → 局部改 → 写回**；表格走二进制 patch + `update`

## 首次配置引导

用户**首次**使用时，Agent 用 **AskQuestion** 依次收集（**不要**让用户手改文件）：

1. **组内周报链接**（`.otl`）
2. **部门周报链接**（`.ksheet` / 表格）
3. （可选）四级部门子表名 — 仅当预检无法自动解析 `resolved_sheet` 时再问

**不要向用户收集**：

- ❌ 成员名单 → 读组内 otl 后 `extract_otl_weekly.py` + `build_config_from_extracted.py` 自动生成
- ❌ 周次（用户未主动说时）→ 默认最新一期

Agent 写入 `config.json` 后保存；后续每周用户通常只需说「周报迁移」。

## 辅助脚本

脚本目录结构见 [scripts/README.md](scripts/README.md)。

| 脚本 | 作用 |
|------|------|
| `scripts/workflow/preflight.py` | **Skill 加载首步**：依赖/WPS_SID/wps365-read/读表/子表/下载 |
| `scripts/workflow/setup_wps_sid.py` | 写入 `assets/config/auth.yaml` |
| `scripts/workflow/run_preview.py` | 一键：预检 → 提取 → 迁移计划预览 |
| `scripts/workflow/apply_migration.py` | 一键：格式化 → 计划 → patch → 可选上传 |
| `scripts/lib/wps365_bridge.py` | wps365-read 路径发现与调用封装 |
| `scripts/extract/extract_otl_weekly.py` | otl 按 `# 日期` + `## 姓名` 提取（AI应用组格式） |
| `scripts/plan/build_config_from_extracted.py` | 从 extracted.json 生成 config.json |
| `scripts/plan/plan_sheet_patches.py` | 根据表头生成 Excel 补丁计划（`--input-xlsx` 支持多子表） |
| `scripts/patch/patch_ksheet_zip.py` | **`.ksheet` 专用**：ZIP/XML 单元格补丁，保留超链接 |
| `scripts/patch/patch_sheet.py` | 对 `.xlsx`/`.et` 做单元格级写入（**不可用于 .ksheet**） |
| `scripts/plan/plan_docx_patches.py` | 生成 docx 补丁计划 |
| `scripts/patch/patch_docx.py` | 对 docx 做局部段落/单元格写入（需 `python-docx`） |
| `scripts/patch/verify_otl_patch.py` | 校验 otl 补丁前后非目标区域未变 |

中间产物统一放 `.cache/`，勿提交仓库。写回云端成功后**默认清理**（`cleanup_cache.py`）；用户要求保留时 `apply_migration.py --keep-cache`。

## 与其它 Skill 协作

- **smart-kmcp**：云文档读写 MCP 工具说明
- **wps365-read / drive**：本地 `run.py` 命令（`download` / `update` / `get-file-content`）— 若用户环境已安装，表格分支优先用其 `download` + `update`
- 无 MCP 时：提示用户配置 `user-wps365`，或手动下载文档到本地后指定 `--local-team` / `--local-dept` 路径（脚本支持）

## 故障排查

| 现象 | 处理 |
|------|------|
| preflight `need_wps_sid` | 按 [wps-sid-guide.md](references/wps-sid-guide.md) 引导 → 用户对话粘贴 → `setup_wps_sid.py` → 自动续跑 |
| preflight `dept_read_failed` | WPS_SID 过期，更新 auth.yaml |
| preflight `need_wps365_read` | 设置 `wps365_read.root` 或安装 wps365-read |
| 部门表定位失败 | 先 `scripts/plan/list_dept_sheets.py` 看全部子表名；调整 `dept_sheet.fourth_dept_name` 或设 `sheet_name` |
| 子表对了但人找不到 | 检查 `week` 与表头一致；`team_name` 是否出现在组标题行；`row_match` 列是否为人名列 |
| 写入后格式乱了 / 链接变文字 | 是否误用 openpyxl 写 `.ksheet`；应改用 `scripts/patch/patch_ksheet_zip.py`；下载件须含 `customXml/item2.xml` hypersublink |
| 部门表没有本周列 | 按 [week-resolution.md](references/week-resolution.md) 插入新列后再迁移；禁止改动其它列 |
| 某人内容为空 | 小组文档未写或标题不匹配；跳过该成员并在结果中标注 |

## 延伸阅读

| 文档 | 用途 |
|------|------|
| [README.md](README.md) | **用户使用指南**（触发词、首次流程、注意点） |
| [references/workflow/INDEX.md](references/workflow/INDEX.md) | **Agent 分步执行索引（必读）** |
| [references/agent-behavior.md](references/agent-behavior.md) | Agent 约束总览（指向 workflow） |
| [references/wps-sid-guide.md](references/wps-sid-guide.md) | 引导用户获取 wps_sid |
| [references/week-resolution.md](references/week-resolution.md) | 周次默认、上周、部门列插入 |
| [references/mapping-rules.md](references/mapping-rules.md) | 定位规则与表示例 |
| [references/ksheet-mcp-limitation.md](references/ksheet-mcp-limitation.md) | 格式能力与写回技术 |
| [references/ai-app-group.md](references/ai-app-group.md) | AI应用组示例配置 |
| [config.template.json](config.template.json) | 配置字段说明 |
