---
id: overview
kind: overview
phase: 3
title: Wiki 总览（wiki_overview）
output: zh/meta/wiki-overview.md
---

# 任务：撰写仓库 Wiki 总览

把总览写到：<b>{{OUTPUT_ABS}}</b>（相对仓库根：{{OUTPUT}}）。
**只写这一个文件。** 它会被原样收入 `repowiki-metadata.json` 的 `wiki_overview` 字段。

## 输入
- 仓库：{{REPO_NAME}}
- 目录树（含每章子页标题与 page_brief）：

```
{{CATALOG_TREE}}
```

- 建议通读部分代表性页面（.qoder/repowiki/zh/content/ 下）后再动笔。

## 内容要求（纯 markdown，不要 YAML front matter）
1. 一级标题为「{{REPO_NAME}} Wiki 总览」。
2. 2~4 段仓库定位与核心价值概述（中文，客观陈述）。
3. 「章节导航」小节：按目录树逐章列出 `章节标题 —— 一句话说明`（bullet 列表，纯文本，不带链接）。
4. 「如何使用本 Wiki」小节：建议的阅读顺序（新手路径 vs 贡献者路径）。

## 文风
{{STYLE}}

完成后运行：`repowiki check <仓库路径> --task overview`
