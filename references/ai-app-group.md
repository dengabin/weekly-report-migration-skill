# AI应用组周报迁移 — 本组配置说明

## 文档对应关系（已按内容自动识别）

| 角色 | 文档 | 链接 | 格式 |
|------|------|------|------|
| **小组周报（源头）** | 版式AI应用组26年周报 | https://365.kdocs.cn/l/cpqRAGyILoLO | `.otl` |
| **部门周报（目标）** | 2026版式产研部-周报 | https://365.kdocs.cn/l/cqGvaEAyY8lG | `.ksheet` |

> 你消息里两个都写了「部门周报」；按文档标题与内容，**otl 是组内每人写的源头**，**ksheet 是产研部汇总表（含多个四级部门子表）**。

## 当前自动识别

- **组名**：AI应用组
- **本周区块**：`# 2026-07-02`（otl 中最新且 ≤ 今天的日期段）
- **成员**：16 人（已从 otl 提取，见 `config.json`）

## 部门 ksheet 的特殊说明

`.ksheet` 目前 **WPS365 MCP 无法直接读/写**（内容抽取返回 400，dbsheet API 缺权限）。

可选方案（任选其一）：

1. **配置 wps365-read + WPS_SID**（推荐自动化）  
   在 `wps365-read` 目录配置 `assets/config/auth.yaml` 或 `$env:WPS_SID`，然后：
   ```bash
   python skills/drive/run.py download cqGvaEAyY8lG --dir .cache
   python scripts/plan/list_dept_sheets.py --config config.json --input .cache/xxx.ksheet
   ```

2. **手动下载部门表**到 `.cache/dept-report.ksheet`，再让 Agent 用 `list_dept_sheets` / `plan_sheet_patches` 定位 **AI应用组** 子表后写入。

3. **在 Cursor 里说**：「我已把部门周报下载到 `.cache/dept-report.ksheet`」，Agent 继续后续步骤。

## 每周一句话

```
用周报迁移 skill，同步本周 AI应用组周报到产研部周报
```

Skill 加载后会**自动跑 preflight**；首次若缺 WPS_SID，按提示粘贴一次即可。

若周次不是默认最新一期，可说「上周」「week 是 YYYY-MM-DD」等，见 [week-resolution.md](references/week-resolution.md)。

一键本地预览（**Agent 执行**）：`python scripts/workflow/run_preview.py`
