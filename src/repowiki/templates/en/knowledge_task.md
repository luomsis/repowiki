---
id: knowledge-plan
kind: knowledge_plan
phase: 2
title: 知识库规划（modules + cards）
output: state/knowledge.json
---

# Task: plan the repository knowledge base (module tree + mechanism card list)

Your only output is one JSON file: `.repowiki/state/knowledge.json`.
**Do not write any cards or module docs; do not modify any other repository files.**

## Repository info
- Repo name: {{REPO_NAME}}
- Key files: {{KEY_FILES}}

## File tree (truncated)
```
{{TREE_SUMMARY}}
```

## Output language
Write every human-readable field (`title`) in **English**, keeping technical proper nouns verbatim.

## JSON Schema
```json
{
  "modules": [
    {
      "id": "m01",
      "title": "<module title (English, may contain technical proper nouns)>",
      "scope": ["<repo path prefix this module covers, e.g. src/core/>"],
      "children": ["<child module id>"],
      "depends_on": ["<other module id this depends on>"],
      "related_to": ["<related module id>"]
    }
  ],
  "cards": [
    {
      "id": "k01",
      "title": "<card title, e.g.: Configuration system — layered YAML + pydantic-settings loading>",
      "category": "configuration_system",
      "scope": ["**"],
      "source_files": ["<repo-relative path>", "..."]
    }
  ]
}
```

## Planning rules
1. Modules = clearly bounded subsystems/sub-packages of the repository (2~8 is a good range, 1~2 levels). The root module covers the whole repository; sub-modules divide by scope path. Root ids m01…, sub-ids m0101…; a sub-module appears both in its parent's `children` and in the top-level `modules` list.
2. Mechanism cards capture cross-cutting mechanisms; `category` is one of six: `configuration_system` / `logging_system` / `error_handling` / `build_system` / `dependency_management` / `frontend_style`. Only create cards for mechanisms that really exist and are worth documenting (0~2 per category; prefer fewer, better ones).
3. Card titles are self-contained (mechanism + key technology) and globally unique; `source_files` are the core files implementing the mechanism (2~8, must really exist).
4. Cards and modules are independent: cards describe "mechanisms", modules describe "structure".

## Self-check
- [ ] JSON parses; module/card ids and titles unique
- [ ] every id referenced by children/depends_on/related_to exists
- [ ] scope and source_files paths really exist
- [ ] category uses only the six enum values

When done run: `repowiki check <repo path> --task knowledge-plan`
