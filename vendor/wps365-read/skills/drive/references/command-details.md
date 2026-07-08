# Command Details

按需读取这个文件；只有在需要参数细节、批量操作写法或更完整的命令示例时再加载。

## 团队文档库

### `doclibs`

获取团队文档库列表，返回所有文档库及其 `drive_id`。

```bash
python skills/drive/run.py doclibs
python skills/drive/run.py doclibs --user-role owner,admin
python skills/drive/run.py doclibs --page-size 20 --page-token "<next_page_token>"
```

- `--user-role`：按角色筛选（逗号分隔）：`owner` / `admin` / `normal`
- 返回每个文档库的 `drive_id`，可配合 `list --drive <drive_id>` 查看目录内容

### `doclib-meta`

获取单个团队文档库的详情信息。

```bash
python skills/drive/run.py doclib-meta <drive_id>
```

- 返回文档库名称、成员数、角色、创建者等详情

## 文件定位与读取

### `search`

普通搜索，适合已知标题片段、关键词、文件名或正文关键字。

```bash
python skills/drive/run.py search "季度复盘"
python skills/drive/run.py search "经营分析" --type file_name
python skills/drive/run.py search "OKR" --scope all,share_to_me --page-size 20
python skills/drive/run.py search "周报" --page-token "<next_page_token>"
```

- `--type`：`file_name` / `content` / `all`
- `--scope`：逗号分隔，可传 `all`、`personal_drive`、`group_drive`、`latest`、`share_by_me`、`share_to_me`、`recycle`

### `ai-search`

文件智能搜索，适合自然语言描述或模糊语义召回。

```bash
python skills/drive/run.py ai-search "项目周报"
python skills/drive/run.py ai-search "季度总结" --recall-strategy paragraph
python skills/drive/run.py ai-search "招投标材料" --file-exts docx,pdf --drive-ids "<drive_id>"
python skills/drive/run.py ai-search "风险复盘" --parent-ids "<parent_id>" --with-drive --with-permission
```

- `--recall-strategy`：`paragraph` / `paragraph_embedding` / `all`
- `--file-exts` / `--exclude-file-exts`：按后缀过滤
- `--drive-ids` / `--parent-ids` / `--scopes`：缩小搜索范围

### `latest`

最近打开或编辑过的文档。

```bash
python skills/drive/run.py latest --page-size 20
python skills/drive/run.py latest --include-exts docx,pdf --with-link
python skills/drive/run.py latest --include-creators "<user_id1>,<user_id2>"
```

### `file-versions`

查看某个文件的历史版本列表，适合用户明确要“版本记录”“历史版本”“文件第几个版本”“版本备注”时使用。

```bash
python skills/drive/run.py file-versions <file_id>
python skills/drive/run.py file-versions <file_id> --without-comment
python skills/drive/run.py file-versions <link_id>
python skills/drive/run.py file-versions <file_id> --with-ext-attrs
python skills/drive/run.py file-versions <file_id> --page-token "<next_page_token>"
```

- 支持直接传 `file_id` 或 `link_id`
- 默认返回版本备注；`--with-comment` 仅用于显式保持默认行为
- `--without-comment`：不返回版本备注
- `--with-ext-attrs`：返回版本扩展属性
- 命令层每次最多展示 20 条版本记录；若返回 `next_page_token`，必须立即通过 `askUserQuestion` 询问用户是否继续展示下一页
- `version_id` 只是版本记录 ID，不代表第几个版本，也不代表总版本数；`history_id` 通常仅用于历史记录标识

### `file-version-diff`

比较同一文件的两个历史版本。命令会下载两个指定版本到本地，提取为 Markdown，再执行 `diff`，最后输出主要变更摘要与 unified diff。

```bash
python skills/drive/run.py file-version-diff <file_id> 12 18
python skills/drive/run.py file-version-diff <link_id> 3 9
python skills/drive/run.py file-version-diff <file_id> 12 18 --drive private
```

- 支持直接传 `file_id` 或 `link_id`
- 两个版本号都必须明确；若用户没提供，先通过 `askUserQuestion` 索取，再重新执行
- 版本号更大的那个视为新版本；即使用户输入顺序相反，也按数值自动归一化
- 命令不会先调用 `file-versions` 做前置校验；版本是否有效由版本下载接口自行判定
- 输出包含：主要变更摘要与 `diff` 结果

### `list`

按目录列文件。适合已经拿到目录 ID 时使用。

```bash
python skills/drive/run.py list --drive private --parent root
python skills/drive/run.py list --drive private --parent "<parent_id>" --page-size 100
python skills/drive/run.py list --drive private --parent "<parent_id>" --all
```

### `get` / `download` / `link-meta`

```bash
python skills/drive/run.py get <file_id>
python skills/drive/run.py get <link_id>
python skills/drive/run.py download <file_id> --dir /tmp/myfiles
python skills/drive/run.py link-meta <link_id>
```

- `get` / `download` 可以直接传 `file_id` 或 `link_id`
- `download` 必须显式传 `--dir`；若用户没指定目录，先通过 `askUserQuestion` 让用户选择“工作空间目录（绝对路径）/ 系统下载目录（绝对路径）/ 自填目录”
- `link-meta` 适合显式拿 `file_id`、`drive_id`、`link_url`

## 创建、上传与写回

### `create`

统一新建云文档、文件夹、快捷方式。

**支持的格式**：`.otl`（智能文档）、`.dbt`（多维表）、`.docx`、`.xlsx`、`.pptx`、`.doc`、`.xls`、`.ppt`，以及 `--file-type folder`（文件夹）和 `--file-type shortcut`（快捷方式）。

