# 周报定位规则

## 1. 小组文档提取（`extract`）

### `heading`（默认，适用于 .otl / .docx 转 Markdown）

```json
{
  "type": "heading",
  "heading": "## 张三",
  "level": 2
}
```

- 从匹配标题行开始，到下一个同级或更高级标题为止，即为该成员内容。
- `heading` 可含 `{name}` 占位，运行时替换为 `members[].name`。

### `regex`

```json
{
  "type": "regex",
  "start": "^### 张三",
  "end": "^### ",
  "flags": "m"
}
```

用于非标准标题格式。

### `table_row`（小组文档本身是表）

```json
{
  "type": "table_row",
  "name_column_index": 0,
  "content_column_index": 2
}
```

在 Markdown 表格中按首列姓名取内容列。

---

## 2.5 部门多子表（四级部门 workbook）

部门周报常见结构：

```
[三级部门周报.xlsx]
├── Sheet: OFD业务部      ← 四级部门 A
├── Sheet: PDF业务部      ← 四级部门 B（你们可能在这）
├── Sheet: 引擎平台部     ← 四级部门 C
└── ...
```

每个子表内部再按「组 → 人」分行，按「周次」分列。

### 配置 `dept_sheet`

```json
"dept_sheet": {
  "fourth_dept_name": "PDF业务部",
  "aliases": ["PDF业务"],
  "match": "contains",
  "fallback_scan": true
}
```

若子表 tab 名固定，可直接写死：

```json
"dept_sheet": {
  "sheet_name": "PDF业务部"
}
```

### 发现子表命令

```bash
python scripts/plan/list_dept_sheets.py --config config.json --input .cache/dept-report.xlsx
```

输出示例：

```json
{
  "sheet_count": 5,
  "sheets": [{"name": "OFD业务部", ...}, {"name": "PDF业务部", ...}],
  "resolved_sheet": "PDF业务部",
  "resolve_reason": "子表名 contains 匹配: 'PDF业务部' -> 'PDF业务部'"
}
```

**只有 `resolved_sheet` 指向的子表会被写入**；其它四级部门子表完全不动。

---

## 3. 部门文档写入（`target`）

### `sheet_cell`（.xlsx / .et）

```json
{
  "type": "sheet_cell",
  "sheet": "周报",
  "row_match": { "column": "A", "contains": "张三" },
  "col_match": { "row": 1, "equals": "2026-W27" }
}
```

| 字段 | 含义 |
|------|------|
| `sheet` | 工作表名；**多子表场景留空**，由 `dept_sheet` 自动解析；单人 target 里也可省略 |
| `row_match.column` | 行锚点列（常 A 列放姓名） |
| `row_match.contains` / `equals` | 匹配组员名或「小组名-姓名」 |
| `col_match.row` | 表头行号（1-based，默认 `options.sheet_header_row`） |
| `col_match.equals` | 与 `config.week` 或 `week_aliases` 匹配 |

**行匹配增强**：若部门表按小组分块，可先匹配 `options.team_row_marker` 所在行区间，再在该区间内找姓名。

### `heading_block`（.otl 部门文档）

```json
{
  "type": "heading_block",
  "heading_path": ["2026-W27", "示例小组名", "张三"],
  "content_mode": "replace_body"
}
```

- `heading_path`：从外到内的标题链。
- `content_mode`：`replace_body` 只换标题下正文；`append` 在原有后追加。

### `docx_table_cell`

```json
{
  "type": "docx_table_cell",
  "table_index": 0,
  "row_match": { "cell": 0, "contains": "张三" },
  "col_match": { "header_row": 0, "equals": "2026-W27" }
}
```

---

## 3. 周次 / 表头模糊匹配

`week` 与表头比较前统一规范化：

1. 去首尾空格
2. 全角数字、标点转半角
3. 可选：忽略大小写

`week_aliases` 中任一命中即视为同一周。

---

## 4. 配置示例：部门表结构（单个子表内）

典型部门周报表：

| 姓名/小组 | 2026-W26 | 2026-W27 | 2026-W28 |
|-----------|----------|----------|----------|
| 示例小组名 | | | |
| 张三 | ... | **← 写入** | |
| 李四 | ... | **← 写入** | |

- `row_match`: A 列 `contains` 姓名
- `col_match`: 第 1 行 `equals` 周次

若姓名列写的是 `PDF内核组-张三`，则 `row_match.contains` 仍可用 `张三` 子串匹配。

---

## 5. 首次对齐检查清单

配置完成后，让用户确认：

- [ ] 小组文档中每位成员标题与 `extract.heading` 一致
- [ ] 部门表头本周列与 `week` / `week_aliases` 一致
- [ ] 部门 workbook 子表：`list_dept_sheets.py` 的 `resolved_sheet` 正确
- [ ] 试运行预览中目标单元格坐标正确
