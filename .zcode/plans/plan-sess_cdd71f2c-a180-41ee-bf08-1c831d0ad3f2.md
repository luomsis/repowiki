# 完成任务的清理设计

## 方案

**1. finalize 成功后自动清除运行时产物**（`state.py` 新增 `cleanup_runtime()`，`metadata.py` 在 metadata 写盘成功后调用）：
- 删除 `state/claims/` 整个目录（含 `.stale-*`/`.released-*` 僵尸目录）
- 删除 `state/tasks/` 整个目录（所有任务规格 .md）
- 保留 `index.json`、`catalog.json`、`knowledge.json`
- 注意：finalize 第一次调用（创建 overview 任务、返回 1）**不**清理；只在 metadata 真正写盘的成功路径清理。`update` 之后再 finalize 会再次清理，行为一致

**2. 新增 `repowiki clean <repo>` 命令**：删除整个 `state/`（面向不需要增量更新的用户）。删除前打印将失去的能力（update/断点续跑/幂等 plan）；不支持删 wiki 本体（破坏性操作留给用户手动 rm）
- cli.py 注册子命令；实现放新函数（约 20 行，放 state.py 或独立小函数）
- 退出码 0；state 不存在时提示并返回 0（幂等）

**3. 文档同步**：README（命令一览表加 clean、可靠性设计小节说明 finalize 自动清理）、SKILL.md（流程说明加一句）、DECISIONS.md 记录该设计决策及理由

**4. 测试**：
- finalize 成功后 tasks/ 与 claims/ 消失、index/catalog/knowledge 仍在；再跑 `update`（有 git 夹具）仍能创建增量任务（specs 目录自动重建）
- `clean` 后 state/ 消失、`status` 报告 0 任务、`clean` 幂等
- finalize 首次调用（创建 overview）不触发清理

## 不做
- 不默认删除整个 state（会坏 update）；不把 kind 等字段补进 metadata 来摆脱 catalog.json 依赖（过度设计）；不做删除 wiki 的破坏性命令

## 验证
pytest 全绿 + 冒烟：e2e 仓库重跑 finalize 观察 state 瘦身，`clean` 后目录消失
