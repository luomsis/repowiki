---
id: overview
kind: overview
phase: 3
title: Wiki 总览（wiki_overview）
output: {{OUTPUT}}
---

# Task: write the repository wiki overview

Write the overview to: <b>{{OUTPUT_ABS}}</b> (repo-relative: {{OUTPUT}}).
**Write only this one file.** It is embedded verbatim as the `wiki_overview` field of `repowiki-metadata.json`.

## Inputs
- Repository: {{REPO_NAME}}
- Chapter tree (each chapter's page titles and page_briefs):

```
{{CATALOG_TREE}}
```

- Skim a few representative pages (under `.repowiki/{{LOCALE}}/content/`) before writing.

## Content requirements (plain markdown, no YAML front matter)
1. The H1 is "{{REPO_NAME}} Wiki Overview".
2. 2~4 paragraphs on the repository's positioning and core value (objective tone).
3. A "Section Navigation" section: for each chapter in the tree, `chapter title —— one-sentence description` (bullet list, plain text, no links).
4. A "How to Use This Wiki" section: suggested reading order (newcomer path vs contributor path).

## Style
{{STYLE}}

While writing, run `repowiki touch <repo path> --task {{TASK_ID}}` every few minutes to renew your claim (long tasks are otherwise reclaimed).

When done run: `repowiki check <repo path> --task overview`
