# scripts 目录说明

> **用户使用指南**请看项目根目录 **[../README.md](../README.md)**。  
> 本文档面向 **Agent / 开发者**，说明脚本布局、调用顺序、参数、缓存策略与注意事项。

Agent 执行迁移时，须先按 **[../references/workflow/INDEX.md](../references/workflow/INDEX.md)** 步骤 1→8 阅读约束 MD，再调用本目录脚本。

---

## 目录结构

```
scripts/
├── lib/                    # 共享库（不直接运行）
│   ├── paths.py            # SKILL_ROOT、.cache 路径
│   ├── sheet_utils.py      # 子表名解析、周次列匹配
│   └── wps365_bridge.py    # wps365-read 调用、WPS_SID 解析
├── workflow/               # 编排入口（Agent 主要调用）
│   ├── preflight.py        # 环境预检、拉取云文档
│   ├── run_preview.py      # 一键预览（预检→提取→格式化→计划）
│   ├── apply_migration.py  # 写回 + 上传 + 默认清缓存
│   ├── cleanup_cache.py    # 清理 .cache 中间产物
│   └── setup_wps_sid.py    # 写入 wps_sid 凭证
├── extract/                # 读取与格式化小组 otl 周报
│   ├── extract_otl_weekly.py
│   ├── format_otl_for_ksheet.py
│   └── extract_team_reports.py
├── plan/                   # 生成迁移计划
│   ├── plan_sheet_patches.py
│   ├── build_config_from_extracted.py
│   └── list_dept_sheets.py
├── patch/                  # 局部写入
│   ├── patch_ksheet_zip.py # .ksheet 唯一合法写回方式
│   ├── patch_sheet.py      # .xlsx 备选（.ksheet 会拒绝）
│   └── patch_docx.py       # .docx 场景（非主流程）
└── dev/                    # 调试 inspect_*.py（日常迁移勿用）
```

所有命令均在 **Skill 根目录**（`report-migration/`）执行。

---

## 标准执行顺序

```
pip install -r requirements.txt          # 缺依赖时静默安装
    ↓
preflight.py                           # 步骤 3：预检 + 拉取 otl/ksheet
    ↓
run_preview.py [--week YYYY-MM-DD]     # 步骤 5–6：提取、格式化、生成计划
    ↓
[AskQuestion 用户确认写回]              # 步骤 6：未确认不得 upload
    ↓
apply_migration.py --upload            # 步骤 7–8：patch → 校验 → 上传 → 清缓存
```

分步调用（与 `run_preview` / `apply_migration` 内部等价）：

```bash
python scripts/extract/extract_otl_weekly.py --markdown .cache/team-report.md --output .cache/extracted.json
python scripts/extract/format_otl_for_ksheet.py --input .cache/extracted.json --kdc-json .cache/dept-content.json --in-place
python scripts/plan/plan_sheet_patches.py --config config.json --dept-kdc-json .cache/dept-content.json --extracted .cache/extracted.json --output .cache/patch-plan.json
python scripts/patch/patch_ksheet_zip.py --config config.json --input .cache/<部门表>.ksheet --plan .cache/patch-plan.json --extracted .cache/extracted.json --output .cache/dept-report-patched.ksheet
```

---

## workflow/ 入口脚本详解

### `preflight.py` — 预检

| 参数 | 说明 |
|------|------|
| `--config` | 默认 `config.json` |
| `--output` | 报告路径，默认 `.cache/preflight-report.json` |
| `--skip-download` | 不下载部门 ksheet 到本地 |

**退出码**：`0` 就绪；`1` 失败；`2` 缺 `wps_sid`（`need_wps_sid`）

**产出**（写入 `.cache/`）：

| 文件 | 说明 |
|------|------|
| `preflight-report.json` | Agent 必读：各检查项 status |
| `team-report.md` | 组内 otl Markdown |
| `dept-content.json` | 部门表 KDC JSON（表头、子表） |
| `dept-report.md` | 部门表 Markdown 摘要 |
| `*.ksheet` | 部门表本地下载件（含 `customXml` 的完整副本） |

---

### `run_preview.py` — 一键预览

| 参数 | 说明 |
|------|------|
| `--config` | 默认 `config.json` |
| `--week` | 覆盖 otl 日期区块，如 `2026-07-02`；未指定则用 otl 最新一期 |

