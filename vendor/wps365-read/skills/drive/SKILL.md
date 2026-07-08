---
name: drive
description: 用于通过 file_id、link_id 或 kdocs.cn URL 定位、读取、更新、分享、查看历史版本或评论 WPS 365 云文档。get-file-content 支持所有主流格式（Word/Excel/PPT/PDF/OFD/图片/网页/纯文本/代码/智能文档/多维表等）的内容解析提取。同时覆盖上传、下载、搜索、文件管理、版本列表与分享链路，并区分“留言 / 全文评论”与“正文批注 / 划选评论”的场景。
---

# 云文档 Drive
用这个 skill 处理文档内容提取解析（get-file-content，支持所有主流文件格式）、文件定位、内容读写、文件流转、组织管理、分享链路、**留言 / 全文评论**（协作评论 API）以及 **正文批注 / 划选评论**（kdc `doc.comments`，见下文「批注与评论」）。

## 前置条件

- 在 `wps365-read` 根目录执行命令

## 快速使用

```bash
python skills/drive/run.py <子命令> [参数...]
```

## 决策规则

- 用户要查看团队文档库列表、团队文档目录、或不知道团队文档库的 `drive_id`：
  先执行 `doclibs` 获取文档库列表和 `drive_id`，再用 `list --drive <drive_id>` 查看具体目录内容
- 用户给的是文件名、标题、关键词，而不是 `file_id`：
  先执行 `search`、`ai-search` 或 `latest`
- 用户给的是 `kdocs.cn` 分享链接（如 `https://365.kdocs.cn/l/xxx`、`https://www.kdocs.cn/l/xxx`）：
  从 URL 路径提取 `link_id`（`/l/` 后的那段字符串），然后按 `link_id` 使用方式操作。
  代码已内置 URL 解析，也可直接传完整 URL 给命令。
  **链接本身不决定文档类型**：解析后通过 `get` / `link-meta` 返回的文件名、`file_id` 等判断是 `.otl`、`.docx`、`.pdf` 等，再按类型选子命令（见「批注与全文评论」表）
- 用户粘贴 **`365.kdocs.cn` 团队文档「目录页」地址栏长链接**（多级路径、纯数字段等），且 **不是** 文档分享短链 `.../l/<link_id>` 时：
  **先说明**：链内 id 多为 **KDocs 路由用**，**不是** Drive 的 **`drive_id` / 文件夹 id**；**勿**当作 **`upload` / `create` 的 `--path`**（或等价父目录），否则易落到默认目录，**不等于对方填错路径**。
  **改用**：`doclibs` + `list --drive <drive_id> --path "团队文档/…"`；口语 **`团队文档->子目录`** 对应 **`团队文档/子目录`**；拿不准则 **`askUserQuestion` 先确认**再操作。细节见 [references/io-details.md](references/io-details.md)「上传到云指定目录却落到别处」、[references/command-details.md](references/command-details.md) `upload` 小节。
- 用户给的是 IM 云文档消息里的 `link_id`：
  直接用 `get`、`download`、`read`、`write`、`update`，或先执行 `link-meta`
- 用户要下载原始文件到本地，但没有明确保存目录：
  先通过 `askUserQuestion` 让用户在以下目录中选择其一，再执行 `download --dir <目录>`：
  1. 工作空间目录（显示绝对路径，如当前工作目录的绝对地址）
  2. 系统下载目录（显示绝对路径，如 `~/Downloads` 展开后的绝对地址）
  3. 用户自填目录
- 用户要查看、读取、解析、提取任何文档的内容（包括 Word、Excel、PPT、PDF、图片、网页、代码文件等所有类型）：
  **统一用 `get-file-content`**（别名 `read` / `extract`）。云文档传 file_id/link_id，本地文件直接传文件路径（自动识别并走异步 KDC 解析：`create_job` → 轮询 `query_job`，无需额外处理超时）
