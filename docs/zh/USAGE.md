# repowiki 使用详解

本文是 README 的配套详解，收纳完整命令参考、Worker 循环契约、并发配方与可靠性机制细节。
快速上手请先看 [README](../../README.md)。English: [USAGE.en](../en/USAGE.md)。

## 离线安装（完整步骤）

repowiki 的运行时依赖**只有 `pyyaml>=6`**，离线安装只需三样东西：仓库源码（或 Release 页
wheel）、pyyaml 的 wheel、目标机上的 Python ≥ 3.10。

**在有网的机器上准备物料**：

```bash
pip download PyYAML==6.* -d wheels/        # 下载 pyyaml wheel（按目标机平台/Python 版本：macOS/Linux 各架构、Windows 的 wheel 互不通用）
pip wheel --no-deps -w wheels/ .           # 或直接用 Release 页附带的 repowiki_cli-*.whl
```

把仓库目录（或 `repowiki_cli-*.whl`）与 `wheels/` 一起拷到目标机，然后：

```bash
pip install --no-index wheels/PyYAML-*.whl        # 先装唯一依赖
pip install --no-index repowiki_cli-*.whl         # 再装 repowiki 本体（或 -e 源码目录）
repowiki --version                                # 验证
```

用 pipx 的话：`pipx install --no-index repowiki_cli-*.whl`。要跑测试套再额外离线装 `pytest`
（`[test]` extra）。

Agent Skill 同样离线可用——skill 已随 whl 打包，装好 CLI 后执行 `repowiki skill install`
即可（纯本地拷贝，无任何在线操作）；skill 只调用本机已装好的 `repowiki` 命令。注意 repowiki
自身零网络，但 `update` 依赖目标仓库本地的 git CLI（`git diff` / `git rev-parse`），git
预装的机器无需额外配置。

## 快速开始

```bash
repowiki plan ~/code/myrepo          # 扫描 → 生成任务清单（代码文件 <10 会拒绝）
repowiki next ~/code/myrepo --claim --json   # 领取任务，按 instructions 执行
# ... 按任务规格撰写产出，然后：
repowiki check ~/code/myrepo --task c01      # 校验+自动修复+状态流转
repowiki finalize ~/code/myrepo      # 组装 metadata.json（两步：先创建 overview 任务）
repowiki site ~/code/myrepo          # 生成单文件离线查看站点（--open 自动打开浏览器）
```

输出结构（`<locale>` 由 plan 自动检测或 `--locale` 指定，当前支持 `zh` / `en`）：

```
myrepo/.repowiki/
├── zh/                     # 或 en/ —— 语言跟随目标仓库
│   ├── content/            # 章节树：目录名=章节名，索引页+子页，固定模板
│   │   ├── 快速开始.md      # 顶级独立页
│   │   └── 项目概述/项目概述.md, 核心概念.md, ...
│   ├── meta/repowiki-metadata.json   # catalogs/items/source_files/snippets/relations
│   ├── wiki.html           # 单文件离线查看站点（repowiki site 生成，双击即开）
│   └── llms.txt / llms-full.txt      # agent 消费索引：章节链接目录 + 全文合并（site 同时导出）
├── knowledge/zh/           # 知识卡片：_index.yaml + 模块文档 + 机制卡片
└── state/                  # 任务清单/规格/认领/locale（内部状态，可随时删除重规划）
```

## Worker 循环契约

任何执行者（subagent / 进程 / 人）按此循环参与，多个循环可同时运行：

```
loop:
  t = repowiki next <repo> --claim --json
  tasks 为空且 busy>0  → 等待重试（他人执行中）
  tasks 为空且 busy=0  → 退出
  按 t.tasks[0].instructions 执行（只写指定的 output 文件）
  执行期定期 repowiki touch <repo> --task <id>   # 心跳续期，防被过期回收
  repowiki check <repo> --task <id> --json
    ok=false → 按 errors 修复后重查；放弃则 repowiki release <repo> --task <id> --force
```

