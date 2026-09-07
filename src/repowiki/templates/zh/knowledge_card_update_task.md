---
id: {{TASK_ID}}
kind: knowledge_card
phase: 2
title: 知识卡片：{{TITLE}}（增量更新）
output: {{OUTPUT}}
---

# 任务：增量更新机制知识卡片「{{TITLE}}」

把更新后的卡片**整体重写**到：<b>{{OUTPUT_ABS}}</b>（相对仓库根：{{OUTPUT}}）。
**只写这一个文件；不得改动仓库源码或其他知识产出。**

## 自上次生成以来变更的文件（本次更新的依据；请重读它们的当前内容）
{{CHANGED_FILES}}

## 卡片核心依据文件（务必重读当前内容）
{{SOURCE_FILES}}

## 当前卡片全文（在它基础上更新，保留仍然正确的部分）
```markdown
{{OLD_CARD}}
```

## 更新规则
1. 对照变更文件修正正文中过时的描述与文件引用；未受影响的小节尽量保持原样。
2. 在正文末尾追加一个小节（固定编号与标题，不可改）：

   ```markdown
   ## 5. 更新摘要

   **变更内容**
   - <具体说明哪部分内容因哪个文件变更而更新>
   ```

3. front matter 逐字段保留（kind/name/category/scope/source_files 按当前实际修正）。
4. 其余结构与文风与首次生成完全一致：固定四个编号小节、H1=「{{TITLE}}」、
   仓库相对路径引用、页间零链接、不用 emoji/表格。

## 硬性检查项
front matter 齐全（kind/name/category/source_files 且文件真实存在）、四个编号小节齐全、
「## 5. 更新摘要」存在、H1=「{{TITLE}}」、无未替换的模板占位符。

撰写期间每隔几分钟执行 `repowiki touch <仓库路径> --task {{TASK_ID}}` 续期认领（长任务防被回收）。

完成后运行：`repowiki check <仓库路径> --task {{TASK_ID}}`