- 用户要看某个文件的**历史版本**、**版本列表**、**版本记录**、**版本备注**：
  用 `file-versions`。支持 `file_id`、`link_id`、`kdocs.cn URL` 输入。
  默认携带版本备注；只有在用户明确不需要时才加 `--without-comment`。
  每次最多展示 20 条版本记录；若返回 `next_page_token`，必须立即通过 `askUserQuestion` 询问是否继续展示下一页。
  输出里 `version` 按 **version_id** 理解、`id` 按 **history_id** 理解；`version_id` 只是记录 ID，不代表第几个版本或总版本数。保留修改者信息，不展示 hash。需要扩展属性时再加 `--with-ext-attrs`
- 用户要**比较两个历史版本**、**对比 v12 和 v18**、**看两个版本差异**、**总结某文件版本改了什么**：
  用 `file-version-diff <file_id|link_id> <版本号A> <版本号B>`。
  如果用户没有提供两个版本号，必须先通过 `askUserQuestion` 让用户补充两个版本号，再执行比较。
  版本号更大的那个视为**新版本**；命令会直接下载两个指定版本到本地，并由版本下载接口自行校验版本是否有效，再用 `_cmd_extract_local` 同链路的本地解析能力提取为 Markdown，最后执行 `diff` 并输出主要变更内容。
- 用户要把 Markdown 内容写回已有文档：
  用 `write`
- 用户要新建云文档（`.otl` `.dbt` `.docx` `.xlsx` `.pptx`）或文件夹：
  用 `create`。`create` **仅支持 WPS 云文档原生格式和文件夹**，不支持 `.md` `.txt` `.pdf` `.jpg` 等非云文档类型
- 用户要将 `.md` `.txt` `.pdf` 等非云文档格式的文件保存到云盘：
  用 `upload`（需要本地先有该文件）。`.md` 文件上传后会自动转为智能文档
- 用户要上传、更新、新建、写入、复制、移动、重命名、另存为、开启/关闭分享：
  **先不带 `--confirm` 执行 dry-run** → 通过 `askUserQuestion` 确认 → 再加 `--confirm` 重跑。每次新操作独立确认，不复用之前的确认。仅当用户在本条请求里说了"直接执行""无需确认"等才可跳过
- 用户要用 Markdown 更新已有的智能文档（`.otl`）或文字文档内容：
  用 `write`（把 Markdown 写回文档）。**绝对不能用 `update`**，`update` 会以二进制覆盖导致 `.otl` 损坏无法打开
- 用户要把刚生成的总结、报告、测试结果保存成一份 Markdown 文档并上传到云文档：
  先把内容写成单个本地 `.md` 文件，再执行 `upload`（仍需走 dry-run）；不要优先走 `create + write --content`
- 用户要检查重名：
  用 `file-check-name`（只读，无需确认）
- 用户要管理收藏、标签、回收站或分享：
  分别进入 `star*`、`tag*`、`deleted-*`、`file-open-link` / `file-close-link`
- 用户明确说的是 **留言**、**全文评论**、**协作区评论**、**回复评论**：
  查看用 `comment-list`，新建/回复用 `comment-create`。
  `comment-update`（修改）和 `comment-delete`（删除）暂不支持。
- 用户明确说的是 **批注**、**侧栏评论**、**正文评论**、**划选评论**、**页边评论**：
  用 `get-file-content` **且指定 `--format kdc`**，优先读取 JSON 里的 `inline_comments`（与 `raw.doc.comments` 同源）；**不要**与 `comment-list` 混用
- 用户要求 **添加批注**、**创建批注**、**写入批注**、**修改批注**、**删除批注**：
  当前开放 API 不支持正文批注/划选评论的写入。
  应明确告知用户此限制，并视场景建议：
  1. 改用「留言 / 全文评论」（`comment-create`）作为替代
  2. 在 WPS 编辑器（桌面端或 Web 端）中手动添加正文批注
  不要静默降级为留言——必须让用户知晓两者的区别并主动选择
