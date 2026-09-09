# repowiki Wiki 总览

## 概述

repowiki 是一个为代码仓库生成结构化 Wiki 的确定性任务编排器，以 Python CLI 形式分发（PyPI 分发名 `repowiki-cli`）。它的核心设计是「确定性编排 + agent 智能」的职责分离：CLI 本身不含任何 LLM 调用，只负责扫描仓库、规划任务、原子分发任务、校验产出与组装元数据；所有智能工作——阅读源码、按任务规格撰写 wiki 页面——由驱动它的任意 coding agent 完成。这一分离使产出质量取决于 agent 的阅读与写作能力，而产出的一致性、可并发性与可校验性由编排器保证。

主要特性包括：页面内使用 mermaid 图表与 `[path:Lx-Ly](file://path#Lx-Ly)` 行级源码引用，确保每个论断可回溯到具体代码；产出语言自动跟随目标仓库（中文或英文，plan 时检测并以 `--locale` 覆盖）；基于文件锁的任务认领与心跳机制支持多个 agent 并发撰写同一仓库的 wiki；finalize 后可将全部页面组装为单文件离线 HTML 站点（`wiki.html`），并导出 `llms.txt` / `llms-full.txt` 供其他 agent 或 IDE 按索引消费。

分发形态有三条线：PyPI 常规安装（依赖仅 `pyyaml`，Python ≥ 3.10，由 GitHub Release 触发 Trusted Publisher 自动上传）；GitHub Release 附带 wheel 供离线环境安装；Agent Skill 分发——skill 文件（`SKILL.md`）随 wheel 内嵌打包，装完 CLI 后执行 `repowiki skill install` 即可安装到各 agent 的全局 skills 目录，仓库同时提供 Claude Code / ZCode 插件清单。

[README.md:1-100](file://README.md#L1-L100)
[pyproject.toml:1-50](file://pyproject.toml#L1-L50)
[src/repowiki/__init__.py:1-21](file://src/repowiki/__init__.py#L1-L21)

## 章节导航

- 项目概述 —— repowiki 的定位、设计理念，以及仓库结构与 PyPI / Skill / 插件三条分发线。
- 快速开始 —— 安装 CLI 与 Agent Skill，跑通从 plan 到 site 的标准生成流程与并发 worker 模式。
- 核心机制 —— 任务状态机与并发控制、任务规格与 zh/en 模板体系、页面校验与自动修复的实现。
- CLI 命令与实现 —— 规划扫描、worker 循环命令、增量更新与过期检测、知识卡片与 finalize、离线站点导出、skill 安装与 CLI 骨架六组命令的实现细节。
- 测试、CI 与设计决策 —— 13 个测试文件的组织、三条 GitHub Actions 流水线、15 条架构决策与领域术语表。

[本节为目录性说明，不直接分析具体文件，故无"章节来源"]

## 如何使用本 Wiki

新手路径：先读「项目概述」建立对定位与产出物形态的整体认识，然后按「快速开始」的「安装与 Agent Skill 安装」装好 CLI 与 skill，再用「标准生成流程」在自己关心的仓库上跑通第一次生成；遇到需要定制或排查的场景时，回到「核心机制」理解任务状态机与校验规则即可定位绝大多数问题。

贡献者与二次开发路径：直接从「核心机制」进入，掌握 state.py 的并发原语与 templates 的规格渲染后，按「CLI 命令与实现」逐组对照源码阅读；「测试套件」说明了每条机制对应的测试入口，「CI 与发布流水线」与「架构决策与术语」则给出修改代码后需要遵守的发版规则与既有决策边界。

[README.md:100-180](file://README.md#L100-L180)
[src/repowiki/skills/repowiki/SKILL.md:25-45](file://src/repowiki/skills/repowiki/SKILL.md#L25-L45)
