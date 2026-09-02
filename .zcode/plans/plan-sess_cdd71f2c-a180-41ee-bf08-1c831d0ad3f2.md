# 主会话持续监控：repowiki watch 命令 + 快速演示

背景：e2e 仓库当前无后台进程在跑（此前 worker 均已结束）；监控是之前 e2e 的临时做法，现固化为工具功能。演示范围已确认为小目录快速验证。

## 1. 新增 `repowiki watch <repo> [--interval 10] [--timeout 3600] [--json]`

阻塞式监控命令——主会话/主 agent 派发后台 worker 后运行它，直到终态自动退出：

- **轮询**：每 interval 秒读取 `TaskStore.stats()`；仅当摘要变化时打印一行进度（时间戳 · done/total · 阶段 · 进行中任务[worker] · failed · exhausted），避免刷屏
- **终止条件与退出码**：
  - 全部 done → **exit 0**（打印最终汇总）
  - 停滞：有未完成任务但无 in_progress 且无可领取（ready 为空，典型= exhausted 毒任务）→ **exit 1**，输出诊断提示
  - 超过 --timeout → **exit 1**
- **--json**：退出时单次输出 `{"reason": "completed|stalled|timeout", "stats": {...}}`（适合主 agent 程序化判断）
- 实现：dispatch.py 新 `run_watch`（纯轮询复用现有 stats/ready_tasks，约 60 行）+ cli.py 注册；无任务时按 UsageError 处理
- 测试（4 个）：完成→0（辅助线程翻转任务状态）、停滞→1（exhausted 场景）、超时→1、空任务→1/报错；interval 用 0.05s 保证测试快速

## 2. 契约文档同步

- **SKILL.md**：主 agent 流程加一步「派发 subagent 后运行 `repowiki watch <repo> --json`（可 run_in_background），退出 0 → finalize；退出 1 → `status` 查看 exhausted/stale 并干预」；监控小节写明退出码语义
- **README.md**：命令表加 watch；「并发配方」小节把监控写入主 agent 职责
- 同步 `~/.agents/skills/repowiki/SKILL.md` 全局副本

## 3. 小目录快速演示（watch 的实测验证）

在 /tmp/repowiki-e2e/metric-threshold（现有小目录：catalog + c01 项目概述索引页 + c0101 核心概念 + c02 快速开始，其中 2 页缺失）：

1. `plan --replan --force` 重置 → 写入小目录 catalog（c0101 已有可用页，随任务重做）→ check 展开 3 个页面任务
2. 派 **1 个后台 worker**（subagent）跑 worker 循环写 3 页
3. 主会话运行 `repowiki watch . --interval 15`（后台 Bash）持续监控——验证进度行输出与退出 0
4. watch 退出后：finalize（exit 3）→ 我写 overview → check → finalize（exit 0）
5. 向用户报告监控时间线（各进度快照 + 最终状态）

## 4. 收尾

- 全套 pytest（91+新增 ≈95）
- 提交（watch 功能一笔）+ 全局技能同步

## 不做

rich Live 动态进度条（保持纯文本行、agent 友好）；watch 的 --stream JSON（单次最终快照够用）；对 watch 做分布式扩展。
