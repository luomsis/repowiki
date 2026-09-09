# repowiki

**中文** | [English](README.en.md)

[![CI](https://github.com/luomsis/repowiki/actions/workflows/ci.yml/badge.svg)](https://github.com/luomsis/repowiki/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/repowiki-cli)](https://pypi.org/project/repowiki-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python ≥ 3.10](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)](#可靠性设计)

为任意仓库生成结构化 Wiki 的构建系统。

`repowiki` 是一个确定性的构建系统：负责任务规划、原子认领、产出校验、自动修复、元数据组装；
智能工作（读代码、写 wiki）由驱动它的 agent（Claude Code / Codex / OpenCode 等 agent CLI，或人）完成。
零 API Key、零网络调用、零 agent CLI 依赖——任何「能跑 shell + 读写文件」的执行者都能参与，包括并发。
Wiki 产出语言自动跟随目标仓库（中文仓库 → `zh/`，英文仓库 → `en/`；`plan --locale` 可显式指定）。

![repowiki 系统架构图](docs/assets/repowiki-architecture.png)

*交互版架构图：[docs/repowiki-architecture.html](docs/repowiki-architecture.html)（明暗主题 · 路径高亮 · 节点搜索，下载后在浏览器打开）*

**看效果**：repowiki 为自己生成的 wiki 已发布为在线样例 → **[直接打开](https://luomsis.github.io/repowiki/zh/wiki.html)**
（每次 push main 自动重建）。

## 为什么是 repowiki

给仓库生成 wiki 的现成方案主要有两条路：云端 AI wiki 服务（代码要上传、按量付费、产出是黑盒），
或者让一个 agent 直接通读仓库现写（大仓库上下文装不下、中断即前功尽弃、难以并行）。
repowiki 走第三条路：**读代码、写 wiki 的智能留给任意 agent，其余一切——任务规划、原子认领、
产出校验、自动修复、断点续跑——做成确定性构建系统。**

| | 云端 AI wiki 服务 | 让 agent 直接读仓库 | repowiki |
|---|---|---|---|
| 智能来源 | 内置 LLM（不可换） | 你的 agent（任选） | 你的 agent（任选） |
| 代码出域 | 是 | 否 | 否 |
| API Key / 网络 | 需要 | 视 agent 而定 | repowiki 本身零依赖 |
| 大仓库 | 受服务方配额限制 | 上下文装不下 | 任务切分，逐页生成 |
| 中断 / 崩溃 | — | 从头再来 | 状态落盘，断点续跑 |
| 并行加速 | — | 难协调 | 多 worker 原子认领，天然并行 |
| 产出质量 | 黑盒 | 靠 agent 自觉 | 模板强制 + 程序化校验 + 自动修复 |

一句话：**agent 负责聪明，repowiki 负责靠谱。**

## 特性

- **确定性编排**：plan / claim / check / 自动修复全是确定性代码——零 API Key、零网络调用、不绑定任何 agent CLI；
- **并发安全，断点续跑**：原子任务认领 + 心跳续期 + 过期自动回收，多个 agent / 进程 / 人同时参与同一仓库；每任务状态落盘，随时中断随时继续；
- **增量更新与 CI 门禁**：`update` 基于 git diff 只重写受影响页面；`stale --fail-if-stale` 拦截「代码改了、wiki 没跟」的 PR；`coverage` 统计 wiki 从未引用的文件；
- **单文件离线站点 + agent 索引**：`site` 产出约 5 MB 自包含 HTML（导航、搜索、mermaid、源码弹层，双击即看），同时导出 `llms.txt` / `llms-full.txt`（[llmstxt.org](https://llmstxt.org/) 约定），任何 agent / IDE 按索引直接读，无需 MCP；
- **强校验，自动修复**：模板强制 + 程序化校验；锚点 / 行号 / H1 / 路径分隔符自动修复，只有语义缺陷才判失败；
- **双语产出，跨平台**：语言自动跟随目标仓库（zh / en）；macOS / Linux / Windows 原生支持（无需 WSL），CI 三平台 × Python 3.10-3.13 矩阵回归；
- **知识卡片与页面原型**：机制卡片 / 模块文档，类别可整表自定义（`--categories`）；页面按主题选 module（结构型，默认）/ flow（流程型）两种模板。

## 目录

- [为什么是 repowiki](#为什么是-repowiki) · [特性](#特性)
- [安装](#安装) · [查看 Wiki](#查看-wiki单文件离线站点) · [命令一览](#命令一览)
- [可靠性设计](#可靠性设计) · [设计边界](#设计边界)
- [贡献](#贡献contributing) · [社区](#社区) · [文档](#文档) · [License](#license)

## 安装

### 1. CLI（必需，Python ≥ 3.10，macOS / Linux / Windows）

```bash
pip install repowiki-cli                # PyPI（运行时依赖仅 pyyaml）
# 或 pipx install repowiki-cli；开发安装：克隆仓库后 pip install -e .
repowiki --version                      # 验证
```

### 2. Agent Skill（可选，让 agent 自动触发本工作流）

skill 文件随 CLI 一起分发，一条命令安装：

```bash
repowiki skill install                  # 默认装入 ~/.agents/skills/repowiki/（各 agent 通用的全局 skills 目录）
repowiki skill install --agent claude   # 或装入指定客户端目录（claude / codex / zcode / cursor / opencode）
repowiki skill status                   # 查看已装版本、是否过期
```

也可把本仓库作为插件安装（`.claude-plugin/` 清单自动识别），或手动拷贝
`src/repowiki/skills/repowiki/` 到客户端 skills 目录。skill 只是指引（告诉 agent 按什么流程
调用 CLI），真正干活的是第 1 步装的 `repowiki` 命令。

### 3. 离线安装

运行时依赖只有 `pyyaml`：在有网机器上下载 `PyYAML` wheel 与 Release 页附带的
[`repowiki_cli-*.whl`](https://github.com/luomsis/repowiki/releases)，拷到目标机后
`pip install --no-index` 两个 wheel 即可；skill 已随 whl 打包，装好后同样执行
`repowiki skill install`（纯本地拷贝）。完整步骤见 [docs/zh/USAGE.md](docs/zh/USAGE.md)。

## 查看 Wiki（单文件离线站点）

上方在线样例即由 `repowiki site` 生成、push main 后自动重建。

![阅读视图：章节导航 + mermaid 渲染 + 源码引用](docs/assets/site-preview-reading.png)

![点击 file:// 源码引用，页内弹层查看带行号的源码片段](docs/assets/site-preview-snippet.png)

`repowiki site <repo> [--open]` 把整个 wiki 打包成**一个自包含的 HTML 文件**
（`<repo>/.repowiki/<locale>/wiki.html`，约 5 MB）：

- markdown + mermaid 全部渲染，引用的源码行区间直接内嵌，点击 `file://` 引用在页内
  弹层查看带行号高亮的源码——无需 IDE、无需网络，发给同事一个文件即可浏览整个 wiki；
- 侧边栏章节导航（可折叠）+ 当前页目录（scroll-spy 跟随高亮）、全文搜索（命中词高亮）、
  代码块一键复制、prev/next 翻页、阅读进度条、暗色/浅色主题（跟随系统 + 手动切换）；
- 完全离线：markdown/mermaid 渲染库（marked/mermaid，MIT）已内嵌进文件本身；
- 幂等可重跑：finalize、update 或手动改了页面之后随时重新执行 `repowiki site` 重建；
- 执行过 `repowiki clean` 也能重建（此时章节顺序退化为目录序，内容不受影响）。

页面按 **module（结构型，默认）/ flow（流程型）** 两种原型撰写，模板与文风规范由校验器
按语言强制；每节末尾「Section sources/章节来源」、每图后「Diagram sources/图表来源」，
引用格式 `[path:Lx-Ly](file://path#Lx-Ly)`，页间零链接（正因如此所有页面任务可完全并行）。
完整小节结构见 [docs/zh/USAGE.md](docs/zh/USAGE.md)。

## 命令一览

| 命令 | 作用 |
|---|---|
| `plan <repo>` | 扫描 + 生成任务清单（产出语言自动检测，`--locale` 可指定） |
| `next --claim` | 领取一个就绪任务，`--json` 含完整 instructions |
| `check --task ID` | 校验产出；锚点/行号/H1 自动修复 |
| `finalize` | 组装 metadata.json（两步：先创建 overview 任务） |
| `site` | 生成单文件离线站点 + llms.txt / llms-full.txt 索引 |
| `update` / `stale` | git diff 增量更新任务 / 只读过期报告（CI 门禁） |
| `skill install` / `status` | 安装 / 检查 agent skill |
| `status` / `clean` | 进度统计 / 清空任务状态 |

完整 15 条命令与全部参数：`repowiki <命令> --help` 或 [docs/zh/USAGE.md](docs/zh/USAGE.md)。
退出码：`0` 成功，`1` 校验失败或用法错误，`2` 状态冲突（任务被他人认领），`3` 进展性等待
（finalize 已创建 overview 任务，完成后再次运行即可）。

## 可靠性设计

- 原子认领（POSIX `fcntl` / Windows `msvcrt` 文件锁）+ 过期自动回收：崩溃 worker 的认领自动回队列，无需人工释放；
- 断点续跑：每任务状态落盘；状态文件损坏时保留现场明确报错，绝不静默清空任务清单；
- `watch` 不假活：过期认领不计入「执行中」，真停滞及时报告而非干等超时；
- finalize 后自动瘦身运行时产物，保留增量更新所需状态。

机制细节（过期窗口调参、`.stale-*` 留痕、心跳语义、瘦身清单）见 [docs/zh/USAGE.md](docs/zh/USAGE.md)。

## 设计边界

- **设计取舍**：`metadata.json` 只含可读字段（catalogs/items/source_files/snippets/relations），运行时状态留在 `state/`；ADR 类知识卡片不生成，机制卡片/模块文档完整支持；产出语言冻结为 zh / en；CLI 交互消息当前为中文（面向驱动它的 agent），不影响 wiki 产出语言。
- **已知边界**：任务规格内嵌完整模板与文风规范（约 4-6k tokens），换取自包含与并行安全，小上下文 agent 可将规格中的模板段落替换为对 `templates/` 目录的引用；产出语言 plan 时锁定，中途更换需 `plan --replan`；`update` 依赖目标仓库本地 git CLI（`git diff` / `git rev-parse`）。
- **Non-Goals**：LLM API 后端 · 内置 agent CLI 检测/执行器 · MCP 封装（agent 读取 wiki 的需求由 `llms.txt` 静态导出满足） · 常驻预览服务器（`site` 产物是纯静态单文件，双击即看） · zh/en 之外的产出语言。

## 贡献（Contributing）

欢迎 issue 与 PR！本地开发：

```bash
git clone https://github.com/luomsis/repowiki.git && cd repowiki
pip install -e '.[test]'
pytest
```

- 行为变更请先开 issue 或去 Discussions 对齐方向，再动手。

## 社区

- 问题、想法，或想晒一晒你生成的 wiki → [GitHub Discussions](https://github.com/luomsis/repowiki/discussions)
- bug 与功能请求 → [Issues](https://github.com/luomsis/repowiki/issues)

## 文档

全部文档集中于 `docs/`（`zh/` 与 `en/` 镜像目录，同名文件一一对应）：

- [使用详解](docs/zh/USAGE.md)（[English](docs/en/USAGE.md)）——完整命令参考、Worker 循环契约、并发配方、可靠性机制细节
- [版本日志](CHANGELOG.md)（[English](CHANGELOG.en.md)，位于仓库根部）
- [领域词汇表](docs/zh/CONTEXT.md)（产出物 / 编排 / 执行三组术语与 Avoid 对照）
- [决策记录](docs/zh/DECISIONS.md)（规格空白处的 15 条最小合理决策）
- 架构决策记录（ADR）：[Windows 原生支持的双锁后端](docs/zh/adr/0001-windows-native-support.md) ·
  [单文件离线站点](docs/zh/adr/0002-single-file-offline-site.md)
- Agent Skill 指引：[中文](src/repowiki/skills/repowiki/SKILL.md) · [English](src/repowiki/skills/repowiki/SKILL.en.md)

## License

[MIT](LICENSE) © luomsis
