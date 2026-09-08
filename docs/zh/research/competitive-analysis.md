# 竞品调研与改进建议

**中文** | [English](../en/research/competitive-analysis.md)

> 调研日期：2026-09-07 · 版本基线：repowiki v0.4.0
> 方法：公开 README / 文档 / 论文 / 官方博客核对（来源见文末），未做逆向或付费实测。

## 结论（TL;DR）

「仓库 → wiki」赛道比直觉拥挤：商业上有 Cognition 的 DeepWiki（公开仓库免费托管，已索引数万仓库），
开源上有 17.9k stars 的 DeepWiki-Open 与 Google/FPT 背书、ACL 2026 论文附体的 CodeWiki。
它们全部走「内置 LLM → 云端服务或本地服务」路线；repowiki 的「确定性编排 + 智能外包给任意 agent +
代码不出本机」定位在开源界仍无人重合。**差距不在生成质量，在分发摩擦与生态接口**：
竞品一行命令/一个 URL 出结果、全部接入 MCP 与 CI 生态；repowiki 需要手动驱动 agent 循环、
安装靠 git URL、无任何 CI 集成。另有一个预警信号：CodeWiki 已支持「Claude Code / Codex CLI 作为
免 API key 后端」——与 repowiki 核心思路部分趋同，窗口期有限。

## 竞品全景

