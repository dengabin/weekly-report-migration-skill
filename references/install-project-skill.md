# 在业务项目里使用本 Skill

用户在**其它项目**里说「加载这个 skill」并**粘贴 Skill 目录**时，Agent 应自动配置。

| 文档 | 读者 |
|------|------|
| [LOAD.md](../LOAD.md) | 用户 & Agent（入口，最短） |
| [load-in-other-project.md](load-in-other-project.md) | Agent（逐步手册） |
| 本文 | 用户 & Agent（机制说明） |

**一键脚本**：`scripts/workflow/install_to_project.ps1`

```
加载这个 skill：d:\branch\skills\report-migration
```

---

## 用户怎么说（复制即用）

在**业务项目**打开 Cursor，对 Agent 说：

```
加载这个 skill：d:\branch\skills\report-migration
```

Agent 会：

1. 校验该目录含 `SKILL.md`
2. 在当前项目创建 `.cursor/rules/weekly-report-migration.mdc`（指针 Rule）
3. 告知「说周报迁移即可开始」

**不需要**用户自己复制文件夹或跑 PowerShell（除非 Agent 不可用）。

若要 **设置页 / `/` 菜单** 也出现 Skill，可说：

```
加载这个 skill：d:\branch\skills\report-migration，要 / 菜单
```

Agent 会在 Rule 之外再加 `.cursor/skills/` 联接。

---

## 三种机制对比

| 机制 | 谁创建 | 设置 / `/` | 说「加载 skill」 | 说「周报迁移」 |
|------|--------|------------|------------------|----------------|
| **指针 Rule（默认）** | `install_to_project.ps1` | ❌ | 执行安装 | ✅ |
| **项目级 Skill 目录（可选）** | 同上 `-WithSkillMenu` | ✅ | — | ✅ |
| **仅打开 Skill 仓库** | 无 | ❌ | 仅仓库内有效 | ✅ 仅仓库内 |

---

## 机制说明

### Skill 能否出现在设置里？

只有 Cursor **索引**到 `.cursor/skills/<name>/SKILL.md` 或全局 `~/.cursor/skills/` 时才会出现。  
**指针 Rule 不会**出现在 Skills 列表——这是正常的，不影响执行。

### Rule 做什么？

薄文件 `.cursor/rules/weekly-report-migration.mdc` 写明：

- 触发词（周报迁移…）
- `SKILL_ROOT` 绝对路径
- 触发后 Agent `Read` 外部 `SKILL.md` 并执行

### 「加载 skill」做什么？

**不是**把 Skill 拷进项目，而是 **Agent 自动写好 Rule**（和可选的 Skill 联接）。

---

## 手动安装（Agent 不可用时）

```powershell
powershell -ExecutionPolicy Bypass -File "d:\branch\skills\report-migration\scripts\workflow\install_to_project.ps1" -SkillRoot "d:\branch\skills\report-migration" -TargetProject "D:\your-app"
```

加 `-WithSkillMenu` 可同时注册 `/` 菜单。

---

## 数据位置

`config.json`、`wps_sid`、`.cache/` 始终在 **SKILL_ROOT**（用户粘贴的目录），不在业务项目根目录。

---

## 快速决策

```
用户在别的项目贴路径 + 加载 skill
  → Agent 跑 install_to_project.ps1（默认 Rule）

还要 / 菜单
  → 加 -WithSkillMenu

只开发 Skill 本体
  → 打开 Skill 仓库当工作区
```
