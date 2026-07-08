# 周报迁移 Skill — 新手指南

将**组内智能文档周报**（`.otl`）里每位成员的内容，自动填入**部门周报表格**（`.ksheet`）对应单元格。

**你不需要会写代码、不需要开终端。** 装好 Skill 后，在 Cursor 对话里说一句话，Agent 会替你完成环境检查、读取云文档、生成预览、写回云端。

---

## 这个 Skill 能帮你做什么

| 自动完成 | 你需要做的 |
|----------|------------|
| 从组内 otl 读取每人本周周报 | 提供两个云文档链接（仅首次） |
| 按姓名匹配部门表对应行 | 预览后点「确认写回」 |
| 按周次匹配部门表对应列（没有则插入） | 缺凭证时在对话里粘贴 `wps_sid` |
| 保留 D 列超链接、只做排版不改正文 | 写回后在浏览器 **Ctrl+F5** 刷新查看 |
| 写回成功后清理本地临时文件 | 说「周报迁移」触发即可 |

**触发词示例**：`周报迁移`、`填部门周报`、`同步周报`、`同步本周周报到部门表`

---

## 使用前准备

请确认你已具备：

1. **Cursor** 编辑器（已安装并可正常登录）
2. **Git**（用于克隆本仓库；也可用「下载 ZIP」代替）
3. **Python 3.10+**（本机已安装即可，**你不用自己跑**；Agent 会自动安装依赖）
4. **金山文档账号**，且对以下两个文档有权限：
   - **组内周报**：`.otl` 智能文档，按 `# 日期` 分周、按 `## 姓名` 分人
   - **部门周报**：`.ksheet` 表格，B 列姓名、各周为列（如 C 列内容）
5. **wps365-read**（可选但推荐）：Skill 会自动在常见路径查找；找不到时 Agent 会问你目录位置

---

## 第一步：获取 Skill 文件

### 方式 A：Git 克隆（推荐）

在终端执行（路径可自定）：

```bash
git clone https://github.com/dengabin/weekly-report-migration-skill.git
```

克隆后目录名一般为 `weekly-report-migration-skill`。

### 方式 B：下载 ZIP

1. 打开 https://github.com/dengabin/weekly-report-migration-skill  
2. 点击 **Code → Download ZIP**  
3. 解压到本地，例如 `D:\skills\weekly-report-migration-skill`

---

## 第二步：把 Skill 加载进 Cursor

Cursor 通过目录里的 `SKILL.md` 识别 Skill。任选下面一种方式安装。

### 方式 1：安装为「个人 Skill」（推荐，所有项目可用）

1. 找到 Cursor 个人 Skill 目录：
   - Windows：`C:\Users\<你的用户名>\.cursor\skills\`
   - macOS：`~/.cursor/skills/`
2. 将克隆/解压后的整个文件夹**复制或软链**到该目录，例如：
   ```
   ~/.cursor/skills/weekly-report-migration/
   ├── SKILL.md
   ├── README.md
   ├── scripts/
   └── ...
   ```
3. **文件夹名建议**与 Skill 名一致：`weekly-report-migration`（对应 `SKILL.md` 里的 `name: weekly-report-migration`）

### 方式 2：安装为「项目 Skill」（仅当前仓库可用）

在你自己的项目根目录下：

```
你的项目/
└── .cursor/
    └── skills/
        └── weekly-report-migration/   ← 把整个 Skill 目录放这里
            ├── SKILL.md
            └── ...
