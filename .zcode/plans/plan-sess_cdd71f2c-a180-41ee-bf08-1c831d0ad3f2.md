# repowiki 最终开发计划（修订版，可直接交给 Coding Agent）

构建 `repowiki`：不含 LLM 的确定性 Wiki 构建系统（Python CLI + SKILL.md 薄封装）。驱动它的 agent 提供智能；对任意 git 仓库生成与 Qoder RepoWiki 类似格式的中文 Wiki，输出到 `<repo>/.qoder/repowiki/`。工具零网络调用、零 LLM 依赖、零 agent CLI 感知。

## 1. Requirements
- R1 输出类似 Qoder repowiki（graphiti 示例为参照）：章节树内容页 + meta/repowiki-metadata.json + knowledge/ 知识卡片 + 增量更新
- R2 范围＝内容页＋metadata＋知识卡片＋增量更新（全部交付，按此优先级排序）
- R3 兼容任何「能执行 shell 命令 + 读写文件」的 agent（ZCode/claude/codex/opencode/人工）
- R4 不配置 LLM provider（无 Key、无 API 后端）
- R5 并发生成：catalog 后所有任务相互独立、可多 worker 并行
- R6 中文输出，技术名词保留英文
- R7 尽快：核心闭环优先，knowledge/updater 可后置独立交付

## 2. MVP Scope
扫描→plan→认领→check→finalize 全闭环；页面/知识卡片/增量三类任务；SKILL.md；完整单测＋e2e。

## 3. Non-Goals（禁止实现）
Windows 支持；en 语言；ADR 会话卡片（示例中 source:session 无法复刻）；MCP 封装；LLM API 后端；`--exec` 执行器；`dispatch` 命令；serve 预览；模板覆盖参数；加密 raw_data 字段；通用 DAG（只用 3 阶段门控）。

## 4. Architecture
```
驱动 agent（智能） ⇄ repowiki CLI（确定性）
plan: 扫描→生成阶段1任务(catalog规划)
agent 执行任务 → 写 catalog.json 或页面文件
check: schema/模板校验 + 确定性自动修复 + 状态流转
next --claim: 原子认领就绪任务 → 阶段2展开全部页面任务(独立)
finalize: 反向提取引用 → 组装 metadata.json
update: git diff → 受影响页重写任务(含更新摘要)
```
职责切分：程序做 扫描/diff/路径派生/锚点/行钳制/校验/修复/元数据组装；agent 做 目录规划/逐页撰写/overview/知识卡片/更新摘要。
worker 循环契约（写入每个任务规格与 SKILL.md）：
`loop: t=$(repowiki next --claim --json) → 无任务退出 → 按规格执行 → repowiki check --task <id> --json → 失败自查修复重查`

## 5. Components（src/repowiki/）
`cli.py`(argparse,子命令见§8) / `scanner.py` / `templates.py`(加载包内模板资产) / `catalog.py`(schema+校验+标题→路径派生) / `tasks.py`(任务规格生成) / `state.py`(状态+原子认领+过期回收) / `validate.py`(规则引擎+自动修复) / `metadata.py` / `updater.py` / `knowledge.py` / `paths.py`(NFC归一化/非法字符/冲突后缀)。
模板资产 `templates/`(包数据)：page_template.md(页面骨架全文)、catalog_task.md、page_task.md、overview_task.md、knowledge_task.md、update_task.md、STYLE.md(mermaid 风格范例：引号+<br/>节点、graph TB/LR、sequenceDiagram 实例)。

