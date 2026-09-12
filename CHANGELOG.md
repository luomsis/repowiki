# Changelog

**中文** | [English](CHANGELOG.en.md)

## 0.7.0 — 2026-09-12

### 新增

- **行号校验分层**：起点越界（start > 文件行数）与区间倒置（start > end）从「静默钳制」
  改为 error 打回 agent 重写——幻觉行号不再被转正为格式合法但语义任意的引用；
  仅终点越界（end > 文件行数）保留自动钳制（良性截断）。
- **引用区间内容 sanity check**：引用行区间经解码后若全为空白行，报 error
  「无法支撑任何论断」——此前行号落在空行/闭括号上一视同仁放行。
- **mermaid 节点文件名核对**：图节点标签中形如文件路径的 token（按 basename 匹配）
  与仓库文件清单比对，未命中报 warning（非阻断，概念命名可忽略）；
  `check` 执行时把 `scan()` 得到的清单经 `known_paths` 传入 `check_page`。
- **小节来源强制**：每个 `##` 小节（「目录」与增量更新「更新摘要」豁免）必须非空、
  且包含「章节来源 / Section sources」标记（i18n 化，`STRINGS` 新增 `section_sources`），
  违例报 error；空小节（剔除代码围栏后无内容）同样报 error。
- **coverage 报告分组与有效覆盖率**：未被引用文件确定性分为 vendor / 其他语言镜像
  （按 locale 变体替换命中已引用集合判定）/ 值得补引用 三组，新增
  `effective_coverage`（分母剔除 vendor 与镜像）与 `uncited_breakdown`（JSON），
  人类可读输出同时给出两个口径并分组展示。

### 变更

- **页面布局**：「本文引用的文件」引用块由页首（H1 之后）移至页面末尾（结论小节之后）；
  增量更新任务的插入锚点同步调整（H1 之后、「目录」之前）；存量 wiki 页面已迁移。
- `validate._file_loc` 除行数外同时返回解码后的行内容（`utf-8` + `errors="replace"`，
  二进制 `\0` 判定保留），供引用区间 sanity check 使用。

### 文档

- templates（zh/en）`STYLE.md` 与 `page_task.md` 的行号规则补充新语义：
  「起点越界/区间倒置会被打回，仅终点越界自动钳制」；`SKILL.md` / `SKILL.en.md`
  硬性规则与自动修复范围描述同步。

### 测试

- 新增 10 个校验器用例：起点越界、区间倒置、空行区间、mermaid 未知/已知文件名、
  小节缺来源、空小节；`test_line_range_clamped` 在新策略下保持通过（end-only 钳制）。
- coverage 新增分组与有效覆盖率用例（vendor 文件 + en 镜像 + zh 双文件被引用场景）；
  conftest / test_i18n 页面夹具补齐小节来源标记以符合新规则；全套 202 项通过。

## 0.6.1 — 2026-09-09

### 文档

- **README 重构**：顶部新增 PyPI 徽章与在线样例前置链接；特性列表重写为 7 条「加粗关键词 +
  一句话效果」；安装主线更新为 PyPI `pip install repowiki-cli`；命令表精简为常用 8 条；
  离线安装压缩；设计取舍 / 已知边界 / Non-Goals 合并为「设计边界」一节；移除易过时的具体数字；
  进一步移除「快速开始 / 用法 / CI 集成」三节（五命令流程、输出结构树与 wiki.yml 集成说明
  并入 USAGE.md），README 聚焦卖点与安装。
- **新增 [docs/zh/USAGE.md](docs/zh/USAGE.md) / [docs/en/USAGE.md](docs/en/USAGE.md)**：
  收纳自 README 移出的完整内容——Worker 循环契约、并发配方（含 worker.sh 脚本）、15 条命令
  完整参数表、module/flow 模板小节枚举、可靠性机制细节与离线安装完整步骤，无信息丢失。

## 0.6.0 — 2026-09-09

### 新增

- **`repowiki skill install / status`**：skill 文件（`SKILL.md` / `SKILL.en.md`）随 wheel
  一起分发，pip 装完 CLI 后一条命令即可把 skill 安装到 agent 全局 skills 目录——默认
  `~/.agents/skills/repowiki/`，`--agent claude|codex|zcode|cursor|opencode` 指定客户端
  目录，`--target <目录>` 完全自定义；安装写入版本戳，幂等可重复执行。
  `repowiki skill status` 报告各处已装版本与包版本的差异，识别未安装 / 手拷无版本戳 /
  过期 / 已是最新四种状态；两命令均支持 `--json`。

### 变更

- **skill 目录迁入包内**：`skills/repowiki/` → `src/repowiki/skills/repowiki/`（单一事实
  源，wheel 与 git/插件安装读同一份文件）；`.claude-plugin/plugin.json` 的 `skills` 字段
  改指 `src/repowiki/skills`。

