# 安装 repowiki 到全局技能

**现状**：全局技能目录为 `~/.agents/skills/<name>/SKILL.md`（现有 graphify 等 13 个技能），frontmatter 惯例为 `name` + `description` + `trigger: /<name>`（提供斜杠命令）。工具本体 `repowiki` CLI 已 `pip install -e` 全局可用，技能无需携带代码。

**步骤**：

1. **补全源仓库 SKILL.md 的 frontmatter**：在 `/Users/luoms/workspace/repowiki/SKILL.md` 的 frontmatter 中加入 `trigger: /repowiki`（与 graphify 等本地技能惯例一致），内容其余部分不动。
2. **安装**：创建 `~/.agents/skills/repowiki/`，把补全后的 SKILL.md 复制过去（保持与源仓库同一份内容，便于日后同步）。
3. **提交**：在 repowiki 仓库提交 frontmatter 变更（一笔小 commit）。

**验证**：`ls ~/.agents/skills/repowiki/` 存在且 frontmatter 完整；新会话中技能列表会出现 `repowiki`（含 `/repowiki` 触发词）。用户即可在任何会话中说「给某仓库生成 repowiki」或输入 `/repowiki` 触发。

**说明**：技能仅是「操作手册」——真正执行时依赖 `repowiki` CLI（已装在当前机器）。若换机器需先 `pip install -e` 工具仓库，此依赖已写在 SKILL.md 的「前置」小节中。
