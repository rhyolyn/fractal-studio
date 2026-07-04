# Review-07: Housekeeping Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. If your harness lacks these skills, execute the tasks in order with strict TDD exactly as written. Tasks here are independent of each other — they may be executed in any order or individually.

**Goal:** Close the remaining small findings from the 2026-07-03 architectural review: the export-thread reuse race, the unchecked PNG write, dead `MainWindow` state, `EditorController`'s reach into editor privates, `SectionPanel._bordered` access, AGENTS.md's other-repo content, and two follow-ups from the 2026-07-03 Codex re-review (workflow-level settings-write regression tests; honest Rust fixture-test name).

**Architecture:** Six independent tasks, each self-contained with its own tests where behavior is involved.

**Tech Stack:** Python 3.12, PySide6 ≥ 6.8, pytest.

**Recommended model:** Claude Sonnet 4.6 for the whole plan. *Reasoning:* every task is small and fully specified. Task 1 (race token) is the only one with concurrency semantics, but the fix is a guard comparison, not a redesign. Haiku 4.5 is acceptable for Tasks 3 and 5 (pure deletion/markdown) if run as separate sessions.

**Dependencies:** none strictly, but if review-06 has merged, file line numbers in `panel_state.py` will have shifted — search by symbol, not line.

## Required Reading (before any code)

1. `AGENTS.md` at the repository root — engineering standards apply. (Task 5 edits this file; read it fully first.)
2. For Task 1: `ui/src/fractal_studio/application/controllers/export_controller.py` in full.
3. For Task 4: `ui/src/fractal_studio/editor.py` and `ui/src/fractal_studio/ui/controllers/editor_controller.py` in full.

## Global Constraints

- UI-only mode must keep working; full suite green at every commit (`cd ui; ..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q`).
- Commit style: conventional commits; one commit per task minimum.

---

### Task 1: Export-thread reuse race — job token

**Problem:** In `ExportController`, `export_done → _export_thread.quit` stops the thread, but `_cleanup_export_thread` runs later via a queued connection. In the gap, `isRunning()` is false, so a second `start_export` can begin — and the *stale* cleanup then nulls the new runner/thread and disconnects the new export's internal signals.

**Files:**
- Modify: `ui/src/fractal_studio/application/controllers/export_controller.py`
- Test: append to the export controller's test file (post-review-04: `ui/tests/test_export_panel.py`; pre-split: `ui/tests/test_ui.py`, class `TestExportPanelCoordinator` area)

- [ ] **Step 1: Write the failing test**

```python
class TestExportCleanupRace(unittest.TestCase):
    def test_stale_cleanup_does_not_clobber_newer_export(self) -> None:
        from fractal_studio.application.controllers.export_controller import ExportController

        controller = ExportController(export_service=object())
        # Simulate: job 1 finished, but before its queued cleanup ran, job 2 started.
        controller._job_id = 2
        controller._export_runner = sentinel_runner = object()
        controller._export_thread = sentinel_thread = object()
        controller._pending_on_status = sentinel_status = lambda _msg: None

        controller._cleanup_export_thread(job_id=1)  # stale cleanup from job 1

        self.assertIs(controller._export_runner, sentinel_runner)
        self.assertIs(controller._export_thread, sentinel_thread)
        self.assertIs(controller._pending_on_status, sentinel_status)

    def test_current_cleanup_still_clears_state(self) -> None:
        from fractal_studio.application.controllers.export_controller import ExportController

        controller = ExportController(export_service=object())
        controller._job_id = 2
        controller._export_runner = object()
        controller._export_thread = object()
        controller._pending_on_status = lambda _msg: None

        controller._cleanup_export_thread(job_id=2)

        self.assertIsNone(controller._export_runner)
        self.assertIsNone(controller._export_thread)
        self.assertIsNone(controller._pending_on_status)
```

Run — expected FAIL: `_cleanup_export_thread() got an unexpected keyword argument 'job_id'` (and no `_job_id` attribute).

- [ ] **Step 2: Implement**

In `ExportController.__init__`, add:

```python
        self._job_id = 0
```

In `start_export`, after the `isRunning()` guard and before creating the runner:

```python
        self._job_id += 1
        job_id = self._job_id
```

Replace the finished-connection:

```python
        self._export_thread.finished.connect(
            lambda job_id=job_id: self._cleanup_export_thread(job_id),
            Qt.ConnectionType.QueuedConnection,
        )
```

Replace `_cleanup_export_thread` (drop the `@Slot()` decorator — it is now invoked via the lambda):

