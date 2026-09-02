# DECISIONS.md — 实现过程中的规格空白处的最小合理决策记录

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
7. **overview 两步 finalize**：首次 finalize 创建阶段3 overview 任务并退出码 1；
   agent 写完 overview 并 check done 后再次 finalize 才写 metadata.json。
8. **章节数建议**：catalog 任务规格中根章节数改为「大仓库 12~18，小仓库 4~8，宁精勿滥」
   （T9 对 10 文件仓库冒烟时发现原表述诱导过度生成）。
9. **attempt 计数**：每次 claim attempts+1（含首次）；ready 排序 attempts 升序——
   失败任务不插队，新任务优先，避免坏任务拖死 worker。
10. **state 清理策略**：finalize 成功后自动清除运行时产物（claims/、tasks/），
    保留 index.json/catalog.json/knowledge.json——update 的增量映射依赖 catalog.json 的
    dependent_files 与树结构（metadata 无 kind 字段无法重建页面路径），index.json 支撑
    plan 幂等与 status。另提供 `clean` 命令整体删除 state/（不删 wiki 本体）。
