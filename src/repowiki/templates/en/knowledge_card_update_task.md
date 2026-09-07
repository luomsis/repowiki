---
id: {{TASK_ID}}
kind: knowledge_card
phase: 2
title: Knowledge card: {{TITLE}} (incremental update)
output: {{OUTPUT}}
---

# Task: incrementally update the mechanism knowledge card "{{TITLE}}"

Rewrite the updated card **as a whole** to: <b>{{OUTPUT_ABS}}</b> (repo-relative: {{OUTPUT}}).
**Write this one file only; never touch repository sources or other knowledge outputs.**

## Files changed since last generation (the basis of this update; re-read their current content)
{{CHANGED_FILES}}

## The card's core reference files (re-read their current content)
{{SOURCE_FILES}}

## Current card in full (update on top of it; keep whatever is still correct)
```markdown
{{OLD_CARD}}
```

## Update rules
1. Fix outdated descriptions and file references against the changed files; keep unaffected sections as-is.
2. Append one section at the end of the body (fixed number and title, do not alter):

   ```markdown
   ## 5. Update Summary

   **Changed content**
   - <state concretely which part was updated because of which file change>
   ```

3. Keep the front matter fields (kind/name/category/scope/source_files, corrected to current reality).
4. Everything else — structure and style — is identical to first generation: the four numbered
   sections, H1 = "{{TITLE}}", repo-relative path references, zero page-to-page links,
   no emoji/tables.

## Hard checks
Front matter complete (kind/name/category/source_files, files must exist), all four numbered
sections present, "## 5. Update Summary" present, H1 = "{{TITLE}}", no unreplaced template
placeholders.

While writing, run `repowiki touch <repo> --task {{TASK_ID}}` every few minutes to renew
your claim (long tasks get reclaimed otherwise).

When done run: `repowiki check <repo> --task {{TASK_ID}}`