一次只持有一个认领：当前任务 check 通过（或放弃）后才回到 `next`（每次 next 只发放一个任务）——
worker 中途退出时手中不留孤儿认领；即便异常退出，过期认领也会自动回队列（见下文可靠性细节）。

## 并发配方

**Subagent 型（Claude Code / OpenCode 等）**：主 agent 先串行完成 plan + catalog，
然后 spawn N 个 subagent 各自跑 worker 循环（N=3~6 即可，页面任务相互独立）。
agent 视角的完整编排指引见 [SKILL.md](../../src/repowiki/skills/repowiki/SKILL.md)。

**无人值守（任何 headless agent CLI，由你决定用哪个）**：

```bash
#!/bin/bash
# worker.sh —— 把 claude 换成 codex exec / opencode run，工具不感知、不限制用哪个 agent
while :; do
  TASK=$(repowiki next . --claim --json)
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

## 命令一览（完整）

| 命令 | 作用 |
|---|---|
| `plan <repo> [--replan [--force]] [--max-pages N] [--knowledge] [--locale auto\|zh\|en]` | 扫描+生成任务清单；产出语言自动检测（README 权重最高）或显式指定，持久化于 `state/locale`；已有合法 catalog.json 则直接展开页面任务；有任务执行中时 replan 需 --force |
| `next [--claim] [--json]` | 领取就绪任务，每次只发放一个（阶段门控：attempts 少者优先）；worker 死亡后过期的认领会自动回队列，无需人工释放；`--json` 含完整 instructions |
| `touch --task ID` | 执行期心跳：刷新认领，防长任务被过期回收 |
| `watch [--interval S] [--timeout S]` | 阻塞监控直到全部完成（exit 0）或停滞/超时（exit 1）；过期认领不算执行中，真停滞可被及时报告 |
| `check --task ID \| --all` | 校验产出；锚点/行号/H1 自动修复；catalog/knowledge-plan 通过后自动展开后续任务；done 为终态（只读报告）；他人认领的任务需 --force |
| `release --task ID [--force]` | 释放认领（崩溃恢复） |
| `finalize` | 组装 metadata.json；要求全部任务 done |
| `site [--open]` | 把完成的 wiki 渲染成单文件离线 HTML（`<locale>/wiki.html`：导航+搜索+mermaid+源码弹层，知识模块文档与卡片纳入「知识库」章），同时导出 `llms.txt` / `llms-full.txt` agent 索引；要求先 finalize；`--open` 生成后用默认浏览器打开 |
| `update [--since <sha>] [--dirty]` | git diff → 受影响页面（含祖先链）与总览页 → 增量重写任务（附「更新摘要」）；同时联动知识库：`source_files` 命中变更的卡片与 scope 命中的模块各建刷新任务；默认仅识别**已提交**变更（since..HEAD），`--dirty` 纳入工作区未提交与未跟踪变更 |
| `stale [--since <ref>] [--dirty] [--fail-if-stale]` | 只读过期报告：复用 `update` 的 diff→受影响页面映射，报告哪些页面/卡片/模块会过期——不创建任务、不写 state；`--fail-if-stale` 供 CI 门禁（命中则 exit 1） |
| `coverage` | 只读覆盖率报告：统计 wiki 页面/总览/知识卡片从未引用的仓库文件与逐页引用密度（确定性计算，JSON 含全量清单） |
| `knowledge [--categories <file>]` | 追加知识卡片任务集（机制卡片 + 模块文档）；`--categories` 用 YAML/JSON 文件整表替换内置六类（持久化于 state）；finalize 时聚合导出 `_index.yaml` / `_module.yaml` |
| `skill install [--agent NAME] [--target DIR]` | 把随包分发的 agent skill 安装到全局 skills 目录：默认 `~/.agents/skills/repowiki/`，`--agent` 指定 `claude` / `codex` / `zcode` / `cursor` / `opencode`（可重复），`--target` 完全自定义；写入版本戳，幂等可重复执行 |
| `skill status [--agent NAME] [--target DIR]` | 报告各处已装 skill 版本与本包版本的差异（未安装 / 手拷无版本戳 / 过期 / 已是最新） |
| `status` | 进度 / 失败列表 / 过期认领 |
| `clean` | 删除整个 `state/`（wiki 产出保留；失去 update/续跑/幂等 plan） |

退出码：`0` 成功，`1` 校验失败或用法错误，`2` 状态冲突（任务被他人认领），`3` 进展性等待
（finalize 已创建 overview 任务，完成后再次运行即可）。

## CI 集成（wiki 门禁 + Pages 发布）

[.github/workflows/wiki.yml](../../.github/workflows/wiki.yml) 提供两个独立 job（wiki-as-code 模式：
仓库跟踪 `.repowiki/` 的内容、元数据与知识库；`state/claims`、`state/tasks` 与可重建的
`wiki.html` 可忽略）：

- **PR wiki 过期门禁**：`repowiki stale . --since origin/main --fail-if-stale` —— 代码改了、
  wiki 过期则自动评论受影响页面并拦截合并（确定性检查，CI 内不跑任何 agent）；
- **GitHub Pages 发布**：push main 后自动 `repowiki site .` 重建并发布，README 挂的在线样例
  即由此产出。

在你的仓库启用：拷贝该 workflow 文件，提交 `.repowiki/`（finalize 之后），并在仓库设置里把
Pages 来源设为 GitHub Actions。

## 页面模板：module 与 flow

页面模板（校验器按语言强制）按原型分两种：**module（默认，结构型）** H1 → `<cite>` 引用块 →
目录 → 简介 → 项目结构（mermaid graph TB）→ 核心组件 → 架构总览（sequenceDiagram）→ 详细组件
分析 → 依赖关系分析（graph LR）→ 性能与一致性考量 → 故障排查指南 → 结论；**flow（流程型）**
简介 → 流程总览（sequenceDiagram）→ 关键步骤 → 参与组件 → 数据与状态变化（graph LR）→ 故障
排查指南 → 结论。规划时在 catalog 节点上用可选 `archetype` 字段选择；每节末尾「Section
sources/章节来源」、每图后「Diagram sources/图表来源」，链接格式
`[path:Lx-Ly](file://path#Lx-Ly)`；页间零链接（正因如此所有页面任务可完全并行）。

## 可靠性设计细节

- **并发安全**：原子 `mkdir` 认领 + 目录 mtime 过期判定（默认 15 分钟，
  `REPOWIKI_STALE_SECONDS` 可调）。
- **队列自愈**：崩溃/被杀 worker 的过期认领由 `next` 自动回收重新入队（改名 `.stale-*` 留痕、
  attempts+1，毒任务上限照常生效），无需人工 `release --force`；活认领靠 `touch` 心跳续期防误抢
  （repowiki 是短命 CLI 进程，记录的 pid 无存活意义，心跳是唯一存活信号）。
- **watch 不假活**：过期认领不计入「执行中」，worker 全部死亡时停滞可被及时报告而非干等超时。
- **确定性优先**：锚点、行号区间、H1、路径分隔符由程序自动修复；
  只有语义缺陷（缺章节、引用不存在文件、mermaid 不闭合）才判失败。
- **断点续跑**：每任务状态落盘（`state/index.json`），随时中断随时继续；产出语言持久化于 `state/locale`。
- **损坏防护**：`state/index.json` 或 `catalog.json` 损坏时保留现场并明确报错（绝不静默清空任务清单），`plan --replan --force` 为显式恢复路径。
- **自动瘦身**：finalize 成功后自动清除运行时产物（`state/claims/`、`state/tasks/`），
  保留 `index.json`/`catalog.json`/`knowledge.json` 供增量更新与幂等重跑；
  不需要增量更新可执行 `repowiki clean <repo>` 删除全部状态（wiki 产出不受影响）。
- **测试**：单测覆盖竞态、孤儿认领自动回收、校验规则正反例（含 flow 原型）、增量映射、过期门禁、
  覆盖率统计、自定义知识类别、知识聚合、双语产出（zh/en）、单文件站点与 llms 索引生成、
  损坏状态文件与非法输入的友好报错（`pytest`；CI 矩阵覆盖 ubuntu/macos/windows × Python 3.10-3.13）。
