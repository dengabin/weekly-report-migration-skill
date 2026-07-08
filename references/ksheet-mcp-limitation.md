# 云文档格式与读取能力说明

## `.ksheet` 与 MCP 的限制

| 操作 | smart-kmcp MCP（user-wps365） | 说明 |
|------|------------------------------|------|
| 获取文件名、file_id、分享链接 | ✅ 可以 | `kso_yundoc_get_file_meta` |
| 读取 `.ksheet` 单元格内容 | ❌ 通常不行 | `kso_yundoc_extract_yundoc_content` 常返回 `400008018` |
| 用 dbsheet 系列工具读写 | ❌ 通常不行 | 面向 `.dbt` 多维表，不是 `.ksheet` |

| 操作 | MCP | 说明 |
|------|-----|------|
| 读小组 `.otl` Markdown | ✅ 可以 | 可提取 `# 日期` + `## 姓名` |

**结论：`.ksheet` 需走 wps365-read 的 KDC 导出链路，不能依赖 MCP 的文档抽取器。**

---

## `.ksheet` 写回与超链接（重要）

部门周报表格 D 列等可点击链接**不存储在 openpyxl 的 `cell.hyperlink`**，而在 `customXml/item2.xml` 的 `hypersublink` / `filelink` 中。

| 操作 | 结果 |
|------|------|
| openpyxl `load_workbook` + `save()` 后 `update` | ❌ `customXml` 丢失，链接变纯文本 |
| `patch_ksheet_zip.py` 只改 `sharedStrings` + 目标 sheet XML | ✅ 超链接原样保留 |

**迁移不变式**：

1. 只写入 `patch-plan.json` 中的目标内容列单元格
2. 非目标单元格、列、子表字节级不得修改
3. 格式化仅允许改列表符号/缩进/样式，不得改正文词句
4. 写回后校验 `hypersublink` 数量与下载原文一致

下载部门表时，使用含完整 `customXml` 的原始 `.ksheet`（体积较大、hypersublink > 0），勿用 openpyxl 另存后的副本。

---

## 格式链路示意

```
kdocs 链接
    │
    ├─ .otl / .docx / .pdf  ──► extract_yundoc_content ──► Markdown ✅
    │
    └─ .ksheet / .xlsx / .et ──► 同上接口 ──► 常失败 ❌
                                      │
                                      └── wps365-read get-file-content (KDC)
```

---

## 要让 Agent 能读/写 ksheet

### 方案 A：内置 wps365-read + WPS_SID（本 Skill 默认）

本仓库 **`vendor/wps365-read/`** 已随 Skill 一起发布，用户 clone 后无需再安装。

凭证：浏览器 `wps_sid` → 本 Skill `assets/config/auth.yaml`（Agent 执行 `setup_wps_sid.py`）。

### 方案 B：手动下载部门表

1. 浏览器下载部门 `.ksheet` 到 `.cache/`
2. 告诉 Agent：「部门表已下载，继续预览」

---

## 和本 Skill 的关系

| 文档 | 读取方式 |
|------|----------|
| 小组 otl | preflight → wps365-read；或 MCP extract |
| 部门 ksheet | preflight → wps365-read `get-file-content` + `download` |

用户只需在首次缺凭证时粘贴一次 `wps_sid`。
