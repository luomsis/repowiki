---
name: repowiki
description: Generate a structured repo wiki for any code repository (mermaid diagrams, file:// source references; output language follows the repo zh/en, overridable with --locale; after finalize, the site command builds a single-file offline HTML viewer; works on macOS/Linux/Windows). Use when the user asks to generate a repo wiki, "生成/更新 repowiki", "给仓库生成 wiki 文档", or mentions repowiki / repo wiki / 仓库文档. Works on any repo path; supports concurrent subagents.
---

[中文](SKILL.md) | **English**

# repowiki: generate a structured wiki for a repository

`repowiki` is a deterministic task orchestrator (no LLM): it plans tasks, validates
outputs, and assembles metadata. **You (the agent) do all the intelligent work**: read
the repository source and write the wiki pages per the task specs (output language
follows the target repo).

## Prerequisites

The `repowiki` CLI needs a one-time install (Python ≥ 3.10; native macOS/Linux/Windows):

```bash
pip install git+https://github.com/luomsis/repowiki.git   # or pipx install git+same-URL
# From a cloned checkout: cd repowiki && pip install -e .
```

Before executing, confirm the `repowiki` command is available (bash: `command -v repowiki`;
PowerShell: `Get-Command repowiki`); if not, install it first.
Shell commands in this document are bash syntax; PowerShell equivalents with identical
semantics are noted separately for Windows.

## Standard flow (serial)

For the target repo (below `<repo>`), run in order:

```bash
repowiki plan <repo>          # 1. scan + generate the task list (output language zh/en auto-detected; first task is the catalog)
repowiki next <repo> --claim --json   # 2. claim one task (read the returned instructions field)
#    3. execute per the task spec: read the hint_files source → write per the template → write to the spec's output path
repowiki check <repo> --task <id>     # 4. validate; on failure fix per errors and re-check
#    5. back to step 2, until next returns empty with busy=0
repowiki finalize <repo>      # 6. first run creates the overview task → execute it → finalize again to produce metadata.json
repowiki site <repo>          # 7. build the single-file offline site .repowiki/<locale>/wiki.html (--open opens the browser)
#    (finalize auto-cleans state/claims and state/tasks on success; catalog/index are kept for update)
#    if you don't need incremental updates, `repowiki clean <repo>` deletes all task state
```

After an incremental update or any post-finalize page rewrites, re-run
`repowiki site <repo>` anytime to rebuild the site (idempotent).

Task types: `catalog` (section-tree planning, produces state/catalog.json) → `page`
(one page each) → `overview`; optional: `repowiki knowledge <repo>` (knowledge cards),
`repowiki update <repo>` (git-diff-based incremental update; rewrites affected pages
with an "Update Summary" section).
The output language is decided at plan time (auto-detection weighted by the README, or
`--locale zh|en`), persisted in `state/locale`; the spec's template matches that
language.

## Concurrent flow (recommended; subagent speedup)

Once the catalog task completes, all page tasks are mutually independent and can run
safely in parallel:

1. The main agent completes `plan` + the catalog task (serial — the only prerequisite).
2. The main agent spawns N **equivalent** subagents running the same worker loop.
   **Never assign task IDs or task lists to workers**: the queue is a global FIFO and
   the division of work is decided entirely by `next`; the main agent only chooses the
   worker count and `--worker` names.
3. The worker loop (each subagent runs independently):

```
loop:
  1. run `repowiki next <repo> --claim --json --worker <name>`
  2. if tasks is empty and busy>0 → wait 30 seconds and retry (other workers are writing)
     if tasks is empty and busy=0 → done
  3. execute per tasks[0].instructions (write only the output file the instructions specify).
     Hold only one claim at a time: each next hands out exactly one task, and you must
     not call next --claim again before the current task completes;
     immediately after claiming, `repowiki touch <repo> --task <id> --worker <name>` once,
     then touch roughly every 3 minutes while writing (a claim un-renewed past the stale
     window is automatically reclaimed and handed to someone else)
  4. run `repowiki check <repo> --task <id> --worker <name> --json`
     - ok=true → back to 1
     - "claimed by someone else" conflict (exit 2) → that claim was reclaimed and taken
       over: don't fight it, don't add --force, back to 1
     - ok=false → fix the same file per errors and re-check (up to 3 times; if it still
       fails, `repowiki release <repo> --task <id> --force` and end this task)
```

Note: `check` must carry an explicit `--task` (or `--all` for crash recovery); done is
terminal and repeated checks are read-only state-wise; the first `finalize` exits with
code 3 (it created the overview task — normal progress).

4. The main agent runs watch. **It must genuinely run in the background with a generous
   `--timeout`** (set to expected total duration × 1.5):

   ```bash
   # bash / git-bash:
   nohup repowiki watch <repo> --interval 15 --timeout 7200 --json > watch.log 2>&1 &
   ```
   ```powershell
   # Windows PowerShell:
   Start-Process -WindowStyle Hidden -FilePath repowiki -ArgumentList "watch","<repo>","--interval","15","--timeout","7200","--json" -RedirectStandardOutput watch.log
   ```

   If watch is handed to a shell tool with its own timeout in the foreground, that
   timeout kills watch, and **a killed process's exit code is not trustworthy**
   (exit 0 may just be truncation; verify with `repowiki status` when in doubt).
   watch exits on its own: **exit 0** = everything done → run finalize (two passes:
   create overview → execute it → finalize again); **exit 1** = stall or timeout →
   inspect with `repowiki status <repo>` and intervene: reset exhausted poison tasks
   with `release --task <id> --force`; stale claims re-queue automatically (default
   15 minutes) and need no manual release — just confirm whether workers are alive and
   spawn replacements if needed.

## Environment variables

- `REPOWIKI_STALE_SECONDS`: claim expiry window (default 900 seconds = 15 minutes).
  After a worker dies, its task stays frozen at most this long before automatically
  re-queuing; workers with touch discipline are never wrongly preempted — usually no
  need to adjust.
- `REPOWIKI_MAX_ATTEMPTS`: max attempts per task (default 3); beyond that it becomes
  exhausted and needs `release --task <id> --force` to reset.

## Hard rules

- **Write only the output file the task spec specifies**; never modify repository
  source code.
- Pages follow the template and STYLE guide embedded in the spec: all required sections
  present, "Section sources" at the end of every section, "Diagram sources" after every
  mermaid diagram, `[path:Lx-Ly](file://path#Lx-Ly)` format, line numbers within bounds,
  zero cross-page links, no emoji/tables.
- Deterministic defects caught by `check` (anchors/line numbers/H1) are auto-repaired —
  no manual handling needed; only fix the semantic issues listed in `errors`.
- Output lives in `<repo>/.repowiki/` (`<locale>/content` pages, `<locale>/meta`
  metadata, `knowledge/<locale>/` knowledge cards, `<locale>/wiki.html` single-file
  viewer; locale was fixed at plan time).
