# Changelog

## 0.2.0 — 2026-09-04

### 变更

- **移除 `next --batch`（破坏性）**：worker 契约本就禁止一次持有多个认领，该参数是无消费者的
  投机接口。现在 `next` 每次只发放一个任务（`ready_tasks(limit=1)`），README / SKILL.md /
  测试同步改为「每次 next 只发放一个任务」。旧脚本里的 `--batch N` 直接删掉即可。
- CLI 分发简化：删除 `main` 中 13 行的 `handlers` 字典，改为各子 parser
  `set_defaults(func=cmd_*)` + `main` 直接 `args.func(args, paths)`；
  `getattr(args, "json", False)` 简化为 `args.json`。
- 新增共享 git 子进程助手 `src/repowiki/gitutil.py`（`run_git(repo, *args, timeout)`），
  scanner / metadata / knowledge / updater 四处各自为政的 subprocess 封装统一收敛到一处；
  失败统一返回 `None`，空输出与失败可区分（保住 update「空 diff = 无变更」语义）。
- `state.stats()` 直接输出 `busy`（复用 stale 判定），`next` / `watch` / `status` 三处繁忙
  口径单源化；`run_next` 不再二次加载 index.json。
- finalize 的 `state/catalog.json` 从单次运行最多解析 3 次减为 1 次；删除 `_emit` 的
  dumps→loads→dumps 往返。

### 清理（ponytail 全仓审计，净删约 76 行）

- 删除仅声明未消费的死代码：`templates.placeholders`、`Inventory.to_dict`、`FileEntry.size`、
  `WikiPaths.repo_rel`、`run_watch` 内的 `snapshot`、`i18n.module_optional_files`、
  `FlatNode.dir`、`validate.check_catalog` 转发包装、metadata 的 `uuid`/`datetime`/`Path`
  死导入等；`_expand_knowledge` 去掉未使用的 `inv` 参数。
- dispatch 的规划任务展开分支从「`(plan_file, expand)` 元组」改为 `if tid == "catalog"` 显式
  判断；`_check_readonly` 冗余的局部导入清理。
- 除上述 `--batch` 外无行为变化；126 个测试全绿。

### 文档

- README 新增「离线安装」一节：运行时仅依赖 pyyaml，给出 `pip download` 备料 +
  `pip install --no-index` 的完整离线路径，以及 skill 目录的手动拷贝方式。

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

- **队列自愈**：worker 死亡后遗留的过期认领由 `next --claim` 自动回收重新入队（此前
  `ready_tasks` 完全排除 in_progress，死认领只能人工 `release --force`，实测曾冻结 25% 页面
  50 分钟）；stale 判定统一为 claim 目录 mtime 单一来源；watch 不再把过期认领计为「执行中」，
  worker 全部死亡时停滞可被及时报告。默认 stale 窗口 45→15 分钟（`REPOWIKI_STALE_SECONDS` 可调）。
- SKILL.md 编排加固：明确禁止主会话给 worker 指定任务清单（全局 FIFO 纯拉取）、禁止 worker
  预支认领（一次只持有一个）、补 watch 后台运行与退出码可信度警告、补环境变量文档。
- 损坏的 `state/index.json` 不再被静默当作空清单（此前一次事务写回会丢掉整份任务清单）；现在保留现场、明确报错，`plan --replan --force` 为显式恢复路径。
- 损坏的 `state/catalog.json` 在 finalize / update / overview 校验路径给出友好错误，不再抛裸 traceback。
- 不存在的任务 id（touch / release）给出友好错误并列出排查指引。
- 非 POSIX 平台（Windows）安装后首次运行改为明确的平台说明，而非 `fcntl` 裸崩溃。
