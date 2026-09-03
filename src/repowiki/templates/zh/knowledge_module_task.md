---
id: {{TASK_ID}}
kind: knowledge_module
phase: 2
title: 知识模块：{{TITLE}}
output: {{OUTPUT_DIR}}
---

# 任务：撰写知识模块文档「{{TITLE}}」

把以下文件写到目录 <b>{{OUTPUT_DIR_ABS}}</b>/ 下（相对仓库根：{{OUTPUT_DIR}}/）。
**只写这个目录内的文件。** `_module.yaml` 由工具自动生成，不要手写。

## 模块信息
- 标题：{{TITLE}}
- 覆盖范围（scope）：{{SCOPE}}
- 子模块：{{CHILDREN}}

## 需要撰写的文件（每个都是简短文档，中文行文、技术名词保留英文）
1. `概述.md` —— 一两句话说明该模块是什么、在仓库中的角色（示例风格：*以 graphiti_core Python 包为共享内核，通过 docker-compose 统一编排 REST server、MCP server、Next.js Web UI 三个运行时服务。*）
2. `技术栈.md` —— 一段话列出语言/框架/构建工具/存储等关键技术选型。
3. `架构设计.md` —— 3~6 条 bullet，说明内部结构与对外契约（调用链、编排入口、跨进程契约等）。
4. `特殊配置与命令.md` —— 一段话给出该模块特有的启动/构建/调试命令（没有则写「无特殊命令，见根目录 README」）。
5. `编码规范.md`（可选）—— 仅当模块内有明确一致的编码约定时写 3~5 条 bullet。

## 要求
- 先通读 scope 下的关键文件再撰写；内容必须与代码实际情况一致。
- 不使用标题层级（这些是片段文档，直接正文/bullet）。
- 篇幅克制：概述 1~2 句、技术栈 1~3 句、架构设计 3~6 条。

撰写期间每隔几分钟执行 `repowiki touch <仓库路径> --task {{TASK_ID}}` 续期认领（长任务防被回收）。

完成后运行：`repowiki check <仓库路径> --task {{TASK_ID}}`
