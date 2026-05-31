# Architecture Cleanup 01 — Quick Wins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the failing Rust test (F7) and add a single aggregate write path for settings (F1), eliminating the bug where theme writes silently erase sidebar collapse state.

**Architecture:** F7 is a path fix in `core/src/lib.rs` — the test references an external file; we redirect it to a checked-in fixture. F1 adds `SettingsRepository.update()` in `persistence.py` and migrates the two callers (`ThemeWorkflowCoordinator` and `SettingsController`) to use it, removing `MainWindow._current_ui_settings` as a cached copy that can drift.

**Tech Stack:** Rust / cargo (F7), Python 3.12 / pytest (F1)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `core/tests/fixtures/china.map` | Legacy palette fixture (256 RGB lines) |
| Modify | `core/src/lib.rs` | Update test to use `fixture_path` instead of external path |
| Modify | `ui/src/fractal_studio/persistence.py` | Add `SettingsRepository.update()` |
| Modify | `ui/tests/test_settings_repository.py` | New unit tests for `update()` |
| Modify | `ui/src/fractal_studio/application/workflows/theme_workflow_coordinator.py` | Use `repo.update()` instead of `repo.save(UiSettings(theme=name))` |
| Modify | `ui/src/fractal_studio/application/controllers/settings_controller.py` | Simplify `save_sidebar_collapsed()` to use `repo.update()` |
| Modify | `ui/src/fractal_studio/main_window.py` | Remove `_current_ui_settings`; simplify `_on_section_collapsed` |

---

## Task 1: Create the legacy palette fixture

**Files:**
- Create: `core/tests/fixtures/china.map`

The failing test `legacy_palette_parser_reads_existing_repo_map` references a file two directories above `core/` that doesn't exist in this repo. The fix redirects it to a checked-in fixture using the existing `fixture_path()` helper, which resolves relative to `CARGO_MANIFEST_DIR/tests/fixtures/`.

The `.map` format is 256 lines of three space-separated integers (R G B, each 0–255). The test only checks `palette.len() == 256` and that the first/last entries parse correctly, so any valid 256-line file works.

- [ ] **Step 1: Create the fixture directory if it doesn't exist**

```powershell
New-Item -ItemType Directory -Force core/tests/fixtures
```

- [ ] **Step 2: Generate the fixture file**

Create `core/tests/fixtures/china.map`. The file must have exactly 256 non-empty lines, each with three integers 0–255. Write this content (a simple grayscale ramp — values 0 through 255):

