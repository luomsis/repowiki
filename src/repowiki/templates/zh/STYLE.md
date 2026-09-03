# 文风与图表规范（所有页面必须遵循）

## 语言
- 正文简体中文；技术名词、类名、文件路径、配置键保留英文原文。
- 中文与英文/数字之间留一个空格（如「Python SDK 使用指南」「BM25 关键词搜索算法」）。
- 不使用 emoji。不使用表格（除非配置项清单确实需要）。

## 章节来源与图表来源（引用格式，强制）
- 每个正文章节末尾附「章节来源」列表；每个 mermaid 图后附「图表来源」列表。
- 链接格式（路径相对仓库根目录，统一正斜杠，行号区间不得超出文件实际行数）：
  - `[README.md:1-120](file://README.md#L1-L120)`
  - `[graphiti_core/graphiti.py:146-283](file://graphiti_core/graphiti.py#L146-L283)`
- 仅供整文件引用时可用 `[nodes.py](file://graphiti_core/nodes.py)` 形式（`<cite>` 块内）。
- 引用的文件必须是真实存在的仓库文件；禁止引用其他 wiki 页面（页间零链接）。
- 某节确无对应代码时写：`[本节为概念性说明，不直接分析具体文件，故无"章节来源"]`

## mermaid 图表风格
- 结构图用 `graph TB`，依赖/关系图用 `graph LR`，交互流程用 `sequenceDiagram`，类型关系可用 `classDiagram`。
- 节点标签必须用双引号包裹，长标签用 `<br/>` 换行并附英文关键名：

```mermaid
graph TB
subgraph "应用层"
REST["REST 服务<br/>FastAPI"]
WEB["Web 界面<br/>Next.js"]
end
subgraph "核心库"
CORE["核心引擎<br/>engine.py"]
end
REST --> CORE
WEB --> REST
```

- sequenceDiagram 的 participant 与消息也用引号包裹：

```mermaid
sequenceDiagram
participant Client as "客户端"
participant API as "REST 服务"
participant Core as "核心引擎"
Client->>API : "POST /api/xxx"
API->>Core : "调用核心方法"
Core-->>API : "结构化响应"
API-->>Client : "JSON 响应"
```

## 页面其他约定
- 一级标题（H1）必须且只能是页面标题；正文层级从 `##` 开始，子组件用 `###`。
- 「目录」小节为数字列表，锚点为 GitHub 风格中文锚点（小写、去标点、空格转 `-`，如 `附录：一键运行清单` → `#附录一键运行清单`）。
- 行文客观陈述，避免营销语气；结论小节给出一句话定位与使用建议。