- 用户说的是 **所有评论**、**全部评论**、**把评论都读出来**，但没限定是哪一类：
  默认按**两类都查**处理。
  1. 先查 `comment-list`（留言 / 全文评论）
  2. 再查 `get-file-content --format kdc --json`（正文批注 / 划选评论）
  3. 汇总输出，并明确标注哪部分是“留言”、哪部分是“正文批注”
- 用户明确要 AI 知识库空间列表或知识库片段召回：
  不要停在这里，切到 `ai-docs` 子 skill；`drive ai-search` 是文件语义搜索，不是知识库空间管理

## 批注与全文评论（勿混用）

| | **留言 / 全文评论** | **正文批注 / 划选评论（kdc）** |
|---|--------------|---------------------|
| **界面** | 底部或独立面板 **「留言」** | 侧栏 **「评论」**、正文划选批注、页边/气泡批注 |
| **读取方式** | `comment-list` | `get-file-content --format kdc --json` |
| **写入方式** | `comment-create`（新建/回复）；`comment-update`（修改）和 `comment-delete`（删除）暂不支持 | **不支持** |
| **输出位置** | `comment-list` 命令输出 | JSON 里的 `inline_comments`，或同源的 `raw.doc.comments` |
| **支持判断** | 看文档对象是否开启全文评论；关闭时接口会直接报错 | **文字文档类**（`.docx` `.doc` `.wps` `.rtf` 等）是主要场景；其它类型仅在服务端导出 `doc.comments` 时可见 |
| **注意** | 仅两级结构：根评论 + 子评论 | 必须显式传 `--format kdc`；若无 `inline_comments` 字段，表示当前类型/版本未导出正文批注 |

> 用户只说“所有评论”时，不要猜成单一路径；默认按“留言 + 正文批注”两类都查。

## 子命令分组

### 文件定位与读取

- `doclibs`：团队文档库列表（获取所有团队文档库及其 `drive_id`）
- `doclib-meta`：单个团队文档库详情
- `search`：普通文件搜索（支持 `--scope`、`--file-exts`、`--time-type`/`--start-time`/`--end-time`、`--drive-ids`、`--creator-ids` 等过滤；详见 `-h`）
- `ai-search`：文件智能搜索（支持 `--file-exts`、`--drive-ids`、`--scopes`、`--recall-strategy` 等过滤；详见 `-h`）
- `latest`：最近文档（支持 `--include-exts`、`--exclude-exts`、`--include-creators` 等过滤；详见 `-h`）
- `file-versions`：文件历史版本列表（默认带版本备注；可用 `--without-comment` 关闭；每次最多 20 条版本记录；若有下一页必须先用 `askUserQuestion` 确认是否继续；可直接传 `file_id` 或 `link_id`）
- `file-version-diff`：比较两个历史版本（下载两个版本到本地、提取 Markdown、执行 `diff`、输出主要变更）
- `list`：目录列表（配合 `doclibs` 返回的 `drive_id` 可查看团队文档库内容）
- `get`：文件详情
- `download`：下载文件到本地。执行前先确认保存目录；优先通过 `askUserQuestion` 让用户选择“工作空间目录（绝对路径）/ 系统下载目录（绝对路径）/ 自填目录”，再用 `--dir` 指定。
- `get-file-content`（别名 `read` / `extract`）：文档内容提取解析（云文档或本地文件）
- `link-meta`：`link_id` 解析为 `file_id` / `drive_id`

### 内容提取支持的文档类型

`get-file-content` 支持两种来源：云文档（`GET .../content`）和本地文件（异步 `POST /v7/coop/asyn_export/create_job` + 轮询 `query_job`）。按文件扩展名自动选择最优格式（markdown > kdc > plain），支持所有主流文档类型：