```

适合团队把 Skill 和项目代码一起提交到 Git。

### 方式 3：直接打开 Skill 目录作为工作区

1. Cursor 菜单 **文件 → 打开文件夹**  
2. 选择 `weekly-report-migration-skill` 目录  
3. 在该工作区的 Agent 对话中使用即可

> 不要放到 `~/.cursor/skills-cursor/`，那是 Cursor 内置 Skill 目录。

### 如何确认加载成功

1. 打开 Cursor **Agent 对话**（Composer / Chat）  
2. 在输入框输入 **`@`**，搜索 `weekly-report-migration` 或 `report-migration`  
3. 若能在列表里看到并选中，说明 Skill 已加载  

也可以不 `@`，直接说触发词（见下文），Agent 会根据 `SKILL.md` 的 `description` 自动匹配。

---

## 第三步：第一次使用（完整 walkthrough）

下面按**真实对话顺序**说明你会经历什么。全程**不用打开终端**。

### 3.1 打开对话并触发

在 Cursor Agent 输入框发送（任选一句）：

```
周报迁移
```

或显式引用 Skill：

```
@weekly-report-migration 周报迁移
```

Agent 会开始检查环境（安装依赖、预检凭证、尝试读取云文档）。

---

### 3.2 首次配置：提供两个文档链接

若你是**第一次使用**（本地还没有 `config.json`），Agent 会依次问你：

| 顺序 | Agent 会问 | 你怎么答 |
|------|------------|----------|
| 1 | 组内周报链接 | 粘贴 otl 链接，如 `https://365.kdocs.cn/l/cpqRAGyILoLO` |
| 2 | 部门周报链接 | 粘贴 ksheet 链接，如 `https://365.kdocs.cn/l/cqGvaEAyY8lG` |
| 3（少数情况） | 部门子表叫什么 | 从 Agent 给出的子表列表里选一个，如 `应用研发-AI应用组` |

**Agent 不会问你要**：组成员名单、周次（除非你主动指定）。

链接从金山文档浏览器地址栏复制即可（`365.kdocs.cn/l/xxxx` 形式）。

---

### 3.3 配置金山文档凭证（仅首次或过期时）

若 Agent 提示缺少 `wps_sid` 或读取部门表失败，会给出**图文步骤**，核心是：

