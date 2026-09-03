---
id: {{TASK_ID}}
kind: page
phase: 2
title: {{TITLE}}
output: {{OUTPUT}}
hint_files:
{{HINT_FILES_YAML}}
---

# Task: write the wiki page "{{TITLE}}"

Write the finished page to: <b>{{OUTPUT_ABS}}</b> (repo-relative: {{OUTPUT}}).
**Write only this one file; never modify repository sources or other wiki pages.**

## Page positioning
- Chapter path: {{CHAPTER_PATH}}
- Page summary: {{SUMMARY}}
- Points this page must cover (page_brief):
{{PAGE_BRIEF}}

## Reference files (read them before writing; cited line numbers must come from their real content)
{{HINT_FILES}}

## Sibling pages (other page titles under the same parent chapter — for orientation only; never link them)
{{SIBLINGS}}

## Page template (follow this skeleton strictly; replace <> placeholders with real content, keep the section order)
{{PAGE_TEMPLATE}}

## Style & diagram rules (mandatory)
{{STYLE}}

## Hard checks (the validator enforces each one; violations fail the task)
1. Exactly one H1, equal to "{{TITLE}}".
2. The `<cite>` block lists the files this page actually references (`[file name](file://repo-relative path)` format, 3~15 files).
3. The "Contents" anchors must match the real section headings (GitHub-style anchors: lowercase, punctuation dropped, spaces → `-`).
4. After the Introduction, every section ends with "Section sources"; every mermaid diagram is followed by "Diagram sources"; link format `[path:Lx-Ly](file://path#Lx-Ly)` with line numbers within the file's real length.
5. At least 2 mermaid diagrams (a structure diagram + a sequence/dependency diagram).
6. Beyond the required sections above you may add "Appendix: <topic>" sections as needed.
7. Never link any other page under `.repowiki/`.

While writing, run `repowiki touch <repo path> --task {{TASK_ID}}` every few minutes to renew your claim (long tasks are otherwise reclaimed).

When done run: `repowiki check <repo path> --task {{TASK_ID}}`
