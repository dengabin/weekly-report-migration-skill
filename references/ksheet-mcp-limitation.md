# 云文档格式与读取能力说明

## 你的部门表能「访问」到什么程度？

对 `https://365.kdocs.cn/l/cqGvaEAyY8lG`（`.ksheet`）：

| 操作 | smart-kmcp MCP（user-wps365） | 说明 |
|------|------------------------------|------|
| 获取文件名、file_id、分享链接 | ✅ 可以 | `kso_yundoc_get_file_meta` 已成功 |
| 读取单元格/表格内容 | ❌ 当前不行 | `kso_yundoc_extract_yundoc_content` 返回 `400008018` |
| 用 dbsheet 系列工具读写 | ❌ 当前不行 | 403 `invalid_scope`，且该 API 面向 `.dbt` 多维表，不是 `.ksheet` |

对小组 otl `cpqRAGyILoLO`：

| 操作 | MCP | 说明 |
|------|-----|------|
| 读 Markdown 正文 | ✅ 可以 | 已验证，可提取 `# 日期` + `## 姓名` |

**结论：不是「云文档读不了」，而是「MCP 内置的内容抽取器只覆盖了部分格式」；`.ksheet` 属于表格引擎，和 `.otl` 不是同一条链路。**

---

## `.ksheet` 写回与超链接（重要）

部门周报表格中的可点击链接（D 列「📄版式AI应用组26年周报」、E 列历史周报内的文内链接）**不存储在 openpyxl 的 `cell.hyperlink`**，而在 `customXml/item2.xml` 的 `hypersublink` / `filelink` 中。

| 操作 | 结果 |
|------|------|
| openpyxl `load_workbook` + `save()` 后 `update` | ❌ `customXml/item2.xml` 丢失或缩水，链接变纯文本 |
| `patch_ksheet_zip.py` 只改 `sharedStrings` + 目标 sheet XML | ✅ 405 个 hypersublink 原样保留 |

**迁移不变式**：

1. 只写入 `patch-plan.json` 中的目标 C 列单元格
2. 非目标单元格、列、子表字节级不得修改
3. 格式化仅允许改列表符号/缩进/字体，不得改正文词句
4. 写回后校验 `hypersublink` 数量与下载原文一致

下载部门表时，优先使用 `.cache` 中含完整 `customXml` 的 `.ksheet`（体积较大、hypersublink > 0），勿用 openpyxl 另存后的副本。

---

```
kdocs 链接
    │
    ├─ .otl / .docx / .pdf  ──► kso_yundoc_extract_yundoc_content ──► Markdown ✅
    │
    └─ .ksheet / .xlsx / .et ──► 同上接口 ──► 400008018 ❌
                                      │
                                      └── 应走「表格内容 API」(KDC 导出)
                                           见 wps365-read 的 get-file-content
```

- **smart-kmcp** 的 `extract_yundoc_content` 本质是 **AirPage/文档类 → Markdown** 转换器。
- **`.ksheet`** 是金山新一代表格格式，内容在表格引擎里，需要 **`GET /v7/drives/{drive_id}/files/{file_id}/content`**（KDC 格式）才能解析。
- MCP 里的 **`kso_dbsheet_*`** 是 **多维表 `.dbt`** 的 CRUD，和 **`.ksheet` 传统周报表** 不是同一类产品；且当前 OAuth 未授权 `kso.dbsheet.read` 权限。

---

## 要让 Agent 能读/写 ksheet，需要额外配什么？

### 方案 A：wps365-read + WPS_SID（推荐，可自动化读表+下载+回写）

1. 确认本机有 `wps365-read`（仓库内路径示例）：
   `D:\branch\skills\testcase\ai-testcase-generate\.cursor\skills\wps365-read`

2. 获取 **WPS_SID**（浏览器登录态 Cookie）：
   - 浏览器打开 https://365.kdocs.cn 并登录
   - F12 → Application（应用程序）→ Cookies → `365.kdocs.cn`
   - 复制名为 **`wps_sid`** 的值

3. 任选一种配置方式：

   **环境变量（临时，当前终端有效）：**
   ```powershell
   $env:WPS_SID = "你的wps_sid值"
   ```

   **或编辑 auth.yaml（持久）：**
   ```
   wps365-read/assets/config/auth.yaml
   ```
   ```yaml
   wps:
     sid: "你的wps_sid值"
     api_base: "https://api.wps.cn"
   ```

4. 验证能否读取部门表：
   ```powershell
   cd D:\branch\skills\testcase\ai-testcase-generate\.cursor\skills\wps365-read
   python skills/drive/run.py get-file-content cqGvaEAyY8lG --json
   ```

   成功时应返回 JSON，内含 `content`（Markdown 表）和 `raw`（KDC 结构）。

5. 之后在 Cursor 里说「继续周报迁移」，Agent 会用该工具链完成：
   - `get-file-content` 读表
   - `download` 下载原文件
   - `update` 写回（单元格 patch 后）

> WPS_SID 会过期，失效后重新从浏览器复制即可。

### 方案 B：手动下载（零配置，但需你动手）

1. 在金山文档网页把 `2026版式产研部-周报(副本).ksheet` 下载到本地
2. 放到 `report-migration/.cache/dept-report.ksheet`
3. 告诉 Agent：「部门表已下载，继续预览」

### 方案 C：向 smart-kmcp 提需求（长期）

请 MCP 维护方：
- 为 `.ksheet` / `.xlsx` 增加与 `get-file-content` 等价的能力，或
- 扩展 OAuth scope 并区分 `.dbt` vs `.ksheet`

---

## 和本 Skill 的关系

**方案 A 已内置为本 Skill 的步骤 -1**，加载 Skill 后 Agent 自动执行 `preflight.py`，无需用户手动配置 wps365-read 路径（可自动发现）。

| 文档 | 读取方式 |
|------|----------|
| 小组 otl | preflight → wps365-read `get-file-content`；或 MCP extract |
| 部门 ksheet | preflight → wps365-read `get-file-content` + `download` |

用户只需在首次缺凭证时提供一次 `wps_sid`。
