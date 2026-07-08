# 周报迁移 Skill — 新手指南

将**组内智能文档周报**（`.otl`）里每位成员的内容，自动填入**部门周报表格**（`.ksheet`）对应单元格。

**你不需要会写代码、不需要开终端、不需要手动复制文件夹。** 把 Skill 目录交给 Cursor Agent，让它帮你获取、安装并执行；你只在对话里回答问题即可。

---

## 这个 Skill 能帮你做什么

| Agent 自动完成 | 你只需要 |
|----------------|----------|
| 获取 / 安装 Skill 到本机 | 说「加载 skill」或打开目录 |
| 安装依赖、预检环境 | **说「周报迁移」之后**；首次再提供两个云文档链接 |
| 从组内 otl 读取每人本周周报 | 缺凭证时粘贴 `wps_sid` |
| 按姓名、周次匹配部门表并写回 | 预览后回复「确认」 |
| 保留超链接、排版、写回后清缓存 | 浏览器 **Ctrl+F5** 查看结果 |

**触发词示例**：`周报迁移`、`填部门周报`、`同步周报`

---

## 使用前准备

请确认你已具备：

1. **Cursor** 编辑器（已安装并可正常登录）
2. **Python 3.10+**（本机有即可，**不用自己跑**；Agent 自动安装依赖）
3. **金山文档账号**，且对以下两个文档有权限：
   - **组内周报**：`.otl` 智能文档，按 `# 日期` 分周、按 `## 姓名` 分人
   - **部门周报**：`.ksheet` 表格，B 列姓名、各周为列（如 C 列内容）

Git 克隆、解压 ZIP、复制目录等操作均可交给 Agent，不必自己动手。

---

## 第一步：把 Skill 交给 Agent（无需手动加载）

Cursor **没有**「用户自己拷文件夹到 `.cursor/skills/`」这种硬性要求。任选下面一种方式，**在对话里说出来**，Agent 会处理其余步骤。

### 方式 A：打开 Skill 目录当工作区（最简单，推荐）

1. Cursor 菜单 **文件 → 打开文件夹**
2. 选择 Skill 所在目录（clone 或解压后的 `weekly-report-migration-skill`）
3. 在 Agent 对话里说：

```
加载这个 skill
```

Agent 会确认 Skill 就绪。**此时不会**索要文档链接。

需要迁移时再说：

```
周报迁移
```

Agent 会直接读取当前目录下的 `SKILL.md` 并开始执行，**无需安装到别处**。

---

### 方式 B：让 Agent 帮你 clone 并安装（从零开始）

在任意 Cursor 工作区，对 Agent 说：

```
请从 GitHub 安装周报迁移 Skill 并执行预检：
https://github.com/dengabin/weekly-report-migration-skill
克隆后安装到 ~/.cursor/skills/weekly-report-migration/，然后按 SKILL.md 走周报迁移流程
```

Agent 会替你完成：

- `git clone` 仓库
- 复制到个人 Skill 目录 `~/.cursor/skills/weekly-report-migration/`（Windows：`C:\Users\<用户名>\.cursor\skills\`）
- 读取 `SKILL.md` 开始预检

装完后你说 `周报迁移` 即可；若 `@` 列表暂时没有出现该 Skill，对 Agent 说「重载窗口」或自己执行一次 **Developer: Reload Window**。

---

### 方式 C：你已有 Skill 目录，让 Agent 安装

若目录已在本地（例如 `D:\skills\weekly-report-migration-skill`），直接说：

```
请把 D:\skills\weekly-report-migration-skill 安装为 Cursor 个人 Skill，
复制到 ~/.cursor/skills/weekly-report-migration/，然后执行周报迁移
```

把路径换成你的实际路径即可。也可以把文件夹拖进对话作为附件。

---

### 你不需要做的事

| 不必手动操作 | Agent 代替 |
|--------------|------------|
| 复制文件夹到 `~/.cursor/skills/` | 你说「帮我安装」即可 |
| `git clone` | Agent 可执行 |
| 解压 ZIP | 你说路径，Agent 可解压并安装 |
| 运行 `pip install` / `python scripts/...` | 全程 Agent 执行 |

> 不要放到 `~/.cursor/skills-cursor/`，那是 Cursor 内置目录；Agent 安装时会自动避开。

---

## 第二步：第一次使用（完整 walkthrough）

下面按**真实对话顺序**说明你会经历什么。

### 2.1 触发

安装或打开目录后，在 Agent 对话发送：

```
周报迁移
```

Agent 会检查环境（依赖、凭证、云文档可读性）。

---

### 2.2 首次配置：提供两个文档链接

若本地还没有 `config.json`，Agent 会依次问你：

| 顺序 | Agent 会问 | 你怎么答 |
|------|------------|----------|
| 1 | 组内周报链接 | 粘贴 otl 链接，如 `https://365.kdocs.cn/l/TEAM_LINK_ID` |
| 2 | 部门周报链接 | 粘贴 ksheet 链接，如 `https://365.kdocs.cn/l/DEPT_LINK_ID` |
| 3（少数情况） | 部门子表叫什么 | 从 Agent 给出的子表列表里选择 |

