# Architectural Review 2026-07-03 — Master Plan and Status Board

> **For agentic workers:** This is the coordination document for the seven implementation plans produced from the 2026-07-03 architectural review. It is **not** an implementation plan itself. Pick the first plan in the status table whose status is `Not started` and whose dependencies are all `Done`, open its file, and execute it with superpowers:subagent-driven-development or superpowers:executing-plans (or your harness's equivalent plan-execution workflow). **Update the status table below when you start and when you finish.**

**Owner:** rhyolyn. The owner reviews plans asynchronously; the "Decisions made for you" section in review-06 and the plan-level designs are approved-by-default unless the owner amends them here.

## Ground rules for every executing agent (any harness)

1. **Read `AGENTS.md` at the repo root first** and follow it: SOLID, TDD where practical, small focused functions, direct reporting of failures, cautious git usage, conventional-commit style. Its instructions take precedence over plan text on style questions. Its C++/Unreal-specific sections do not apply to this repository (review-07 Task 5 relocates them).
2. **One plan = one branch.** Branch from up-to-date `main` (e.g. `review-01-save-json-wiring`). Use an isolated worktree if your harness supports it (superpowers:using-git-worktrees). Merge/PR per plan; do not stack unmerged plans unless the dependency table forces it.
3. **Never claim done without running the verification commands** in the plan (superpowers:verification-before-completion). Baseline before any plan: Python `177 passed, 11 subtests` for `pytest -m "unit or integration"` from `ui/`; Rust `24 passed` for `cargo test` from `core/`. Review-04 records the authoritative collected count and later plans add tests — update the baseline column when you merge.
4. **Environment:** Windows, venv at `.venv/` (repo root). Python suite: `cd ui; ..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q`. Rust: `cd core; cargo test -q`. Rust core is optional for UI work; plans state when a maturin build is needed.
5. **Update this file** (status + notes column + baseline if it changed) in the same commit that completes a plan, or in the merge commit.

## Status board

| # | Plan file | Scope (one line) | Status | Depends on | Recommended model | Risk | Notes |
|---|---|---|---|---|---|---|---|
| 01 | `2026-07-03-review-01-save-json-wiring.md` | Colormap "Save JSON" button saves a favorite instead of palette JSON — rewire to the existing (dead) save pipeline | Done | — | Sonnet 4.6 | Low | PR branch `review-01-save-json-wiring`; UI suite now prints `180 passed, 11 subtests passed` |
| 02 | `2026-07-03-review-02-rust-gil-parallel-render.md` | Release the GIL during renders; rayon row-parallel `render_image`; makes `"multithreaded_cpu"` honest | Done | — | **Opus 4.8** | Medium | Merged in PR #2; Rust baseline now `26 passed` |
| 03 | `2026-07-03-review-03-import-policy-guard.md` | Shim-import guard scans nonexistent dirs (vacuous); fix paths, add domain layer-direction test, fix README claim | Done | — | Sonnet 4.6 | Low | PR branch `review-03-import-policy-guard`; import-policy tests now `3 passed` |
| 04 | `2026-07-03-review-04-split-test-ui.md` | Split the 2,988-line `test_ui.py` into ~10 per-area modules + `tests/support.py`; zero behavior change | In progress | — | Sonnet 4.6 | Low | Baseline collected count: `181`; must precede 05/06 so their test diffs are reviewable |
| 05 | `2026-07-03-review-05-unify-render-invocation.md` | Single `CoreBackend.render(RenderRequest)` + single status formatter; remove redundant widget debounce | Not started | 03, 04 | Sonnet 4.6 | Medium | Touches worker/export/controller call sites |
| 06 | `2026-07-03-review-06-wiring-hardening.md` | Required panel-state collaborators (no silent no-ops); delete two pass-through coordinators; `FavoriteRestoreTarget` protocol | Not started | 01, 03, 04 (05 recommended) | **Fable 5** (Opus 4.8 ok) | High | Largest refactor; reviewer must reject any reintroduced `\| None = None` wiring param |
| 07 | `2026-07-03-review-07-housekeeping.md` | Export-thread race token; checked PNG write; dead MainWindow state; editor mutator API; AGENTS.md scoping; settings-write workflow pins + Rust test rename | Not started | — (see plan note re: 06 line drift) | Sonnet 4.6 (Haiku ok for Tasks 3, 5) | Low | Six independent tasks; may be executed piecemeal |

**Execution order:** 01 → 02 → 03 → 04 → 05 → 06 → 07. Plans 01/02/03 are mutually independent and may run in parallel worktrees; 04 may also run in parallel with 01-03 if merge conflicts in `ui/tests/` are managed (01 and 03 create *new* test files, so conflicts are unlikely). 05 and 06 are strictly sequential after their dependencies. 07 can slot in anywhere but expect line-number drift if run after 06.

## Model recommendation rationale (summary)

- **Sonnet 4.6** for plans whose design is fully pinned in the plan document and whose work is mechanical or narrowly scoped (01, 03, 04, 05, 07). The plans deliberately carry the judgment so a mid-tier model executes with fidelity; escalate only if a plan's assumptions turn out wrong.
- **Opus 4.8** for plan 02 because the failure modes (GIL-bound borrows crossing `allow_threads`, parallel-loop data dependence) are subtle, non-local, and compiler-error-driven — worth stronger reasoning even with pinned code.
- **Fable 5** for plan 06 because it is the only plan requiring live design judgment across ~14 files, and the known failure mode (a model "fixing" broken tests by re-adding optional-collaborator defaults) silently defeats the plan's entire purpose. If executing with subagents, use the strongest available model for the *reviewer* role too.

## Findings → plan traceability

From the 2026-07-03 review (conversation record; severity in parentheses):

| Finding | Plan |
|---|---|
| 1. "Save JSON" saves a favorite (High) | 01 |
| 2. GIL held during renders (High) | 02 |
| 3. `render_strategy` claims multithreaded, is not (Medium) | 02 |
| 4. Vacuous import-policy test + README claim (Medium-High) | 03 |
| 5. Export-thread reuse race (Low-Medium) | 07 Task 1 |
| 6. `is_julia`/`formula_params` dual source of truth (Low) | **Backlog — needs design session** (see below) |
| 7. Optional-collaborator silent no-ops (High, architectural) | 06 Phase B |
| 8. Pass-through coordinator layers (Medium-High) | 06 Phase A |
| 9. Composition-root getter/lambda wiring (Medium) | 06 Phase B2/C (partial; full inversion deferred — see backlog) |
| 10. Render call plumbed 3× (Medium) | 05 |
| 11. Controllers mutate widget privates (Medium) | 07 Task 4 |
| 12. `lib.rs` monolith; coloring fused to iteration (Medium, forward-looking) | Backlog |
| 13a. `test_ui.py` monolith | 04 |
| 13b. Dead `MainWindow` path state | 07 Task 3 |
| 13c. Unchecked `image.save` | 07 Task 2 |
| 13d. Double render debounce | 05 Task 4 |
| 13e. AGENTS.md other-repo content | 07 Task 5 |

## Backlog (deliberately not planned — do not pick these up without owner input)

1. **`is_julia` / `formula_params` remodel** — *needs a brainstorming session with the owner.* The flag is **not** derivable from the params union (phoenix can run in Julia mode while carrying `PhoenixParams`), so the fix is a real state-model redesign (likely an explicit `mode` + per-formula params), which ripples through persistence (`favorites.json` compat), the Rust call surface, and the params panel. Wrong to bundle into a mechanical plan.
2. **Rust core module split + iteration/coloring separation** — split `core/src/lib.rs` into `formulas` / `coloring` / `palette` / `io` / bindings, and separate the escape-iteration pass (buffer of escape values) from the coloring pass (palette mapping). The second half makes 20 fps palette cycling nearly free (re-map instead of re-render). Do this the next time `lib.rs` is touched for a feature; plan then.
3. **Full composition-root construction-order inversion** — eliminate the remaining getter indirection by building widgets before panel states (sections builders return widgets; states constructed after). Deferred from plan 06 as its own design exercise; re-evaluate after 06 lands, since 06 removes most of the pressure.
4. **Test-suite runtime** — full suite is ~6.6 minutes. After plan 04, profile the slowest modules (`pytest --durations=20`) and decide whether anything warrants optimization.
5. **Qt teardown exit code** — on Windows the full UI suite prints all tests passing, then the Python process exits `-1073740791` (`0xC0000409`) during Qt teardown. This predates review-01 and still occurs after review-03 (`181 passed, 11 subtests passed` printed). Investigate separately so future feature branches do not misattribute the nonzero process exit.

## Historical plans (do not execute)

Every plan in this directory dated **before 2026-07-03** (`2026-05-29-ui-polish`, `2026-05-30-arch-01` through `arch-04`, `2026-05-30-attach-codex-architectural-analysis`, `2026-05-31-async-rendering`) was executed in May-June 2026 and carries a `Status: COMPLETED` banner. They are records, not work queues. A 2026-07-03 Codex re-review confirmed the arch-01 changes are live in the tree (`SettingsRepository.update()`, coordinator migration, Rust fixture path).

## Change log

| Date | Change |
|---|---|
| 2026-07-03 | Master plan and plans 01-07 created from the architectural review. |
| 2026-07-03 | Codex re-review of arch-01: bannered all seven pre-2026-07-03 plans as COMPLETED; added review-07 Task 6 (workflow-level settings-write regression tests + Rust fixture-test rename). |
