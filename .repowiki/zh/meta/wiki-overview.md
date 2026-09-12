# repowiki Wiki 总览

## 更新摘要

**变更内容**
- 校验器升级：行号校验分层——仅终点越界自动钳制到文件末尾，起点越界、区间倒置、引用区间全为空行判 error 打回重写；每个 `##` 小节（目录与更新摘要除外）必须非空且携带「章节来源」标记（标记词来自 i18n.STRINGS 新增的 `section_sources` key）；`check_page` 新增 `known_paths` 参数，mermaid 图节点标签中形如文件名的 token 与仓库文件清单核对，不存在仅告警。
- 覆盖率报告升级：未引用文件确定性分组（vendor / locale_mirror / other）并新增 `effective_coverage` 有效覆盖率（分母剔除 vendor 与其他语言镜像）。
- 模板与 skill 文档同步：zh/en 的 STYLE.md、page_task.md 与 SKILL.md / SKILL.en.md 更新行号规则表述；tests/conftest.py、test_validate.py、test_coverage.py 夹具与用例扩充（全量 202 项测试通过）。本轮受影响页面均已附「更新摘要」小节。

**章节来源**
- [src/repowiki/validate.py:1-9](file://src/repowiki/validate.py#L1-L9)
- [src/repowiki/dispatch.py:354-357](file://src/repowiki/dispatch.py#L354-L357)
- [src/repowiki/coverage.py:63-80](file://src/repowiki/coverage.py#L63-L80)

## 仓库定位与核心价值

repowiki 是一个为任意代码仓库生成结构化 Wiki 的构建系统：产出由 mermaid 图与 `file://` 源码行号引用构成，输出语言自动跟随目标仓库（中文仓库生成 `zh/`，英文仓库生成 `en/`，也可用 `plan --locale` 显式指定）。它刻意把系统拆成两半——CLI 承担全部确定性工作（任务规划、原子认领、产出校验、自动修复、元数据组装），而读代码、写页面的智能工作交给驱动它的任意 agent（Claude Code、Codex、OpenCode 等），两者通过任务队列协作。

这种分工带来三个直接后果。其一，repowiki 自身零 API Key、零网络调用、零 agent CLI 依赖，任何「能跑 shell + 读写文件」的执行者都能参与；其二，任务状态落盘，中断或崩溃后可断点续跑，多 worker 通过原子认领天然并行，大仓库被切分成逐页任务而不受单一上下文限制；其三，产出质量不靠 agent 自觉，而是由模板强制小节骨架、程序化校验与确定性自动修复兜底。

repowiki 的产出面向两类消费者：人类读者获得单文件离线站点（`wiki.html`，内联全部源码引用与渲染脚本）；agent 与 IDE 获得遵循 llmstxt.org 约定的 `llms.txt` / `llms-full.txt` 索引。本仓库自身也以「wiki-as-code」方式维护这份 Wiki——产出入库、运行态状态忽略，每次 push main 自动重建在线样例。

**章节来源**
- [README.md:11-16](file://README.md#L11-L16)
- [README.md:27-30](file://README.md#L27-L30)
- [docs/zh/CONTEXT.md:1-40](file://docs/zh/CONTEXT.md#L1-L40)

## 章节导航

- 项目概述 —— repowiki 的定位与核心概念、从 plan 到 site 的端到端构建流程，以及关键设计决策（ADR）与竞品差异。
  - 项目定位与核心概念：任务/认领/校验等词汇表与 wiki-as-code 工作流。
  - 端到端构建流程：plan → 领取 → 撰写 → check → finalize → site 的全链路与状态变化。
  - 设计决策与 ADR：Windows 原生支持、单文件离线站点两篇 ADR 与竞争分析结论。
- 快速开始 —— 安装 CLI（PyPI / 离线 whl / 源码）并跑通第一个 wiki 生成流程的最短路径，含 agent skill 安装。
- 任务编排与状态管理 —— 编排侧五大机制的实现：仓库扫描与任务规划、任务领取与并发调度、校验与自动修复、增量更新与覆盖率。
  - 仓库扫描与任务规划：scanner / i18n / plan / catalog 四个模块如何产出任务清单。
  - 任务领取与并发调度：next / check / release / status 原语、认领状态机与 stale 回收。
  - 校验与自动修复：validate 的校验维度（含行号分层校验与逐小节「章节来源」规则）、哪些缺陷自动修复、哪些回给 agent。
  - 增量更新与覆盖率：基于 git diff 的 update、stale 过期检测与 coverage 覆盖率报告（含未引用文件分组与有效覆盖率）。
- 内容产出与模板 —— 「写页面」的一侧：任务规格模板与 STYLE 规范、产出路径规则、知识卡片系统、finalize 元数据汇总。
  - 页面模板与撰写规范：module 与 flow 两套模板的差异与硬性行文规范。
  - 产出写入与路径规则：确定性路径推导与双格式输出缝。
  - 知识卡片系统：卡片任务集、类别定制与聚合。
  - 总览页与元数据汇总：overview 任务生命周期与 repowiki-metadata.json 的构建。
- 站点与分发 —— wiki 的两种消费形态：单文件离线站点（内联 mermaid/marked）与 llms.txt 索引，以及 agent skill 的跨客户端安装。
- 测试与工程化 —— pytest 测试体系与功能面的映射，CI、PyPI Trusted Publisher 发布流水线与 wiki 自举工作流。

**章节来源**
- [本节为概念性说明，不直接分析具体文件，故无"章节来源"]

## 如何使用本 Wiki

新手路径（了解并跑通）：先读「项目概述」的「项目定位与核心概念」与「端到端构建流程」建立整体模型，再按「快速开始」安装 CLI 并对一个玩具仓库跑通 plan → 撰写 → check → finalize → site 全流程；遇到并发或中断问题时回到「任务编排与状态管理」查认领与回收语义。

贡献者路径（参与开发）：从「测试与工程化」的「测试体系」入手了解质量门禁与用例布局，再深入「任务编排与状态管理」的「校验与自动修复」与「内容产出与模板」各页，对应修改 `src/repowiki/` 下模块；改动涉及发布时读「CI 与发布流水线」确认发版纪律（版本号同步、双语 CHANGELOG、whl 附 Release、pytest 全绿门禁）。维护已有 wiki 时，「增量更新与覆盖率」提供了 update / stale / coverage 三个保活工具的用法。

**章节来源**
- [本节为概念性说明，不直接分析具体文件，故无"章节来源"]
