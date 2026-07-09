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

0. **Read** `{SKILL_ROOT}/LOAD.md`（本页摘要）与本文全文

### 1. 解析并校验 SKILL_ROOT

- 从用户消息提取目录路径，规范化为绝对路径
- 确认存在 `{SKILL_ROOT}/SKILL.md` 与 `{SKILL_ROOT}/scripts/workflow/install_to_project.ps1`
- 不存在 → 告知用户路径无效，**停止**

### 2. 确定业务项目根目录 TARGET_PROJECT

- 默认 = **当前 Cursor 工作区根目录**（`workspace root`）
- 若用户明确指定其它项目路径，用用户指定的
- **禁止**把 SKILL_ROOT 当成 TARGET_PROJECT

### 3. 自动安装（默认：指针 Rule，不复制 Skill）

在 Shell 中执行（Agent 代跑，不让用户手敲）：

```powershell
powershell -ExecutionPolicy Bypass -File "{SKILL_ROOT}/scripts/workflow/install_to_project.ps1" -SkillRoot "{SKILL_ROOT}" -TargetProject "{TARGET_PROJECT}"
```

脚本会：

- 创建 `{TARGET_PROJECT}/.cursor/rules/weekly-report-migration.mdc`
- 写入正确的 `SKILL_ROOT`
- 若已存在则**覆盖更新**路径（幂等）

**默认不**安装 `.cursor/skills/`（除非用户明确要求「要 / 菜单」或「要设置里显示」）。

若用户要 Skill 菜单入口，追加参数：

```powershell
... install_to_project.ps1 ... -WithSkillMenu
```

### 4. 向用户汇报（场景 A 结束）

示例回复：

> 已在当前项目配置周报迁移 Skill。  
> - 指针规则：`.cursor/rules/weekly-report-migration.mdc`  
> - Skill 本体：`{SKILL_ROOT}`（未复制到本项目）  
>  
> 需要迁移时说 **「周报迁移」** 或 @weekly-report-migration。  
> 首次会分两次收集组内 / 部门文档链接。

**禁止**在本步跑 preflight、**禁止**索要文档链接、**禁止** pip install。

### 5. 与场景 B 的边界

| 用户说 | 场景 |
|--------|------|
| 加载 / 安装 skill（+ 路径） | **A** → 只装 Rule/可选 Skill 目录 |
| 周报迁移、填部门周报… | **B** → Read SKILL.md → workflow 01→08 |

若用户同一句里既给路径又说「周报迁移」→ 先完成步骤 3 安装，**紧接着自动进入场景 B**（不必再等用户二次触发）。

---

## 安装后文件布局

```
TARGET_PROJECT/
  .cursor/
    rules/
      weekly-report-migration.mdc    ← Agent 根据触发词 Read 外部 SKILL

SKILL_ROOT/                          ← 用户粘贴的目录，唯一本体
  SKILL.md
  config.json                        ← 首次迁移后生成
  .cache/
  scripts/...
```

---

## 故障排查

| 现象 | 处理 |
|------|------|
| 业务项目无 `.cursor` | 脚本自动创建 |
| Rule 已存在但路径旧 | 重跑 `install_to_project.ps1` 覆盖 |
| 用户要卸载 | 删除 `weekly-report-migration.mdc`；可选删除 `.cursor/skills/weekly-report-migration` 联接 |

---

**相关**： [LOAD.md](../LOAD.md)、[install-project-skill.md](install-project-skill.md)、[templates/report-migration-pointer.mdc](../templates/report-migration-pointer.mdc)