```python
    def _cleanup_export_thread(self, job_id: int) -> None:
        if job_id != self._job_id:
            return  # stale cleanup from a previous job; a newer export owns the state
        try:
            self._export_result_signal.disconnect(self._on_export_result)
            self._export_status_signal.disconnect(self._on_export_status)
        except RuntimeError:
            pass
        self._pending_on_status = None
        self._export_runner = None
        self._export_thread = None
```

- [ ] **Step 3: Run the new tests and the full suite; commit** `fix: guard export-thread cleanup with a job token so stale cleanup cannot clobber a newer export`.

---

### Task 2: Check the PNG write result

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py` — `MainWindowExportState._do_export`, inner `on_done`
- Test: `ui/tests/test_export_panel.py` (or `test_ui.py` pre-split)

- [ ] **Step 1: Failing test** — extract the current inline `on_done` behavior into a testable seam first: in `_do_export`, replace the inline `image.save(path_str)` block with a call to a module-level function in `panel_state.py`:

```python
def save_export_image(raw: bytes, width: int, height: int, path_str: str, on_status: Callable[[str], None]) -> None:
    image = QImage(raw, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
    if not image.save(path_str):
        on_status(f"Export failed — could not write {path_str}")
        return
    on_status(f"Saved {width}×{height} render to {path_str}")
```

Test (integration marker):

```python
class TestSaveExportImage(unittest.TestCase):
    def test_reports_failure_when_path_is_unwritable(self) -> None:
        from fractal_studio.ui.sections.panel_state import save_export_image

        statuses: list[str] = []
        raw = bytes(2 * 2 * 4)
        save_export_image(raw, 2, 2, "Z:/nonexistent_dir_xyz/out.png", statuses.append)
        self.assertTrue(statuses and statuses[0].startswith("Export failed"))

    def test_reports_success_for_writable_path(self) -> None:
        import tempfile
        from pathlib import Path
        from fractal_studio.ui.sections.panel_state import save_export_image

        statuses: list[str] = []
        raw = bytes(2 * 2 * 4)
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "out.png")
            save_export_image(raw, 2, 2, target, statuses.append)
            self.assertTrue(Path(target).exists())
        self.assertTrue(statuses and statuses[0].startswith("Saved 2×2"))
```

- [ ] **Step 2:** Implement; `on_done` inside `_do_export` becomes:

```python
        def on_done(raw: bytes | None) -> None:
            if not raw:
                on_status("Export failed — backend not available.")
                return
            save_export_image(raw, width, height, path_str, on_status)
```

- [ ] **Step 3:** Run tests + suite; commit `fix: report failure when the exported PNG cannot be written`.

---

### Task 3: Remove dead `MainWindow` path state

**Files:**
- Modify: `ui/src/fractal_studio/main_window.py`

- [ ] **Step 1:** Verify the fields are dead: `grep -rn "_favorites_path\|_settings_path" ui/` — expected: only the assignments in `main_window.py` (`_init_window_state`) and the module constants `_FAVORITES_PATH`/`_SETTINGS_PATH` at lines ~34-35. If any other reader exists, stop and reassess.
- [ ] **Step 2:** Delete `self._favorites_path = _FAVORITES_PATH` and `self._settings_path = _SETTINGS_PATH` from `_init_window_state`, the two module-level constants, and the now-unused `from pathlib import Path` import if nothing else uses it (grep the file).
- [ ] **Step 3:** Run suite (startup smoke tests cover this file); commit `refactor: remove dead path state from MainWindow; factory owns persistence paths`.

---

### Task 4: Stop mutating widget privates from controllers

**Files:**
- Modify: `ui/src/fractal_studio/editor.py` (`ColorCubeEditor`)
- Modify: `ui/src/fractal_studio/ui/controllers/editor_controller.py`
- Modify: `ui/src/fractal_studio/ui/widgets/section_panel.py` + `ui/src/fractal_studio/ui/sections/sections.py` (`_register`)
- Tests: `ui/tests/test_color_editor.py`, `ui/tests/test_section_panel.py`

- [ ] **Step 1: Add the mutator API to `ColorCubeEditor`** (public methods, after the existing properties):

```python
    @property
    def drag_state(self) -> DragState | None:
        return self._drag_state

    def begin_drag(self, state: DragState) -> None:
        self._drag_state = state

    def end_drag(self) -> None:
        self._drag_state = None

    def replace_control_points(self, points: list[Color]) -> None:
        self._control_points = list(points)

    def append_control_point(self, color: Color) -> None:
        self._control_points.append(color)

    def update_control_point(self, index: int, color: Color) -> None:
        self._control_points[index] = color

    def set_generated_palette(self, palette: list[Color]) -> None:
        self._palette = list(palette)

    def cached_face_pixmap(self, key: tuple[int, int, int]) -> QPixmap | None:
        return self._face_pixmaps.get(key)

    def cache_face_pixmap(self, key: tuple[int, int, int], pixmap: QPixmap) -> None:
        self._face_pixmaps[key] = pixmap