| 文档类别 | 支持的扩展名 |
|---------|------------|
| 智能文档 | `.otl`（支持段落/表格/组件/文本框元素筛选） |
| 文字文档 | `.docx` `.doc` `.dot` `.wps` `.wpt` `.dotx` `.docm` `.dotm` `.rtf` `.uot` |
| 表格文档 | `.xlsx` `.xls` `.xlt` `.et` `.ett` `.xltx` `.csv` `.xlsm` `.xltm` `.xlsb` `.uos` `.ksheet` |
| 演示文档 | `.pptx` `.ppt` `.pot` `.potx` `.pps` `.ppsx` `.dps` `.dpt` `.pptm` `.potm` `.ppsm` `.uop` |
| PDF/OFD | `.pdf` `.ofd` `.uof` |
| 网页 | `.mht` `.mhtml` `.htm` `.html` `.xml` |
| 图片 | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.tif` `.tiff` `.psd` `.svg` |
| 设计/矢量 | `.vsd` `.vsdx` `.cdr` |
| 纯文本/代码 | `.txt` `.log` `.c` `.cpp` `.java` `.h` `.asm` `.s` `.asp` `.bat` `.bas` `.prg` `.cmd` `.lrc` |
| 电子书 | `.epub` |
| 数据库 | `.dbf` |
| 多维表 | `.dbt`（结构化记录操作优先用 `dbsheet` skill） |

> 默认输出 Markdown 可读格式（表格类自动转为 Markdown 表格，文档类拼接段落），同时附带原始 JSON。
> `.dbt` 的增删改查记录、查表结构等操作应优先切到 `dbsheet` skill。
>
> **抽取格式**：默认按扩展名自动选择——能转 markdown 的用 markdown，不能的用 kdc。需要 **正文批注 / 划选评论** 时必须显式加 **`--format kdc`**，优先读 `--json` 输出里的 `inline_comments`；其底层来源仍是 `raw.doc.comments`。

### 创建、上传与写回

- `create`：新建云文档（`.otl` `.dbt` `.docx` `.xlsx` `.pptx` 等）、文件夹、快捷方式。**不支持** `.md` `.txt` `.pdf` 等非云文档格式
- `upload`：上传本地文件；单个 `.md` 自动创建为智能文档
- `update`：上传本地文件覆盖已有云文档（**不可用于 `.otl` `.dbt`，会损坏文档**）
- `write`：把 Markdown 写回已有文档

### 文件管理

- `file-copy`：复制文件
- `file-move`：移动文件
- `file-rename`：重命名文件
- `file-save-as`：另存为
- `file-check-name`：检查名称是否已存在

### 组织管理

- `star` / `favorites`：收藏列表
- `star-add-items`：批量添加收藏
- `star-remove-items`：批量移除收藏
- `tags` / `user-tags`：标签列表
- `tag-get`：标签详情
- `tag-objects`：标签对象列表
- `tag-create`：创建标签
- `tag-add-objects`：批量绑定标签对象
- `tag-remove-objects`：批量解绑标签对象

### 回收站与分享

- `deleted-list`：回收站列表
- `deleted-restore`：还原回收站文件
- `file-delete`：将文件移入回收站
- `file-open-link`：开启分享
- `file-close-link`：关闭分享

### 全文评论（协作评论 API）

- `comment-list`：获取文档评论列表（根评论传 origin_id=0，子评论传根评论 ID）
- `comment-create`：创建评论或回复
- `comment-update`：修改评论内容（暂不支持）
- `comment-delete`：删除评论（暂不支持）

> 全文评论仅支持两级结构（根评论 + 子评论）。根评论 page_size 最大 10，子评论最大 100。
>
> 与 **正文批注（`doc.comments`）**不是同一套数据；读正文批注请用 `get-file-content --format kdc`，见上文「批注与全文评论」表。

## 高风险操作

- `upload`
- `update`
- `create`
- `write`
- `file-copy`
- `file-move`
- `file-rename`
- `file-save-as`
- `file-open-link`
- `file-close-link`
- `file-delete`
- `comment-create`
- `comment-update`
- `comment-delete`

这些命令默认都是 dry-run（不带 `--confirm`）。

### 默认行为：dry-run + askUserQuestion 确认

1. 先执行不带 `--confirm` 的 dry-run，输出预览（目标文件、操作类型等）
2. 通过 `askUserQuestion` 向用户确认**本次操作**（选项如"确认执行""取消"）
3. 确认后，再追加 `--confirm` 重新执行
4. 不能因为预览结果正常，就自动补跑 `--confirm`
5. 每次新的变更操作都必须重新走此流程；之前操作的确认不能复用到下一次操作

### 跳过确认

当用户在**当前请求**中使用了明确的跳过意图表达时，可直接带 `--confirm` 执行，跳过 dry-run：

- "直接执行" "无需确认" "不用确认" "立即写入" "立即移动"

注意：之前对话中的笼统授权（如"以后都不用确认"）不适用于后续新的高风险操作，每次仍需在当前请求中明确表达。

## 关键约束

- `file_id` 指的是云文档对象 ID，不是本地文件路径，也不是仓库里的同名文件
- `link_id` 可以直接传给 `get`、`download`、`read`、`write`、`update`；需要显式拿 `file_id` / `drive_id` 时再执行 `link-meta`
- `download` 不应假设固定默认目录；如果用户没指定保存目录，必须先通过 `askUserQuestion` 让用户选择：
  1. 工作空间目录（显示绝对路径）
  2. 系统下载目录（显示绝对路径）
  3. 自定义目录
- `file-version-diff` 要求两个版本号；若缺少任一版本号，必须先通过 `askUserQuestion` 向用户索取，不能自行猜测“上一版”“最新版”
- `upload` 与 `update` 的区别：
  `upload` 是创建新文件，`update` 是覆盖已有文件新版本
- 单个 `.md` 文件走 `upload` 时，会自动创建智能文档（`.otl`）并写入 Markdown，而不是按普通附件上传
- 对“新建一份 Markdown 文档并上传”这类场景，优先落本地 `.md` 文件后调用 `upload`，不要把长 Markdown 直接塞进 shell 的 `write --content`
- `write` 只接受 Markdown 输入：
  智能文档（`.otl`）是插入内容，文字文档（`.docx`/`.doc`/`.wps`）和 PDF（`.pdf`）是转换后覆盖原文件
- `write` 与 `update` 不要混用：
  `write` 适合“把 Markdown 写回文档”，`update` 适合“拿本地二进制文件替换云端版本”
- **获取文档内容必须用 `get-file-content`**，不要用 `download` 后本地解析。所有文件类型（Word/Excel/PPT/PDF/图片等）统一走此命令，输出 kdc 格式自动转 Markdown。本地文件走异步解析（create_job + query_job 轮询，最长 300s）。`download` 仅适合需要原始文件（而非文本内容）的场景
- **严禁用 `update` 覆盖智能文档（`.otl`）或多维表（`.dbt`）**：
  `update` 是二进制覆盖，会直接损坏 `.otl` / `.dbt` 导致文档无法打开。要更新智能文档内容，必须用 `write`
- **获取文档内容必须用 `get-file-content`**，不要用 `download` 后本地解析。所有文件类型（Word/Excel/PPT/PDF/图片等）统一走此命令，输出 kdc 格式自动转 Markdown。本地文件走异步解析（create_job + query_job 轮询，最长 300s）
- `get-file-content` 默认输出 Markdown + 原始 JSON；需要结构化结果时加 `--json`，只要正文时加 `--raw`
- `create` 仅支持 WPS 云文档格式（`.otl` `.dbt` `.docx` `.xlsx` `.pptx` 等）和文件夹；`.md` `.txt` `.pdf` 等非云文档格式会报"请求参数不支持"，应改用 `upload`
- `create --file-type shortcut` 时必须提供 `--file-id`
- 目录定位优先用 `--path`，只有已经拿到明确目录 ID 时再用 `--parent` 或 `--parent-id`
- KDocs **目录页**完整 URL 不可当作云盘 **`--path` / 父目录**（见上条「目录页长链接」）；本机 `download --dir` 也**勿填**网页 URL
- `ai-search` 的返回是文件召回结果，不是 AI 知识库 space / drive 列表
- 用户明确要“收藏的文档”时，只能用 `star` / `favorites`；如果该能力失败，应说明收藏列表获取失败，而不是降级成 `latest`、`search` 或其它近似结果
- 全文评论仅支持**两级结构**（根评论 + 子评论），`comment-list` 的 `--origin-id 0` 查根评论（page_size 最大 10），传根评论 ID 查子评论（page_size 最大 100）
- `comment-list`、`comment-create` 均支持 `file_id`、`link_id`、`kdocs.cn URL` 输入
- **正文批注 / 划选评论**：用 `get-file-content <id|url> --format kdc --json`，优先读 `inline_comments`；默认格式对文字文档类为 `markdown`，不含 `doc.comments`

需要参数细节、命令示例、读写边界或输出格式约定时，查看：

- [references/command-details.md](references/command-details.md)
- [references/io-details.md](references/io-details.md)

## 常用示例

```bash
# 先找文件
python skills/drive/run.py search "季度复盘"
python skills/drive/run.py ai-search "项目周报"

