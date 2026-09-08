# Changelog

[中文](CHANGELOG.md) | **English**

## 0.5.1 — 2026-09-08

### Fixed

- **Version detection adapted to the new distribution name**: after the rename to
  `repowiki-cli`, a clean install reported `repowiki --version` as 0.0.0 (the `__init__`
  metadata lookup still used the old name) — it now queries `repowiki-cli` first with a
  legacy-name fallback.

### Changed

- **PyPI distribution name set to [`repowiki-cli`](https://pypi.org/project/repowiki-cli/)**:
  the `repowiki` name on PyPI is taken by a same-purpose project (he-yufeng/RepoWiki).
  This changes nothing about usage — the command is still `repowiki` and the import
  package is still `repowiki`; after `pip install repowiki-cli` everything works as
  documented. Offline-install wheel filenames become `repowiki_cli-*.whl`.

## 0.5.0 — 2026-09-08

### Added

- **Page archetypes (module / flow)**: catalog page nodes gain an optional `archetype`
  field — process/mechanism-themed pages set `"archetype": "flow"` to use the flow
  template (Introduction / Flow Overview / Key Steps / Involved Components / Data and
  State Changes / Troubleshooting / Conclusion, with a sequence diagram + state graph);
  the default `module` keeps the original structural nine-section template. The validator
  enforces required sections per archetype, and the catalog task spec steers the planner.
- **`coverage` subcommand**: read-only coverage report — repository files never cited by
  any wiki page/overview/knowledge card, per-page citation density and zero-citation
  pages, all computed deterministically (the "provable quality" metric competitors
  cannot offer).
- **`--dirty` for `update`/`stale`**: by default only committed changes count
  (since..HEAD); `--dirty` adds uncommitted working-tree (staged + unstaged) and
  untracked changes — the wiki can catch up before you commit.
- **Overview page in incremental updates**: when `update` hits any page, it also queues
  an `overview-update` task (refreshes the positioning paragraphs and section
  navigation; no "Update Summary" section — validation keeps the overview shape).
- **Configurable knowledge-card categories**: `repowiki knowledge --categories <file>`
  replaces the built-in six with a YAML/JSON list (lowercase ids, ≤12 categories),
  persisted in `state/knowledge_categories.json` and enforced by check/update; without
  the flag behavior is unchanged (zero migration).
- **`llms.txt` / `llms-full.txt` export**: `repowiki site` now writes, alongside
  `wiki.html`, a chapter-organized link index (`llms.txt`) and a concatenated full-text
  companion (`llms-full.txt`), following the [llmstxt.org](https://llmstxt.org/)
  convention — any agent / IDE can consume the wiki by index, no MCP required.
- **Read-only `stale` subcommand**: `repowiki stale <repo> [--since <ref>] [--fail-if-stale]`
  — reuses `update`'s diff→affected-pages mapping (ancestor chains + knowledge linkage)
  to report which pages/cards/modules would go stale; creates no tasks, writes no state;
  `--fail-if-stale` exits 1 for CI gates.
- **Official GitHub Action (`wiki.yml`)**: on PRs, runs the stale gate automatically —
  comments the affected pages and blocks the merge when stale (deterministic check, no
  agent in CI); on push to main, rebuilds with `site` and publishes to GitHub Pages.
  Wiki-as-code mode: the repo tracks `.repowiki/` content/metadata/knowledge/llms
  indexes; `state/claims`, `state/tasks` and the rebuildable `wiki.html` are ignored.
- **Three site-UI reworks**: stronger H1/H2 hierarchy (H1 grows to 2em/800 and keeps the
  only full-width underline; H2 switches to accent-colored text with a 3px matching left
  bar); chapter navigation rebuilt (the chapter title itself is now a link to the
  chapter's index page in the accent color, all-caps dropped, and the dropdown no longer
  repeats the identically named index entry); the on-page TOC is collapsible and docks to
  the bottom of the sidebar when collapsed (the TOC panel's own styling is unchanged).
- **PyPI publishing ready**: pyproject now carries complete publishing metadata
  (readme / urls / keywords / classifiers); `pip install repowiki` becomes available
  after the first upload.

### Fixed

- Site UI: H1 and H2 previously shared foreground color + full-width underlines, making
  the visual hierarchy hard to tell apart (addressed by the three reworks above).

### Housekeeping

- The built-in knowledge category table moved to `DEFAULT_KNOWLEDGE_CATEGORIES`
  (with per-category guidance, tasks.py); the plan task spec now renders the category
  list via `{{CATEGORY_BLOCK}}` instead of hardcoding it in the template.

### Tests

- Tests 157 → 187: positive/negative and end-to-end coverage for the coverage report,
  staleness gate, `--dirty`, overview incremental refresh, custom knowledge categories,
  the flow archetype, and llms export.

### Documentation

- Added a competitive-analysis report
  (`docs/{zh,en}/research/competitive-analysis.md`: DeepWiki / DeepWiki-Open / CodeWiki /
  GitDiagram / Swimm / Repomix, with P0-P2 ranked improvements); DECISIONS gains #15
  (research conclusions and the adopted P0 direction) and #16 (P1 implementation
  trade-offs).
- Both READMEs: new "CI Integration" section, `stale`/`coverage` command rows, GitHub
  Pages live sample link, agent-consumption and page-archetype feature bullets; the
  overview-update limitation was removed from Known Limitations (now implemented).

## 0.4.0 — 2026-09-07

### Added

- Knowledge cards now cover the full lifecycle:
  - **update ↔ knowledge linkage**: `update` maps changed files against the knowledge plan — cards whose `source_files` changed and modules whose scope was touched each get an incremental refresh task (card updates carry a "## 5. Update Summary" section, enforced by `check` via `is_update`);
  - **site Knowledge Base chapter**: knowledge module docs and cards join `wiki.html` as regular pages under a dedicated nav chapter — searchable, with source popups and mermaid; card front matter is stripped for display;
  - **cross-epoch re-arm**: `update` regenerates specs of done `*-update` tasks from the previous round and resets them to pending — fixing the second update round silently doing nothing after a finalize.
- Knowledge YAML exports fill `source_files`: `_index.yaml` / `_module.yaml` collect the union of card source files falling under each module's scope (previously always empty).

### Fixed

- Removed unreachable dead code in `knowledge.py`.

## 0.3.3 — 2026-09-07

### Fixed

- **Site drawer menu button**: the topbar `#menu-btn` is a dead control on desktop,
  where the sidebar is always visible; it now only shows on narrow screens (≤900px).

### Documentation

- Replaced the ASCII architecture diagram on both README landing pages with drawn
  diagrams (Chinese diagram for the Chinese README, English one for the English
  README); added the interactive architecture HTML and specs
  (`docs/repowiki-architecture*.html`/`.json`, with light/dark themes, path
  highlighting, and node search).
- Softened the "no LLM" self-description: the README lead and features now say
  "deterministic build"; the package description, CLI `--help`, and module docstring
  follow suit.

## 0.3.2 — 2026-09-05

### Added

- Centralized bilingual docs: `docs/` restructured into `zh/` + `en/` mirrors (CONTEXT,
  DECISIONS, and the ADRs moved in), plus a full English `CHANGELOG.en.md` and `docs/en/**`;
  README and CHANGELOG stay at the root (the GitHub landing page and the Releases page
  render them from there).
- English README (`README.en.md`); README polish: badges, a "Why repowiki" comparison,
  Features, Usage, a Roadmap, Contributing, community links, and a table of contents.

### Fixed

- **Locale auto-detection prefers README.md**: `detect_locale` used to take the first
  entry of `sorted(glob("README*"))` — `README.en.md` sorts before `README.md`, so a
  bilingual repo's `plan --replan` misdetected the output language as en. README.md now
  wins when present; the remaining README* files are only a fallback.

## 0.3.1 — 2026-09-05

### Fixed

- **Windows CI compatibility** (pre-existing issue, fixed in the same window as the two
  entries below): test fixtures' `read_text`/`write_text` calls lacked an explicit
  `encoding="utf-8"`, so 10 cases raised UnicodeDecodeError/UnicodeEncodeError under
  Windows' default cp1252; reading index.json in `state.py` and the `os.replace` atomic
  swap raced in both directions on Windows (CPython opens files without
  FILE_SHARE_DELETE, so reading or writing either side hits PermissionError) — readers
  and writers now both go through `.index.lock` with a short retry on the swap-in; the
  missing-lock-backend test now masks both `fcntl` and `msvcrt` (it previously masked
  only the POSIX side, making the test a no-op on Windows).
- **`watch` false stall reports**: when a task happened to complete between the
  top-of-loop snapshot and the stall decision, `ready_tasks` was already empty and the
  run was misreported as "stalled" with exit 1 — the stall is now re-confirmed against
  fresh stats before being declared.
- **Catalog validation rejects placeholder titles**: `validate_catalog` errors when a
  node title contains `{{...}}`-shaped template placeholders. Previously such titles
  slipped all the way into task specs and page H1s (templates.render substitutes by
  key and keeps unknown placeholders verbatim, so `{{TITLE}}` was filled back in as a
  literal), while output validation then judged that literal in the H1 an "unreplaced
  placeholder" — the task was unsolvable from the moment its spec was generated (in
  practice one page task burned all its retries this way). Planning rule 3 in both the
  zh/en catalog task templates now states the ban explicitly.
- **Placeholder scanning targets non-code text only**: the three "still contains an
  unreplaced template placeholder" checks (page/card/overview) now strip fenced code
  blocks and inline code before scanning — when a doc page legitimately discusses the
  placeholder mechanism, literal `{{...}}` inside code is content, not a defect; leftover
  placeholders in prose still fail. The regex was renamed to the public
  `repowiki.validate.PLACEHOLDER_RE` for reuse by catalog.py.

### Changed

- **Site viewer (wiki.html) visual overhaul**: design-token system (Chinese-glyph font
  stack, h1-h6 type scale, radius/shadow tokens), code-block header bar (language tag +
  copy button), sidebar on-page TOC + scroll-spy highlighting + section collapsing,
  layered dark theme, table zebra striping, mermaid card containers, prev/next paging,
  reading progress bar, top-bar SVG icons and breadcrumbs, search hit highlighting, and
  `prefers-reduced-motion` / `:focus-visible` accessibility details. The payload
  structure and the single-file contract are unchanged (still exactly 4 inline scripts,
  zero external resources).

### Tests

- 2 new cases: catalog title containing a placeholder → error; placeholder inside a
  code block/inline code → passes. 149 tests green.

## 0.3.0 — 2026-09-04

### Added

- **Native Windows support**: concurrent state control switched to dual stdlib lock
  backends (POSIX `fcntl` / Windows `msvcrt.locking`), removing the "POSIX only, use
  WSL on Windows" runtime gate; fixed two `split("/")` calls in `tasks.py` that picked
  the wrong repo name for backslash paths; the CI matrix gained `windows-latest`
  (3.10-3.13 fully); SKILL.md gained the PowerShell equivalents (`Get-Command`,
  `Start-Process` background watch). Runtime dependencies unchanged (pyyaml only).
- **`repowiki site <repo> [--open]`: single-file offline viewing site**. Run after
  finalize; renders all pages into one self-contained HTML (`<locale>/wiki.html`,
  about 4-5 MB): marked + mermaid render libraries embedded (vendored into the repo and
  shipped with the wheel, MIT), `file://` source references open popups showing the
  embedded line-numbered snippets, sidebar navigation, client-side full-text search,
  dark/light themes. Idempotent and re-runnable; still rebuildable from the on-disk
  pages after `repowiki clean` (section order degrades to directory order). The README
  Non-Goals entry "HTML preview service" was reworded to "resident preview server".

### Fixed

- Two frontend defects in the site viewer (found in post-release smoke testing, fixed
  in this release): clicking an on-page "TOC" anchor triggered the hash router and fell
  back to the overview page — anchor hashes now only scroll and never switch pages;
  navigation highlighting misused `querySelector` so only the first link participated
  in highlight switching — switched to `querySelectorAll`.
- The plugin manifest `.claude-plugin/plugin.json` lagged at 0.1.0; synced to 0.3.0
  with pyproject.

### Docs

- Added a root-level `CONTEXT.md` glossary (domain terms in three groups: artifacts /
  orchestration / execution).
- Added `docs/adr/0001` (stdlib dual-lock-backend trade-off for native Windows support)
  and `docs/adr/0002` (single-file offline site: motivation for withdrawing the
  Non-Goal and the alternatives considered).
- README: platform statement covers all three platforms, new "Viewing the Wiki (single-
  file offline site)" section, `site` added to the command table, offline install notes
  that the pyyaml wheel must match the target platform (Windows included).