```

Note the existing `_face_pixmaps` dict is typed `dict[tuple[int, int], QPixmap]` but keyed with 3-tuples `(face, w, h)` in `EditorController.face_pixmap` — fix the annotation to `dict[tuple[int, int, int], QPixmap]` while here.

- [ ] **Step 2: Rewrite every `editor._x` access in `EditorController`** to use the API: `editor._control_points.clear()` → `editor.replace_control_points([])`; `editor._control_points = [...]` → `editor.replace_control_points([...])`; `editor._control_points.append(c)` → `editor.append_control_point(c)`; `editor._control_points[index] = c` → `editor.update_control_point(index, c)`; reads of `editor._control_points` → `editor.control_points` (existing property — note it returns a copy; in `refresh_palette` and loops that is correct behavior, but in `handle_mouse_move` read `current = editor.control_points[index]` which copies the list per event — acceptable at ≤ a few dozen points); `editor._palette = ...` → `editor.set_generated_palette(...)`; `editor._drag_state` reads → `editor.drag_state`; assignments → `begin_drag`/`end_drag`; `editor._face_pixmaps` get/set → `cached_face_pixmap`/`cache_face_pixmap`. Verify with `grep -n "editor\._" ui/src/fractal_studio/ui/controllers/editor_controller.py` — expected zero matches when done.
- [ ] **Step 3: `SectionPanel` bordered flag** — add to `ui/src/fractal_studio/ui/widgets/section_panel.py`:

```python
    @property
    def is_bordered(self) -> bool:
        return self._bordered
```

and in `ui/src/fractal_studio/ui/sections/sections.py` `_register`, change `if panel._bordered:` to `if panel.is_bordered:`.

- [ ] **Step 4:** Run editor/section tests, then full suite; commit `refactor: give ColorCubeEditor a mutator API; controllers stop writing widget privates`.

---

### Task 5: Excise other-project content from AGENTS.md

**Files:**
- Modify: `AGENTS.md`

This file mixes durable cross-project preferences with content specific to an Unreal Engine repo (`d:\p4\ss`, Builder scripts, Blueprint conventions). Agents working in *this* repo waste attention on it. Edit conservatively — remove only what demonstrably belongs to the other repo; relocate C++-generic preferences under a clearly-scoped heading.

- [ ] **Step 1:** Delete the entire `## Repo Builder Commands` section (lines ~112-122: everything from the heading through the Live Coding bullet).
- [ ] **Step 2:** In `## Class Organization`, delete the four Blueprint-specific bullets: "Put Blueprint-callable functions at the top…", "Put helper and persistence-only prototypes below the user-facing or Blueprint-facing APIs.", "Use a blank line between Blueprint-callable function declarations…", "Do not add blank lines between adjacent non-Blueprint function prototypes…". Keep "Keep `.cpp` function definition order aligned…" but see Step 3.
- [ ] **Step 3:** Create a new section near the end, `## C++ Projects Only (not applicable to this repository)`, and move into it verbatim: the guard-macro bullet from Coding Style Preferences ("Prefer the repository guard/logging macros such as `RETURN_FALSE_IF`…"), the `.cpp` file-layout bullet from Coding Style Preferences ("In `.cpp` files, prefer core class functionality near the top…"), and the `.cpp`/`.h` ordering bullet from Class Organization. Do not reword them — the owner may reuse this file in C++ repos.
- [ ] **Step 4:** Under `## Repo-Specific Guidance`, add:

```markdown
- This repository is Python (PySide6 UI) + Rust (PyO3 core). Tests: `cd ui; pytest` (unit) / `pytest -m "unit or integration"` (full) and `cd core; cargo test`.
- Implementation plans and their status board live in `docs/superpowers/plans/` (see `2026-07-03-review-00-master.md`).
```

- [ ] **Step 5:** Render-check the markdown (headings intact, no orphaned bullets), then commit `docs: scope AGENTS.md to this repo; move C++/Unreal-only guidance aside`.

### Task 6: Pin the settings aggregate-write path; rename the Rust fixture test honestly