# 读取云文档正文
python skills/drive/run.py get-file-content <file_id>
python skills/drive/run.py get-file-content <file_id> --json
python skills/drive/run.py get-file-content <file_id> --include-elements para,table
# 正文批注 / 划选评论（kdc 中 doc.comments，若服务端有导出）
python skills/drive/run.py get-file-content <file_id|url> --format kdc --json

# 下载文件到本地（先通过 askUserQuestion 确认保存目录，再显式传 --dir）
python skills/drive/run.py download <file_id> --dir "$PWD"

# 解析本地文件（异步，自动轮询等待结果，最长 300s）
python skills/drive/run.py get-file-content /path/to/file.docx
python skills/drive/run.py get-file-content /path/to/file.pdf

# 新建云文档（仅支持 .otl .dbt .docx .xlsx .pptx 等云文档格式和文件夹）
python skills/drive/run.py create 反馈管理.dbt
python skills/drive/run.py create 项目周报.docx --path "项目A"
python skills/drive/run.py create 项目资料 --file-type folder

# 上传本地文件（支持任意格式；.md 自动转为智能文档）
python skills/drive/run.py upload ./report.docx --path "项目A"
python skills/drive/run.py upload ./notes.md --path "项目A"

# 写回与更新
python skills/drive/run.py write <file_id> --file ./content.md
python skills/drive/run.py update <file_id> ./new-version.docx

