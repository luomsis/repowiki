# repowiki Wiki 总览

<cite>
**本文引用的文件**
- [README.md](file://README.md)
- [src/repowiki/cli.py](file://src/repowiki/cli.py)
- [docs/zh/USAGE.md](file://docs/zh/USAGE.md)
</cite>

## 章节导航

- 项目概述 —— repowiki 的定位（确定性编排 + agent 执行）与端到端构建生命周期
  - 项目定位与核心概念：catalog / 任务规格 / claim / check / finalize 五概念心智模型
  - 端到端构建流程：plan → catalog → pages → finalize → site 五步时序与阶段门控
- 快速开始 —— 安装、生成、查看一条龙的最短路径
- CLI 命令参考 —— 15 个子命令、参数与退出码约定（api 原型）
- 架构与源码分层 —— 四层结构与依赖方向约定
  - 源码分层与依赖方向：各层职责边界与纵向切片（layer 原型）
  - 任务状态与目录数据模型：任务/节点/路径三实体与状态机（data 原型）
- 任务编排与校验 —— 扫描规划、并发调度、校验修复、增量门禁四个机制
- 内容产出与模板 —— 六种页面原型、知识卡片与站点/llms 产出
- 测试与工程化 —— 无 LLM 全链路回归、CI 矩阵与发布流水线

## 如何使用本 Wiki

第一次接触 repowiki：先读「项目概述」建立"确定性编排 + agent 执行"的心智模型，再按「快速开始」跑通一次生成。想改造或扩展它：「架构与源码分层」给出改动归层的坐标系，「页面原型与模板体系」是扩展页面骨架的入口。日常维护与 CI 集成看「任务编排与校验」与「CI 与发布流水线」。每页末尾的 file:// 引用可在离线站点里点开查看带行号的源码片段。

## 术语表

- 确定性编排（deterministic orchestration）：CLI 只做可计算的规划/校验/状态管理，不做任何语义判断的工作方式。
- 驱动 agent（driving agent）：消费任务规格、读写代码仓库、产出 wiki 内容的外部编码 agent（如 Claude Code / Codex）。
- catalog（章节树）：agent 规划产出、CLI 校验持有的章节结构，`state/catalog.json` 是 wiki 结构的唯一事实来源。
- archetype（页面原型）：页面的骨架类型，共六种——module/flow/layer/data/api/event。
- 任务规格（spec）：`state/tasks/<id>.md`，内嵌完整模板与规范的自包含任务说明。
- claim（认领）：worker 对任务的原子占用（mkdir 目录），互斥的并发凭证。
- 心跳（heartbeat）：touch 命令刷新认领目录 mtime，是 worker 存活的唯一信号。
- 过期回收（stale reclaim）：认领目录超过窗口无心跳后由下一个 next 自动重新入队。
- check：校验 agent 产出的命令，自动修复确定性缺陷、打回结构性缺陷。
- 自动修复（auto-fix）：对锚点/H1/路径分隔符/行号终点越界等可计算缺陷的就地修正。
- archetype 小节表：i18n.STRINGS 中每种原型的必备小节清单，校验器据此打回缺小节的页面。
- finalize（两步制）：第一次创建总览任务（exit 3），第二次聚合元数据（exit 0）。
- 增量更新（incremental update）：基于 git diff 只重写受影响页面的 update 机制。
- 过期门禁（staleness gate）：stale --fail-if-stale 在 PR 里拦截"代码改了、wiki 没跟"。
- llms.txt：面向 agent 的 wiki 索引约定（llmstxt.org），与单文件离线站点构成两种分发形态。
- wiki-as-code：把 `.repowiki/` 产出随仓库提交、由 CI 保鲜的使用模式。
