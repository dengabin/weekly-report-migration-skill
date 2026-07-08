# IO Details

按需读取这个文件；只有在需要理解读写能力边界、输出格式差异、发送云文档消息或常见错误时再加载。

## 读取与写回支持范围

| 操作 | 支持类型 | 行为 |
|------|----------|------|
| `get-file-content`（别名 `read` / `extract`） | 所有主流格式：智能文档、文字文档、表格、演示、PDF/OFD、网页、图片、纯文本/代码等（完整列表见 SKILL.md） | 云文档内容提取解析；支持本地文件直接解析 |
| `write` | 智能文档（`.otl`）、文字文档（`.docx` / `.doc` / `.wps`）、PDF（`.pdf`） | 智能文档插入；文字/PDF 转换后覆盖 |
| `update` | 任意可上传文件 | 本地文件整文件覆盖为新版本 |

## `get-file-content`（别名 `read` / `extract`）

支持两种来源：

1. **云文档**：开放平台能力 **[获取文件内容](https://365.kdocs.cn/3rd/open/documents/app-integration-dev/wps365/server/yundoc/file/get-file-content)**：`GET /v7/drives/{drive_id}/files/{file_id}/content`
2. **本地文件**：`POST /v7/coop/asyn_export/create_job` 创建解析任务 → `GET /v7/coop/asyn_export/{task_id}/query_job` 轮询（默认 2s 间隔，最长 300s），传本地路径时自动识别

### 支持的文档类型

完整列表见 [SKILL.md](../SKILL.md) 的「内容提取支持的文档类型」表。包括但不限于：

- **智能文档** `.otl`（支持 `--include-elements` 元素筛选）
- **文字文档** `.docx` `.doc` `.wps` `.rtf` 等
- **演示文档** `.pptx` `.ppt` `.dps` 等
- **PDF/OFD** `.pdf` `.ofd`
- **表格文档** `.xlsx` `.xls` `.et` `.csv` `.ksheet` 等
- **网页** `.html` `.mht` 等
- **图片** `.jpg` `.png` `.svg` `.psd` 等
- **纯文本/代码** `.txt` `.log` `.java` `.cpp` 等
- **其他** `.epub` `.vsd` `.dbf` `.dbt` 等

### 输出格式

按文件类型自动选择最优抽取格式（markdown > kdc > plain），输出 Markdown 可读文本：

- 支持 markdown 的类型（`.docx`、`.pdf`、`.otl` 等）：直接请求服务端 markdown 格式（需配合 `include_elements=all` 保留表格等元素）
- 其余类型（`.xlsx`、`.pptx`、`.dbt` 等）：请求 kdc 格式，本地转为 Markdown（表格 → Markdown 表格，段落 → 文本）
- `.pom`/`.pof`（processon）：请求 plain 格式

输出模式：

- 默认：Markdown 可读格式 + `## 原始数据 (JSON)`
- `--json`：仅输出 JSON（含 `content`、`raw`、`format`）
- `--raw`：仅输出 Markdown 正文，无摘要头和原始 JSON

### 抽取格式 `--format`（`auto` | `markdown` | `kdc` | `plain`）

- 默认按扩展名自动选择——能转 markdown 的用 markdown（`.otl`/`.docx`/`.pdf` 等），不能的用 kdc（`.xlsx`/`.pptx` 等）。
- 需要 **文字文档类正文中可能出现的内嵌批注**（服务端 kdc 中常见字段 `doc.comments`）时，必须 **`--format kdc`**；仅 `markdown` 时响应体通常不含该结构。**其它在线类型**（智能文档、表格、演示等）是否出现该字段取决于服务端导出，无则数组为空或不存在。
- 示例：`python skills/drive/run.py get-file-content <file_id|url> --format kdc --json`，在输出的 `raw.doc.comments` 中解析（若有）。

### `--include-elements`

可选元素：

- `para`
- `table`
- `component`
- `textbox`
- `all`

规则：

- 传多个元素时用半角逗号连接
- `all` 只能单独使用
- 如果传了非 `all` 组合，脚本会自动补上 `para`

示例：

```bash
# 云文档
python skills/drive/run.py get-file-content <file_id> --include-elements all
python skills/drive/run.py get-file-content <file_id> --include-elements para,table

# 本地文件（异步，自动轮询等待结果）
python skills/drive/run.py get-file-content /path/to/file.docx
python skills/drive/run.py get-file-content /path/to/file.pdf
```

## `write`

### 智能文档

- 使用内容插入接口
- `--mode overwrite` 会从开头插入
- `--mode append` 会在末尾追加
- 适合把 Markdown 段落、说明、总结补充进已有文档

### 文字文档 / PDF

- 先把 Markdown 转换成目标格式
- 再通过更新接口覆盖原文件
- 会生成新版本
- 更接近“整体替换内容”，而不是局部插入

### 输入限制

- `--content` 与 `--file` 必须二选一
- `--template` 仅对文字文档转换有意义
- 不要把 `write` 当成“上传本地 docx 文件”的入口；那是 `update`

## `upload`、`update`、`write` 的区别

### `upload`

- 创建一个新的云端文件
- 单个 `.md` 会自动变成智能文档
- 如果内容是 agent 刚生成的 Markdown，总结、报告、测试记录这类“先生成再上传”的任务，也优先走这个路径

### `update`

- 已知目标 `file_id` / `link_id`
- 直接用本地文件覆盖现有云文档

### `write`

- 已知目标 `file_id` / `link_id`
- 把 Markdown 内容写进现有云文档
- 更适合 AI 生成内容回填

## 新建 Markdown 文档的推荐路径

当用户表达的是：

- “把以上内容整理成一份 Markdown 文件上传到我的文档”
- “生成一份总结并保存到云文档”
- “把这段结果输出成 md 文档放到云端”

优先做法：

1. 先把生成内容写入单个本地 `.md` 文件
2. 再执行 `python skills/drive/run.py upload <that.md> --path "..."`

原因：

- `upload` 对单个 `.md` 有内建的智能文档创建路径
- 比 `create` 后再 `write --content` 更稳
- 能避免 shell 引号、换行、反引号、JSON 花括号被错误解析
- 对跨平台路径也更友好

不推荐作为首选的做法：

- 为了“新建一份 Markdown 文档”先 `create` 一个空 `.otl`
- 再把长内容通过 `write --content "..."` 直接塞进命令行

只有在目标文档已经存在、并且确实是在“回填/追加到现有文档”时，才优先考虑 `write`

## 输出格式约定

大多数命令默认行为：

1. 先输出 Markdown 摘要
2. 再输出 `## 原始数据 (JSON)`

例外：

- `get-file-content --json`：只输出 JSON（含 `content`、`raw` 和 `format`）
- `get-file-content --raw`：只输出 Markdown 正文

这意味着如果后续步骤需要稳定提取 `file_id`、`drive_id`、`link_id`、`page_token`，优先从 JSON 区块取值。

## IM 云文档消息

上传、创建或查询文件后，返回里常见：

- `link_id`
- `link_url`

给 IM 发送云文档消息时，通常使用它们组装：

```json
{
  "type": "cloud",
  "cloud": {
    "id": "<link_id>",
    "link_id": "<link_id>",
    "link_url": "https://kdocs.cn/l/xxx"
  }
}
```

如果只有 `link_id`，可先执行 `link-meta` 补齐信息。

## 常见错误

- `400008018`
  文档内容抽取失败，可能原因：文件为空/损坏、文件类型不兼容、或服务端临时异常
- `400000004`
  常见于格式不匹配，例如把不兼容内容直接覆盖到智能文档
- 401 / 403
  凭证无效或当前账号无权限
- “文件不存在”
  检查本地路径是否正确；如果用户给的是云文档标题，不要把它当成本地路径
- 上传到云指定目录却落到别处（常与「目录页」有关）
  用户若把 `365.kdocs.cn` **目录页地址栏长链接**当作 `upload` / `create` 的 **`--path`**：其中 id 常为 **KDocs 路由用**，≠ Drive 文件夹 id，**勿整段粘贴**。让用户用 **`团队文档->开放引擎`** 式层级说明（`--path` 写成 **`团队文档/开放引擎`**），或 **`askUserQuestion` 先确认**文档库与文件夹，再 `doclibs`+`list`+`--path`。
