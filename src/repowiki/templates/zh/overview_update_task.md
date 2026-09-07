---
id: {{TASK_ID}}
kind: overview
phase: 3
title: Wiki 总览（增量更新）
output: {{OUTPUT}}
---

# 任务：增量刷新仓库 Wiki 总览

代码发生了变更，总览需要同步刷新。把更新后的总览写到：
<b>{{OUTPUT_ABS}}</b>（相对仓库根：{{OUTPUT}}）。
**只改写这一个文件**（旧内容见下方「当前总览」），保持整体结构与篇幅，不要推倒重写。

## 输入
- 仓库：{{REPO_NAME}}
- 自上次生成以来的变更文件：
```
{{CHANGED_FILES}}
```
- 当前目录树（含每章子页标题与 page_brief，若章节有增删需同步「章节导航」）：

```
{{CATALOG_TREE}}
```

## 当前总览（待刷新）
```
{{OLD_OVERVIEW}}
```

## 内容要求（纯 markdown，不要 YAML front matter）
1. 一级标题保持「{{REPO_NAME}} Wiki 总览」。
2. 沿用既有段落结构：仓库定位与核心价值概述、`章节导航`、`如何使用本 Wiki` 三部分缺一不可；
   仅在变更涉及的部分做修改——新增/删除章节要反映到「章节导航」，重大机制变化要反映到定位概述。
3. 不要添加「更新摘要」之类的小节；总览不是页面，保持紧凑。
4. 不要 YAML front matter，不要页间链接。

## 文风
{{STYLE}}

撰写期间每隔几分钟执行 `repowiki touch <仓库路径> --task {{TASK_ID}}` 续期认领（长任务防被回收）。

完成后运行：`repowiki check <仓库路径> --task {{TASK_ID}}`
