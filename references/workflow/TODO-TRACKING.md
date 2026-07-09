# TodoWrite 八步跟踪（强制，不可省略）

> **维护约定**：编辑 `SKILL.md`、`agent.mdc`、`INDEX.md` 或任意 workflow 文档时，**不得删除或弱化**本节要求。新增 AskQuestion、禁止临时 py 等约束时，须与 TodoWrite **并列**保留，**禁止互相替代**。

---

## 何时执行

用户触发**场景 B：周报迁移**后，Agent 在跑任何脚本、读云文档之前，**第一件事**必须是 `TodoWrite`。

安装 Skill（场景 A）**不**创建本列表。

---

## 八项任务（与 workflow 01→08 一一对应）

**仅首次**使用 `merge=false` 创建；之后**只用** `merge=true` 更新 `status`。

| id | 对应文档 | 任务说明（`content` 照抄或等价） |
|----|----------|-----------------------------------|
| `step01` | [01-原则与用户边界.md](01-原则与用户边界.md) | 步骤1：原则与用户边界 |
| `step02` | [02-首次配置与文档链接.md](02-首次配置与文档链接.md) | 步骤2：首次配置与文档链接 |
| `step03` | [03-环境预检与凭证.md](03-环境预检与凭证.md) | 步骤3：环境预检与凭证 |
| `step04` | [04-周次解析与部门列.md](04-周次解析与部门列.md) | 步骤4：周次解析与部门列 |
| `step05` | [05-提取成员与生成计划.md](05-提取成员与生成计划.md) | 步骤5：提取成员与生成计划 |
| `step06` | [06-预览与用户确认.md](06-预览与用户确认.md) | 步骤6：预览与用户确认 |
| `step07` | [07-写回与格式约束.md](07-写回与格式约束.md) | 步骤7：写回与格式约束 |
| `step08` | [08-校验与汇报.md](08-校验与汇报.md) | 步骤8：校验与汇报 |

---

## 初始化模板（Agent 照抄）

```
TodoWrite(merge=false, todos=[
  { id: "step01", content: "步骤1：原则与用户边界",           status: "in_progress" },
  { id: "step02", content: "步骤2：首次配置与文档链接",       status: "pending" },
  { id: "step03", content: "步骤3：环境预检与凭证",         status: "pending" },
  { id: "step04", content: "步骤4：周次解析与部门列",         status: "pending" },
  { id: "step05", content: "步骤5：提取成员与生成计划",       status: "pending" },
  { id: "step06", content: "步骤6：预览与用户确认",         status: "pending" },
  { id: "step07", content: "步骤7：写回与格式约束",         status: "pending" },
  { id: "step08", content: "步骤8：校验与汇报",             status: "pending" }
])
```

读完 [01-原则与用户边界.md](01-原则与用户边界.md) 后立刻：

```
TodoWrite(merge=true, todos=[
  { id: "step01", status: "completed" },
  { id: "step02", status: "in_progress" }
])
```

---

## 状态更新规则

1. **每完成一个 workflow 步骤**：当前 `step0N` → `completed`，下一步 → `in_progress`。
2. **AskQuestion 阻塞**（缺 sid、缺链接、缺子表名、待写回确认）：当前步保持 `in_progress`，**禁止**结束回合；其它步保持原 `status`。
3. **禁止**再次 `merge=false`（会清空用户可见的八步列表）。
4. **禁止**只更新部分 id、导致列表里少于 8 项。
5. 用户靠 Todo 面板看「01→08 走到哪一步」；与脚本成败、AskQuestion 等约束**无关**，都必须保持八项可见。

---

## 与其它硬性规定的关系

| 约束 | 关系 |
|------|------|
| AskQuestion 不中断会话 | 阻塞时 Todo 当前步 `in_progress`，解决后续跑 |
| 禁止临时 `.py` | 并列约束，不能因加强脚本禁令而省略 TodoWrite |
| 分两次问链接 | 发生在 step02 内，step02 保持 `in_progress` |
| `need_dept_sheet` | 发生在 step03 内，step03 保持 `in_progress` |

---

**权威引用**：本文件为 TodoWrite 的单一事实来源；`SKILL.md`、`agent.mdc`、`INDEX.md` 均须指向此处。