**Agent 不会问**：组成员名单、周次（除非你主动指定）。

---

### 2.3 配置金山文档凭证（仅首次或过期时）

若提示缺少 `wps_sid`，Agent 会给出步骤。你只需：

1. 浏览器登录 [365.kdocs.cn](https://365.kdocs.cn)  
2. **F12** → **Application** → **Cookies** → `365.kdocs.cn` → 复制 **`wps_sid`** 的值  
3. 回到对话**直接粘贴**

Agent 自动保存并继续，无需你跑命令。详见 [references/wps-sid-guide.md](references/wps-sid-guide.md)。

---

### 2.4 预览 → 确认 → 写回

Agent 展示迁移预览（人数、周次、目标列），你核对后回复：

```
确认
```

**未确认前不会上传云端。**

写回成功后：

1. 浏览器打开部门周报  
2. **Ctrl+F5** 强刷  
3. 抽查本周列内容、换行、D 列链接  

---

### 第一次使用 · 对话示例

```
你：  请安装周报迁移 Skill 并执行周报迁移
      （或：已打开 Skill 目录，直接说「周报迁移」）

Agent：（自动 clone/安装/预检…）
      请提供组内周报链接
你：  https://365.kdocs.cn/l/TEAM_LINK_ID

Agent：请提供部门周报链接
你：  https://365.kdocs.cn/l/DEPT_LINK_ID

Agent：（若缺凭证）请粘贴 wps_sid
你：  （粘贴）

Agent：预览 N 人 → C 列，周次 YYYY-MM-DD，是否确认写回？
你：  确认

Agent：已写回，请 Ctrl+F5 刷新部门表
```

---

## 第三步：以后每周怎么用

组内 otl 写完后，在 Cursor 说一句：

```
周报迁移
```

`config.json` 和凭证已保存时，通常不会再问链接。Agent 自动取最新一周 → 预览 → 你确认 → 写回。

---

## 常用说法

| 你想做的事 | 在对话里说 |
|------------|------------|
| 从零安装并开始 | `请安装周报迁移 Skill 并执行周报迁移` |
| 默认迁移（最新一周） | `周报迁移` |
| 同步上一周 | `周报迁移，粘贴上一周的` |
| 指定某周 | `周报迁移，week 是 2026-07-02` |
| 写回后保留本地缓存 | `周报迁移，保留缓存` |
| 重新配置文档链接 | `重新配置周报迁移的文档链接` |
| 让 Agent 重装 Skill | `请重新安装周报迁移 Skill` |

---

## 重要说明

### 写回范围

- **只改**指定周的**内容列**；不改历史周、其它子表、已有超链接  
- 粘贴内容**只排版**（列表符、缩进），**不改正文**  

### 你不需要做的事

| 不要做 | 原因 |
|--------|------|
| 手动复制 Skill 到 `.cursor/skills/` | 对 Agent 说「帮我安装」 |
| 运行 `python scripts/...` | Agent 代跑 |
| 提供组成员名单 | 从 otl 自动读取 |
| 手动编辑 `config.json` | 在对话里说改链接即可 |

### 本地缓存

写回成功后默认清空 `.cache/`；需留档时说 **「保留缓存」**。

### `wps_sid` 会过期

按 Agent 提示重新粘贴即可，无需重装 Skill。

---

## 常见问题

| 现象 | 怎么办 |
|------|--------|
| 不知道从哪开始 | 先说「加载 skill」；要迁移时再说「周报迁移」 |
| `@` 里搜不到 Skill | 无所谓，直接说 `周报迁移`；或让 Agent 安装到 `~/.cursor/skills/` 后重载窗口 |
| Agent 让你自己跑 python | 回复：`请按 Skill 要求你自动执行` |
| 预览人数少于组内人数 | otl 该周该人未写，或 `## 姓名` 与部门表 B 列不一致 |
| 部门表看不到更新 | **Ctrl+F5** 强刷 |
| 想换文档链接 | 对话里说 `更新周报迁移的文档链接` |

---

## 文档与仓库

| 资源 | 说明 |
|------|------|
| 本仓库 | https://github.com/dengabin/weekly-report-migration-skill |
| [SKILL.md](SKILL.md) | Agent 技术入口（用户无需阅读） |
| [references/wps-sid-guide.md](references/wps-sid-guide.md) | 获取 wps_sid |
| [references/mapping-rules.md](references/mapping-rules.md) | 部门表行列规则 |

---

## 快速检查清单

- [ ] 已用 Cursor 打开 Agent 对话
- [ ] 已让 Agent 安装 Skill，或已打开 Skill 目录作为工作区
- [ ] 准备好组内 otl、部门 ksheet 两个链接
- [ ] 对两个文档有读/写权限
- [ ] 组内 otl 已按 `# 日期` + `## 姓名` 写好本周内容

全部就绪后，发送：

```
周报迁移
```

或从零开始：

```
请安装周报迁移 Skill 并执行周报迁移
```