## 6. Data Model
**目录布局** `<repo>/.qoder/repowiki/{zh/{content/**, meta/repowiki-metadata.json}, knowledge/zh/**, state/{index.json, catalog.json, tasks/<id>.md, claims/<id>/{worker,ts}}}`
**catalog.json**：`{"repo_name":str, "chapters":[Node]}`；Node=`{"id":str(c01…),"title":str中文,"slug":str[a-z0-9-],"summary":str,"kind":"chapter"|"page","dependent_files":[仓库相对路径],"page_brief":str(本页要点，成为任务提示),"children":[Node]}`；约束：全局标题唯一、深度≤4(chapter 才有 children)、dependent_files 必须存在于扫描清单(无效项剔除并告警)、根级 kind:page = 顶级独立页。
**index.json**：`{"tasks":{"<id>":{"kind":"catalog|page|overview|knowledge_module|knowledge_card|page_update","phase":1|2|3,"status":"pending|in_progress|done|failed","title":str,"output":str(相对 .qoder/repowiki/)，“spec":"state/tasks/<id>.md","attempts":int,"claimed_at":ISO,"heartbeat_at":ISO,"worker":str}},"created_at":ISO}`
**任务规格 state/tasks/<id>.md**：YAML frontmatter(id/kind/title/output/hint_files/checklist) + 正文(目标/完整模板/STYLE 摘录/输出路径/自检清单/worker 契约)。文件生成后不可变。
**页面模板骨架**(page_template.md 主体)：H1 → `<cite>`(本文引用的文件+file://链接) → [增量页: ## 更新摘要] → ## 目录(数字列表中文锚点) → ## 简介 → ## 项目结构(mermaid graph TB) → ## 核心组件 → ## 架构总览(sequenceDiagram) → ## 详细组件分析(###子节) → ## 依赖关系分析(graph LR) → ## 性能与一致性考量 → ## 故障排查指南 → ## 结论 → [可选 ## 附录]；每图后`图表来源`、每节末`章节来源`，格式 `[path:Lx-Ly](file://path#Lx-Ly)`；页间零链接。
**metadata.json 产出字段**：wiki_repo{id,name,progress_status,last_commit_id,generated_at}；wiki_catalogs[{id,name,description=slug,parent_id,dependent_files,prompt=page_brief,progress_status}]；wiki_items[{catalog_id,title}]；source_files[{id=md5(path),path,filename}]；code_snippets[{id=md5(path+range),path,line_range}]；knowledge_relations[{type:CONTAINS|REFERENCED_BY,from,to}]；wiki_overdown→wiki_overview(str)。明确舍弃：raw_data/recovery_checkpoint(内部状态留在 state/)。

## 7. 路径与确定性规则（paths.py）
标题→路径：NFC 归一化；替换 `/\:*?"<>|` 与控制字符为全角对应或删除；目录名=章节名；索引页文件名=章节名.md；重名冲突追加 `__2`；POSIX 分隔符；file:// 链接统一正斜杠。目录锚点：GitHub 算法（小写、去 `：:` 等标点、空格转 `-`、保留中文）。行区间：钳制到 [1, 文件行数]。

## 8. Interfaces（CLI 契约；全部支持 --json；退出码 0=成功 1=校验失败/用法错 2=状态冲突）
- `repowiki plan <repo> [--replan] [--max-pages N] [--knowledge]`：扫描(代码文件<10 → 报错退出1)；写阶段1 catalog 任务；若 state/catalog.json 已存在且合法则直接展开阶段2任务(除非 --replan 重置)。JSON: `{"tasks_total":N,"phases":{...},"warnings":[...]}`
- `repowiki next <repo> [--claim] [--batch N] [--json]`：返回前置阶段全 done 的就绪任务(优先级: attempts 少→phase 小→目录序)；--claim 原子 mkdir claims/<id> 写 worker+时间戳、状态→in_progress；无任务且阶段未完成返回空列表。JSON: `{"tasks":[{"id","kind","title","output","spec_path","instructions":str(规格正文)}]}`
- `repowiki check <repo> [--task ID]`：校验 catalog.json(schema)或页面(见§9)；确定性缺陷自动修复并在结果标 `fixed:[...]`；语义缺陷列 `errors:[{rule,path,detail}]`，状态→failed；通过→done+刷新 heartbeat；catalog 任务通过时自动展开阶段2任务。幂等。
- `repowiki release <repo> --task ID [--force]`：in_progress→pending(force 可释放他人认领)
- `repowiki finalize <repo>`：任一任务非 done → 报错退出1；解析全部页面提取 file:// 引用→组装 metadata.json；创建阶段3 overview 任务(生成后再跑一次 finalize 写入 wiki_overview)
- `repowiki update <repo> [--since <sha>]`：git diff --name-only；非 git 仓库报错；变更文件∩dependent_files(含祖先章节链)→生成 page_update 任务(规格含旧页全文+变更文件清单+更新摘要要求)；新顶级目录>2 个时提示建议全量
- `repowiki knowledge <repo>`：追加 knowledge 任务集(阶段2)
- `repowiki status <repo>`：任务统计/失败列表/过期认领

## 9. 校验规则（validate.py，自动修复 vs 报错明确分开）
自动修复(静默修+报告 fixed)：目录锚点不匹配→重写；行区间越界→钳制；H1 与任务标题不一致→重写 H1；引用路径大小写/分隔符→归一。
报错(→failed，错误信息含精确位置与期望)：文件为空/截断(无 H1 或 <6 个 `##` 节)；缺必备章节(简介/项目结构/核心组件/架构总览/详细组件分析/依赖关系分析/结论)；`<cite>` 缺失或无有效引用；file:// 目标不存在于仓库；mermaid 围栏不平衡；catalog schema 违例(§6 约束)。
告警(不阻断)：页间互链；单页引用文件>15。

## 10. Task DAG
```
T0 脚手架 ─→ T1 scanner ┐
          ─→ T2 模板资产 ┼→ T4 plan ─→ T5 state/claim ─→ T6 next ─┐
          ─→ T3 catalog schema ┘                                 ├→ T8 check ─→ T9 早期e2e冒烟
                                    T7 validate+修复 ─────────────┘        │
T9 ─→ T10 finalize/metadata ─→ T11 knowledge ─┬→ T14 完整e2e
                              ─→ T12 updater ─┤
T6/T8 后并行: T13 SKILL.md+README ────────────┘
```
串行主干 T0→T4→T5→T6→T8→T9→T10；T1/T2/T3 并行；T11/T12/T13 并行；每任务含自测。

## 11. Detailed Tasks（DoD 格式：做/改/不改/输入/输出/验证/DONE）
- **T0** 做:pyproject(pyyaml+rich,console_script repowiki)+包骨架+pytest 配置。验证:`pip install -e . && repowiki --help`。DONE:命令可用。
- **T1** scanner:输入 repo 路径→输出 Inventory{files:[{path,loc,lang}],tree_summary(每目录≤20文件截断),key_files}。git ls-files 优先，回退 os.walk(跳过 .git/node_modules/venv/dist/target/build)。不改:其他模块。验证:对 graphiti 仓库快照测试。DONE:单测过。
- **T2** 模板资产:按 §6 骨架与 STYLE.md 写全 7 个模板文件(内容来自示例逆向)。验证:模板含全部必备标题占位。DONE:文件齐且占位符 {{TITLE}} 等定义一致。
- **T3** catalog schema+校验+paths.py 路径派生。验证:合法/非法夹具各≥5。DONE:单测过。
- **T4** plan 命令:集成 T1/T2/T3；写 catalog 任务规格；catalog.json 已存在则展开阶段2任务(每页任务=§6 任务规格,含 hint_files=dependent_files、完整模板)。不改:state 并发逻辑。验证:夹具仓库跑通两种路径。DONE:单测过。
- **T5** state:index.json 读写(原子 tmp+rename)、claim(原子 mkdir,失败返回冲突)、release、stale(heartbeat 超45min→可被认领,attempts+1)。验证:多进程竞态测试(10 进程×50 任务零重复)。DONE:竞态单测过。
- **T6** next:就绪过滤+优先级+--batch+--json(含 instructions)。DONE:契约单测过。
- **T7** validate:§9 全规则+自动修复。验证:每规则至少 1 正 1 反夹具。DONE:规则单测全过。
- **T8** check:validate 集成+状态流转+catalog 通过展开阶段2。DONE:集成单测过。
- **T9** 早期 e2e 冒烟:由我(ZCode)对 fixture 小仓库驱动 plan→手写1页→check→修复→done。DONE:闭环走通,暴露的规格缺陷回修 T2。
- **T10** finalize:file:// 解析(正则)+source_files/code_snippets/relations 组装+overview 任务。验证:对冒烟产出断言字段。DONE:metadata 单测过。
- **T11** knowledge:模块树任务(_module.yaml+概述/技术栈/架构设计/特殊配置与命令/编码规范)+机制卡片任务(六类:config/logging/error/build/deps/style,front matter+四节)+_index.yaml 组装(程序侧由各卡片 front matter 聚合)。DONE:夹具过。
- **T12** updater:§8 逻辑+page_update 规格(旧页+diff 文件+更新摘要/**已更新** 标记要求)。验证:构造两次 commit 夹具断言映射。DONE:映射单测过。
- **T13** SKILL.md(触发词/worker 契约/并发 subagent 配方)+README(安装/流程/并发配方含 5 行 shell 无人值守示例/格式说明/Non-Goals)。DONE:按 SKILL.md 从零走通一次。
- **T14** 完整 e2e:对一个小型真实仓库(从 workspace 选),我 spawn ≥3 subagent 并发跑 worker 循环→finalize；产出与 graphiti 示例做结构比对清单(章节树/模板节/引用格式/metadata 字段)。DONE:AC1-AC6 全过。最后 `git init`+初始提交(征得同意)。

## 12. Tests
单测(全离线):scanner(空仓库/非git/大repo截断)；catalog schema(违例矩阵)；paths(NFC/非法字符/重名/中文括号)；state(竞态/stale/幂等)；validate(§9 每规则正反夹具)；metadata(字段断言)；updater(删除/改名/祖先链)；knowledge(聚合)。e2e:T9 冒烟+T14 并发。

## 13. Acceptance Criteria
- AC1 ≥3 并发 worker 完成小仓库全流程，tasks 全 done，产出模板全合规
- AC2 单 worker 串行同样可行
- AC3 kill 模拟的 stale 认领被回收且不重复不丢失
- AC4 合成 commit 后 update 仅重生成映射页且含「## 更新摘要」
- AC5 knowledge 产出 _index.yaml+模块+卡片且 schema 校验通过
- AC6 与 graphiti 示例结构比对清单逐项一致(允许字段差异=明示舍弃项)
- AC7 全测试套件通过；工具运行全程无网络调用

## 14. Risks
规格不自解释→完整模板内嵌+T9 早冒烟；目录规划差→范例章节结构+--replan 回路；竞态→原子操作+专项测试；校验误报→确定性项自动修复；中文路径→NFC+专项测试；knowledge/updater 拖期→DAG 后置独立交付。

## 15. Open Decisions（默认已定，可被用户推翻）
stale 阈值 45min；确定性缺陷静默修复+fixed 报告；代码文件<10 拒绝 plan。

## 16. Agent Execution Rules（给执行本计划的 Coding Agent）
1. 禁止新增 §3 Non-Goals 任何项与计划外基础设施；2. 严格按 T 序，T1/T2/T3 与 T11/T12/T13 组内可并行；3. 每任务先写测试夹具再实现；4. 所有文件写入仅限本仓库；5. 模板内容以 graphiti 示例为准，不确定处读示例原文件；6. 遇规格空白不得臆造——在任务内以最小合理实现并记录到 DECISIONS.md。

**结论：GO** —— 三项 Open Decisions 已采用安全默认值，无阻塞项，可立即开工。