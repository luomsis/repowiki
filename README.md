# repowiki

复刻 Qoder [RepoWiki](https://docs.qoder.com/user-guide/repo-wiki) 的仓库 Wiki 生成器——但**不含任何 LLM**。

`repowiki` 是一个确定性的构建系统：负责任务规划、原子认领、产出校验、自动修复、元数据组装；
智能工作（读代码、写 wiki）由驱动它的 agent（ZCode / Claude Code / Codex / OpenCode / 人）完成。
零 API Key、零网络调用、零 agent CLI 依赖——任何「能跑 shell + 读写文件」的执行者都能参与，包括并发。

```
┌────────────┐  plan     ┌─────────────────────────────────────────┐
│  驱动 agent │ ────────▶ │ .repowiki/state/  任务清单+规格    │
│ (串行/并发) │ ◀──────── │  catalog → pages → overview 三阶段      │
│            │  next     │  原子认领 · 断点续跑 · 过期回收           │
│  写页面/JSON │ ────────▶ │ zh/content/**.md  (校验+自动修复)       │
└────────────┘  check    │ zh/meta/repowiki-metadata.json          │
                         │ knowledge/zh/**  (模块+机制卡片)         │
                         └─────────────────────────────────────────┘
```

## 安装

```bash
pip install -e .        # 依赖仅 pyyaml + rich，Python ≥ 3.10
```

## 快速开始

```bash
repowiki plan ~/code/myrepo          # 扫描 → 生成任务清单（代码文件 <10 会拒绝）
repowiki next ~/code/myrepo --claim --json   # 领取任务，按 instructions 执行
# ... 按任务规格撰写产出，然后：
repowiki check ~/code/myrepo --task c01      # 校验+自动修复+状态流转
repowiki finalize ~/code/myrepo      # 组装 metadata.json（两步：先创建 overview 任务）
```

输出结构（与 Qoder RepoWiki 格式一致）：

```
myrepo/.repowiki/
├── zh/
│   ├── content/            # 章节树：目录名=章节名，索引页+子页，固定模板
│   │   ├── 快速开始.md      # 顶级独立页
│   │   └── 项目概述/项目概述.md, 核心概念.md, ...
│   └── meta/repowiki-metadata.json   # catalogs/items/source_files/snippets/relations
├── knowledge/zh/           # 知识卡片：_index.yaml + 模块文档 + 机制卡片
└── state/                  # 任务清单/规格/认领（内部状态，可随时删除重规划）
```

页面模板（校验器强制）：H1 → `<cite>` 引用块 → 目录（中文锚点）→ 简介 → 项目结构（mermaid
graph TB）→ 核心组件 → 架构总览（sequenceDiagram）→ 详细组件分析 → 依赖关系分析（graph LR）
→ 性能与一致性考量 → 故障排查指南 → 结论；每节末尾「章节来源」、每图后「图表来源」，
链接格式 `[path:Lx-Ly](file://path#Lx-Ly)`；页间零链接（正因如此所有页面任务可完全并行）。

## Worker 循环契约

任何执行者（subagent / 进程 / 人）按此循环参与，多个循环可同时运行：

```
loop:
  t = repowiki next <repo> --claim --json
  tasks 为空且 busy>0  → 等待重试（他人执行中）
  tasks 为空且 busy=0  → 退出
  按 t.tasks[0].instructions 执行（只写指定的 output 文件）
  repowiki check <repo> --task <id> --json
    ok=false → 按 errors 修复后重查；放弃则 repowiki release <repo> --task <id> --force
```

### 并发配方

**Subagent 型（ZCode / Claude Code / OpenCode）**：主 agent 先串行完成 plan + catalog，
然后 spawn N 个 subagent 各自跑 worker 循环（N=3~6 即可，页面任务相互独立）。
详见 [SKILL.md](SKILL.md)。

**无人值守（任何 headless agent CLI，由你决定用哪个）**：

```bash
#!/bin/bash
# worker.sh —— 把 claude 换成 codex exec / opencode run，工具不感知、不限制用哪个 agent
while :; do
  TASK=$(repowiki next . --claim --batch 1 --json)
  N=$(echo "$TASK" | jq '.tasks | length')
  if [ "$N" -eq 0 ]; then
    [ "$(echo "$TASK" | jq '.busy')" -eq 0 ] && break   # 空且无人执行 → 退出
    sleep 30 && continue                                # 空但 busy>0 → 等待重试
  fi
  ID=$(echo "$TASK" | jq -r '.tasks[0].id')
  claude -p "$(echo "$TASK" | jq -r '.tasks[0].instructions')" --permission-mode acceptEdits &
  while kill -0 $! 2>/dev/null; do
    repowiki touch . --task "$ID"; sleep 300            # 执行期心跳，防长任务被回收
  done
  repowiki check . --task "$ID" --worker my-worker
done
```

## 命令一览

| 命令 | 作用 |
|---|---|
| `plan <repo> [--replan [--force]] [--max-pages N] [--knowledge]` | 扫描+生成任务清单；已有合法 catalog.json 则直接展开页面任务；有任务执行中时 replan 需 --force |
| `next [--claim] [--batch N] [--json]` | 领取就绪任务（阶段门控：attempts 少者优先）；`--json` 含完整 instructions |
| `touch --task ID` | 执行期心跳：刷新认领，防长任务被过期回收 |
| `watch [--interval S] [--timeout S]` | 阻塞监控直到全部完成（exit 0）或停滞/超时（exit 1）；主会话据此决定 finalize 或干预 |
| `check --task ID \| --all` | 校验产出；锚点/行号/H1 自动修复；catalog/knowledge-plan 通过后自动展开后续任务；done 为终态（只读报告）；他人认领的任务需 --force |
| `release --task ID [--force]` | 释放认领（崩溃恢复） |
| `finalize` | 组装 metadata.json；要求全部任务 done |
| `update [--since <sha>]` | git diff → 受影响页面（含祖先链）→ 增量重写任务（附「更新摘要」）；仅识别**已提交**变更（since..HEAD），工作区未提交改动不可见 |
| `knowledge` | 追加知识卡片任务集（六类机制卡片 + 模块文档） |
| `status` | 进度 / 失败列表 / 过期认领 |
| `clean` | 删除整个 `state/`（wiki 产出保留；失去 update/续跑/幂等 plan） |

退出码：`0` 成功，`1` 校验失败或用法错误，`2` 状态冲突（任务被他人认领），`3` 进展性等待（finalize 已创建 overview 任务，完成后再次运行即可）。

## 可靠性设计

- **并发安全**：原子 `mkdir` 认领 + 目录 mtime 过期判定（默认 45 分钟，
  `REPOWIKI_STALE_SECONDS` 可调）；崩溃 worker 的任务可被安全回收。
- **确定性优先**：锚点、行号区间、H1、路径分隔符由程序自动修复；
  只有语义缺陷（缺章节、引用不存在文件、mermaid 不闭合）才判失败。
- **断点续跑**：每任务状态落盘（`state/index.json`），随时中断随时继续。
- **自动瘦身**：finalize 成功后自动清除运行时产物（`state/claims/`、`state/tasks/`），
  保留 `index.json`/`catalog.json`/`knowledge.json` 供增量更新与幂等重跑；
  不需要增量更新可执行 `repowiki clean <repo>` 删除全部状态（wiki 产出不受影响）。
- **测试**：81 个单测覆盖竞态、过期回收、校验规则正反例、增量映射、知识聚合（`pytest`）。

## 与 Qoder 原版的差异

- `metadata.json` 形状兼容但不输出加密 `raw_data`/`recovery_checkpoint`（内部状态在 `state/`）。
- ADR 类知识卡片（源自 Qoder 会话历史）不生成；机制卡片/模块文档完整支持。
- 仅简体中文（`zh/`）、仅 POSIX 路径。

## 已知边界

- `overview` 总览不参与增量更新：结构性重构后建议 `plan --replan` 全量重生成。
- 每个任务规格内嵌完整模板与文风规范（约 4-6k tokens）——换取任务自包含与并行安全；
  小上下文 agent 可将规格中的模板段落替换为对 `templates/` 目录的引用。
- 页面语言硬性为中文（校验器强制中文小节标题）；`file://` 引用解析、程序化领取依赖 `jq` 属常见但非必需。

## Non-Goals

LLM API 后端 · 内置 agent CLI 检测/执行器 · MCP 封装 · HTML 预览服务 · Windows · en 语言。
