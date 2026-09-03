# Changelog

## 0.1.0 — 2026-09-03

首个公开版本。

- 确定性任务编排器：`plan` / `next` / `check` / `touch` / `watch` / `release` / `finalize` / `update` / `knowledge` / `status` / `clean`。
- catalog → page → overview 三阶段任务流，原子认领、过期回收、断点续跑、finalize 后自动瘦身。
- 产出语言自动跟随目标仓库（zh/en：README 权重最高的确定性检测，`plan --locale` 可显式指定，持久化于 `state/locale`）；校验器、模板、知识卡片按语言成套提供，表驱动可扩展。
- 校验器 + 确定性自动修复（锚点、行号区间、H1、路径分隔符）。
- 基于 git diff 的增量更新（页面重写附「更新摘要 / Update Summary」小节）。
- 知识卡片任务集（机制卡片 + 模块文档）。
- 以 Agent Skill 形式分发（`skills/repowiki/SKILL.md`），CLI 以 `pip install git+…` 安装。

### 变更

- 去除第三方品牌引用，定位为通用的仓库 Wiki 生成器；扫描器不再特殊处理旧版第三方输出目录。

### 修复

- 损坏的 `state/index.json` 不再被静默当作空清单（此前一次事务写回会丢掉整份任务清单）；现在保留现场、明确报错，`plan --replan --force` 为显式恢复路径。
- 损坏的 `state/catalog.json` 在 finalize / update / overview 校验路径给出友好错误，不再抛裸 traceback。
- 不存在的任务 id（touch / release）给出友好错误并列出排查指引。
- 非 POSIX 平台（Windows）安装后首次运行改为明确的平台说明，而非 `fcntl` 裸崩溃。
