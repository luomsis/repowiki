# DECISIONS.md — minimal-reasonable decisions made where the spec was silent

[中文](../zh/DECISIONS.md) | **English**

(Plan Agent Execution Rule #6: never invent where the spec is silent; record it here.)

1. **Module split**: the plan listed only `tasks.py`; during implementation the plan
   command's orchestration was split into `plan.py` and the next/check/release/status
   orchestration into `dispatch.py` — keeping tasks.py (spec generation) decoupled from
   the command layer.
2. **busy signal**: the `next` response gained a `busy` field (count of in-progress
   tasks). The spec only said "exit when there are no tasks", which made workers exit
   early while others were still executing, leaving later tasks unclaimed (exposed by
   the T5 race unit test). The worker contract became "empty and busy>0 → wait and
   retry".
3. **Claim expiry**: judged by the claim directory's own mtime, not an internal ts file —
   ts is written after mkdir, and in that window a fresh claim would be judged
   infinitely old and get preempted (a real race bug caught by the concurrency tests).
4. **In-spec title pre-rendering**: `{{TITLE}}` in the page template embedded in page
   task specs is pre-rendered to the real title, guarding against agents forgetting the
   substitution (exposed by the T9 smoke test).
5. **Anchor algorithm**: GitHub's rule is "strip punctuation, whitespace → -", not
   "punctuation also → -" — the correct anchor for `附录：一键` is `附录一键`, not
   `附录-一键` (exposed by a unit test).
6. **Catalog task idempotency**: `plan` no longer creates a catalog task when a valid
   catalog.json already exists (page tasks expand directly); `--replan` clears and
   restarts. This is the "catalog review loop" entry point added during review: a
   human/agent can edit state/catalog.json directly and re-run plan.
7. **Two-pass finalize**: the first finalize creates the phase-3 overview task and exits
   with code 3 (progress-pending, not an error); only after the agent writes the
   overview and it checks done does the second finalize write metadata.json.
8. **Section-count guidance**: the catalog task spec's root section count became
   "large repos 12~18, small repos 4~8, prefer precision over volume" (the T9 smoke run
   on a 10-file repo showed the original wording induced over-generation).
9. **Attempt counting**: every claim does attempts+1 (including the first); ready
   sorting is attempts ascending — failed tasks don't cut in line, new tasks go first,
   preventing one bad task from starving workers.
10. **State cleanup policy**: after finalize succeeds, runtime artifacts (claims/,
    tasks/) are cleared automatically while index.json/catalog.json/knowledge.json are
    kept — update's incremental mapping depends on catalog.json's dependent_files and
    tree structure (metadata has no kind field, so page paths can't be rebuilt from it),
    and index.json backs idempotent plan and status. A `clean` command deletes all of
    state/ (not the wiki itself) for those who don't need incremental updates.
11. **Lifecycle guards (P0/P1 review fixes)**: the `touch` heartbeat command + check
    renewing the claim along the way (prevents takeover and double-writes mid-execution);
    done is terminal and repeated checks are read-only (with specs cleaned up, flipping
    a done task to failed would create a task with no spec to execute); failed tasks
    past REPOWIKI_MAX_ATTEMPTS become exhausted and need `release --force` to reset
    (poison tasks must not spin workers forever); check requires an explicit
    `--task`/`--all` and verifies claim ownership (prevents cross-worker misuse);
    index.json uses flock to serialize read-modify-write (mtime re-checks have a
    TOCTOU window; the 6×12 stress test lost 3 updates); finalize verifies page
    existence (a `--max-pages` trial run no longer produces ghost entries) and signals
    progress with exit code 3 on first run; replan requires --force while tasks are
    in_progress.
12. **Automatic stale-claim reclamation**: practice (a 40-page concurrent run where one
    worker's exit left 15 claims freezing the queue for 50 minutes) showed the
    preemption path in `_try_mkdir_claim` was unreachable through the CLI —
    `ready_tasks` excluded in_progress entirely, so dead workers' claims could only be
    cleared by manual `release --force`. Fix: `ready_tasks` includes "in_progress with
    an expired claim", and `next --claim` reclaims via the existing preemption path
    (renamed `.stale-*` for the record, attempts+1, poison-task caps as usual); stale
    determination unified to the claim directory's mtime as the single source (the old
    stats() second determination based on index.heartbeat_at is retired, avoiding
    conflict between sweep and busy accounting); watch's in_flight also excludes
    expired claims (otherwise the stall branch is unreachable when all workers die,
    and one just waits out the timeout). Default stale window 45→15 minutes: the
    balance between the freeze ceiling and wrongful-takeover risk (no wrong takeovers
    as long as workers keep touch discipline).
13. **No pid liveness detection**: repowiki is a short-lived CLI process; a pid recorded
    at claim time is meaningless once the command exits and cannot serve as a liveness
    signal. The liveness signal is the voluntary `touch` heartbeat, and the expiry
    window is the only reclamation delay for a dead process. `next` also gains no
    `--task`: the queue stays a pure FIFO pull; by-ID operations belong to
    `check --task`/`release --task` — by-ID claiming would tempt the main session to
    assign task lists to workers, the exact root of the claim chaos seen in practice.
14. **Placeholder scanning targets non-code text only**: while generating repowiki's
    own wiki, one page's topic is the placeholder mechanism, so literal `{{TITLE}}` in
    body code was judged "unreplaced placeholder" — an unsolvable task (the H1 rule and
    the check rule were mutually exclusive). The fix has two layers: catalog validation
    rejects titles containing placeholder shapes (at the source — titles go into page
    H1s and output paths); output validation's placeholder scan strips fenced code
    blocks and inline code first (leftovers in prose still fail). "Showing a
    placeholder literal inside code" is legitimate content; "leaving a placeholder in
    prose" is the defect.
15. **Competitive research on record & P0 direction adopted** (2026-09-07; full study in
    [research/competitive-analysis.md](research/competitive-analysis.md)): after comparing
    DeepWiki / DeepWiki-Open / CodeWiki / GitDiagram / Swimm / Repomix, the gap is judged to be
    distribution friction and ecosystem interfaces rather than generation quality. Four P0 items
    adopted: `site` exports `llms.txt` / `llms-full.txt` (satisfying "let other agents consume the
    wiki" with static files, without crossing the MCP non-goal); pyproject metadata completed for a
    future PyPI publish (the upload itself needs a maintainer account and happens separately); a
    read-only `stale` subcommand + GitHub Action (PR wiki-staleness gate + Pages publishing —
    targeting Swimm's "docs that don't go stale" pitch, fully deterministic, no agent in CI, writes
    no state). P1 (page archetypes, configurable knowledge-card categories, coverage report) is
    queued for the next version; P2 (Q&A layer, MCP, large-monorepo evidence) awaits a decision.
16. **Implementation trade-offs for the four P1 content-depth items** (2026-09-08):
    ① **Page archetypes** are declared by an optional `archetype` field on catalog nodes
    (`module` default / `flow` for process-mechanism pages); the catalog task spec (rule 8)
    steers the planner toward flow only for flow/mechanism-themed pages. `check` does not
    store the archetype in the task record — it looks the node up in the catalog by task id
    (single source of truth; stale tasks still validate against the right template after a
    replan). Flow has seven required sections (Introduction / Flow Overview / Key Steps /
    Involved Components / Data and State Changes / Troubleshooting / Conclusion) and still
    clears MIN_SECTIONS=6 plus the two-mermaid bar; all other validator rules (cite /
    anchors / line ranges / placeholders) are archetype-agnostic.
    ② **`--dirty` semantics**: `git diff <since>` (working tree, staged + unstaged) plus
    `ls-files --others --exclude-standard` (untracked) — "I changed code but haven't
    committed and still want the wiki to catch up" is a real local-iteration need; the CI
    gate keeps the default committed-only view for reproducibility.
    ③ **Overview in incremental updates**: whenever any page is affected this round, an
    `overview-update` task is queued (the overview describes the repo as a whole; a page
    hit means structural content changed). The overview is not a page — its spec explicitly
    forbids an "Update Summary" section, and validation reuses check_overview's
    H1-plus-two-sections shape.
    ④ **Custom knowledge categories**: `knowledge --categories <file>` replaces the built-in
    six wholesale (not append — appending would break the 0-2-per-category less-is-more
    baseline), persisted in `state/knowledge_categories.json`; check/update validate against
    the persisted list, falling back to the built-ins when absent (zero migration for
    existing repos). Ids are limited to `^[a-z][a-z0-9_]{1,39}$` so they are safe in YAML
    front matter.
    Of item 8's low-hanging fruit, the overview and `--dirty` have landed; **bilingual CLI
    interaction messages are deferred** (kept on the roadmap): the messages target the
    driving agent (which reads either language), and a full string-table migration would
    be a large mechanical change with the lowest marginal value.
17. **Roadmap removal & scope freeze** (2026-09-08): output languages are frozen to
    zh/en — the table-driven mechanism stays but no more languages will be added; the
    "bilingual CLI messages" plan is cancelled and CLI messages remain as they are
    (aimed at the driving agent); the README Roadmap section is removed — completed work
    lives in the CHANGELOG, direction discussions go to Discussions. The same day the
    PyPI distribution name was set to `repowiki-cli` (`repowiki` was taken by the
    same-purpose project he-yufeng/RepoWiki; the command and import package remain
    `repowiki`), with publishing via Trusted Publisher (`pypi.yml`, tokenless OIDC).
