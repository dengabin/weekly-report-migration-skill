# Agent 执行索引（按序阅读，不可跳步）

> **仅当用户要执行迁移**（如「周报迁移」）时，才按下列顺序阅读并执行。  
> 用户只说「加载 / 安装 skill」时：**不要**进入本索引，见 [01-原则与用户边界.md](01-原则与用户边界.md) §1.0。

| 步骤 | 文档 | 何时执行 |
|------|------|----------|
| 1 | [01-原则与用户边界.md](01-原则与用户边界.md) | **每次**触发 Skill 时首先阅读 |
| 2 | [02-首次配置与文档链接.md](02-首次配置与文档链接.md) | `config.json` 缺链接或首次使用时 |
| 3 | [03-环境预检与凭证.md](03-环境预检与凭证.md) | 每次迁移开始前 |
| 4 | [04-周次解析与部门列.md](04-周次解析与部门列.md) | 预检通过后、提取内容前 |
| 5 | [05-提取成员与生成计划.md](05-提取成员与生成计划.md) | 周次与列就绪后 |
| 6 | [06-预览与用户确认.md](06-预览与用户确认.md) | 计划生成后、写回前 |
| 7 | [07-写回与格式约束.md](07-写回与格式约束.md) | 用户确认写回后 |
| 8 | [08-校验与汇报.md](08-校验与汇报.md) | 写回完成后 |

## 执行规则

1. **每步开始前**必须先 `Read` 该步 MD 全文，再动手。
2. 某步条件不满足（如缺 `wps_sid`）时，**在该步内完成**（引导用户、等待输入、自动续跑），不得跳过后续步骤的逻辑要求。
3. 步骤 2 可在已有 `config.json` 时**快速过一遍**确认，不必重复问答。
4. 技术细节延伸阅读（非逐步必读）：  
   - [../wps-sid-guide.md](../wps-sid-guide.md)  
   - [../week-resolution.md](../week-resolution.md)  
   - [../ksheet-mcp-limitation.md](../ksheet-mcp-limitation.md)  
   - [../team-name-resolution.md](../team-name-resolution.md)  
   - [../mapping-rules.md](../mapping-rules.md)  
   - [../../vendor/README.md](../../vendor/README.md)（内置 wps365-read）

## 一键脚本对照

| 阶段 | Agent 执行的命令 |
|------|------------------|
| 步骤 3 | `pip install -r requirements.txt` → `python scripts/workflow/preflight.py` |
| 步骤 5 | `python scripts/workflow/run_preview.py`（或分步 extract → format → plan） |
| 步骤 7 | `python scripts/workflow/apply_migration.py --upload` |
| 步骤 8 | 写回成功后自动 `cleanup_cache.py`（用户未要求保留时） |

用户**永不**手动执行上表命令。
