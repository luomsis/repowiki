---
id: {{TASK_ID}}
kind: overview
phase: 3
title: Wiki Overview (incremental update)
output: {{OUTPUT}}
---

# Task: incrementally refresh the repository wiki overview

Code has changed and the overview must follow. Write the refreshed overview to:
<b>{{OUTPUT_ABS}}</b> (repo-relative: {{OUTPUT}}).
**Rewrite only this file** (current content under "Current overview" below), keeping the
existing structure and length — do not start from scratch.

## Inputs
- Repository: {{REPO_NAME}}
- Files changed since the last generation:
```
{{CHANGED_FILES}}
```
- Current catalog tree (chapter/subpage titles with page_briefs; if sections were added
  or removed, "Section Navigation" must reflect it):

```
{{CATALOG_TREE}}
```

## Current overview (to refresh)
```
{{OLD_OVERVIEW}}
```

## Content requirements (plain markdown, no YAML front matter)
1. Keep the H1 as "{{REPO_NAME}} Wiki Overview".
2. Keep the existing paragraph structure: repo positioning & core value, `Section
   Navigation`, `How to Use This Wiki` — all three are required; modify only the parts
   the changes touch — added/removed sections must be reflected in "Section Navigation",
   major mechanism changes in the positioning paragraphs.
3. Do not add "Update Summary" or similar sections; the overview is not a page — keep it
   tight.
4. No YAML front matter, no cross-page links.

## Style
{{STYLE}}

While writing, run `repowiki touch <repo-path> --task {{TASK_ID}}` every few minutes to
renew your claim (prevents reclamation on long tasks).

When done run: `repowiki check <repo-path> --task {{TASK_ID}}`
