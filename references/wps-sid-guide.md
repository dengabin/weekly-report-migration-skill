# 获取 wps_sid（Agent 引导用户用）

当预检 `status` 为 `need_wps_sid` 或读部门 ksheet 失败（凭证过期）时，Agent **在对话中**向用户展示以下流程，并**等待用户下一条消息粘贴**，不得让用户自己去跑脚本。

---

## Agent 应发给用户的话术（可复制改写）

你需要提供一次浏览器 Cookie `wps_sid`，用于读取/写回部门 `.ksheet`（MCP 无法直接读写表格）。

### 获取步骤

1. 在 **Chrome / Edge** 打开并登录 [金山文档](https://365.kdocs.cn)（需能打开你的部门周报）
2. 按 **F12** 打开开发者工具 → 切到 **Application（应用程序）** 标签  
   - 若无 Application：切 **网络 Network** → 刷新页面 → 点任意 `kdocs.cn` 请求 → **Cookie**
3. 左侧展开 **Cookies** → 选择 `https://365.kdocs.cn` 或 `https://www.kdocs.cn`
4. 在列表中找到名为 **`wps_sid`** 的一行，**双击 Value 列**复制整段值（通常很长一串字母数字）
5. **回到本对话**，在**下一条消息**中直接粘贴，不要加引号、不要换行

### 注意

- `wps_sid` 会过期；若过几天迁移失败，按同样步骤重新复制粘贴即可
- 只需粘贴 **Value**，不要截图 Cookie 全表
- 粘贴后我会自动配置并继续迁移，**你不需要运行任何命令**

---

## Agent 收到 wps_sid 后（自动执行，用户不参与）

```bash
python scripts/workflow/setup_wps_sid.py "<用户粘贴的值>"
python scripts/workflow/preflight.py
```

然后**立即续跑** `run_preview.py` 或此前中断的步骤，无需用户再次确认「是否已配置」。

---

## 存放位置

`assets/config/auth.yaml`：

```yaml
wps:
  sid: "<wps_sid>"
  api_base: "https://api.wps.cn"
```

Agent 写入后勿将完整 sid 回显给用户；日志中仅显示掩码。
