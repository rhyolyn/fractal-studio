# Review-03: Repair the Import-Policy Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. If your harness lacks these skills, execute the tasks in order with strict TDD exactly as written.

**Goal:** Fix the vacuous legacy-shim import guard (it currently scans two directories that do not exist, so it passes while checking zero files), add the layer-direction test the README promises, and correct the README's description.

**Architecture:** `ui/tests/test_import_policy.py` computes `repo_root = parents[2]` (the git root) and then scans `<git-root>/src` and `<git-root>/tests` — neither exists; the real trees are `<git-root>/ui/src` and `<git-root>/ui/tests`. `Path.rglob` on a missing directory silently yields nothing. We fix the paths, add a can't-be-vacuous assertion, and add a new test forbidding upward (`application`/`services`/`ui`) and Qt imports in the domain layer (`state.py`, `persistence.py`).

**Tech Stack:** Python 3.12, pytest (`unit` marker only — no Qt involved).

**Recommended model:** Claude Sonnet 4.6. *Reasoning:* small, fully-specified test-code change; no design judgment needed. Haiku 4.5 could do the path fix alone, but the new layer-direction test benefits from Sonnet's care with regexes and failure messages, and the whole plan is one short session anyway.

## Required Reading (before any code)

1. `AGENTS.md` at the repository root — engineering standards apply. The C++/Unreal sections do not apply.
2. `ui/tests/test_import_policy.py` in full (it is 132 lines).
3. `README.md` "Development Notes" section (the "Import policy test" bullet, ~line 247).

## Global Constraints

- Both new/fixed tests must carry `@pytest.mark.unit` and run green without PySide6.
- The guard must fail loudly if it ever scans zero files again (vacuousness protection).
- Run tests from `ui/`: `..\.venv\Scripts\python.exe -m pytest tests/test_import_policy.py -v`.
- Commit style: conventional commits.

---

### Task 1: Fix the shim-guard paths and add vacuousness protection

**Files:**
- Modify: `ui/tests/test_import_policy.py`

**Interfaces:**
- Produces: module-level constant `UI_PACKAGE_ROOT: Path` used by Task 2's test as well.

- [ ] **Step 1: Demonstrate the bug (red)**

Temporarily add this test at the bottom of `ui/tests/test_import_policy.py` to prove the current scan is empty:

```python
@pytest.mark.unit
def test_shim_guard_scans_real_files() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    scoped = _iter_python_files(repo_root / "src") + _iter_python_files(repo_root / "tests")
    assert scoped, "shim guard scanned zero files — the paths are wrong"
```

Run: `..\.venv\Scripts\python.exe -m pytest tests/test_import_policy.py::test_shim_guard_scans_real_files -v`
Expected: FAIL with "shim guard scanned zero files".

- [ ] **Step 2: Fix the paths**

At module level (below the regex definitions), add:

```python
UI_PACKAGE_ROOT = Path(__file__).resolve().parents[1]  # .../fractal-studio/ui
```

In `test_no_legacy_root_shim_imports_in_source_or_tests`, replace:

```python
    repo_root = Path(__file__).resolve().parents[2]
    src_root = repo_root / "src"
    tests_root = repo_root / "tests"

    scoped_files = _iter_python_files(src_root) + _iter_python_files(tests_root)
```

with:

```python
    src_root = UI_PACKAGE_ROOT / "src"
    tests_root = UI_PACKAGE_ROOT / "tests"

    scoped_files = _iter_python_files(src_root) + _iter_python_files(tests_root)
    assert scoped_files, (
        f"import-policy guard scanned zero files under {src_root} and {tests_root} — "
        "the directory layout changed; update this test's paths"
    )
    assert any(p.name == "main_window.py" for p in scoped_files), (
        "expected main_window.py in scan scope — paths look wrong"
    )
```

Also update the violation message path base: `rel = file_path.relative_to(repo_root)` becomes `rel = file_path.relative_to(UI_PACKAGE_ROOT)`.

In `test_no_qt_imports_in_services`, simplify the equivalent lines:

```python
    src_root = UI_PACKAGE_ROOT / "src" / "fractal_studio"
```

and delete the now-unused `repo_root = ...` / `ui_root = ...` lines in that test; change its `rel = file_path.relative_to(repo_root)` to `rel = file_path.relative_to(UI_PACKAGE_ROOT)`.

- [ ] **Step 3: Run — the temporary test and both fixed tests must pass**

```powershell
cd ui
..\.venv\Scripts\python.exe -m pytest tests/test_import_policy.py -v
```

Expected: all PASS. **If the shim guard now reports violations, they are real, previously-masked regressions** — fix the offending imports to canonical package paths (`fractal_studio.application...`, `fractal_studio.ui...`, `fractal_studio.services...`) rather than weakening the test. As of 2026-07-03 the expectation is zero violations.

- [ ] **Step 4: Delete the temporary Step-1 test, then commit**

The vacuousness assertion now lives inside the real test, so the scaffold test is redundant. Delete `test_shim_guard_scans_real_files`, re-run the file, then:

```powershell
git add ui/tests/test_import_policy.py
git commit -m "fix: import-policy shim guard scanned nonexistent directories; scan ui/src and ui/tests"
```

---

### Task 2: Add the layer-direction test the README promises

**Files:**
- Modify: `ui/tests/test_import_policy.py`
- Modify: `README.md` (~line 247)

**Interfaces:**
- Consumes: `UI_PACKAGE_ROOT` from Task 1.

- [ ] **Step 1: Write the test**

Append to `ui/tests/test_import_policy.py`:

```python
_DOMAIN_LAYER_FILES = ("state.py", "persistence.py")
_UPWARD_OR_QT_IMPORT_PATTERN = re.compile(
    r"^\s*(?:from|import)\s+(?:PySide6\b|fractal_studio\.(?:application|services|ui)\b)"
)


@pytest.mark.unit
def test_domain_layer_does_not_import_upward_or_qt() -> None:
    src_root = UI_PACKAGE_ROOT / "src" / "fractal_studio"
    violations: list[str] = []

    for name in _DOMAIN_LAYER_FILES:
        file_path = src_root / name
        assert file_path.exists(), f"expected domain module missing: {file_path}"
        lines = file_path.read_text(encoding="utf-8").splitlines()
        for line_no, line in enumerate(lines, start=1):
            if _UPWARD_OR_QT_IMPORT_PATTERN.match(line):
                violations.append(f"{name}:{line_no}: {line.strip()}")

    assert not violations, (
        "Domain layer must not import PySide6 or upper layers "
        "(application/services/ui).\n" + "\n".join(violations)
    )
```

- [ ] **Step 2: Run — expect pass (both files are currently clean)**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_import_policy.py::test_domain_layer_does_not_import_upward_or_qt -v
```

Expected: PASS. To confirm the test can actually fail, temporarily add `from PySide6.QtCore import QObject` to the top of `ui/src/fractal_studio/state.py`, re-run, watch it FAIL with the file/line in the message, then revert that line.

- [ ] **Step 3: Correct the README**

In `README.md`, replace the bullet (~line 247):

```markdown
- **Import policy test:** `tests/test_import_policy.py` enforces that lower layers (`state.py`, `persistence.py`) do not import from application or UI layers. Run it as part of the unit suite.
```

with:

```markdown
- **Import policy tests:** `tests/test_import_policy.py` enforces three rules as part of the unit suite: no imports of legacy root-shim module names, no PySide6/widget imports inside `services/`, and no upward (`application`/`services`/`ui`) or Qt imports inside the domain layer (`state.py`, `persistence.py`).
```

- [ ] **Step 4: Full unit run and commit**

```powershell
..\.venv\Scripts\python.exe -m pytest -q
git add ui/tests/test_import_policy.py README.md
git commit -m "test: enforce domain-layer import direction; document actual import-policy guards"
```

## Done criteria

- All three policy tests pass and each fails loudly when fed a deliberate violation.
- The shim guard can never again pass on an empty scan.
- README describes what the tests actually enforce.