**不写回、不上传、不清理缓存**。产出 `extracted.json`、`patch-plan.json` 等供后续 `apply_migration` 使用。

---

### `apply_migration.py` — 写回与上传

| 参数 | 说明 |
|------|------|
| `--config` | 默认 `config.json` |
| `--upload` | 校验通过后上传到云文档（**用户确认后**才加此参数） |
| `--input` | 部门 ksheet 本地路径；默认自动选 `.cache` 中 hypersublink 最多的 `.ksheet` |
| `--skip-download` | 上传前不重新 download 云文档 |
| `--skip-bullet-format` | 保留 otl 原文 `-` 列表符（默认转为 `•/◦/▪`） |
| `--link-id` | 覆盖 config 中的部门文档 link_id |
| **`--keep-cache`** | **写回成功后保留 `.cache`**（见下文「缓存策略」） |

**退出码**：

| 码 | 含义 |
|----|------|
| 0 | 成功（本地 patch 或已上传） |
| 1 | 计划未全部 ready / 缺输入文件 |
| 2 | patch 脚本失败 |
| 3 | 写后校验失败 / hypersublink 为空 |
| 4 | 缺 WPS_SID 或 wps365-read |
| 5 | 上传失败 |
| 6 | 上传成功但缓存清理失败 |

不加 `--upload` 时仅生成本地 `dept-report-patched.ksheet`，**不清理缓存**。

---

### `cleanup_cache.py` — 清理缓存

| 参数 | 说明 |
|------|------|
| `--cache-dir` | 默认 `.cache` |
| `--dry-run` | 仅列出将删除项，不实际删除 |

```bash
# 预览
python scripts/workflow/cleanup_cache.py --dry-run

# 实际清理
python scripts/workflow/cleanup_cache.py
```

---

### `setup_wps_sid.py` — 配置凭证

```bash
python scripts/workflow/setup_wps_sid.py "<用户粘贴的 wps_sid>"
```

写入 `assets/config/auth.yaml`。用户**只在对话中粘贴**，不自行跑命令；Agent 收到后执行并**自动续跑** preflight。

---

## 缓存策略（`.cache/`）

中间产物统一放在 Skill 根目录 `.cache/`，**勿提交 git**。

### 默认：写回成功后自动清理

`apply_migration.py --upload` 上传**成功**后，会自动调用 `cleanup_cache.py`，删除 `.cache` 下全部文件与子目录，**保留空 `.cache` 文件夹**。

典型被清理项：

- 下载的 `*.ksheet` / `*.xlsx`
- `team-report.md`、`dept-report.md`、`dept-content.json`
- `extracted.json`、`patch-plan.json`
- `dept-report-patched.ksheet`、`apply-report.json`
- 调试残留 `test-*.xlsx` 等

### 何时清理 / 不清理

| 场景 | 是否清理 | Agent 做法 |
|------|----------|------------|
| `--upload` 成功，用户未提保留 | ✅ 自动清理 | 默认 `apply_migration.py --upload` |
| 用户说「保留缓存」「不要清理 .cache」「留档排查」 | ❌ 不清理 | 加 `--keep-cache` |
| 仅 `run_preview`、未写回 | ❌ 不清理 | 后续 apply 还要用 |
| `apply_migration` 未加 `--upload`（仅本地 patch） | ❌ 不清理 | 便于检查 patched 文件 |
| patch / 校验 / 上传任一步失败 | ❌ 不清理 | 便于重试步骤 5–7 |
| 用户事后要求清理 | ✅ 手动清理 | `cleanup_cache.py` |

### 用户话术 → Agent 参数

| 用户说法 | Agent 参数 / 命令 |
|----------|-------------------|
| （默认，迁移成功） | `apply_migration.py --upload` |
| 保留缓存 / 不要清理 | `apply_migration.py --upload --keep-cache` |
| 只预览不写回 | `run_preview.py`（不调用 apply） |
| 同步上周 | `run_preview.py --week <日期>` 或先更新 `config.week` |
| 不要改列表符 | `apply_migration.py --upload --skip-bullet-format` |
| 手动清缓存 | `cleanup_cache.py` |

向用户汇报成功时可顺带一句：「本地中间文件已清理。」（若用了 `--keep-cache` 则说「已按你要求保留 .cache」）