| 产品 | 形态 | 核心机制 | 与 repowiki 的关键差异 |
|---|---|---|---|
| [DeepWiki](https://deepwiki.com/)（Cognition） | 商业，公开仓库免费 | 内置 LLM + 预计算代码图 | Ask Devin 问答；Deep Research 深度研究模式；官方 [MCP server](https://docs.devin.ai/work-with-devin/deepwiki-mcp)（`read_wiki_structure` / `read_wiki_contents` / `ask_question`），任何 MCP agent 可调用 |
| [DeepWiki-Open](https://github.com/AsyncFuncAI/deepwiki-open)（17.9k★，MIT） | 开源自托管（Docker） | 内置 LLM + RAG | 多 provider（OpenAI / OpenRouter / Gemini / Ollama 本地）；与仓库对话的 RAG chat；已发布 2.0（Grok Wiki） |
| [CodeWiki](https://github.com/FSoft-AI4Code/CodeWiki)（FPT/Google，1.7k★，MIT，ACL 2026） | 开源 pip CLI | 层次化分解 + 递归多 agent | 10 种语言；声称支撑 1.4M LOC；自建 [CodeWikiBench](https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/) 且总分反超 DeepWiki（68.79% vs 64.06%）；**支持 Claude Code / Codex CLI 免 API key 后端**；`--update` 增量；MCP server；GitHub Pages viewer；按文档类型（api/architecture/user-guide/developer）生成 |
| [GitDiagram](https://github.com/ahmedkhaleel2004/gitdiagram) | 开源 + 免费托管 | 内置 LLM | 只做一张可点击架构图；GitHub URL 把 `hub` 换成 `diagram` 即用——零摩擦是它的全部卖点 |
| [Swimm](https://swimm.io/) | 商业 | 确定性 code-coupling + AI | 哲学与 repowiki 最近：文档锚定到具体代码片段，代码变更时**自动检测文档过期并在 CI 拦截**——「文档不过期」是核心卖点；IDE 插件 + AI chat |
| [Repomix](https://repomix.com/) / [Gitingest](https://gitingest.com/) | 开源 CLI / Web | 把仓库打包成 LLM 上下文 | 不生成 wiki，但用户群与 repowiki 高度重合：是「生成 wiki」的上游动作（先打包 → 再理解），天然互补/引流渠道 |

## 各竞品详评与启示

### DeepWiki（Cognition）——标杆与天花板

免费托管版覆盖数万公开仓库；卖点是「**可对话**的文档」：Ask 问答（Fast / Deep Research 两档）
把静态 wiki 变成研究入口；MCP server 让任何 agent（Claude Code、Cursor、Copilot…）把
「读某个仓库的 wiki / 问某个仓库的问题」变成一次工具调用。

**启示**：「让其他 agent 消费 wiki」是真实且被验证的需求。repowiki 的 Non-Goal 是不做 MCP 封装，
但同一需求可以用**静态文件**满足：`llms.txt` / `llms-full.txt` 是新兴的 agent 读取约定，
repowiki 的内容页本来就是 markdown，导出近零成本——这是对 MCP 非目标最优雅的回应。

### DeepWiki-Open——开源形态的对照组

证明了「自托管 + 自选模型」有大量需求（17.9k stars），但它仍要求：装 Docker、配 API key（或本地
Ollama）、接受产出不可验证。repowiki 在「产出可信、零密钥、单文件产物」上全面更优，
缺的只是它的「开箱即跑」——这也是 repowiki 上手摩擦的镜像。

### CodeWiki——最需要正视的对手

学术出身（ACL 2026，arXiv 2510.24428），工程形态与 repowiki 最接近：pip 安装、本地 CLI、
产出 markdown + mermaid、支持 GitHub Pages viewer、有增量 `--update --compare-to`。
两个动作值得警惕/借鉴：

1. **它已经做了「agent CLI 当后端」**：订阅模式下用本地 Claude Code / Codex CLI 驱动，免 API key——
   repowiki「智能外包」的差异点被部分覆盖。repowiki 仍领先的：多 worker 并发认领、断点续跑、
   程序化校验与自动修复、单文件离线站点、双语产出。
2. **它自带基准**（CodeWikiBench，21 仓库、分语言评分）：把「生成质量」变成可引用的数字，
   是极强的营销与迭代工具。repowiki 的确定性架构天然适合另一类指标：引用有效率、文件覆盖率、
   更新滞后——竞品做不到的「可证明的质量」。

### Swimm——确定性路线的商业先例

Swimm 用专利 code-coupling 把文档锚到代码，代码变了文档自动标记过期、CI 里拦截——
证明了「确定性保鲜」是有商业价值的独立卖点。repowiki 的 `update` 已有全部内部要件
（diff → `dependent_files` → 受影响页面），缺的只是一个只读的 CI 入口（见 P0-3）。

### GitDiagram / Repomix / Gitingest——摩擦力教员

GitDiagram 的全部产品就是「零摩擦」：改 URL 即出图。Repomix/Gitingest 把「给 LLM 喂仓库」
做成一行命令。共同启示：分发摩擦每降一级，用户量涨一个量级；repowiki 当前的
git-URL 安装 + 手动驱动循环是最大的漏斗瓶颈。

## repowiki 的差异化优势（应坚持）

- **agent 无关**：竞品全部锁死自家模型；「编排确定性 + 智能外包」没有第二个实现。
- **产出可信**：模板强制 + 程序化校验 + 自动修复 + `file://` 引用内嵌真实源码行。
- **并发安全 + 断点续跑 + 增量更新**：竞品仅有单进程、无中断恢复（CodeWiki 有增量，无并发调度）。
- **零依赖单文件离线站点、双语产出、3 系统 CI**：工程质量在同赛道开源中明显偏高。

## 改进建议

### P0 — 低成本、高杠杆、不越「非目标」红线（本轮采纳，见 DECISIONS #15）

1. **导出 `llms.txt` / `llms-full.txt`**：`site` 时按章节索引全部页面并合并全文，
   占住「wiki for agents」生态位——对 DeepWiki MCP 需求的静态文件回应。
2. **PyPI 就绪与发布**：补全 pyproject 元数据（readme/urls/classifiers）；
   `pip install repowiki-cli` / `uvx repowiki-cli` 是上手摩擦的最大单项。
3. **只读 `stale` 子命令 + 官方 GitHub Action**：`repowiki stale --since <ref>` 复用 update 的
   diff→受影响页面映射（不写 state），CI 里做「代码改了、wiki 过期」门禁（对标 Swimm）；
   push main 自动 `site` 重建并发布 GitHub Pages（在线样例）。
4. **在线样例**：把本仓库自产的 wiki 发布到 GitHub Pages 并在 README 挂链接
   （截图已有，缺一个「点开就看」的活样例）。

### P1 — 内容深度与质量度量（已实现，实现取舍见 DECISIONS #16；其中 CLI 双语仍留 roadmap）

5. **页面原型多样化**：每页同构的 9 段模板在大仓库不合适，拆 overview / module / flow 三种
   archetype，validator 按 archetype 分规则；借鉴 CodeWiki 按受众/文档类型选模板。
6. **知识卡片类别可配置**：解除 6 类机制卡片的硬编码天花板，允许用户自定义类别清单。
7. **`repowiki coverage` 报告**：确定性计算「从未被任何页面引用的源文件」与引用密度——
   竞品给不出的可证明质量指标。
8. **roadmap 低垂果实**：overview 页纳入增量更新；`update` 支持 `--dirty` 读未提交变更；
   CLI 交互消息双语。

### P2 — 战略选择题（需拍板，可能触碰非目标）

9. **问答层**：不做 RAG 是对的；克制做法是把「用你的 agent + llms.txt 提问」写成 recipe。
10. **MCP server**：DeepWiki / CodeWiki / Repomix 全都有，生态位压力真实；若破例，
    `next/check/status` 包成三个 MCP tool 即可。破例之前 llms.txt 是足够替代。
11. **大型 monorepo 实证**：挑 2-3 个知名大仓库公开战例，验证「并行分治」卖点。
12. **更多产出语言**（ja/ko）：表驱动设计下成本 = 一张字符串表 + 一套模板。

## 来源

- DeepWiki：<https://deepwiki.com/> · [Cognition 博客：DeepWiki MCP Server](https://cognition.com/blog/deepwiki-mcp-server) · [Devin 文档：DeepWiki MCP](https://docs.devin.ai/work-with-devin/deepwiki-mcp)
- DeepWiki-Open：<https://github.com/AsyncFuncAI/deepwiki-open>
- CodeWiki：<https://github.com/FSoft-AI4Code/CodeWiki> · [Google Developers Blog](https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/) · arXiv 2510.24428
- GitDiagram：<https://github.com/ahmedkhaleel2004/gitdiagram>
- Swimm：<https://swimm.io/>
- Repomix：<https://repomix.com/> · Gitingest：<https://gitingest.com/>
