---
id: {{TASK_ID}}
kind: page_update
phase: 2
title: {{TITLE}}（增量更新）
output: {{OUTPUT}}
hint_files:
{{HINT_FILES_YAML}}
---

# Task: incrementally update the wiki page "{{TITLE}}"

Rewrite the full updated page to: <b>{{OUTPUT_ABS}}</b> (repo-relative: {{OUTPUT}}).
**Write only this one file; never modify repository sources or other wiki pages.**

## Files changed since the last generation (the basis of this update; re-read their current content)
{{CHANGED_FILES}}

## Points this page must cover (page_brief, still valid)
{{PAGE_BRIEF}}

## Current page in full (update on top of it; keep whatever is still correct)
```markdown
{{OLD_PAGE}}
```

## Update rules
1. Right after the `<cite>` block and before the table of contents, insert one section:

   ```markdown
   ## Update Summary

   **Changed content**
   - <state concretely which part was updated because of which file change, e.g.: API endpoint path updated, migrated from /old to /new>
   ```

2. Fix outdated descriptions, line ranges, and diagrams against the changed files; keep unaffected sections as-is.
3. Add an "Update Summary" entry to the "Contents" list (before "Introduction").
4. If there was a major improvement, you may append an `**Updated**` marker to the relevant item in the "Conclusion" section.
5. Everything else — structure, style, citation rules — is identical to first generation:

{{STYLE}}

## Hard checks
Same as first generation (H1 = "{{TITLE}}", all required sections present, "Update Summary" present, section/diagram source links real with line numbers in range, ≥2 mermaid diagrams, zero page-to-page links).

While writing, run `repowiki touch <repo path> --task {{TASK_ID}}` every few minutes to renew your claim (long tasks are otherwise reclaimed).

When done run: `repowiki check <repo path> --task {{TASK_ID}}`
