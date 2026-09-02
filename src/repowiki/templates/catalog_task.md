---
id: catalog
kind: catalog
phase: 1
title: 目录规划（catalog）
output: state/catalog.json
---

# 任务：为仓库规划 Wiki 目录树

你的唯一产出是一个 JSON 文件：`.qoder/repowiki/state/catalog.json`（相对仓库根目录）。
**不要写任何 wiki 页面，不要改动仓库其他文件。**

## 仓库信息
- 仓库名：{{REPO_NAME}}
- 代码文件数：{{CODE_FILE_COUNT}}
- 关键文件：{{KEY_FILES}}

## 仓库文件树（每目录最多展示 20 个文件，已截断）
```
{{TREE_SUMMARY}}
```

## 代码文件清单（可作 dependent_files 引用；已截断至 {{FILE_LIST_COUNT}} 条）
```
{{FILE_LIST}}
```

## JSON Schema
```json
{
  "repo_name": "<仓库名>",
  "chapters": [
    {
      "id": "c01",
      "title": "<章节标题（简体中文，专有名词保留英文）>",
      "slug": "<english-slug>",
      "summary": "<一句话中文描述>",
      "kind": "chapter",
      "dependent_files": ["<仓库相对路径>"],
      "page_brief": "<该索引页应涵盖的要点（中文 bullet 式描述，2-5 条）>",
      "children": [
        { "id": "c0101", "title": "...", "slug": "...", "summary": "...", "kind": "page", "dependent_files": ["..."], "page_brief": "..." }
      ]
    }
  ]
}
```

## 规划规则（校验器将逐条检查，违例会导致任务失败）
1. 根级 `kind: "chapter"` 表示一个章节目录（大型仓库 12~18 个为宜，小仓库按主题 4~8 个即可，宁精勿滥）；根级 `kind: "page"` 表示顶级独立页面（如「快速开始」「贡献指南」，仅在仓库确有对应内容时创建）。
2. 树深度 ≤ 4（根章节为第 1 层）。只有 `kind: "chapter"` 可以有 `children`；子节点既可以是 `page`（叶子页面）也可以是 `chapter`（子章节目录，需自带一个同名索引页）。
3. **所有节点的 title 全局唯一**；id 全局唯一且体现层级（c01、c0101、c010102…）。
4. `dependent_files` 只能引用上面清单中真实存在的路径；每个页面 3~12 个文件为宜。索引页的 dependent_files 取该章最具代表性的文件。
5. `page_brief` 用中文写明该页要覆盖的内容要点——它会成为页面撰写任务的提示词，务必具体（覆盖哪些模块/类/流程/配置）。
6. 覆盖面要求（参照同类型项目的 wiki 结构）：项目概述、快速开始、核心概念、主要功能/SDK 使用、配置、部署运维、API 参考、示例/贡献指南等——按本仓库实际情况裁剪，不生搬硬套。
7. `slug` 为小写英文与连字符（如 `project-overview`、`quick-start`）。

## 质量自检（写文件前自查）
- [ ] JSON 可被解析（建议写完后重新读一遍确认）
- [ ] 每个 title/slug/id 全局唯一，深度 ≤ 4
- [ ] 所有 dependent_files 路径存在于上面清单
- [ ] 章节划分按「主题」而非机械按目录；每页有具体的 page_brief

完成后运行：`repowiki check <仓库路径> --task catalog`
