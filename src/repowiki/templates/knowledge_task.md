---
id: knowledge-plan
kind: knowledge_plan
phase: 2
title: 知识库规划（modules + cards）
output: state/knowledge.json
---

# 任务：规划仓库知识库（模块树 + 机制卡片清单）

你的唯一产出是一个 JSON 文件：`.repowiki/state/knowledge.json`。
**不要写任何卡片或模块文档，不要改动仓库其他文件。**

## 仓库信息
- 仓库名：{{REPO_NAME}}
- 关键文件：{{KEY_FILES}}

## 仓库文件树（截断）
```
{{TREE_SUMMARY}}
```

## JSON Schema
```json
{
  "modules": [
    {
      "id": "m01",
      "title": "<模块标题（中文，可含英文专名）>",
      "scope": ["<该模块覆盖的仓库路径前缀，如 src/core/>"],
      "children": ["<子模块 id>"],
      "depends_on": ["<依赖的其他模块 id>"],
      "related_to": ["<相关模块 id>"]
    }
  ],
  "cards": [
    {
      "id": "k01",
      "title": "<卡片标题，如：配置系统 — YAML + pydantic-settings 分层加载>",
      "category": "configuration_system",
      "scope": ["**"],
      "source_files": ["<仓库相对路径>", "..."]
    }
  ]
}
```

## 规划规则
1. 模块 = 仓库中边界清晰的子系统/子项目（2~8 个为宜，可 1~2 层）。根模块覆盖仓库整体，子模块按 scope 路径划分。模块 id 顶层 m01…，子模块 m0101…；子模块需同时出现在父模块 children 与 modules 列表中。
2. 机制卡片聚焦横切机制，category 六选一：`configuration_system` / `logging_system` / `error_handling` / `build_system` / `dependency_management` / `frontend_style`。只为仓库中真实存在且值得记录的机制建卡（0~2 张/类，宁缺毋滥）。
3. 卡片标题自包含（机制 + 关键技术），全局唯一；source_files 是实现该机制的核心文件（2~8 个，必须真实存在）。
4. 卡片与模块相互独立：卡片描述「机制」，模块描述「结构」。

## 质量自检
- [ ] JSON 可解析；模块/卡片 id 与标题唯一
- [ ] children/depends_on/related_to 引用的 id 都存在
- [ ] scope 与 source_files 路径真实存在
- [ ] category 只用六个枚举值之一

完成后运行：`repowiki check <仓库路径> --task knowledge-plan`
