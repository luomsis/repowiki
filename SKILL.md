---
name: repowiki
description: Generate a Qoder-style RepoWiki (structured Chinese wiki with mermaid diagrams and file:// source links) for any repository. Use when the user asks to "generate repo wiki", "生成/更新 repowiki", "给仓库生成 wiki 文档", or mentions repowiki/仓库文档/RepoWiki. Works on any repo path; concurrent subagents supported.
trigger: /repowiki
---

# repowiki：为仓库生成 Qoder 风格的 Wiki

`repowiki` 是一个确定性的任务编排器（无 LLM）：它规划任务、校验产出、组装元数据。
**你（agent）负责所有智能工作**：读仓库源码、按任务规格撰写中文 wiki 页面。

## 前置

```bash
pip install -e /Users/luoms/workspace/repowiki   # 一次性安装，提供 repowiki 命令
```

## 标准流程（串行）

对目标仓库（下称 `<repo>`）依次执行：

```bash
repowiki plan <repo>          # 1. 扫描并生成任务清单（首个任务是 catalog 目录规划）
repowiki next <repo> --claim --json   # 2. 领取一个任务（读返回的 instructions 字段）
#    3. 按任务规格执行：通读 hint_files 源码 → 按模板撰写 → 写到规格指定的 output 路径
repowiki check <repo> --task <id>     # 4. 校验；失败则按 errors 修复后重新 check
#    5. 回到第 2 步，直到 next 返回空且 busy=0
repowiki finalize <repo>      # 6. 首次会创建 overview 任务→执行→再 finalize 生成 metadata.json
#    （finalize 成功后自动清理 state/claims 与 state/tasks；catalog/index 保留供 update）
#    不需要增量更新时可执行 `repowiki clean <repo>` 删除全部任务状态
```

任务类型：`catalog`（目录树规划，产出 state/catalog.json）→ `page`（逐页撰写）→ `overview`（总览）；
可选：`repowiki knowledge <repo>`（知识卡片）、`repowiki update <repo>`（基于 git diff 的增量更新，重写受影响页并附「更新摘要」小节）。

## 并发流程（推荐，subagent 加速）

catalog 任务完成后所有页面任务相互独立，可安全并行：

1. 主 agent 完成 `plan` + catalog 任务（串行，这是唯一前置）。
2. 主 agent 派 N 个 subagent，每个 subagent 独立执行同一 worker 循环：

```
loop:
  1. 运行 `repowiki next <repo> --claim --json --worker <名字>`
  2. 若 tasks 为空且 busy>0 → 等待 30 秒重试（其他 worker 正在写）
     若 tasks 为空且 busy=0 → 结束
  3. 按 tasks[0].instructions 执行（只写 instructions 指定的 output 文件）；
     撰写期间每隔几分钟运行 `repowiki touch <repo> --task <id> --worker <名字>` 续期认领
  4. 运行 `repowiki check <repo> --task <id> --worker <名字> --json`
     - ok=true → 回到 1
     - ok=false → 按 errors 修复同一文件后重新 check（最多 3 次，仍失败则
       `repowiki release <repo> --task <id> --force` 并结束本任务）
```

注意：`check` 必须显式带 `--task`（或崩溃恢复用 `--all`）；done 是终态，重复 check 只读不改状态；
`finalize` 第一次运行退出码为 3（表示已创建 overview 任务，属正常进展）。

3. 全部完成后主 agent 执行 `finalize`（两步：创建 overview → 执行 → 再 finalize）。

## 硬性规则

- **只写任务规格指定的 output 文件**，绝不改动仓库源码。
- 页面遵循规格内嵌的模板与 STYLE 规范：必备小节齐全、每节末尾「章节来源」、每个 mermaid 图后「图表来源」、`[path:Lx-Ly](file://path#Lx-Ly)` 格式、行号不越界、页间零链接、不用 emoji/表格。
- `check` 的确定性缺陷（锚点/行号/H1）会被自动修复，无需手动处理；只需修复 `errors` 列出的语义问题。
- 输出位于 `<repo>/.repowiki/`（zh/content 页面、zh/meta 元数据、knowledge/zh 知识卡片）。
