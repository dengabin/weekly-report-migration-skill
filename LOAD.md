# 加载到其它 Cursor 项目

用户在**业务项目**（非本 Skill 开发仓库）里粘贴本目录路径并说「**加载 / 安装这个 skill**」时使用本文。

---

## 用户怎么说（复制改路径）

```
加载这个 skill：d:\branch\skills\report-migration
```

可选 — 需要 **设置页 / `/` 菜单**：

```
加载这个 skill：d:\branch\skills\report-migration，要 / 菜单
```

---

## Agent 做什么

1. **Read** [references/load-in-other-project.md](references/load-in-other-project.md)
2. **Shell**（`TargetProject` = 当前 Cursor **工作区根**，不是本目录）：

```powershell
powershell -ExecutionPolicy Bypass -File "<本目录>/scripts/workflow/install_to_project.ps1" -SkillRoot "<本目录>" -TargetProject "<当前工作区根>"
```

用户要 `/` 菜单时加 `-WithSkillMenu`。

3. 汇报：已在业务项目创建 `.cursor/rules/weekly-report-migration.mdc`；迁移时说「**周报迁移**」。

**禁止**在本步跑 preflight、pip install 或索要 otl / 部门链接。

---

## 装好后文件在哪

| 内容 | 位置 |
|------|------|
| 指针 Rule | `<业务项目>/.cursor/rules/weekly-report-migration.mdc` |
| Skill 本体、`config.json`、`.cache/` | **本目录（SKILL_ROOT）** |

---

详见 [references/install-project-skill.md](references/install-project-skill.md)。