---

## 子目录脚本速查

### extract/

| 脚本 | 用途 |
|------|------|
| `extract_otl_weekly.py` | 按 `# 日期` + `## 姓名` 从 otl Markdown 提取；`--week` 可选 |
| `format_otl_for_ksheet.py` | 列表符、缩进、续行对齐；默认从同行 E 列参考样式 |
| `extract_team_reports.py` | 多源 otl 合并提取（少用） |

### plan/

| 脚本 | 用途 |
|------|------|
| `plan_sheet_patches.py` | 生成 `patch-plan.json`（成员→单元格映射） |
| `build_config_from_extracted.py` | 从 `extracted.json` 回填 `config.members[]` |
| `list_dept_sheets.py` | 列出部门表子表名（定位 AI应用组 等） |

### patch/

| 脚本 | 用途 |
|------|------|
| **`patch_ksheet_zip.py`** | **`.ksheet` 唯一写回路径**：只改 `sharedStrings` + 目标 sheet XML |
| `patch_sheet.py` | `.xlsx` 局部 patch；对 `.ksheet` 直接拒绝 |
| `patch_docx.py` | Word 周报场景 |

---

## 关键约束（违反会导致链接丢失或格式错误）

1. **`.ksheet` 禁止 openpyxl `save()`** — 会破坏 `customXml/item2.xml` 中 `hypersublink`（D 列「📄组内周报」变纯文本）
2. **patch 输入** — 优先使用含完整 `customXml`、体积较大的原始下载 `.ksheet`（`hypersublink` > 0）
3. **成员名单** — 只从 otl `## 姓名` 自动解析，禁止让用户手填
4. **写回范围** — 仅改指定周次的**内容列**；不改历史周、其它子表、已有超链接
5. **内容真源** — `content_raw` 为语义真源；`content` 仅排版（符号/缩进）；`strict_verbatim` 校验 plan 与 extracted 一致
6. **确认门控** — 步骤 6 用户确认前不得 `--upload`
7. **周次** — 用户未指定时不询问；默认 otl 最新一期（见 `references/week-resolution.md`）
8. **部门表无本周列** — 须插入新列再迁移（ZIP/XML 级，禁止 openpyxl 整文件保存）；见 workflow 步骤 4

---

## Agent 与用户分工

| 用户 | Agent |
|------|-------|
| 对话触发「周报迁移」 | 执行全部 `python scripts/...` |
| 首次提供组内/部门文档链接 | 写入 `config.json` |
| 缺凭证时粘贴 `wps_sid` | `setup_wps_sid.py` → 续跑 |
| 预览后点「确认写回」 | `apply_migration.py --upload` |
| 可选：说「保留缓存」 | 加 `--keep-cache` |

**禁止**让用户运行 `pip`、下载上传云文档、手改 `config.json`、提供成员名单。

---

## 故障排查速查

| 现象 | 检查 |
|------|------|
| `need_wps_sid` / `dept_read_failed` | 引导用户粘贴 sid → `setup_wps_sid.py` |
| hypersublink 为 0 | 换用 `.cache` 中原始大体积 ksheet，勿用 openpyxl 另存文件 |
| 补丁未全部 ready | 组内 otl 该周缺 `## 姓名` 或姓名与部门表 B 列不一致 |
| 换行/缩进不对 | 检查 `format_otl_for_ksheet.py` 是否执行；C 列样式应从 E 列复制 |
| 上传成功但浏览器旧内容 | 提醒用户 **Ctrl+F5** 强刷 |

更多技术细节：[../SKILL.md](../SKILL.md)、[../references/ksheet-mcp-limitation.md](../references/ksheet-mcp-limitation.md)

---

## 相关文档

| 文档 | 用途 |
|------|------|
| [../README.md](../README.md) | 用户指南（触发词、首次流程） |
| [../references/workflow/INDEX.md](../references/workflow/INDEX.md) | Agent 分步执行索引 |
| [../references/wps-sid-guide.md](../references/wps-sid-guide.md) | 获取 wps_sid |
| [../references/week-resolution.md](../references/week-resolution.md) | 周次与部门列 |
| [../references/mapping-rules.md](../references/mapping-rules.md) | 行列定位规则 |
