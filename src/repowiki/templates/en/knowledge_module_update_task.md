---
id: {{TASK_ID}}
kind: knowledge_module
phase: 2
title: Knowledge module: {{TITLE}} (incremental update)
output: {{OUTPUT_DIR}}
---

# Task: incrementally update the knowledge module docs "{{TITLE}}"

Module directory: <b>{{OUTPUT_DIR_ABS}}</b> (repo-relative: {{OUTPUT_DIR}}).
**Write only the three docs inside this directory; never touch repository sources or other knowledge outputs.**

## Module info
- Scope: {{SCOPE}}

## Files changed since last generation (only those falling inside the module scope; re-read their current content)
{{CHANGED_FILES}}

## Files to rewrite (each is a short doc, in English)
1. `overview.md` —— one or two sentences: what this module is and its role in the repository.
2. `tech-stack.md` —— one paragraph listing the key languages/frameworks/build tools/storages.
3. `architecture.md` —— 3~6 bullets on internal structure and external contracts (call chains, orchestration entry points, cross-process contracts).

## Update rules
1. Fix outdated descriptions against the changed files; docs unaffected by the changes may stay as-is (but must still exist and be non-empty).
2. Keep it tight: overview 1~2 sentences, tech stack 1~3 sentences, architecture 3~6 bullets.
3. Reference repository files by relative path; no emoji/tables.

## Hard checks
All three files (`overview.md`/`tech-stack.md`/`architecture.md`) exist and are non-empty.

While writing, run `repowiki touch <repo> --task {{TASK_ID}}` every few minutes to renew
your claim (long tasks get reclaimed otherwise).

When done run: `repowiki check <repo> --task {{TASK_ID}}`
