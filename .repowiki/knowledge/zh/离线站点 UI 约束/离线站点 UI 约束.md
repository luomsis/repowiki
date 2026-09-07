---
kind: frontend_style
name: 离线站点 UI 约束
category: frontend_style
scope:
  - "src/repowiki/"
source_files:
  - src/repowiki/templates/site.html
  - src/repowiki/templates/site/app.js
  - src/repowiki/site.py
  - src/repowiki/templates.py
---

# 离线站点 UI 约束

## 1. 体系概览

`repowiki site` 的产物是一个零网络的自包含 HTML 站点，其 UI 由三处共担：`templates/site.html` 提供骨架与 design tokens 主题变量，`templates/site/app.js` 承担导航/搜索/主题切换/mermaid 初始化等运行时行为，`site.py` 负责把 payload 与 JS 安全注入骨架。所有视觉与交互改动都必须同时尊重这三层的既有约定——CSS 变量单一样式来源、断点化的抽屉侧栏、注入转义规则——否则就会出现「桌面端死控件」「主题丢变量」这类回归。

- 布局分区固定：topbar（进度条/菜单/面包屑/主题按钮）→ sidebar（可折叠章节导航）→ content → 页内目录栏 → pager → 页脚。
- 主题是 CSS 变量驱动的双主题，暗色变体与亮色一一对应，`color-scheme` 跟随系统。
- 注入面有四：`SITE_PAYLOAD` / `MARKED_JS` / `MERMAID_JS` / `APP_JS`，由 `templates.render` 替换。

## 2. 关键文件与包

- HTML 骨架与主题变量
  - [src/repowiki/templates/site.html:13-49](file://src/repowiki/templates/site.html#L13-L49)：`:root`（亮色）与 `[data-theme="dark"]`（暗色）两组 design tokens；[src/repowiki/templates/site.html:7](file://src/repowiki/templates/site.html#L7) 的 `<meta name="color-scheme" content="light dark">` 让原生控件跟随系统；[src/repowiki/templates/site.html:58](file://src/repowiki/templates/site.html#L58) 尊重 `prefers-reduced-motion`。
  - [src/repowiki/templates/site.html:74-76](file://src/repowiki/templates/site.html#L74-L76) 与 [src/repowiki/templates/site.html:298-300](file://src/repowiki/templates/site.html#L298-L300)：`#menu-btn` 抽屉开关默认隐藏、仅在 ≤900px 媒体查询内显示——桌面端侧栏常驻，按钮必须不是死控件。
- 运行时行为
  - [src/repowiki/templates/site/app.js:59-73](file://src/repowiki/templates/site/app.js#L59-L73)：nav 树两级渲染（章节按钮 + 子页链接），展开状态持久化 `localStorage("rw-nav")`；[src/repowiki/templates/site/app.js:283-309](file://src/repowiki/templates/site/app.js#L283-L309)：全文搜索与命中高亮。
- 注入与转义
  - [src/repowiki/site.py:357-375](file://src/repowiki/site.py#L357-L375)：payload JSON 全局把 `<` 转义为 `\u003c` 防 XSS；`_script_safe` 把内嵌 JS 里的 `</script` 改写为 `<\/script`，防止提前闭合 inline script 标签。
  - [src/repowiki/templates.py:20-27](file://src/repowiki/templates.py#L20-L27)：`{{PLACEHOLDER}}` 替换时未知占位符刻意原样保留，让校验器能兜底报告漏替换。

## 3. 架构与设计约定

- 样式单一样式来源：颜色/间距/阴影/圆角一律引用 CSS 变量 tokens，组件层不允许硬编码色值；暗色主题不是「再写一套样式」而是「补全 `--token` 的暗色取值」。
- 响应式断点 900px：桌面侧栏常驻（无需开关），窄屏侧栏抽屉化并靠 `#menu-btn` + backdrop 开合；新增顶栏控件必须声明自己在两个断点下的可见性与可用性。
- 内容与皮肤分离：`site.py` 只产出数据（payload）与转义后的 JS，不写样式；`site.html` 不含业务逻辑；`app.js` 只读 payload 渲染，保持「数据进、DOM 出」的方向。
- 主题切换走 `data-theme` 属性 + `localStorage` 持久化，mermaid 主题由 `app.js` 注入 `mermaid.initialize({ theme: ... })` 与 body 状态保持一致，禁止在 HTML 里写死浅色。
- 完全离线是硬约束：marked/mermaid 由 `vendor/*.js` 内嵌，任何新依赖必须同样进 vendor 并打进 `pyproject.toml` 的 package-data。

## 4. 开发者应遵循的规则

1. 改站点样式前先查 [src/repowiki/templates/site.html:13-49](file://src/repowiki/templates/site.html#L13-L49) 是否已有对应 token；新增视觉变量必须同时给出亮/暗两组取值，并在深浅两主题下目检。
2. 涉及 ≤900px 布局时，新增的顶栏/侧栏控件要么两个断点都可用，要么像 `#menu-btn` 一样显式声明单断点显示；禁止恢复「桌面显示但点了没反应」的控件。
3. 任何要内嵌进 `<script>` 的 JS 片段必须经 `_script_safe` 转义后再拼接；payload 新增字段保持 JSON 可序列化，转义由 `site.py` 统一处理，不要在模板里手工拼 HTML。
4. `app.js` 中改 DOM 选择器/结构时，同步核对 nav（两级结构）、搜索、toc spy、pager 四处的选择器常量；导航只支持「章节 → 子页」两级，新增层级需要先改渲染契约。
5. 每次改动后运行 `repowiki site` 重建产物，并在浅色/深色两种主题下各检查一次导航、搜索与源码弹层；`wiki.html` 是纯静态文件，双击即可验证。
