---
id: {{TASK_ID}}
kind: page
phase: 2
title: {{TITLE}}
output: {{OUTPUT}}
hint_files:
{{HINT_FILES_YAML}}
---

# 任务：撰写 Wiki 页面「{{TITLE}}」

把完成的页面写到：<b>{{OUTPUT_ABS}}</b>（相对仓库根：{{OUTPUT}}）。
**只写这一个文件；不得改动仓库源码或其他 wiki 页面。**

## 页面定位
- 章节路径：{{CHAPTER_PATH}}
- 页面摘要：{{SUMMARY}}
- 本页要点（page_brief）：
{{PAGE_BRIEF}}

## 参考文件（建议通读后再动笔；引用行号必须来自真实内容）
{{HINT_FILES}}

## 姊妹页面（同一父章节下的其他页面标题，仅供定位，禁止链接它们）
{{SIBLINGS}}

## 页面模板（严格遵循以下骨架；<> 占位内容替换为真实内容，小节顺序不可变）
{{PAGE_TEMPLATE}}

## 文风与图表规范（强制）
{{STYLE}}

## 硬性检查项（校验器会逐条检查，违例任务失败）
1. H1 必须且只能是「{{TITLE}}」。
2. `<cite>` 块内列出本文实际引用的文件（`[文件名](file://仓库相对路径)` 格式，3~15 个）。
3. 「目录」的锚点必须与实际章节标题对应（GitHub 中文锚点：去 `：` 等标点、空格转 `-`）。
4. 简介之后每个小节末尾都有「章节来源」；每个 mermaid 图后都有「图表来源」；链接格式 `[path:Lx-Ly](file://path#Lx-Ly)`，行号不得超出文件实际行数。
5. 至少 2 个 mermaid 图（结构图 + 时序/依赖图）。
6. 除模板列出的必备小节外，可按需增加「附录：<主题>」小节。
7. 禁止链接任何 `.repowiki/` 下的其他页面。

完成后运行：`repowiki check <仓库路径> --task {{TASK_ID}}`