**Problem (from the 2026-07-03 Codex re-review of the completed arch-01 work):** `SettingsRepository.update()` preserves sibling fields and repository-level tests prove it — but nothing pins that the *callers* use it. A future revert of `ThemeWorkflowCoordinator` to `repo.save(UiSettings(theme=name))` would erase `sidebar_collapsed` again and every existing test would stay green. Separately, the Rust test `legacy_palette_parser_reads_existing_repo_map` reads a checked-in grayscale-ramp fixture, not the historical China palette its name implies.

**Files:**
- Test: `ui/tests/test_settings_and_theme.py` (post-review-04; pre-split: `ui/tests/test_ui.py`)
- Modify: `core/src/lib.rs` (test rename only)

- [ ] **Step 1: Write the two workflow-level regression tests** (integration marker; these must pass immediately — they pin current correct behavior):

```python
class TestSettingsWritePreservation(unittest.TestCase):
    """Workflow-level pins for the arch-01 fix: partial settings writes must go
    through SettingsRepository.update() and preserve sibling fields. These fail
    if any caller reverts to repo.save(UiSettings(theme=name))."""

    def test_theme_persist_preserves_sidebar_collapsed(self) -> None:
        import tempfile
        from pathlib import Path

        from fractal_studio.application.controllers.settings_controller import SettingsController
        from fractal_studio.application.controllers.theme_controller import ThemeController
        from fractal_studio.application.coordinators.settings_dialog_coordinator import (
            SettingsDialogCoordinator,
        )
        from fractal_studio.application.workflows.theme_workflow_coordinator import (
            ThemeWorkflowCoordinator,
        )
        from fractal_studio.persistence import SettingsRepository
        from fractal_studio.services.settings_service import SettingsWorkflowService
        from fractal_studio.state import UiSettings
        from fractal_studio.theme import get_theme

        with tempfile.TemporaryDirectory() as tmp:
            repo = SettingsRepository(Path(tmp) / "settings.json")
            repo.save(UiSettings(theme="light", sidebar_collapsed={"export": True}))

            coordinator = ThemeWorkflowCoordinator(
                SettingsDialogCoordinator(SettingsController(), SettingsWorkflowService()),
                ThemeController(),
                repo,
            )
            coordinator.apply_theme_name(
                theme_name="dark",
                persist=True,
                current_theme="light",
                current_theme_spec=get_theme("light"),
                application=None,
                refresh_dynamic_widgets=lambda: None,
            )

            final = repo.load().settings
            self.assertEqual(final.theme, "dark")
            self.assertEqual(final.sidebar_collapsed, {"export": True})

    def test_sidebar_collapse_persist_preserves_theme(self) -> None:
        import tempfile
        from pathlib import Path

        from fractal_studio.application.controllers.settings_controller import SettingsController
        from fractal_studio.persistence import SettingsRepository
        from fractal_studio.state import UiSettings

        with tempfile.TemporaryDirectory() as tmp:
            repo = SettingsRepository(Path(tmp) / "settings.json")
            repo.save(UiSettings(theme="dark", sidebar_collapsed={}))

            SettingsController().save_sidebar_collapsed(repo, "export", True)

            final = repo.load().settings
            self.assertEqual(final.theme, "dark")
            self.assertEqual(final.sidebar_collapsed, {"export": True})
```

- [ ] **Step 2: Prove each test can fail** — temporarily change `ThemeWorkflowCoordinator`'s `persist_theme` lambda to `lambda name: self._settings_repo.save(UiSettings(theme=name))` (add the `UiSettings` import), run the first test, watch it FAIL on `sidebar_collapsed == {}`; revert. Do the equivalent for the second (`repo.save(replace(s, ...))` → `repo.save(UiSettings(sidebar_collapsed=...))`); revert.

- [ ] **Step 3: Rename the Rust test** — in `core/src/lib.rs`, rename `legacy_palette_parser_reads_existing_repo_map` to `legacy_palette_parser_reads_256_line_fixture` (body unchanged — the fixture is a checked-in grayscale ramp, and the test only verifies parse behavior, not historical content). Run `cd core; cargo test -q` — expected: all pass.

- [ ] **Step 4: Run the full Python suite; commit** `test: pin settings partial-write preservation at workflow level; rename Rust fixture test honestly`.

## Done criteria

- All six tasks committed independently; full suite green.
- `grep -n "editor\._" ui/src/fractal_studio/ui/controllers/editor_controller.py` returns nothing.
- Stale-cleanup race covered by tests; failed PNG writes surface in the status bar.
- AGENTS.md contains no `d:\p4`, Builder, or Blueprint references outside the clearly-marked C++-only section.
