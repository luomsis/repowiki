# Competitive Analysis & Improvement Proposals

[中文](../../zh/research/competitive-analysis.md) | **English**

> Research date: 2026-09-07 · Baseline: repowiki v0.4.0
> Method: public READMEs / docs / papers / official blogs (sources at the end); no reverse engineering or paid trials.

## TL;DR

The "repo → wiki" space is more crowded than intuition suggests: commercially, Cognition's
DeepWiki (free hosting for public repos, tens of thousands indexed); on the open-source side,
DeepWiki-Open (17.9k stars) and CodeWiki (Google/FPT-backed, ACL 2026 paper + benchmark).
All of them follow the "built-in LLM → cloud or self-hosted service" route; repowiki's position —
deterministic orchestration + intelligence outsourced to any agent + code never leaves the machine —
is still unmatched in open source. **The gap is not generation quality but distribution friction and
ecosystem interfaces**: competitors deliver with one command or one URL and all ship MCP and CI
integrations, while repowiki requires manually driving an agent loop, installs via git URL, and has
zero CI integration. One warning sign: CodeWiki already supports "Claude Code / Codex CLI as a
no-API-key backend" — partially converging with repowiki's core idea. The window is limited.

## Landscape

| Product | Form | Core mechanism | Key difference vs repowiki |
|---|---|---|---|
| [DeepWiki](https://deepwiki.com/) (Cognition) | Commercial, free for public repos | Built-in LLM + precomputed code graph | "Ask Devin" Q&A; Deep Research mode; official [MCP server](https://docs.devin.ai/work-with-devin/deepwiki-mcp) (`read_wiki_structure` / `read_wiki_contents` / `ask_question`) callable by any MCP agent |
| [DeepWiki-Open](https://github.com/AsyncFuncAI/deepwiki-open) (17.9k★, MIT) | OSS self-hosted (Docker) | Built-in LLM + RAG | Multiple providers (OpenAI / OpenRouter / Gemini / local Ollama); RAG chat with the repo; 2.0 released |
| [CodeWiki](https://github.com/FSoft-AI4Code/CodeWiki) (FPT/Google, 1.7k★, MIT, ACL 2026) | OSS pip CLI | Hierarchical decomposition + recursive multi-agent | 10 languages; claims up to 1.4M LOC; own [CodeWikiBench](https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/) beats DeepWiki overall (68.79% vs 64.06%); **Claude Code / Codex CLI no-API-key backends**; incremental `--update`; MCP server; GitHub Pages viewer; doc types (api/architecture/user-guide/developer) |
| [GitDiagram](https://github.com/ahmedkhaleel2004/gitdiagram) | OSS + free hosting | Built-in LLM | One clickable architecture diagram; swap `hub`→`diagram` in any GitHub URL — zero friction is the whole product |
| [Swimm](https://swimm.io/) | Commercial | Deterministic code-coupling + AI | Philosophically closest to repowiki: docs anchored to code snippets, **automatic staleness detection enforced in CI** when code changes — "docs that don't go stale" is the core pitch; IDE plugins + AI chat |
| [Repomix](https://repomix.com/) / [Gitingest](https://gitingest.com/) | OSS CLI / Web | Pack a repo into LLM context | Not wiki generators, but the upstream move ("pack first, understand next") with the exact same audience — natural partners/funnels |

## Detailed notes & lessons

### DeepWiki (Cognition) — the benchmark

Free hosted version covers tens of thousands of public repos; the pitch is **conversable
documentation**: Ask (Fast / Deep Research) turns a static wiki into a research entrance, and the
MCP server lets any agent (Claude Code, Cursor, Copilot…) consume "read a repo's wiki / ask a repo a
question" as one tool call.

**Lesson**: "let other agents consume the wiki" is a real, validated need. repowiki's non-goal is
wrapping an MCP server, but the same need can be met with **static files**: `llms.txt` /
`llms-full.txt` are an emerging agent-consumption convention, and repowiki's pages are already
markdown — export is nearly free. The most elegant answer to the MCP non-goal.

### DeepWiki-Open — the open-source control group

Proves massive demand for "self-hosted + bring your own model" (17.9k stars), yet it still requires
Docker, API keys (or local Ollama), and unverifiable output. repowiki wins on trustworthy output,
zero keys, and a single-file artifact; what it lacks is exactly DeepWiki-Open's "works out of the
box" — a mirror of repowiki's onboarding friction.

### CodeWiki — the competitor to take most seriously

Academic roots (ACL 2026, arXiv 2510.24428) but the engineering shape closest to repowiki: pip
install, local CLI, markdown + mermaid output, GitHub Pages viewer, incremental
`--update --compare-to`. Two moves matter:

1. **It already ships "agent CLI as backend"**: subscription mode drives local Claude Code / Codex
   CLIs with no API key — partially covering repowiki's "outsource the intelligence" differentiator.
   repowiki still leads on: multi-worker concurrent claiming, crash-safe resume, programmatic
   validation with auto-repair, single-file offline site, bilingual output.
2. **It ships a benchmark** (CodeWikiBench: 21 repos, per-language scores): turning "quality" into a
   citable number is powerful for marketing and iteration alike. repowiki's deterministic
   architecture is naturally suited to a different class of metrics — citation validity, file
   coverage, update latency — provable quality that LLM-pipeline competitors cannot offer.

### Swimm — the commercial precedent for the deterministic route

Swimm's patented code-coupling anchors docs to code; when code changes, docs are flagged stale and
CI enforces a gate — proof that "deterministic freshness" is a standalone, monetizable selling
point. repowiki's `update` already contains every internal piece (diff → `dependent_files` →
affected pages); it lacks only a read-only CI entrance (see P0-3).

### GitDiagram / Repomix / Gitingest — friction instructors

GitDiagram's entire product is zero friction: change the URL, get a diagram. Repomix/Gitingest made
"feed a repo to an LLM" a one-liner. Shared lesson: every notch of distribution friction removed is
an order of magnitude of users; repowiki's git-URL install + manually driven loop is the biggest
funnel bottleneck today.

## repowiki's durable advantages

- **Agent-agnostic**: every competitor locks in their own model; "deterministic orchestration +
  outsourced intelligence" has no second implementation.
- **Trustworthy output**: enforced templates + programmatic validation + auto-repair + `file://`
  citations embedding real source lines.
- **Concurrency-safe + crash-resumable + incremental**: competitors are single-process with no
  crash recovery (CodeWiki has incremental, none has concurrent scheduling).
- **Zero-dependency single-file offline site, bilingual output, 3-OS CI**: engineering quality
  clearly above peers in this niche.

## Improvement proposals

### P0 — low cost, high leverage, no non-goal crossed (adopted this round; see DECISIONS #15)

1. **Export `llms.txt` / `llms-full.txt`**: index all pages by chapter and concatenate full text
   during `site`, claiming the "wiki for agents" niche — a static-file answer to the DeepWiki MCP
   need.
2. **PyPI readiness & publishing**: complete pyproject metadata (readme/urls/classifiers);
   `pip install repowiki` / `uvx repowiki` is the single biggest onboarding win.
3. **Read-only `stale` subcommand + official GitHub Action**: `repowiki stale --since <ref>` reuses
   update's diff→affected-pages mapping (writes no state) as a CI gate for "code changed, wiki
   stale" (à la Swimm); on push to main, rebuild with `site` and publish to GitHub Pages (live
   sample).
4. **Live sample**: publish this repo's self-generated wiki to GitHub Pages and link it from the
   README (screenshots exist; what's missing is a "click and see" artifact).

### P1 — content depth & quality metrics (implemented; trade-offs in DECISIONS #16; bilingual CLI messages remain on the roadmap)

5. **Page archetypes**: the identical 9-section template fits large repos poorly; split into
   overview / module / flow archetypes with per-archetype validator rules; consider
   audience/doc-type template variants à la CodeWiki.
6. **Configurable knowledge-card categories**: lift the hard-coded 6-category ceiling; let users
   supply custom category lists.
7. **`repowiki coverage` report**: deterministically compute "source files never cited by any page"
   and citation density — provable quality competitors cannot offer.
8. **Roadmap low-hanging fruit**: include the overview page in incremental updates; `update --dirty`
   for uncommitted changes; bilingual CLI messages.

### P2 — strategic choices (need a decision; may cross non-goals)

9. **Q&A layer**: skipping RAG is right; the restrained move is a documented recipe of "your agent +
   llms.txt".
10. **MCP server**: DeepWiki, CodeWiki and Repomix all ship one; the ecosystem pressure is real. If
    ever crossed, wrapping `next/check/status` as three MCP tools is enough. Until then llms.txt
    suffices.
11. **Large-monorepo evidence**: run 2-3 famous large repos and publish the results to back the
    "parallel divide-and-conquer" claim.
12. **More output languages** (ja/ko): with the table-driven design, cost = one string table + one
    template set.

## Sources

- DeepWiki: <https://deepwiki.com/> · [Cognition blog: DeepWiki MCP Server](https://cognition.com/blog/deepwiki-mcp-server) · [Devin docs: DeepWiki MCP](https://docs.devin.ai/work-with-devin/deepwiki-mcp)
- DeepWiki-Open: <https://github.com/AsyncFuncAI/deepwiki-open>
- CodeWiki: <https://github.com/FSoft-AI4Code/CodeWiki> · [Google Developers Blog](https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/) · arXiv 2510.24428
- GitDiagram: <https://github.com/ahmedkhaleel2004/gitdiagram>
- Swimm: <https://swimm.io/>
- Repomix: <https://repomix.com/> · Gitingest: <https://gitingest.com/>
