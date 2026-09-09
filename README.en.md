# repowiki

[中文](README.md) | **English**

[![CI](https://github.com/luomsis/repowiki/actions/workflows/ci.yml/badge.svg)](https://github.com/luomsis/repowiki/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/repowiki-cli)](https://pypi.org/project/repowiki-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python ≥ 3.10](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)](#reliability)

A build system that generates a structured wiki for any repository.

`repowiki` is a deterministic build system: it handles task planning, atomic claiming,
output validation, auto-repair, and metadata assembly. The intelligent work — reading
code, writing the wiki — is done by whatever agent drives it (Claude Code / Codex /
OpenCode or any agent CLI, or a human). Zero API keys, zero network calls, zero agent
CLI dependencies: any executor that "can run a shell and read/write files" can
participate — concurrently, too. The wiki's output language follows the target
repository automatically (Chinese repo → `zh/`, English repo → `en/`; `plan --locale`
overrides explicitly).

![repowiki system architecture](docs/assets/repowiki-architecture-en.png)

*Interactive version: [docs/repowiki-architecture-en.html](docs/repowiki-architecture-en.html) (light/dark themes · path highlighting · node search — download and open in a browser)*

**See it live**: repowiki's own wiki is published as an online sample →
**[open it here](https://luomsis.github.io/repowiki/zh/wiki.html)** (rebuilt
automatically on every push to main).

## Why repowiki

There are two well-trodden paths to a repo wiki today: cloud AI wiki services (your
code leaves the machine, pay per use, output is a black box), or letting one agent
read the whole repo and write it in one go (large repos don't fit in context, an
interruption throws everything away, and parallelism is hard to coordinate).
repowiki takes a third path: **the intelligence — reading code, writing the wiki —
stays with any agent you choose; everything else (task planning, atomic claiming,
output validation, auto-repair, crash recovery) is a deterministic build system.**

| | Cloud AI wiki service | One agent reads the repo | repowiki |
|---|---|---|---|
| Source of intelligence | Built-in LLM (fixed) | Your agent (any) | Your agent (any) |
| Code leaves your machine | Yes | No | No |
| API keys / network | Required | Depends on agent | repowiki itself needs none |
| Large repos | Vendor quota limits | Doesn't fit in context | Split into page-level tasks |
| Interruption / crash | — | Start over | State on disk, resume anytime |
| Parallel speedup | — | Hard to coordinate | Multi-worker atomic claims, parallel by design |
| Output quality | Black box | Agent's own discipline | Enforced templates + programmatic validation + auto-repair |

In one sentence: **the agent supplies the intelligence; repowiki supplies the
reliability.**

## Features

- **Deterministic orchestration**: plan / claim / check / auto-repair are all deterministic code — no API keys, no network calls, bound to no agent CLI;
- **Concurrency-safe, resumable**: atomic task claiming + heartbeat renewal + automatic stale-claim reclamation — multiple agents / processes / humans share one repo; per-task state is persisted, so interrupt anytime and pick up where you left off;
- **Incremental updates and CI gates**: `update` uses git diff to rewrite only affected pages; `stale --fail-if-stale` blocks PRs where "code changed, wiki didn't"; `coverage` lists the files the wiki never cites;
- **Single-file offline site + agent indexes**: `site` produces a self-contained ~5 MB HTML file (navigation, search, mermaid, source popups — double-click to view), and exports `llms.txt` / `llms-full.txt` (the [llmstxt.org](https://llmstxt.org/) convention) so any agent / IDE can read the wiki by index, no MCP required;
- **Strong validation, auto-repair**: enforced templates + programmatic validation; anchors, line ranges, H1s, and path separators are repaired programmatically — only semantic defects fail;
- **Bilingual, cross-platform**: output language follows the target repo (zh / en); native macOS / Linux / Windows support (no WSL needed), CI regression on a 3-platform × Python 3.10-3.13 matrix;
- **Knowledge cards and page archetypes**: mechanism cards / module docs with wholesale category customization (`--categories`); pages pick `module` (structural, default) or `flow` (process) templates by theme.

## Table of Contents

- [Why repowiki](#why-repowiki) · [Features](#features)
- [Install](#install) · [Viewing the Wiki](#viewing-the-wiki-single-file-offline-site) · [Command Reference](#command-reference)
- [Reliability](#reliability) · [Design Boundaries](#design-boundaries)
- [Contributing](#contributing) · [Community](#community) · [Documentation](#documentation) · [License](#license)

## Install

### 1. CLI (required; Python ≥ 3.10, macOS / Linux / Windows)

```bash
pip install repowiki-cli                # PyPI (only runtime dependency: pyyaml)
# or pipx install repowiki-cli; dev install: clone, then pip install -e .
repowiki --version                      # verify
```

### 2. Agent Skill (optional; lets an agent trigger the workflow automatically)

The skill files ship with the CLI; one command installs them:

```bash
repowiki skill install                  # default: ~/.agents/skills/repowiki/ (the shared global skills directory)
repowiki skill install --agent claude   # or a specific client (claude / codex / zcode / cursor / opencode)
repowiki skill status                   # check the installed version / staleness
```

You can also install this repo as a plugin (the `.claude-plugin/` manifest is detected
automatically), or manually copy `src/repowiki/skills/repowiki/` into your client's
skills directory. The skill is only a playbook (it tells the agent how to call the
CLI); the actual work is done by the `repowiki` command from step 1.

### 3. Offline installation

The only runtime dependency is `pyyaml`: on a networked machine, download a `PyYAML`
wheel plus the [`repowiki_cli-*.whl`](https://github.com/luomsis/repowiki/releases)
attached to the Release page, copy both to the target machine and
`pip install --no-index` them; the skill ships inside the whl, so afterwards run
`repowiki skill install` (a purely local copy). Full steps in
[docs/en/USAGE.md](docs/en/USAGE.md).

## Viewing the Wiki (single-file offline site)

The live sample linked above was produced by `repowiki site` and rebuilt on every
push to main.

![Reading view: section navigation + mermaid rendering + source references](docs/assets/site-preview-reading.png)

![Click a file:// source reference to inspect the line-numbered snippet in a popup](docs/assets/site-preview-snippet.png)

`repowiki site <repo> [--open]` packs the whole wiki into **one self-contained HTML
file** (`<repo>/.repowiki/<locale>/wiki.html`, roughly 5 MB):

- markdown + mermaid fully rendered; referenced source line ranges are embedded
  directly — click a `file://` reference to inspect the highlighted, line-numbered
  snippet in an in-page popup. No IDE, no network; send a colleague one file and they
  can browse the whole wiki;
- collapsible sidebar section navigation + on-page table of contents (scroll-spy
  highlighting), full-text search (hit highlighting), one-click code copy, prev/next
  paging, reading progress bar, dark/light theme (follows system + manual toggle);
- fully offline: the markdown/mermaid rendering libraries (marked/mermaid, MIT) are
  embedded in the file itself;
- idempotent: re-run `repowiki site` anytime after finalize, update, or manual edits;
- works even after `repowiki clean` (section order degrades to directory order;
  content is unaffected).

Pages are written in one of two archetypes, **module (structural, default) / flow
(process)**, with templates and style rules enforced by the validator per language;
each section ends with "Section sources", each diagram with "Diagram sources", in the
format `[path:Lx-Ly](file://path#Lx-Ly)`; zero cross-page links (which is exactly why
all page tasks can run fully in parallel). The full section layout lives in
[docs/en/USAGE.md](docs/en/USAGE.md).

## Command Reference

| Command | What it does |
|---|---|
| `plan <repo>` | Scan + generate the task list (output language auto-detected, `--locale` to override) |
| `next --claim` | Claim one ready task; `--json` includes full instructions |
| `check --task ID` | Validate outputs; anchors/line ranges/H1 auto-repaired |
| `finalize` | Assemble metadata.json (two passes: creates an overview task first) |
| `site` | Build the single-file offline site + llms.txt / llms-full.txt indexes |
| `update` / `stale` | git-diff incremental rewrite tasks / read-only staleness report (CI gate) |
| `skill install` / `status` | Install / inspect the agent skill |
| `status` / `clean` | Progress stats / wipe task state |

All 15 commands and every flag: `repowiki <command> --help` or
[docs/en/USAGE.md](docs/en/USAGE.md).
Exit codes: `0` success, `1` validation failure or usage error, `2` state conflict
(task claimed by someone else), `3` progress-pending wait (finalize created the
overview task; run finalize again once it completes).

## Reliability

- Atomic claiming (POSIX `fcntl` / Windows `msvcrt` file locks) + automatic stale
  reclamation: claims from crashed workers return to the queue with no manual release;
- Resumable: per-task state persists on disk; corrupted state files are reported
  loudly with the scene preserved — never a silent wipe of the task list;
- `watch` never fakes liveness: expired claims don't count as "executing", so a real
  stall is reported promptly instead of waiting out the timeout;
- Runtime artifacts are slimmed down automatically after finalize, keeping what
  incremental updates need.

Mechanism internals (staleness window tuning, `.stale-*` bookkeeping, heartbeat
semantics, the slim-down list) live in [docs/en/USAGE.md](docs/en/USAGE.md).

## Design Boundaries

- **Design trade-offs**: `metadata.json` contains only human-readable fields
  (catalogs/items/source_files/snippets/relations); runtime state stays in `state/`;
  ADR-style knowledge cards are not generated, while mechanism cards and module docs
  are fully supported; output languages are frozen to zh / en; CLI interaction
  messages are currently Chinese (aimed at the driving agent) and do not affect the
  wiki's output language.
- **Known limitations**: each task spec embeds the full template and style guide
  (about 4-6k tokens) — the price of self-contained, parallel-safe tasks;
  small-context agents can replace that section with a reference to the `templates/`
  directory; the output language is locked at plan time, switching requires
  `plan --replan`; `update` relies on the target repo's local git CLI
  (`git diff` / `git rev-parse`).
- **Non-Goals**: LLM API backends · built-in agent CLI detection/execution · MCP
  wrappers (the agent-reads-the-wiki need is met by the static `llms.txt` export) ·
  resident preview servers (the `site` artifact is a purely static single file) ·
  output languages beyond zh/en.

## Contributing

Issues and PRs are welcome! Local development:

```bash
git clone https://github.com/luomsis/repowiki.git && cd repowiki
pip install -e '.[test]'
pytest
```

- For behavior changes, open an issue or start a Discussions thread to align on
  direction before writing code.

## Community

- Questions, ideas, or want to show off a wiki you generated →
  [GitHub Discussions](https://github.com/luomsis/repowiki/discussions)
- Bugs and feature requests → [Issues](https://github.com/luomsis/repowiki/issues)

## Documentation

All docs are centralized under `docs/` (mirrored `zh/` and `en/` directories, same
file names in both):

- [Usage reference](docs/en/USAGE.md) ([中文](docs/zh/USAGE.md)) — full command reference, worker loop contract, concurrency recipes, reliability internals
- [Changelog](CHANGELOG.en.md) ([中文](CHANGELOG.md), at the repo root)
- [Domain glossary](docs/en/CONTEXT.md) (three term groups — artifacts /
  orchestration / execution — with Avoid lists)
- [Decision log](docs/en/DECISIONS.md) (15 minimal-reasonable decisions where the
  spec leaves blanks)
- Architecture decision records (ADRs): [dual lock backends for native Windows
  support](docs/en/adr/0001-windows-native-support.md) · [single-file offline
  site](docs/en/adr/0002-single-file-offline-site.md)
- Agent Skill playbook: [English](src/repowiki/skills/repowiki/SKILL.en.md) ·
  [中文](src/repowiki/skills/repowiki/SKILL.md)

## License

[MIT](LICENSE) © luomsis
