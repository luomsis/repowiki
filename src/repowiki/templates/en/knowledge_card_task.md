---
id: {{TASK_ID}}
kind: knowledge_card
phase: 2
title: 知识卡片：{{TITLE}}
output: {{OUTPUT}}
---

# Task: write the mechanism knowledge card "{{TITLE}}"

Write the card to: <b>{{OUTPUT_ABS}}</b> (repo-relative: {{OUTPUT}}).
**Write only this one file; the directory in the path was created by the tool.**

## Card metadata (YAML front matter, fill in every field)
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

## Card body structure (four numbered sections, headings must not change)
```markdown
# {{TITLE}}

## 1. System Overview

<One paragraph on the mechanism: which approach is used, what problem it solves, which parts it covers.>

- <3~5 key-point bullets: framework/layering/priorities/key syntax>

## 2. Key Files and Packages

- <file-group topic>
  - <path>: <this file's responsibility, one or two sentences>
  - <path>: <...>

## 3. Architecture and Design Conventions

- <convention topic>
  - <the concrete convention>

## 4. Rules for Developers

1. <situational rule (when to do what, what is forbidden)>
2. <...>
3. <...>
```

## Reference files (the card's core evidence — read them thoroughly)
{{SOURCE_FILES}}

## Requirements
- Everything comes from the real code; file paths are real; write in English, keeping technical nouns verbatim.
- "Rules for Developers" must be actionable conventions (when/where/do what/never do what), not slogans.
- 30~80 lines total is a good size.

While writing, run `repowiki touch <repo path> --task {{TASK_ID}}` every few minutes to renew your claim (long tasks are otherwise reclaimed).

When done run: `repowiki check <repo path> --task {{TASK_ID}}`
