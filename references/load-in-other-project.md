# 在其它项目里「加载本 Skill」（Agent 执行手册）

> **何时读本文**：用户在**业务项目**工作区粘贴 Skill 目录路径并说「加载 / 安装这个 skill」时。  
> **不要**在用户仅打开 Skill 开发仓库当工作区时读本文（那种情况只需确认就绪）。

---

## 用户典型输入

```
加载这个 skill：d:\branch\skills\report-migration
```

或分开两句：先贴路径，再说「加载 skill」。

---

## Agent 必须执行的步骤

0. **Read** `{SKILL_ROOT}/LOAD.md` 与本文

### 1. 解析并校验 SKILL_ROOT

- 从用户消息提取目录路径，规范化为绝对路径
- 确认存在 `{SKILL_ROOT}/SKILL.md` 与 `{SKILL_ROOT}/scripts/workflow/install_to_project.py`
- 不存在 → 告知用户路径无效，**停止**

### 2. 确定业务项目根目录 TARGET_PROJECT

- 默认 = **当前 Cursor 工作区根目录**
- 若用户明确指定其它项目路径，用用户指定的
- **禁止**把 SKILL_ROOT 当成 TARGET_PROJECT

### 3. 自动安装指针 Rule（仅此一步，不装 Skill 目录）

```bash
python "{SKILL_ROOT}/scripts/workflow/install_to_project.py" --skill-root "{SKILL_ROOT}" --target-project "{TARGET_PROJECT}"
```

（Windows 亦可：`powershell -ExecutionPolicy Bypass -File .../install_to_project.ps1 -SkillRoot ... -TargetProject ...`）

生成：`{TARGET_PROJECT}/.cursor/rules/weekly-report-migration.mdc`  
若已存在则**覆盖更新** `SKILL_ROOT`（幂等）。

**禁止**安装 `.cursor/skills/` 或配置 `/` 菜单。

### 4. 向用户汇报（场景 A 结束）

> 已在当前项目配置周报迁移（指针 Rule）。  
> - 规则：`.cursor/rules/weekly-report-migration.mdc`  
> - Skill 本体：`{SKILL_ROOT}`  
>  
> 需要迁移时说 **「周报迁移」** 或 @weekly-report-migration。

**禁止**在本步跑 preflight、索要文档链接、pip install。

### 5. 与场景 B 的边界

| 用户说 | 场景 |
|--------|------|
| 加载 / 安装 skill（+ 路径） | **A** → 只装 `.mdc` |
| 周报迁移、填部门周报… | **B** → Read SKILL.md → workflow 01→08 |

若用户同一句里既给路径又说「周报迁移」→ 先完成步骤 3，**紧接着进入场景 B**。

---

## 安装后文件布局

```
TARGET_PROJECT/
  .cursor/
    rules/
      weekly-report-migration.mdc

SKILL_ROOT/
  SKILL.md
  profiles/<业务项目 profile>/
    config.json
    .cache/
  scripts/...
```

---

## 故障排查

| 现象 | 处理 |
|------|------|
| 业务项目无 `.cursor` | 脚本自动创建 |
| Rule 路径旧 | 重跑 `install_to_project.ps1` |
| 卸载 | 删除 `weekly-report-migration.mdc` |

---

**相关**：[LOAD.md](../LOAD.md)、[install-project-rule.md](install-project-rule.md)、[templates/report-migration-pointer.mdc](../templates/report-migration-pointer.mdc)
