# Wiki 查看器：单文件离线 HTML，渲染库内嵌

v0.2.0 的 Non-Goals 明确排除"HTML 预览服务"。用户要求"给生成的文档加一个 web 页面方便查看"后，
我们选择在 `finalize` 之后用独立命令 `repowiki site` 生成**一个自包含 HTML 文件**
（`<locale>/wiki.html`）：全部页面、被引用的源码行区间、markdown 渲染库（marked）与
mermaid 渲染库全部内嵌进文件，浏览器双击即看，零服务器、零网络，单文件即可分享。
这一决定回撤了原 Non-Goal——排除的本意是"不做常驻服务"，静态单文件产物不违背该初衷，故 Non-Goals
改述为"不做常驻预览服务器"。

## Considered Options

- **本地服务器 `repowiki serve`**：体验更像"网站"，但终端需常驻、Windows 后台进程别扭，且产物不如单文件易分享；
- **Python 端渲染 markdown（如 mistune）**：产物更小，但新增运行时依赖，且 mermaid 仍需浏览器或 CDN，离线故事不完整；
- **CDN 引用渲染库**：零体积，但离线打开时 markdown/mermaid 无法渲染，与工具的离线安装定位冲突。

## Consequences

- 每个生成的 wiki.html 约 4-5 MB（内嵌 mermaid ~3.5 MB），对一个仓库的文档而言可接受；
  vendor 的 minified JS 提交进仓库并随 wheel 分发（见 `src/repowiki/vendor/README.md`）。
- 站点生成是纯派生产物：幂等、可随时重跑；`repowiki clean` 删掉 state 后仍能从磁盘页面重建
  （章节顺序退化为目录序）。
- 页面间刻意零链接的既定设计不变——站点导航由目录规划树派生，不依赖页间链接。
