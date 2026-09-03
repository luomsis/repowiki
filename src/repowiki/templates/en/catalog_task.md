---
id: catalog
kind: catalog
phase: 1
title: Wiki 目录规划（catalog）
output: state/catalog.json
---

# Task: plan the wiki chapter tree for this repository

Your only output is one JSON file: `.repowiki/state/catalog.json` (relative to the repo root).
**Do not write any wiki pages; do not modify any other repository files.**

## Repository info
- Repo name: {{REPO_NAME}}
- Code files: {{CODE_FILE_COUNT}}
- Key files: {{KEY_FILES}}

## File tree (max 20 files per directory shown, truncated)
```
{{TREE_SUMMARY}}
```

## Code file list (valid dependent_files targets; truncated to {{FILE_LIST_COUNT}} entries)
```
{{FILE_LIST}}
```

## Output language
Write every human-readable field (`title`, `summary`, `page_brief`) in **English**, keeping proper nouns and technical terms verbatim. The wiki generated from this catalog will be in English.

## JSON Schema
```json
{
  "repo_name": "<repository name>",
  "chapters": [
    {
      "id": "c01",
      "title": "<chapter title (English, keep technical proper nouns)>",
      "slug": "<english-slug>",
      "summary": "<one-sentence English description>",
      "kind": "chapter",
      "dependent_files": ["<repo-relative path>"],
      "page_brief": "<points this index page must cover (English, 2-5 bullet-style items)>",
      "children": [
        { "id": "c0101", "title": "...", "slug": "...", "summary": "...", "kind": "page", "dependent_files": ["..."], "page_brief": "..." }
      ]
    }
  ]
}
```

## Planning rules (each is checked by the validator; violations fail the task)
1. Root-level `kind: "chapter"` = a chapter directory (12~18 for large repos, 4~8 topic-based for small ones — prefer precision over volume); root-level `kind: "page"` = a standalone top-level page (e.g. "Quick Start", "Contributing"), only when the repo actually has such content.
2. Tree depth ≤ 4 (root chapters are level 1). Only `kind: "chapter"` may have `children`; children are either `page` (leaf pages) or `chapter` (sub-directories, which must carry their own same-named index page).
3. **All node titles are globally unique**; ids are globally unique and hierarchical (c01, c0101, c010102…).
4. `dependent_files` may only reference paths that really exist in the list above; 3~12 files per page is a good range. A chapter index page cites the chapter's most representative files.
5. `page_brief` states the concrete points the page must cover — it becomes the prompt for the page-writing task, so be specific (which modules/classes/flows/configs).
6. Coverage expectations (mirroring wikis of comparable projects): project overview, quick start, core concepts, main features/SDK usage, configuration, deployment/operations, API reference, examples/contributing — trim to what this repository actually contains; do not force sections that do not apply.
7. `slug` is lowercase English and hyphens (e.g. `project-overview`, `quick-start`).

## Self-check (before writing the file)
- [ ] JSON parses (re-read the file after writing to confirm)
- [ ] Every title/slug/id globally unique, depth ≤ 4
- [ ] All dependent_files paths exist in the list above
- [ ] Chapters are split by topic, not mechanically by directory; every page has a concrete page_brief

When done run: `repowiki check <repo path> --task catalog`
