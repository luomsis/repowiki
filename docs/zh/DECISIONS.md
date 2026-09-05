# DECISIONS.md — 实现过程中的规格空白处的最小合理决策记录

**中文** | [English](../en/DECISIONS.md)

（计划 Agent Execution Rule #6：遇规格空白不得臆造，记录于此。）

1. **模块拆分**：计划只列了 `tasks.py`，实现时把 plan 命令编排独立为 `plan.py`、
   next/check/release/status 编排独立为 `dispatch.py`——避免 tasks.py（规格生成）与命令层耦合。
2. **busy 信号**：`next` 返回体新增 `busy` 字段（进行中任务数）。规格只说「无任务退出」，
   会造成 worker 在他人执行中时提前退出、后续任务无人接手（T5 竞态单测暴露）。
   worker 契约相应改为「空且 busy>0 → 等待重试」。
3. **认领过期判定**：以 claim 目录自身 mtime 为准，而非目录内 ts 文件——ts 在 mkdir 之后写入，
   该窗口内新鲜认领会因 ts 缺失被误判为无限旧而遭抢占（并发单测捕获的真实竞态 bug）。
4. **模板内嵌标题预渲染**：page 任务规格内嵌的页面模板中 `{{TITLE}}` 先渲染为真实标题，
   避免 agent 忘记替换（T9 冒烟暴露）。
5. **锚点算法**：GitHub 规则是「删标点、空白转 -」，而非「标点也转 -」——
   `附录：一键` 的正确锚点是 `附录一键` 不是 `附录-一键`（单测暴露）。
6. **catalog 任务幂等**：`plan` 遇到已存在且合法的 catalog.json 时不再创建 catalog 任务
   （直接展开页面任务）；`--replan` 清空重来。这是评审阶段补充的「目录评审回路」入口：
   人/agent 可直接编辑 state/catalog.json 后重新 plan。
7. **overview 两步 finalize**：首次 finalize 创建阶段3 overview 任务并退出码 3（进展性等待，非错误）；
   agent 写完 overview 并 check done 后再次 finalize 才写 metadata.json。
8. **章节数建议**：catalog 任务规格中根章节数改为「大仓库 12~18，小仓库 4~8，宁精勿滥」
   （T9 对 10 文件仓库冒烟时发现原表述诱导过度生成）。
9. **attempt 计数**：每次 claim attempts+1（含首次）；ready 排序 attempts 升序——
   失败任务不插队，新任务优先，避免坏任务拖死 worker。
10. **state 清理策略**：finalize 成功后自动清除运行时产物（claims/、tasks/），
    保留 index.json/catalog.json/knowledge.json——update 的增量映射依赖 catalog.json 的
    dependent_files 与树结构（metadata 无 kind 字段无法重建页面路径），index.json 支撑
    plan 幂等与 status。另提供 `clean` 命令整体删除 state/（不删 wiki 本体）。
11. **生命周期守卫（P0/P1 评审修复）**：`touch` 心跳命令+check 顺带续期（防执行期被抢双写）；
    done 为终态、重复 check 只读（spec 已清理后翻失败会产生无规格可执行任务）；failed 超过
    REPOWIKI_MAX_ATTEMPTS 进 exhausted 需 `release --force` 重置（防毒任务空转 worker）；
    check 必须显式 `--task`/`--all` 且校验认领归属（防跨 worker 误翻）；index.json 用 flock
    串行化读改写（mtime 复查有 TOCTOU 窗口，6×12 压测丢 3 次更新）；finalize 校验页面存在
    （--max-pages 试跑不再产生幽灵条目）且首次运行退出码 3 表达进展；replan 有 in_progress
    时需 --force。
12. **过期认领自动回收**：实战（40 页并发生成，一 worker 退出后遗留 15 个认领冻结队列 50 分钟）
    暴露 `_try_mkdir_claim` 的抢占路径经 CLI 不可达——`ready_tasks` 完全排除 in_progress，
    死 worker 的认领只能人工 `release --force`。修复：`ready_tasks` 纳入「in_progress 且
    认领过期」的任务，`next --claim` 走既有抢占路径自动回收（`.stale-*` 留痕、attempts+1，
    毒任务上限照常生效）；stale 判定统一为 claim 目录 mtime 单一来源（原 stats() 基于
    index.heartbeat_at 的第二套判定废弃，避免 sweep 与 busy 统计打架）；watch 的 in_flight
    同步排除过期认领（否则 worker 全死后停滞分支永远不可达，只能干等超时）。
    默认 stale 窗口 45→15 分钟：冻结上限与误抢风险（worker 遵守 touch 纪律则无误抢）的平衡。
13. **不做 pid 存活检测**：repowiki 是短命 CLI 进程，认领时记录的 pid 在命令退出后立即失效，
    不能作为认领者存活信号；存活信号就是自愿的 `touch` 心跳，过期窗口是死进程的唯一回收延迟。
    `next` 亦不加 `--task`：队列保持纯 FIFO 拉取，按 ID 操作由 `check --task`/`release --task`
    承担——按 ID 认领会诱导主会话给 worker 指定任务清单，正是实战中认领混战的根源。
14. **占位符扫描只针对非代码文本**：为 repowiki 自身生成 wiki 时，有一页的主题就是占位符机制，
    正文代码里出现字面 `{{TITLE}}` 被校验器判「未替换占位符」，任务无解（H1 与检查规则互斥）。
    修复分两层：catalog 校验拒绝 title 含占位符形态（源头——title 会写进页面 H1 与输出路径）；
    产物校验的占位符扫描改为剔除 fenced 代码块与行内代码后进行（散文残留仍失败）。
    「在代码里展示占位符字面量」是合法内容，「在散文里残留占位符」才是缺陷。
