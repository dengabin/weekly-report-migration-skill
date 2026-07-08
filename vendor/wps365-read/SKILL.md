---
name: wps365-read
description: WPS 365 V7 API skill 工具集，包含云文档、多维表、智能表格、传统表格、AI 知识库等办公协作能力。用户需要在 WPS 365 中查询这些资源时使用本 skill，并按需继续打开对应子 skill 获取详细命令与参数。
---

# WPS 365 Skill 工具集

聚合入口只保留最常用的导航信息；具体命令、参数和返回结构通过子 skill 渐进式披露，避免重复占用上下文窗口。

## 快速开始

```bash
cd wps365-read
```

- 默认在仓库根目录执行 `python skills/<skill>/run.py ...`
- 需要详细命令、参数约束或返回字段时，再打开对应子 skill 的 `SKILL.md`

## Skill 概览

| Skill | 能力 | 常见触发 | 详细说明 |
|------|------|----------|----------|
| `drive` | 云文档管理与文档内容提取解析（get-file-content，支持所有主流格式；云文档或本地文件均可） | 解析/提取/读取任意文档内容（含本地文件）、找文档、上传下载、管分享、kdocs.cn 链接 | [skills/drive/SKILL.md](skills/drive/SKILL.md) |
| `ai-docs` | AI 知识库列表与召回 | 找知识库、从知识库召回片段 | [skills/ai-docs/SKILL.md](skills/ai-docs/SKILL.md) |

## 常见场景

### 围绕文档做操作

1. 目标是知识库召回：直接切到 [skills/ai-docs/SKILL.md](skills/ai-docs/SKILL.md)
2. **其他所有文档**的内容提取/解析（Word、Excel、PPT、PDF、图片、网页、代码文件、智能文档等）、正文抽取、Markdown 写回、搜索文档、文件流转：打开 [skills/drive/SKILL.md](skills/drive/SKILL.md)，使用 `get-file-content`（云文档传 file_id，本地文件直接传路径）

## 使用原则

- 先在本文件定位能力，再按需打开一个子 skill，避免一次性加载全部细节
- 需要副作用操作时，优先确认目标对象标识，例如 `driver_id`、`file_id`
- **歧义消解**：需要定位单一目标对象但搜索命中多条时，须通过 `askUserQuestion` 让用户选择，不得自行挑选；用户意图明确覆盖多条（如"把这些都…"）或仅浏览列表时无需确认
- **严禁用 `2>/dev/null` 或其他方式吞掉 stderr**：命令失败时 stderr 含关键错误信息，吞掉会导致无法区分"没有结果"和"查询失败"
- 子 skill 若存在更细的注意事项，以子 skill 说明为准
