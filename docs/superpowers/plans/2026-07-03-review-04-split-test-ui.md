# Review-04: Split the test_ui.py Monolith Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. If your harness lacks these skills, execute the tasks in order exactly as written.

**Goal:** Split `ui/tests/test_ui.py` (2,988 lines; 31 test classes plus 4 shared helper classes, spanning every layer) into focused per-area test modules with a shared support module, changing **zero test behavior** — same tests, same markers, same collected count.

> **Amended 2026-07-03 after Codex plan review** (post PRs #1-#3, main @ `181320d`): all counts and line numbers in this document are as-of that commit — `test_ui.py` itself is untouched by PRs #1-#3, but the *suite* baseline moved (new test files landed). Task 1's recorded number is the only authoritative baseline; never trust a hard-coded count from this document. The amendment also moved `TestFavoritePersistence` to its own module and added the `conftest.py` bootstrap/ignore-list steps (Task 1 Step 2a and the per-task recipe item 1a).

**Architecture:** Pure code motion. Shared helpers (`_get_app`, `QtWindowTestCase`, the `Dummy*Backend` classes) move to `ui/tests/support.py`; each test class moves verbatim to a module named for the area under test. Every batch move ends with a collected-count check against the baseline so nothing is silently dropped.

**Tech Stack:** Python 3.12, pytest, unittest-style classes (as-is — do not convert styles).

**Recommended model:** Claude Sonnet 4.6. *Reasoning:* zero design decisions — the mapping is fully specified below — but the volume of verbatim code motion across a 3,000-line file needs disciplined context management, which is above Haiku's comfortable range. Opus/Fable would be wasted here.

**Do this plan BEFORE review-05 and review-06** — those refactors rewrite many of these tests, and their diffs are only reviewable once the tests live in focused files.

## Required Reading (before any code)

1. `AGENTS.md` at the repository root — engineering standards apply ("Keep tests small and focused"). The C++/Unreal sections do not apply.
2. The top ~120 lines of `ui/tests/test_ui.py` (imports, `_get_app`, `QtWindowTestCase`, `DummyEditorBackend`, `DummyUnavailableBackend`, `DummyPaletteBackend`).
3. `ui/pyproject.toml` `[tool.pytest.ini_options]` — markers and default `-m unit`.

## Global Constraints

- **No test bodies change.** Move code verbatim; only module-level imports and helper references are adjusted.
- Preserve every `@pytest.mark.unit` / `pytest.mark.integration` marker exactly. If markers are applied at module level in `test_ui.py` (check the top of the file), replicate the same mechanism in each new module.
- The collected test count must match the baseline at every checkpoint (baseline captured in Task 1).
- Shared helpers live in `ui/tests/support.py` — a plain module, not `conftest.py`, so imports stay explicit (`from tests.support import QtWindowTestCase` will not work since tests run from `ui/` with rootdir `ui`; use `from support import ...` if pytest inserts the tests dir on `sys.path`, otherwise `from tests.support import ...` — verify with the first move and use whichever import the existing conftest/rootdir setup resolves; `ui/conftest.py` exists and makes `ui/` the rootdir, so `from tests.support import ...` is the expected form).
- One commit per task, suite green at every commit.

---

### Task 1: Capture the baseline and create the support module

**Files:**
- Create: `ui/tests/support.py`
- Modify: `ui/tests/test_ui.py` (delete the moved helpers, import from support instead)

- [ ] **Step 1: Record the baseline collected count**

```powershell
cd ui
..\.venv\Scripts\python.exe -m pytest -m "unit or integration" --collect-only -q | Select-Object -Last 2
```

Write the reported item count into the master plan's status table row for review-04 (~181 items after PRs #1-#3, but the authoritative number is whatever this command prints — record it and use it at every later checkpoint; do not compare against any count written in this document).

- [ ] **Step 2a: Move the `sys.path` bootstrap into `ui/conftest.py`**

`test_ui.py` lines 13-14 insert `ui/src` onto `sys.path` so tests run from a fresh checkout without an editable install:

```python
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))
```

This must survive the split, but not by copy-pasting it into ten files. Add it once to `ui/conftest.py` (which pytest loads before collecting any test module):

```python
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
```

(Note the path differs: `conftest.py` sits in `ui/`, so it is `parent / "src"`, not `parents[1]`.) Delete the two lines from `test_ui.py` in the same commit. The identical pre-existing copies in `test_backend.py`, `test_render_workers.py`, and `test_main_window_section_panel_states.py` become redundant but are **out of scope** — leave them (removing them is a one-liner for review-07-style housekeeping).

`ui/conftest.py` also maintains `collect_ignore_glob` listing Qt-importing test files to skip when PySide6 is absent — `tests/test_ui.py` is on that list. Every split file that imports PySide6 at module level must be added to it (recipe item 1a below), and Task 11 removes the `test_ui.py` entry.

- [ ] **Step 2: Move shared helpers verbatim**

Create `ui/tests/support.py` containing, moved **verbatim** from `test_ui.py`:
- `_get_app` (test_ui.py line ~37) — rename to public `get_app` in support.py and update call sites as you move classes.
- `QtWindowTestCase` (line ~44)
- `DummyEditorBackend` (line ~57)
- `DummyUnavailableBackend` (line ~87)
- `DummyPaletteBackend` (line ~92)

Copy whatever imports those helpers need from the top of `test_ui.py` (only the ones they need). In `test_ui.py`, delete the moved code and add:

```python
from tests.support import (
    DummyEditorBackend,
    DummyPaletteBackend,
    DummyUnavailableBackend,
    QtWindowTestCase,
    get_app as _get_app,
)
```

(The alias keeps the remaining monolith untouched; new files import `get_app` directly.)

- [ ] **Step 3: Verify count unchanged, suite green, commit**

```powershell
..\.venv\Scripts\python.exe -m pytest -m "unit or integration" --collect-only -q | Select-Object -Last 2
..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q
git add ui/tests/support.py ui/tests/test_ui.py
git commit -m "refactor: extract shared test helpers to tests/support.py"
```

Expected: identical count to Step 1; suite green.

---

### Task 2 through Task 10: Move classes by area

Each task follows the identical recipe, so it is stated once; the per-task table below gives the file names and exact class lists (line numbers refer to the pre-split `test_ui.py` from grep on 2026-07-03 and will drift as you delete — search by class name, not line).

**Recipe per task:**
1. Create the new test file with `from __future__ import annotations`, the minimal imports its classes need (copy from `test_ui.py`'s header), any module-level `pytestmark` that applied in `test_ui.py`, and the listed classes moved **verbatim**.
1a. If the new file imports PySide6 at module level (directly or via `tests.support`), add its path to `collect_ignore_glob` in `ui/conftest.py` in the same commit — otherwise a no-PySide6 environment fails at collection instead of skipping.
2. Delete those classes from `test_ui.py`.
3. Run: `..\.venv\Scripts\python.exe -m pytest -m "unit or integration" --collect-only -q | Select-Object -Last 2` — count must equal the Task 1 baseline.
4. Run the new file: `..\.venv\Scripts\python.exe -m pytest tests/<new_file> -m "unit or integration" -v` — all pass.
5. Commit: `git add ui/tests/<new_file> ui/tests/test_ui.py && git commit -m "refactor: move <area> tests to tests/<new_file>"`.

| Task | New file | Classes to move (verbatim) |
|---|---|---|
| 2 | `ui/tests/test_export_panel.py` | `TestCustomResolutionDialog`, `TestExportPanel`, `TestExportPanelCoordinator` |
| 3 | `ui/tests/test_viewport_widget.py` | `TestViewportRenderScheduling`, `TestViewportController`, `TestViewportSizing`, `TestViewportHints` |
| 4 | `ui/tests/test_params_panel.py` | `TestParamsPanel`, `TestParamsPanelController`, `TestSidebarWiringCoordinator` |
| 5 | `ui/tests/test_palette_workflows.py` | `TestPaletteWorkflowService`, `TestPalettePanelCoordinator`, `TestPalettePreviewCoordinator`, `TestPalettePreviewWidget` |
| 6 | `ui/tests/test_settings_and_theme.py` | `TestAppearanceSettings`, `TestSettingsWorkflowService`, `TestWindowStartupCoordinator`, `TestSettingsDialogCoordinator`, `TestThemeWorkflowCoordinator`, `TestThemeController` |
| 7 | `ui/tests/test_color_editor.py` | `TestColorCubeEditor`, `TestThumbnailHelpers` |
| 8 | `ui/tests/test_favorites_widgets.py` | `TestFavoriteHoverPresenter`, `TestFavoriteThumbnailRow`, `TestFavoriteRowStylePresenter` |
| 8b | `ui/tests/test_favorites_persistence.py` | `TestFavoritePersistence` (persistence/workflow integration, not widget behavior — kept separate so focused runs stay meaningful) |
| 9 | `ui/tests/test_favorites_controllers.py` | `TestFavoritesController`, `TestFavoritesPanelCoordinator`, `TestFavoritesWorkflowCoordinator` |
| 10 | `ui/tests/test_main_window_shell.py` | `TestMainWindowController`, `TestWorkspaceLayout` |

Notes:
- If a class uses a helper that another moved class also uses and it is not yet in `support.py` (e.g., a module-level fixture function defined mid-file), move that helper to `support.py` in the same task and import it from both places.
- Do not merge these with the pre-existing focused files (`test_render_workers.py`, `test_section_panel.py`, etc.) — keep this plan pure motion.

---

### Task 11: Delete the empty monolith

**Files:**
- Delete: `ui/tests/test_ui.py`

- [ ] **Step 1:** After Task 10, `test_ui.py` should contain only imports. Verify: `..\.venv\Scripts\python.exe -m pytest tests/test_ui.py --collect-only -q` reports 0 items (or the file is import-only). If any stray function/class remains, move it per the recipe first.
- [ ] **Step 2:** `git rm ui/tests/test_ui.py`, and remove `"tests/test_ui.py"` from `collect_ignore_glob` in `ui/conftest.py`.
- [ ] **Step 3:** Final verification:

```powershell
..\.venv\Scripts\python.exe -m pytest -m "unit or integration" --collect-only -q | Select-Object -Last 2
..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q
```

Expected: count equals the Task 1 recorded baseline; suite pass count equals the Task 1 run. (Windows note: the process may exit `0xC0000409` after printing all-pass — the known Qt teardown crash, master-plan backlog item 5; pass counts are authoritative.)

- [ ] **Step 4:** Commit:

```powershell
git commit -m "refactor: remove test_ui.py monolith after per-area split"
```

## Done criteria

- `test_ui.py` gone; ~11 focused test modules plus `support.py`; `collect_ignore_glob` covers every new Qt-importing module and no longer lists `test_ui.py`.
- Collected count and pass count identical to the Task 1 recorded baseline (no hard-coded number — the baseline is whatever Task 1 measured).
- A no-PySide6 environment still collects cleanly: `pytest -q` (unit-only default) passes without collection errors.
- No test body modified (verify: `git diff <pre-split-commit> HEAD -- ui/tests` shows only moves/imports — spot-check three classes).