```
0 0 0
1 1 1
2 2 2
3 3 3
4 4 4
5 5 5
6 6 6
7 7 7
8 8 8
9 9 9
10 10 10
11 11 11
12 12 12
13 13 13
14 14 14
15 15 15
16 16 16
17 17 17
18 18 18
19 19 19
20 20 20
21 21 21
22 22 22
23 23 23
24 24 24
25 25 25
26 26 26
27 27 27
28 28 28
29 29 29
30 30 30
31 31 31
32 32 32
33 33 33
34 34 34
35 35 35
36 36 36
37 37 37
38 38 38
39 39 39
40 40 40
41 41 41
42 42 42
43 43 43
44 44 44
45 45 45
46 46 46
47 47 47
48 48 48
49 49 49
50 50 50
51 51 51
52 52 52
53 53 53
54 54 54
55 55 55
56 56 56
57 57 57
58 58 58
59 59 59
60 60 60
61 61 61
62 62 62
63 63 63
64 64 64
65 65 65
66 66 66
67 67 67
68 68 68
69 69 69
70 70 70
71 71 71
72 72 72
73 73 73
74 74 74
75 75 75
76 76 76
77 77 77
78 78 78
79 79 79
80 80 80
81 81 81
82 82 82
83 83 83
84 84 84
85 85 85
86 86 86
87 87 87
88 88 88
89 89 89
90 90 90
91 91 91
92 92 92
93 93 93
94 94 94
95 95 95
96 96 96
97 97 97
98 98 98
99 99 99
100 100 100
101 101 101
102 102 102
103 103 103
104 104 104
105 105 105
106 106 106
107 107 107
108 108 108
109 109 109
110 110 110
111 111 111
112 112 112
113 113 113
114 114 114
115 115 115
116 116 116
117 117 117
118 118 118
119 119 119
120 120 120
121 121 121
122 122 122
123 123 123
124 124 124
125 125 125
126 126 126
127 127 127
128 128 128
129 129 129
130 130 130
131 131 131
132 132 132
133 133 133
134 134 134
135 135 135
136 136 136
137 137 137
138 138 138
139 139 139
140 140 140
141 141 141
142 142 142
143 143 143
144 144 144
145 145 145
146 146 146
147 147 147
148 148 148
149 149 149
150 150 150
151 151 151
152 152 152
153 153 153
154 154 154
155 155 155
156 156 156
157 157 157
158 158 158
159 159 159
160 160 160
161 161 161
162 162 162
163 163 163
164 164 164
165 165 165
166 166 166
167 167 167
168 168 168
169 169 169
170 170 170
171 171 171
172 172 172
173 173 173
174 174 174
175 175 175
176 176 176
177 177 177
178 178 178
179 179 179
180 180 180
181 181 181
182 182 182
183 183 183
184 184 184
185 185 185
186 186 186
187 187 187
188 188 188
189 189 189
190 190 190
191 191 191
192 192 192
193 193 193
194 194 194
195 195 195
196 196 196
197 197 197
198 198 198
199 199 199
200 200 200
201 201 201
202 202 202
203 203 203
204 204 204
205 205 205
206 206 206
207 207 207
208 208 208
209 209 209
210 210 210
211 211 211
212 212 212
213 213 213
214 214 214
215 215 215
216 216 216
217 217 217
218 218 218
219 219 219
220 220 220
221 221 221
222 222 222
223 223 223
224 224 224
225 225 225
226 226 226
227 227 227
228 228 228
229 229 229
230 230 230
231 231 231
232 232 232
233 233 233
234 234 234
235 235 235
236 236 236
237 237 237
238 238 238
239 239 239
240 240 240
241 241 241
242 242 242
243 243 243
244 244 244
245 245 245
246 246 246
247 247 247
248 248 248
249 249 249
250 250 250
251 251 251
252 252 252
253 253 253
254 254 254
255 255 255
```

- [ ] **Step 3: Verify the file has exactly 256 lines**

```powershell
(Get-Content core/tests/fixtures/china.map | Measure-Object -Line).Lines
```
Expected: `256`

---

## Task 2: Fix the Rust test to use the fixture

**Files:**
- Modify: `core/src/lib.rs` (around line 1038)

- [ ] **Step 1: Update the test**

In `core/src/lib.rs`, find the test `legacy_palette_parser_reads_existing_repo_map` (around line 1038). Replace the entire `fs::read_to_string(...)` call argument with `fixture_path("china.map")`:

Current code (lines 1040–1047):
```rust
    fn legacy_palette_parser_reads_existing_repo_map() {
        let contents = fs::read_to_string(
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("..")
                .join("..")
                .join("Julia")
                .join("ColorMaps")
                .join("china.map"),
        )
        .unwrap();
```

Replace with:
```rust
    fn legacy_palette_parser_reads_existing_repo_map() {
        let contents = fs::read_to_string(fixture_path("china.map")).unwrap();
```

