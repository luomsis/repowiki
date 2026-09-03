---
name: repowiki
description: 为任意代码仓库生成结构化的仓库 Wiki（mermaid 图、file:// 源码引用；产出语言自动跟随仓库 zh/en，可 --locale 指定）。Use when the user asks to generate a repo wiki, "生成/更新 repowiki", "给仓库生成 wiki 文档", or mentions repowiki / 仓库文档 / repo wiki. Works on any repo path; supports concurrent subagents.
---

# repowiki：为仓库生成结构化的 Wiki

`repowiki` 是一个确定性的任务编排器（无 LLM）：它规划任务、校验产出、组装元数据。
**你（agent）负责所有智能工作**：读仓库源码、按任务规格撰写 wiki 页面（产出语言跟随目标仓库）。

## 前置

`repowiki` CLI 需一次性安装（Python ≥ 3.10，仅 macOS/Linux）：

```bash
pip install git+https://github.com/luomsis/repowiki.git   # 或 pipx install git+同URL
# 已克隆仓库时：cd repowiki && pip install -e .
```

执行前先确认 `repowiki` 命令可用（`command -v repowiki`）；不存在则先安装。

## 标准流程（串行）

对目标仓库（下称 `<repo>`）依次执行：

```bash
repowiki plan <repo>          # 1. 扫描并生成任务清单（自动检测产出语言 zh/en；首个任务是 catalog 目录规划）
repowiki next <repo> --claim --json   # 2. 领取一个任务（读返回的 instructions 字段）
#    3. 按任务规格执行：通读 hint_files 源码 → 按模板撰写 → 写到规格指定的 output 路径
repowiki check <repo> --task <id>     # 4. 校验；失败则按 errors 修复后重新 check
#    5. 回到第 2 步，直到 next 返回空且 busy=0
repowiki finalize <repo>      # 6. 首次会创建 overview 任务→执行→再 finalize 生成 metadata.json
#    （finalize 成功后自动清理 state/claims 与 state/tasks；catalog/index 保留供 update）
#    不需要增量更新时可执行 `repowiki clean <repo>` 删除全部任务状态
```

任务类型：`catalog`（目录树规划，产出 state/catalog.json）→ `page`（逐页撰写）→ `overview`（总览）；
可选：`repowiki knowledge <repo>`（知识卡片）、`repowiki update <repo>`（基于 git diff 的增量更新，重写受影响页并附「更新摘要/Update Summary」小节）。
产出语言由 plan 时确定（README 权重最高的自动检测，或 `--locale zh|en`），持久化于 `state/locale`，规格中的模板即对应语言。

## 并发流程（推荐，subagent 加速）

catalog 任务完成后所有页面任务相互独立，可安全并行：

1. 主 agent 完成 `plan` + catalog 任务（串行，这是唯一前置）。
2. 主 agent 派 N 个**等价** subagent 执行同一 worker 循环。
   **禁止给 worker 指定任务 ID 或清单**：队列是全局 FIFO，分工完全由 `next` 决定；
   主 agent 只决定 worker 数量与 `--worker` 命名。
3. worker 循环（每个 subagent 独立执行）：

```
loop:
  1. 运行 `repowiki next <repo> --claim --json --worker <名字>`
  2. 若 tasks 为空且 busy>0 → 等待 30 秒重试（其他 worker 正在写）
     若 tasks 为空且 busy=0 → 结束
  3. 按 tasks[0].instructions 执行（只写 instructions 指定的 output 文件）。
     一次只持有一个认领：每次 next 只发放一个任务，当前任务完成前不得再次 next --claim；
     认领后立即 `repowiki touch <repo> --task <id> --worker <名字>` 一次，
     撰写期间每约 3 分钟 touch 一次（认领超过 stale 窗口未续期会被自动回收转给他人）
  4. 运行 `repowiki check <repo> --task <id> --worker <名字> --json`
     - ok=true → 回到 1
     - 报「由他人认领」冲突（exit 2）→ 该认领已被回收并被接手：
       不争抢、不加 --force，回到 1
     - ok=false → 按 errors 修复同一文件后重新 check（最多 3 次，仍失败则
       `repowiki release <repo> --task <id> --force` 并结束本任务）
```

注意：`check` 必须显式带 `--task`（或崩溃恢复用 `--all`）；done 是终态，重复 check 只读不改状态；
`finalize` 第一次运行退出码为 3（表示已创建 overview 任务，属正常进展）。

4. 主 agent 运行 watch 监控。**必须真正后台运行并给足 `--timeout`**（按预期总时长 × 1.5 设置），
   例如 `nohup repowiki watch <repo> --interval 15 --timeout 7200 --json > watch.log 2>&1 &`；
   前台交给有超时限制的 bash 工具运行时，超时会杀掉 watch，**被杀进程的退出码不可信**
   （exit 0 可能只是截断假象，存疑时先用 `repowiki status` 核实）。
   watch 自动退出：**exit 0** = 全部完成 → 执行 finalize（两步：创建 overview → 执行 → 再 finalize）；
   **exit 1** = 停滞或超时 → 用 `repowiki status <repo>` 查看详情并干预：
   exhausted 毒任务用 `release --task <id> --force` 重置；stale 认领会自动回队列
   （默认 15 分钟），无需人工释放，确认 worker 是否存活、必要时补派即可。

## 环境变量

- `REPOWIKI_STALE_SECONDS`：认领过期窗口（默认 900 秒 = 15 分钟）。worker 死亡后其任务
  最长冻结这么久即自动回队列；worker 遵守 touch 纪律时不会被误抢，一般无需调整。
- `REPOWIKI_MAX_ATTEMPTS`：单任务最大尝试次数（默认 3），超过后 exhausted，
  需 `release --task <id> --force` 重置。

## 硬性规则

- **只写任务规格指定的 output 文件**，绝不改动仓库源码。
- 页面遵循规格内嵌的模板与 STYLE 规范：必备小节齐全、每节末尾「Section sources/章节来源」、每个 mermaid 图后「Diagram sources/图表来源」、`[path:Lx-Ly](file://path#Lx-Ly)` 格式、行号不越界、页间零链接、不用 emoji/表格。
- `check` 的确定性缺陷（锚点/行号/H1）会被自动修复，无需手动处理；只需修复 `errors` 列出的语义问题。
- 输出位于 `<repo>/.repowiki/`（`<locale>/content` 页面、`<locale>/meta` 元数据、`knowledge/<locale>/` 知识卡片；locale 已在 plan 时确定）。
