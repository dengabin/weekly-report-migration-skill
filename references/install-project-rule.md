# 在业务项目里启用周报迁移（指针 Rule）

用户在**其它项目**粘贴 Skill 目录并说「**加载这个 skill**」时，Agent 自动在当前项目写入 **一个** `.mdc` 规则文件，**不**安装 `.cursor/skills/`、**不**注册 `/` 菜单。

| 文档 | 读者 |
|------|------|
| [LOAD.md](../LOAD.md) | 用户 & Agent（入口） |
| [load-in-other-project.md](load-in-other-project.md) | Agent（逐步手册） |
| 本文 | 机制说明 |

**一键脚本**：`scripts/workflow/install_to_project.py`

---

## 用户怎么说

在**业务项目**打开 Cursor：

```
加载这个 skill：d:\branch\skills\report-migration
```

Agent 会创建：

```
<业务项目>/.cursor/rules/weekly-report-migration.mdc
```

之后说「**周报迁移**」或 @该规则即可。`config.json`、`.cache/` 在 **SKILL_ROOT** 的 `profiles/<PROFILE_ID>/`（安装时按业务项目路径自动分配）。

---

## 机制

| 项目 | 说明 |
|------|------|
| 指针 Rule | 写明触发词 + `SKILL_ROOT`；Agent 触发后 `Read` 外部 `SKILL.md` |
| 为何不装 Skill 目录 | Cursor Skills 列表与 `/` 菜单非必需；Rule 更轻、可提交 Git |
| 「加载 skill」做什么 | 只写 `.mdc`，**不**复制 Skill、**不**跑 preflight |

---

## 手动安装（Agent 不可用时）

```bash
python "d:\branch\skills\report-migration\scripts\workflow\install_to_project.py" --skill-root "d:\branch\skills\report-migration" --target-project "D:\your-app"
```

---

## 卸载

删除 `<业务项目>/.cursor/rules/weekly-report-migration.mdc`。

---

## 与 Skill 开发仓库的区别

| 场景 | 做法 |
|------|------|
| 在业务项目用迁移 | 贴路径 + 加载 → 装 `.mdc` |
| 改 Skill 代码 | 打开 Skill 仓库当工作区；已有 `report-migration-agent.mdc` |
