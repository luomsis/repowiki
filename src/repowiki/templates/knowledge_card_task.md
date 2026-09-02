---
id: {{TASK_ID}}
kind: knowledge_card
phase: 2
title: 知识卡片：{{TITLE}}
output: {{OUTPUT}}
---

# 任务：撰写机制知识卡片「{{TITLE}}」

把卡片写到：<b>{{OUTPUT_ABS}}</b>（相对仓库根：{{OUTPUT}}）。
**只写这一个文件；路径中的目录已由工具创建。**

## 卡片元数据（YAML front matter，逐字段填写）
```yaml
---
kind: {{CATEGORY}}
name: {{TITLE}}
category: {{CATEGORY}}
scope:
{{SCOPE_YAML}}
source_files:
{{SOURCE_FILES_YAML}}
---
```

## 卡片正文结构（固定四个编号小节，标题不可改）
```markdown
# {{TITLE}}

## 1. 体系概览

<一段话总述该机制：采用什么方案、解决什么问题、覆盖哪些部分。>

- <要点 bullet：框架/分层/优先级/关键语法等，3~5 条>

## 2. 关键文件与包

- <文件组主题>
  - <path>：<该文件承担的职责，一两句>
  - <path>：<...>

## 3. 架构与设计约定

- <约定主题>
  - <具体约定内容>

## 4. 开发者应遵循的规则

1. <场景化规则（何时做什么、禁止什么）>
2. <...>
3. <...>
```

## 参考文件（卡片的核心依据，务必通读）
{{SOURCE_FILES}}

## 要求
- 全部内容来自代码实况；文件路径真实；中文行文、技术名词保留英文。
- 「开发者应遵循的规则」必须是可执行的约定（何时/何地/做什么/禁止什么），不是口号。
- 篇幅 30~80 行为宜。

撰写期间每隔几分钟执行 `repowiki touch <仓库路径> --task {{TASK_ID}}` 续期认领（长任务防被回收）。

完成后运行：`repowiki check <仓库路径> --task {{TASK_ID}}`