### 文档

- README（zh/en）安装节改为推荐 `pip install repowiki-cli` + `repowiki skill install`，
  手动拷贝降级为备选；离线安装节更新为「装好 CLI 后 `repowiki skill install`」；
  skill 路径引用同步到新位置。

### 测试

- 新增 `tests/test_skill_install.py`（7 项）：包内 skill 资源可读（守护 package-data）、
  默认/`--agent`/`--target` 三种目标安装、幂等与旧版更新报告、status 四态判定。

### 清理

- **Roadmap 小节移除**：产出语言冻结为 zh/en，不再扩展更多语言；「CLI 交互消息双语」计划
  取消（CLI 消息维持现状，面向驱动它的 agent）。

## 0.5.1 — 2026-09-08

### 修复

- **版本号检测适配新分发名**：分发名改为 `repowiki-cli` 后，干净安装的 `repowiki --version`
  显示 0.0.0（`__init__` 的 metadata 查询仍用旧名）——现优先查 `repowiki-cli`，兼容旧名回退。

### 变更

- **PyPI 分发名定为 [`repowiki-cli`](https://pypi.org/project/repowiki-cli/)**：PyPI 上的
  `repowiki` 名已被同用途项目（he-yufeng/RepoWiki）占用。分发名变更不影响使用——
  命令名仍为 `repowiki`、import 包名仍为 `repowiki`，`pip install repowiki-cli` 后照常使用；
  离线安装的 wheel 文件名相应变为 `repowiki_cli-*.whl`。

## 0.5.0 — 2026-09-08

### 新增

- **页面原型（module / flow）**：catalog 页面节点新增可选 `archetype` 字段——流程/机制主题页设
  `"archetype": "flow"` 使用流程型模板（简介/流程总览/关键步骤/参与组件/数据与状态变化/故障
  排查/结论，配时序图+状态图），默认 `module` 保持原结构型九段模板；校验器按原型分必备小节
  规则，catalog 任务规格引导规划者按主题选型。
- **`coverage` 子命令**：只读覆盖率报告——统计 wiki 页面/总览/知识卡片从未引用的仓库文件、
  逐页引用密度与零引用页面，全部确定性计算（对标竞品给不出的「可证明质量」指标）。
- **`update`/`stale` 新增 `--dirty`**：默认只看已提交变更（since..HEAD）；`--dirty` 纳入工作区
  未提交（暂存+未暂存）与未跟踪变更——改完没提交也能让 wiki 跟上。
- **overview 总览页纳入增量更新**：`update` 命中任何页面时自动排 `overview-update` 任务
  （同步定位概述与章节导航；总览不加「更新摘要」小节，校验沿用总览形状）。
- **知识卡片类别可配置**：`repowiki knowledge --categories <file>` 用 YAML/JSON 清单整表替换
  内置六类（id 限小写下划线，≤12 类），持久化于 `state/knowledge_categories.json`，
  check/update 按其校验；未提供时行为不变（零迁移）。
- **`llms.txt` / `llms-full.txt` 导出**：`repowiki site` 在生成 `wiki.html` 的同时，按章节导出
  全部页面的链接索引 `llms.txt` 与全文合并版 `llms-full.txt`（遵循 [llmstxt.org](https://llmstxt.org/)
  约定）——任何 agent / IDE 可直接按索引消费 wiki，无需 MCP。
- **只读 `stale` 子命令**：`repowiki stale <repo> [--since <ref>] [--fail-if-stale]`——复用
  `update` 的 diff→受影响页面映射（含祖先链与知识库联动），报告哪些页面/卡片/模块会过期；
  不创建任务、不写 state；`--fail-if-stale` 命中即 exit 1，供 CI 门禁。
- **官方 GitHub Action（`wiki.yml`）**：PR 上自动跑 stale 门禁并在过期时评论受影响页面、拦截合并
  （确定性检查，CI 内不跑 agent）；push main 自动 `site` 重建并发布 GitHub Pages。
  采用 wiki-as-code 模式：仓库跟踪 `.repowiki/` 的内容/元数据/知识库/llms 索引，
  `state/claims`、`state/tasks` 与可重建的 `wiki.html` 忽略。
- **站点 UI 三项**：H1/H2 层级区分度增强（H1 加大为 2em/800 并保留全宽下划线，H2 改为主题色
  文字 + 3px 同色左侧竖条）；章节导航层级重构（章节标题本身成为指向该章索引页的链接并以
  主题色显示、去掉全大写样式，下拉中不再重复显示与章节同名的索引页）；「本页内容」目录框
  支持折叠并在折叠时停靠侧栏底部（目录面板样式维持原状）。
- **PyPI 发布就绪**：pyproject 补全 readme / urls / keywords / classifiers，
  `pip install repowiki` 待首次上传后可用。

### 修复

- 站点 UI：原先 H1 与 H2 同为前景色 + 全宽下划线，视觉层级难以区分（见上条的三项重构）。

### 清理

- 内置知识类别表迁移为带说明的 `DEFAULT_KNOWLEDGE_CATEGORIES`（tasks.py），规划任务规格的
  类别清单改为渲染注入（`{{CATEGORY_BLOCK}}`），不再硬编码于模板。

### 测试

- 测试 157 → 187：新增 coverage 报告、stale 门禁、`--dirty`、overview 增量刷新、自定义
  知识类别、flow 原型与 llms 导出的正反例与端到端覆盖。

### 文档

- 新增竞品调研报告（`docs/{zh,en}/research/competitive-analysis.md`：DeepWiki /
  DeepWiki-Open / CodeWiki / GitDiagram / Swimm / Repomix 对标与 P0-P2 改进分级）；
  决策记录追加第 15 条（调研结论与 P0 采纳）与第 16 条（P1 四项实现取舍）。
- README 双语：新增「CI 集成」一节、`stale`/`coverage` 命令行、GitHub Pages 在线样例链接、
  agent 消费接口与页面原型特性项；「已知边界」移除 overview 不参与增量更新一条（已实现）。

## 0.4.0 — 2026-09-07

### 新增

- 知识卡片全生命周期补全：
  - **update 联动知识库**：`update` 把变更文件对照知识规划——`source_files` 命中的卡片、scope 命中的模块各建增量刷新任务（卡片更新规格附「## 5. 更新摘要」小节，`check` 按 `is_update` 校验）；
  - **site 知识库章**：知识模块文档与卡片作为普通页面纳入 `wiki.html` 侧边栏「知识库」章——可搜索、源码弹层、mermaid 全部生效，卡片 front matter 渲染时剥离；
  - **跨周期重武装**：`update` 对上一轮 done 的 `*-update` 任务按最新变更集重新生成规格并重置为 pending——修复跨 finalize 周期后第二轮 update 空转的问题。
- 聚合导出填充 `source_files`：`_index.yaml` / `_module.yaml` 按模块 scope 收集命中卡片的源文件并集（原先恒为空数组）。

### 修复

- 移除 `knowledge.py` 中不可达的死代码。

## 0.3.3 — 2026-09-07

### 修复

- **站点抽屉菜单按钮**：桌面端侧栏常驻，顶栏 `#menu-btn` 是死控件；现在仅在窄屏
  （≤900px）显示。

### 文档

- README 双语首页的 ASCII 架构图替换为绘制的架构图：中文版配中文图、英文版配英文图；
  新增交互版架构图与规格（`docs/repowiki-architecture*.html`/`.json`，支持明暗主题、
  路径高亮、节点搜索）。
- 自我描述不再刻意强调「不含 LLM」：README 首句与特性列表改为「确定性构建」表述，
  包 description、CLI `--help`、模块 docstring 同步。

## 0.3.2 — 2026-09-05

### 新增

- 文档集中双语化：`docs/` 改为 `zh/`+`en/` 镜像结构（CONTEXT、DECISIONS、ADR 迁入
  `docs/zh/`），新增全量英文版 `CHANGELOG.en.md` 与 `docs/en/**`；README、CHANGELOG
  留在仓库根部（GitHub 主页与 Releases 页渲染依赖根目录）。
- README 英文版 `README.en.md`；README launch 打磨：badges、「为什么是 repowiki」对比表、
  Features、用法（Usage）、Roadmap、Contributing、社区入口、目录。
- 新增 `skills/repowiki/SKILL.en.md`（SKILL.md 的英文姊妹版）。

### 修复

- **语言自动检测优先 README.md**：`detect_locale` 原取 `sorted(glob("README*"))` 的
  第一个——`README.en.md` 排序在 `README.md` 之前，双语仓库的 `plan --replan` 会把
  产出语言误判为 en；现在 README.md 存在时以其为准，缺失才回退其余 README*。

## 0.3.1 — 2026-09-05

### 修复

- **Windows CI 兼容**（预存问题，与上两条同窗修复）：测试夹具的 `read_text`/`write_text`
  未显式 `encoding="utf-8"`，Windows 默认 cp1252 下 10 个用例报 UnicodeDecodeError/
  UnicodeEncodeError；`state.py` 读 index.json 与 `os.replace` 原子换入在 Windows 存在
  双向竞态（CPython 打开文件不带 FILE_SHARE_DELETE，读写任何一侧都会撞 PermissionError），
  现在读者与写方统一走 `.index.lock` 并对换入做短暂重试；锁后端缺失测试修正为同时屏蔽
  `fcntl` 与 `msvcrt`（原只屏蔽 POSIX 侧，Windows 上测试形同虚设）。
- **watch 停滞误报**：某任务在循环顶部快照与停滞判定之间恰好完成时，`ready_tasks` 已空
  导致误报「停滞」退出 1——宣布停滞前用新鲜 stats 复核。
- **catalog 校验拒绝占位符标题**：节点 title 含 `{{...}}` 模板占位符形态时 `validate_catalog`
  报错。此前这类标题会一路穿透进任务规格与页面 H1（templates.render 按 key 替换、未知占位符
  原样保留，`{{TITLE}}` 被填回字面量），而产物校验又把 H1 里的该字面量判为「未替换占位符」
  ——任务从规格生成那一刻起就注定无解（实战中一个页面任务因此耗尽重试）。
  同步在 zh/en 两份 catalog 任务模板的规划规则第 3 条写明禁令。
- **占位符扫描只针对非代码文本**：页面/卡片/总览三处「仍含未替换的模板占位符」检查改为剔除
  fenced 代码块与行内代码后扫描——文档页 legitimately 讨论占位符机制时，代码里的字面
  `{{...}}` 是内容而不是缺陷；散文中的残留占位符照旧失败。正则更名为公开的
  `repowiki.validate.PLACEHOLDER_RE` 供 catalog.py 复用。

### 变更

- **站点查看器（wiki.html）视觉全面改版**：引入设计令牌体系（中文字形字体栈、h1-h6 字阶、
  圆角/阴影令牌）、代码块头栏（语言标签 + 复制按钮）、侧栏页内目录 + scroll-spy 跟随高亮 +
  章节折叠、暗色主题层次分离、表格斑马纹、mermaid 卡片容器、prev/next 翻页、阅读进度条、
  顶栏 SVG 图标与面包屑、搜索命中词高亮、`prefers-reduced-motion` 与 `:focus-visible`
  可访问性细节。payload 结构与单文件契约不变（仍恰好 4 个内联 script、零外部资源）。

### 测试

- 新增 2 个用例：catalog title 含占位符 → 报错；占位符出现在代码块/行内代码中 → 通过。
  149 个测试全绿。

## 0.3.0 — 2026-09-04

### 新增

- **Windows 原生支持**：并发状态控制改为 stdlib 双锁后端（POSIX `fcntl` / Windows `msvcrt.locking`），
  删除"仅支持 POSIX，Windows 请用 WSL"的运行时门控；修复 `tasks.py` 两处在反斜杠路径下取错仓库名的
  `split("/")`；CI 矩阵加入 `windows-latest`（3.10-3.13 全跑）；SKILL.md 补 PowerShell 等价命令
  （`Get-Command`、`Start-Process` 后台 watch）。运行时依赖不变（仅 pyyaml）。
- **`repowiki site <repo> [--open]`：单文件离线查看站点**。finalize 后执行，把全部页面渲染为一个
  自包含 HTML（`<locale>/wiki.html`，约 4-5 MB）：marked + mermaid 渲染库内嵌（vendor 进仓库随
  wheel 分发，MIT）、`file://` 源码引用点击弹层展示内嵌的行号源码片段、侧边栏导航、客户端全文搜索、
  暗/亮主题。幂等可重跑；`repowiki clean` 之后仍可从磁盘页面重建（章节顺序退化为目录序）。
  README Non-Goals 的「HTML 预览服务」相应改述为「常驻预览服务器」。

### 修复

- 站点查看器的两处前端缺陷（发布后冒烟测试发现，已随本版本修正）：点击页内「目录」锚点会触发
  hash 路由回退到总览页——现在锚点 hash 只滚动不切页；导航高亮误用 `querySelector` 导致只有
  第一个链接参与高亮切换——改为 `querySelectorAll`。
- 插件清单 `.claude-plugin/plugin.json` 版本号滞后（0.1.0），与 pyproject 同步为 0.3.0。

### 文档

- 新增根级 `CONTEXT.md` 术语表（产出物/编排/执行三组域术语）。
- 新增 `docs/adr/0001`（Windows 原生支持的 stdlib 双锁后端取舍）与 `docs/adr/0002`
  （单文件离线站点：回撤 Non-Goal 的动机与备选方案）。
- README：平台声明覆盖三平台、新增「查看 Wiki（单文件离线站点）」一节、命令表补 `site`、
  离线安装注明 pyyaml wheel 按目标平台下载（含 Windows）。

### 测试

- 新增 14 个 `tests/test_site.py` 用例：payload 组装与导航树（含章节自身页）、源码片段行区间提取与
  缺失标记、`</script>` 逃逸防护、幂等重建、locale 隔离、clean 后降级构建、`--open`/`--json` 行为；
  锁后端缺失的用例改为验证"双后端均不可用"的友好报错。140 个测试全绿。

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