- [ ] **Step 2: Run the Rust test suite from core/**

```powershell
cd core && cargo test -q
```
Expected: all tests pass, including `legacy_palette_parser_reads_existing_repo_map`. No failures.

- [ ] **Step 3: Commit**

```powershell
git add core/tests/fixtures/china.map core/src/lib.rs
git commit -m "fix: use checked-in fixture for legacy_palette_parser_reads_existing_repo_map"
```

---

## Task 3: Add `SettingsRepository.update()` with unit tests

**Files:**
- Modify: `ui/src/fractal_studio/persistence.py`
- Modify: `ui/tests/test_settings_repository.py` (create if it doesn't exist)

The `update()` method performs a read-modify-write as a single operation. This is the only path that should write settings going forward.

- [ ] **Step 1: Check if `ui/tests/test_settings_repository.py` exists**

```powershell
Test-Path ui/tests/test_settings_repository.py
```

If it does not exist, create it. If it does exist, append the new tests below to it.

- [ ] **Step 2: Write the failing tests**

In `ui/tests/test_settings_repository.py`:

```python
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from fractal_studio.persistence import SettingsRepository
from fractal_studio.state import UiSettings


@pytest.mark.unit
def test_update_returns_transformed_settings(tmp_path: Path) -> None:
    repo = SettingsRepository(tmp_path / "settings.json")
    result = repo.update(lambda s: dataclasses.replace(s, theme="dark"))
    assert result.theme == "dark"


@pytest.mark.unit
def test_update_persists_to_disk(tmp_path: Path) -> None:
    repo = SettingsRepository(tmp_path / "settings.json")
    repo.update(lambda s: dataclasses.replace(s, theme="sepia"))
    reloaded = repo.load().settings
    assert reloaded.theme == "sepia"


@pytest.mark.unit
def test_update_preserves_other_fields(tmp_path: Path) -> None:
    repo = SettingsRepository(tmp_path / "settings.json")
    repo.update(lambda s: dataclasses.replace(s, sidebar_collapsed={"params": True}))
    repo.update(lambda s: dataclasses.replace(s, theme="dark"))
    final = repo.load().settings
    assert final.theme == "dark"
    assert final.sidebar_collapsed == {"params": True}


@pytest.mark.unit
def test_update_receives_current_stored_state(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    repo = SettingsRepository(path)
    repo.update(lambda s: dataclasses.replace(s, theme="sepia"))
    seen: list[UiSettings] = []
    repo.update(lambda s: seen.append(s) or s)
    assert seen[0].theme == "sepia"
```

- [ ] **Step 3: Run the tests to verify they fail**

```powershell
cd ui && pytest tests/test_settings_repository.py -v -m unit
```
Expected: `AttributeError: 'SettingsRepository' object has no attribute 'update'`

- [ ] **Step 4: Add `update()` to `SettingsRepository`**

In `ui/src/fractal_studio/persistence.py`, update the imports to include `Callable` and `TypeVar`, then add the method to `SettingsRepository` after `load()`:

```python
from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass
from collections.abc import Callable
from typing import Literal

from fractal_studio.state import (
    FavoriteSnapshot,
    UiSettings,
    deserialize_favorites_payload,
    deserialize_settings_payload,
    serialize_favorites_payload,
    serialize_settings_payload,
)
```

Then inside `SettingsRepository`, after `load()`:

```python
    def update(self, transform: Callable[[UiSettings], UiSettings]) -> UiSettings:
        current = self.load().settings
        updated = transform(current)
        self.save(updated)
        return updated
```

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
cd ui && pytest tests/test_settings_repository.py -v -m unit
```
Expected: 4 tests PASS.

- [ ] **Step 6: Run the full unit suite to verify nothing broke**

```powershell
cd ui && pytest -m unit -q
```
Expected: all existing unit tests PASS.

- [ ] **Step 7: Commit**

```powershell
git add ui/src/fractal_studio/persistence.py ui/tests/test_settings_repository.py
git commit -m "feat: add SettingsRepository.update() for aggregate settings writes"
```

---

## Task 4: Migrate `ThemeWorkflowCoordinator` to use `repo.update()`

**Files:**
- Modify: `ui/src/fractal_studio/application/workflows/theme_workflow_coordinator.py`

The problem is on line 51:
```python
persist_theme=lambda name: self._settings_repo.save(UiSettings(theme=name)),
```
This constructs a fresh `UiSettings(theme=name)`, losing `sidebar_collapsed` values.

- [ ] **Step 1: Add `dataclasses` import**

In `theme_workflow_coordinator.py`, add `import dataclasses` after the existing imports:

```python
from __future__ import annotations

import dataclasses
from collections.abc import Callable

from PySide6.QtWidgets import QApplication, QWidget
# ... rest unchanged
```

- [ ] **Step 2: Replace the `persist_theme` lambda**

Find:
```python
            persist_theme=lambda name: self._settings_repo.save(UiSettings(theme=name)),
```

Replace with:
```python
            persist_theme=lambda name: self._settings_repo.update(
                lambda s: dataclasses.replace(s, theme=name)
            ),
```

- [ ] **Step 3: Remove the now-unused `UiSettings` import if it's only used there**

Check if `UiSettings` is used anywhere else in the file:
```powershell
rg "UiSettings" ui/src/fractal_studio/application/workflows/theme_workflow_coordinator.py
```

If the only match is the line you just replaced, remove `UiSettings` from the import:

```python
from fractal_studio.state import ThemeSpec
```

(Remove the `UiSettings` part of the `from fractal_studio.state import ...` line.)

- [ ] **Step 4: Run the unit suite**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add ui/src/fractal_studio/application/workflows/theme_workflow_coordinator.py
git commit -m "fix: use repo.update() in ThemeWorkflowCoordinator to preserve sidebar state"
```

---

## Task 5: Simplify `SettingsController` and remove `_current_ui_settings` from `MainWindow`

**Files:**
- Modify: `ui/src/fractal_studio/application/controllers/settings_controller.py`
- Modify: `ui/src/fractal_studio/main_window.py`

Currently `save_sidebar_collapsed()` takes `current: UiSettings` as a parameter (the caller's cached copy, which may be stale). Using `repo.update()` means we always read the authoritative current state from disk, eliminating the stale-cache bug.

- [ ] **Step 1: Update `save_sidebar_collapsed()` in `settings_controller.py`**

Replace the entire method:

```python
    def save_sidebar_collapsed(
        self,
        repo: SettingsRepository,
        current: UiSettings,
        key: str,
        collapsed: bool,
    ) -> UiSettings:
        updated = replace(
            current,
            sidebar_collapsed={**current.sidebar_collapsed, key: collapsed},
        )
        repo.save(updated)
        return updated
```

with:

```python
    def save_sidebar_collapsed(
        self,
        repo: SettingsRepository,
        key: str,
        collapsed: bool,
    ) -> None:
        repo.update(
            lambda s: replace(s, sidebar_collapsed={**s.sidebar_collapsed, key: collapsed})
        )
```

The return type changes from `UiSettings` to `None` — callers no longer need the result.

- [ ] **Step 2: Remove now-unused imports from `settings_controller.py`**

The `UiSettings` import is no longer needed. Remove it:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any, Protocol

from PySide6.QtWidgets import QDialog, QWidget

from fractal_studio.persistence import SettingsRepository
```

(Remove `from fractal_studio.state import UiSettings`)

- [ ] **Step 3: Update `MainWindow._on_section_collapsed()`**

In `ui/src/fractal_studio/main_window.py`, find `_on_section_collapsed`:

```python
    def _on_section_collapsed(self, section_key: str, collapsed: bool) -> None:
        self._current_ui_settings = self._settings_controller.save_sidebar_collapsed(
            self._settings_repo, self._current_ui_settings, section_key, collapsed
        )
```

Replace with:

```python
    def _on_section_collapsed(self, section_key: str, collapsed: bool) -> None:
        self._settings_controller.save_sidebar_collapsed(
            self._settings_repo, section_key, collapsed
        )
```

- [ ] **Step 4: Remove `_current_ui_settings` from `MainWindow._init_window_state()`**

Find:
```python
        self._current_ui_settings = UiSettings()    # replaced in _finalize_startup
```

Delete that line.

- [ ] **Step 5: Remove the assignment in `_finalize_startup()`**

Find:
```python
        self._current_ui_settings = startup.load_result.settings
```

Delete that line.

- [ ] **Step 6: Remove the now-unused `UiSettings` import from `main_window.py`**

Check if `UiSettings` is used anywhere else:
```powershell
rg "UiSettings" ui/src/fractal_studio/main_window.py
```

If no matches remain, remove `from fractal_studio.state import UiSettings` from the imports.

- [ ] **Step 7: Run the unit suite**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

- [ ] **Step 8: Commit**

```powershell
git add ui/src/fractal_studio/application/controllers/settings_controller.py ui/src/fractal_studio/main_window.py
git commit -m "refactor: remove _current_ui_settings; settings writes always read from repo"
```

---

## Self-Review

**Spec coverage:**
- F7 (Rust test path): Tasks 1–2 ✓
- F1 (settings aggregate): Tasks 3–5 ✓
- `SettingsRepository.update()` is the single write path: Task 3 ✓
- `ThemeWorkflowCoordinator` no longer constructs fresh `UiSettings`: Task 4 ✓
- `save_sidebar_collapsed` no longer takes stale `current`: Task 5 ✓
- `_current_ui_settings` removed from `MainWindow`: Task 5 ✓

**Placeholder scan:** None.

**Type consistency:** `update(transform: Callable[[UiSettings], UiSettings]) -> UiSettings` defined in Task 3, used identically in Tasks 4 and 5.