> 注意：`.md`、`.txt`、`.pdf`、`.jpg` 等非云文档格式**不支持**，会报"请求参数不支持"。这类文件请改用 `upload` 命令。

```bash
python skills/drive/run.py create 反馈管理.dbt
python skills/drive/run.py create 文档.otl --path "我的文档/子目录"
python skills/drive/run.py create 项目资料 --file-type folder --parent-id "<parent_id>" --drive "<drive_id>"
python skills/drive/run.py create 快捷入口 --file-type shortcut --file-id "<target_file_id>" --parent-id "<parent_id>"
```

- `--path` 与 `--parent-id` 二选一即可；优先 `--path`
- `--file-type shortcut` 时必须带 `--file-id`
- `--on-conflict`：`fail` / `rename` / `overwrite` / `replace`

### `upload`

上传本地文件。单个 `.md` 文件会自动新建为智能文档并写入 Markdown。

```bash
python skills/drive/run.py upload ./report.docx
python skills/drive/run.py upload ./report.docx --path "我的文档/项目A"
python skills/drive/run.py upload ./notes.md --path "我的文档/项目A"
python skills/drive/run.py upload ./budget.xlsx --filename "预算-v2.xlsx"
```

- 普通上传时可用 `--parent` 指定父目录 ID
- `.md` 自动走智能文档创建流程，`--path` 比 `--parent` 更有意义

### `update`

把本地文件作为新版本覆盖到已有云文档。

> **不可用于智能文档（`.otl`）和多维表（`.dbt`）**：`update` 是二进制覆盖，会直接损坏这些格式导致无法打开。更新智能文档内容请用 `write`。

```bash
python skills/drive/run.py update <file_id> ./new-version.docx
python skills/drive/run.py update <link_id> ./new-version.pdf
```

### `write`

把 Markdown 写回已有文档。

```bash
python skills/drive/run.py write <file_id> --content "# 新标题"
python skills/drive/run.py write <file_id> --file ./content.md
python skills/drive/run.py write <file_id> --file ./appendix.md --mode append
python skills/drive/run.py write <file_id> --file ./content.md --template ./template.docx
```

- `--content` 与 `--file` 必须二选一
- `--mode`：`overwrite` / `append`
- `--template` 只对文字文档转换有意义

## 文件管理

### `file-copy` / `file-move`

```bash
python skills/drive/run.py file-copy <src_drive_id> <file_id> --dst-drive-id <dst_drive_id> --dst-parent-id <dst_parent_id>
python skills/drive/run.py file-move <src_drive_id> <file_id> --dst-drive-id <dst_drive_id> --dst-parent-id <dst_parent_id>
```

### `file-rename` / `file-save-as` / `file-check-name`

```bash
python skills/drive/run.py file-rename <drive_id> <file_id> --dst-name "需求文档-已评审.docx"
python skills/drive/run.py file-save-as <drive_id> <file_id> --dst-drive-id <dst_drive_id> --dst-parent-id <dst_parent_id> --name "副本.docx"
python skills/drive/run.py file-check-name <drive_id> <parent_id> --name "需求文档.docx"
```

## 收藏、标签、回收站、分享

### `star` / `star-add-items` / `star-remove-items`

```bash
python skills/drive/run.py star --page-size 20
python skills/drive/run.py favorites --page-size 20
python skills/drive/run.py star-add-items --objects "<file_id1>,<file_id2>"
python skills/drive/run.py star-add-items --objects-json '[{"id":"<file_id1>"}]'
python skills/drive/run.py star-remove-items --objects "<file_id1>"
python skills/drive/run.py star-remove-items --item-ids "<item_id1>,<item_id2>"
```

- `favorites` 是 `star` 的别名，语义完全相同
- 用户问“我收藏了哪些文档”时，只应使用这组命令
- 如果 `star` / `favorites` 执行失败，应直接说明“收藏列表当前无法获取”并保留失败事实
- 不要擅自降级成 `latest`、`search` 或“最近访问文档”，因为它们不是收藏列表

### `tags` / `tag-*`

```bash
python skills/drive/run.py tags --label-type custom --page-size 20
python skills/drive/run.py tag-get <label_id>
python skills/drive/run.py tag-create --name "重点项目"
python skills/drive/run.py tag-objects <label_id> --page-size 20
python skills/drive/run.py tag-add-objects <label_id> --objects "<file_id1>,<file_id2>"
python skills/drive/run.py tag-remove-objects <label_id> --objects "<file_id2>"
```

- `tag-objects` 默认会尝试补全对象元信息
- 如只想看原始对象 ID，可加 `--no-resolve-meta`

### `deleted-list` / `deleted-restore`

```bash
python skills/drive/run.py deleted-list --page-size 20
python skills/drive/run.py deleted-list --drive-id "<drive_id>" --with-drive
python skills/drive/run.py deleted-restore <file_id>
```

### `file-open-link` / `file-close-link`

```bash
python skills/drive/run.py file-open-link <drive_id> <file_id> --scope anyone
python skills/drive/run.py file-open-link <drive_id> <file_id> --role-id "<role_id>" --opts-json '{"can_view":true}'
python skills/drive/run.py file-close-link <drive_id> <file_id> --mode pause
python skills/drive/run.py file-close-link <drive_id> <file_id> --mode delete
```

## 补充约定

- `private`、`roaming`、`special` 可以作为逻辑盘名传入；脚本会解析为实际 `drive_id`
- 命令里出现的 `<file_id>`、`<drive_id>`、`<parent_id>` 优先从上一步 JSON 输出里提取
- 如果用户给的是文档标题，不要先在当前仓库找本地文件；先用 `search` / `ai-search` / `latest`