### Tests

- 14 new cases in `tests/test_site.py`: payload assembly and navigation tree (including
  a section's own page), source-snippet line-range extraction and missing markers,
  `</script>` escaping protection, idempotent rebuilds, locale isolation, degraded
  build after clean, `--open`/`--json` behavior; the missing-lock-backend case now
  verifies the friendly "both backends unavailable" error. 140 tests green.

## 0.2.0 — 2026-09-04

### Changed

- **Removed `next --batch` (breaking)**: the worker contract already forbids holding
  more than one claim at a time, so the flag was a speculative interface with no
  consumers. `next` now hands out exactly one task per call (`ready_tasks(limit=1)`),
  and README / SKILL.md / tests were updated to "each next hands out one task". Just
  delete `--batch N` from old scripts.
- CLI dispatch simplified: removed the 13-line `handlers` dict in `main` in favor of
  `set_defaults(func=cmd_*)` on each subparser + `main` calling `args.func(args, paths)`
  directly; `getattr(args, "json", False)` simplified to `args.json`.
- Added a shared git subprocess helper `src/repowiki/gitutil.py`
  (`run_git(repo, *args, timeout)`); the four ad-hoc subprocess wrappers in scanner /
  metadata / knowledge / updater converged into one place; failures uniformly return
  `None`, and empty output is distinguishable from failure (preserving update's
  "empty diff = no changes" semantics).
- `state.stats()` outputs `busy` directly (reusing the stale determination), unifying
  the busy accounting across `next` / `watch` / `status` into one source; `run_next` no
  longer loads index.json a second time.
- finalize's `state/catalog.json` went from up to 3 parses per run to 1; removed the
  dumps→loads→dumps round-trip in `_emit`.

### Cleanup (ponytail whole-repo audit, ~76 lines removed net)

- Deleted declared-but-unconsumed dead code: `templates.placeholders`,
  `Inventory.to_dict`, `FileEntry.size`, `WikiPaths.repo_rel`, the `snapshot` inside
  `run_watch`, `i18n.module_optional_files`, `FlatNode.dir`, the `validate.check_catalog`
  forwarding wrapper, metadata's dead `uuid`/`datetime`/`Path` imports, etc.;
  `_expand_knowledge` dropped its unused `inv` parameter.
- dispatch's plan-task expansion branch changed from a "`(plan_file, expand)` tuple" to
  an explicit `if tid == "catalog"` check; removed a redundant local import in
  `_check_readonly`.
- No behavior changes beyond `--batch` above; 126 tests green.

### Docs

- README gained an "Offline install" section: the only runtime dependency is pyyaml,
  with the full offline path via `pip download` staging + `pip install --no-index`, and
  how to manually copy the skill directory.

## 0.1.0 — 2026-09-03

First public release.

- Deterministic task orchestrator: `plan` / `next` / `check` / `touch` / `watch` /
  `release` / `finalize` / `update` / `knowledge` / `status` / `clean`.
- catalog → page → overview three-phase task flow with atomic claiming, stale-claim
  reclamation, resumability, and automatic slim-down after finalize.
- Output language follows the target repo automatically (zh/en: deterministic detection
  with the README weighted highest, `plan --locale` to force, persisted in
  `state/locale`); validators, templates, and knowledge cards ship as language-matched
  sets, extensible via string tables.
- Validator + deterministic auto-repair (anchors, line ranges, H1, path separators).
- git-diff-based incremental updates (page rewrites gain an "Update Summary" section).
- Knowledge-card task set (mechanism cards + module docs).
- Distributed as an Agent Skill (`skills/repowiki/SKILL.md`); the CLI installs via
  `pip install git+…`.

### Changed

- Removed third-party brand references; repositioned as a generic repository wiki
  generator; the scanner no longer special-cases the old third-party output directory.

### Fixed

- **Self-healing queue**: expired claims left behind by dead workers are automatically
  reclaimed and re-queued by `next --claim` (previously `ready_tasks` excluded all
  in_progress tasks, so dead claims could only be cleared by manual `release --force`;
  in practice this froze 25% of pages for 50 minutes); stale determination unified to
  the claim directory's mtime as the single source; `watch` no longer counts expired
  claims as "executing", so a stall is reported promptly once all workers die. Default
  stale window 45→15 minutes (tunable via `REPOWIKI_STALE_SECONDS`).
- SKILL.md orchestration hardening: explicitly forbids the main session assigning task
  lists to workers (global FIFO pure pull) and forbids workers pre-claiming tasks
  (hold only one claim at a time); adds background watch instructions and exit-code
  trustworthiness warnings; adds environment variable docs.
- A corrupted `state/index.json` is no longer silently treated as an empty task list
  (previously one transactional write-back could lose the whole list); the scene is now
  preserved with an explicit error, and `plan --replan --force` is the explicit
  recovery path.
- A corrupted `state/catalog.json` produces a friendly error on the finalize / update /
  overview validation paths instead of a bare traceback.
- Nonexistent task ids (touch / release) produce a friendly error with troubleshooting
  pointers.
- First run on non-POSIX platforms (Windows) after install shows an explicit platform
  notice instead of crashing on a bare `fcntl` import.
