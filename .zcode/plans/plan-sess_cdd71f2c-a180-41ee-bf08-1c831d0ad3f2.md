# 按优先级修复 repowiki 生命周期与 agent 通用性问题

对象：`/Users/luoms/workspace/repowiki`（本会话构建，81 测试全绿）。全部问题的根因与行号已在上轮评审确认。每项修复带回归测试，完成后文档（README/SKILL/DECISIONS）同步、提交。

## 修复设计（按优先级）

### P0-1【L1】执行期心跳防双写
- `state.py`：`heartbeat()` 已有，新增 `touch` 命令（cli+dispatch 转发）：刷新 claim 目录 mtime + `heartbeat_at`（对 in_progress 任务有效，done/无认领报 ConflictError）
- `dispatch.run_check`：check 处理 in_progress 任务时顺带调 `heartbeat()`（把"check 刷新心跳"从文档约定变成工具行为）
- worker 契约文本更新（SKILL/README/任务规格模板末尾）：「撰写期间每隔几分钟执行 `repowiki touch <repo> --task <id>` 防止长任务被误回收」
- 默认 stale 阈值不变（45min）

### P0-2【L2】done 终态化，消除死锁
- `dispatch.run_check`：显式 `--task` 指向 **done** 任务时→只读校验报告（展示 ok/errors/fixed），**不改状态**；输出注明「done 为终态，如需重生成请用 update」
- （依赖 P1-2 的 `--all` 改造后）默认路径不再触碰 done
- 测试：done 任务 check 后状态仍为 done

### P0-3【L3】毒任务重试上限
- `state.py`：`REPOWIKI_MAX_ATTEMPTS`（默认 3）。`ready_tasks` 排除 `attempts >= max_attempts` 的 failed 任务；`stats()` 新增 `exhausted` 列表；`busy` 计数不含 exhausted
- 逃生舱：`release --task <id> --force` 扩展为也对 exhausted 的 failed 任务有效（重置 attempts=0 回 pending）——人工/主 agent 显式干预
- `status` 展示 exhausted；文档写入

### P0-4【A1】check 选择器显式化 + 认领归属校验
- `check` 不带选择器 → UsageError「请指定 --task <id> 或 --all」（旧默认行为移到 `--all`，供崩溃恢复/主 agent 用）
- 归属校验：`check --task` 目标若 in_progress 且 `claims/<id>/worker` 与当前 `--worker`（新参数，缺省不校验）不一致 → ConflictError，需 `--force`。主 agent/人工场景用 `--all --force`
- 测试：无选择器报错；done 只读；他人认领被拒

### P1-1【L4】index.json 乐观锁
- `state.py`：新增 `_transaction(mutate)` 助手——记录 load 前 `st_mtime_ns`，mutate 后 save 前复查，变了则重读重放（最多 5 次）；`_merge_task`/`update`/`add_tasks` 全部走它
- 测试：多进程 × 各自翻转不同任务状态，断言无丢失（现有竞态测试加强版）

### P1-2【L5】finalize 页面存在性门禁
- `metadata.run_finalize`：组装前校验 catalog 每个节点 output 文件存在；缺失→UsageError 列出缺失清单（提示 `--max-pages` 试跑场景），不写 metadata
- 测试：缺页 finalize 失败并列出页名

### P1-3【A2】finalize 退出码语义
- 新退出码 **3**＝"进展性等待"：首次 finalize 创建 overview 任务后返回 3（原 1）；`--json` 增加 `next_action` 字段
- 同步：README 退出码表、SKILL 流程、`test_finalize_two_step_overview` 断言 1→3

### P1-4【L6】replan busy 守卫
- `plan --replan`：index.json 存在且含 in_progress 任务 → UsageError（提示先等完成或 `--force`）；plan 新增 `--force`
- 测试：in_progress 时 replan 报错、--force 通过

### P2（文档与小修，一次提交）
- **L7**：README update 小节注明「仅识别已提交变更（since..HEAD），工作区未提交改动不可见」
- **L8**：`update` 已存在 pending 的同名 `-update` 任务时输出警告（基线可能过期，建议先完成或 clean）
- **L9**：`tasks.build_update_task` 在旧页面文件不存在时生成 `kind=page` 任务（而非要求不存在的更新摘要）；签名微调
- **A3**：重写 README 无人值守 shell 示例，正确实现「空且 busy>0 → sleep 重试」契约
- **L10/A4/A5/A6**：README「已知边界」小节记录（overview 不参与增量、模板内嵌的 token 代价、中文硬门槛、jq 依赖），不做实现

## 实施顺序与验证

1. P0 四项（state.py→dispatch.py→cli.py→模板/契约文本）+ 各自测试
2. P1 四项 + 测试
3. P2 文档与小修
4. 全套 pytest（81+新增 ≈90）+ e2e 冒烟（touch/check 语义/replan 守卫对 /tmp/repowiki-e2e 实测）
5. 提交（P0/P1/P2 各一笔），同步全局技能 SKILL.md 副本

## 不做
- 分布式锁/守护进程级心跳（单机多 worker 场景，touch+契约已覆盖）
- 任务规格的轻量引用模式（A4，权衡后维持自包含）
- 多语言（A5）、overview 增量（L10）——记录为已知边界