1. 浏览器打开 [365.kdocs.cn](https://365.kdocs.cn) 并登录  
2. 按 **F12** 打开开发者工具 → **Application（应用）** → **Cookies** → 选中 `365.kdocs.cn`  
3. 找到名为 **`wps_sid`** 的 Cookie，复制它的**值**（一长串字符）  
4. 回到 Cursor 对话，**在下一条消息直接粘贴**，不要加多余说明  

Agent 收到后会自动保存凭证并**继续执行**，你无需运行任何命令。

详细截图说明见：[references/wps-sid-guide.md](references/wps-sid-guide.md)

---

### 3.4 等待预览

环境就绪后，Agent 会：

1. 拉取组内 otl 与部门表  
2. 从 otl **自动解析成员**（`## 姓名` 标题）  
3. 确定**周次**（你没指定时 = 组内**最新一期**）  
4. 检查部门表是否有对应周列（没有会先插入列）  
5. 展示**迁移预览**，例如：

```
预览 — 16 人将写入「应用研发-AI应用组」C 列
周次：2026-07-02

王亮  → C12  [ready]  本周完成…
高升  → C13  [ready]  …
…
```

请核对：人数、周次、子表名是否正确。

---

### 3.5 确认写回

Agent 会问你是否写回云端。你回复：

```
确认
```

或点击 Agent 提供的确认选项。

**未确认前不会上传**，这是安全门控。

---

### 3.6 查看结果

写回成功后 Agent 会告知：

- 云端文档版本号  
- 成功写入人数  
- 本地 `.cache` 已自动清理（除非你要求保留）  

请你：

1. 浏览器打开**部门周报**  
2. 按 **Ctrl+F5** 强制刷新（否则可能看到旧缓存）  
3. 抽查：本周列内容、换行、D 列「📄组内周报」链接是否仍可点击  

---

### 第一次使用 · 对话示例（浓缩版）

```
你：  周报迁移

Agent：请提供组内周报链接
你：  https://365.kdocs.cn/l/cpqRAGyILoLO

Agent：请提供部门周报链接
你：  https://365.kdocs.cn/l/cqGvaEAyY8lG

Agent：（若缺凭证）请按步骤获取 wps_sid… 请在下一条消息粘贴
你：  （粘贴 wps_sid）

Agent：预览 16 人 → C 列，周次 2026-07-02，是否确认写回？
你：  确认

Agent：已写回 v21，请 Ctrl+F5 刷新部门表
```

---

## 第四步：以后每周怎么用

组内 otl 大家写完后，新开或继续 Cursor 对话，说一句：

```
周报迁移
```

即可。因为 `config.json` 和凭证已保存，通常**不会再问链接**。

Agent 自动：

1. 取组内**最新一周**  
2. 写入部门表**同一周列**  
3. 预览 → 你确认 → 写回  

---

## 常用说法（可选参数）

你说的话会改变 Agent 行为，**不用记命令**，自然语言即可：

| 你想做的事 | 在对话里说 |
|------------|------------|
| 默认迁移（最新一周） | `周报迁移` |
| 同步**上一周** | `周报迁移，粘贴上一周的` |
| 指定某周 | `周报迁移，week 是 2026-07-02` 或 `同步 6.26-7.2 那周` |
| 写回后**保留本地缓存**（排查用） | `周报迁移，保留缓存` |
| 重新配置文档链接 | `重新配置周报迁移的文档链接` |

---

## 重要说明

### 写回范围（Skill 强制遵守）

- **只改**指定那一周的**内容列**单元格  
- **不改**历史周、其它组子表、已有超链接  
- 对粘贴内容**只做排版**（列表符、缩进），**不改正文词句**  

### 你不需要做的事

| 不要做 | 原因 |
|--------|------|
| 运行 `python scripts/...` | Agent 代跑；若 Agent 让你跑，回复「请按 Skill 自动执行」 |
| 提供组成员名单 | 从组内 otl 自动读取 |
| 未指定周次时选「哪一周」 | 默认最新一期 |
| 手动编辑 `config.json` | Agent 维护；要改链接在对话里说 |

### 本地缓存

- 每次**写回成功**后，默认清空 `.cache/` 临时文件  
- 需要留档时说：**「保留缓存」**  

### `wps_sid` 会过期

过几天若迁移失败，按 Agent 提示**重新粘贴**即可，无需重装 Skill。

---

## 常见问题

| 现象 | 怎么办 |
|------|--------|
| `@` 里搜不到 Skill | 检查是否放到 `~/.cursor/skills/` 或 `.cursor/skills/`，且含 `SKILL.md`；重启 Cursor |
| Agent 让你自己跑 python | 回复「请按 Skill 要求你自动执行」 |
| 预览人数少于组内人数 | 该人在 otl 该周未写，或 `## 姓名` 与部门表 B 列不一致 |
| 部门表看不到更新 | **Ctrl+F5** 强刷；确认写的是正确子表和周次列 |
| 部门表还没有本周列 | 告诉 Agent「继续」，应自动插入列再写入 |
| 想换组内/部门文档 | 对话里说「更新周报迁移的文档链接」 |

---

## 文档与仓库

| 资源 | 说明 |
|------|------|
| 本仓库 | https://github.com/dengabin/weekly-report-migration-skill |
| [SKILL.md](SKILL.md) | Agent 技术入口（你一般不用读） |
| [references/wps-sid-guide.md](references/wps-sid-guide.md) | 获取 wps_sid 详细步骤 |
| [references/mapping-rules.md](references/mapping-rules.md) | 部门表行列规则 |
| [references/ai-app-group.md](references/ai-app-group.md) | AI应用组配置示例 |
| [scripts/README.md](scripts/README.md) | 脚本说明（开发者/Agent 用） |

---

## 快速检查清单

开始第一次迁移前，打勾确认：

- [ ] Skill 已放入 `~/.cursor/skills/weekly-report-migration/`（或项目 `.cursor/skills/`）
- [ ] Cursor 里 `@` 能搜到 `weekly-report-migration`，或直接说触发词
- [ ] 已准备好组内 otl、部门 ksheet 两个链接
- [ ] 对两个文档有读/写权限
- [ ] 组内 otl 按 `# 日期` + `## 姓名` 写好本周内容

全部就绪后，在 Agent 对话输入 **`周报迁移`** 即可开始。