# link_id 解析
python skills/drive/run.py link-meta <link_id>

# 留言 / 全文评论（协作区，非正文 doc.comments）
python skills/drive/run.py comment-list <file_id>
python skills/drive/run.py comment-list <file_id> --origin-id <root_comment_id>
python skills/drive/run.py comment-create <file_id> -c "评论内容"
python skills/drive/run.py comment-create <file_id> -c "回复内容" --origin-id <root_id>

# 所有评论（默认两类都查，再分组汇总）
python skills/drive/run.py comment-list <file_id|url>
python skills/drive/run.py get-file-content <file_id|url> --format kdc --json
```

## 输出格式

默认先输出 Markdown 摘要，再附 `## 原始数据 (JSON)`，便于继续提取 `file_id`、`drive_id`、`link_id`、`page_token` 等标识。

例外：

- `get-file-content --json`：仅输出 JSON
- `get-file-content --raw`：仅输出正文

## 注意事项

- 用户没有对本次操作给出明确确认或跳过意图时，不要对高风险操作追加 `--confirm`
- 如果用户只给了文档标题，例如 `经营周报`，先用搜索能力定位，不要在当前仓库中查找同名本地文件
- 如果目标是多维表 `.dbt` 的 schema、sheet、record 操作，先用本 skill 拿到 `file_id`，再切到 `dbsheet`
- 如果目标是把云文档发送到 IM，会用到返回里的 `link_id` / `link_url`
- 需要定位单一文档但搜索命中多条时，须通过 `askUserQuestion` 让用户选择，不得自行挑选
- 需要完整参数说明或边界行为时，以 `python skills/drive/run.py <子命令> -h` 为准
