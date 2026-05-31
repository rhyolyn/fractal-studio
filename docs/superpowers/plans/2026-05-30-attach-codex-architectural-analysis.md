# Attach Codex Analysis + Pages Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Link the Codex architectural analysis into the live `pages/` documentation site, clean up all dead MkDocs artifacts, and document how the `pages/` system works for future contributors.

**Architecture:** The live site is `pages/` — static HTML deployed by CI to GitHub Pages with no build step. `mkdocs.yml` and `docs/user-guide/` are vestigial MkDocs leftovers that never deploy and must be removed. The Codex analysis (`docs/codex-architectural-analysis-2026-05-30.md`) gets a matching `pages/codex-analysis.html` styled like the existing architecture page, plus sidebar links added to all 8 existing docs pages.

**Tech Stack:** HTML, CSS (existing `pages/styles.css` system), PowerShell for verification, AGENTS.md for documentation

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Delete | `mkdocs.yml` | Dead config — replaced by `pages/` static site, never referenced by CI |
| Delete | `docs/index.md` | Dead MkDocs home page |
| Delete | `docs/user-guide/viewport.md` | Dead MkDocs source — content lives in `pages/viewport.html` |
| Delete | `docs/user-guide/palette-editor.md` | Same |
| Delete | `docs/user-guide/export.md` | Same |
| Delete | `docs/user-guide/favorites.md` | Same |
| Delete | `docs/user-guide/settings.md` | Same |
| Modify | `README.md` | Remove two stale non-existent doc links; add Codex analysis; update project tree to include `pages/` |
| Create | `pages/codex-analysis.html` | Styled HTML page for the Codex analysis, matching site layout |
| Modify | `pages/architecture.html` | Add Codex Analysis to sidebar; rename own label to "Architecture Design"; update page-nav next link |
| Modify | `pages/viewport.html` | Add Codex Analysis to Developer sidebar group |
| Modify | `pages/palette-editor.html` | Same |
| Modify | `pages/export.html` | Same |
| Modify | `pages/favorites.html` | Same |
| Modify | `pages/settings.html` | Same |
| Modify | `pages/getting-started.html` | Same |
| Modify | `pages/changelog.html` | Same |
| Modify | `AGENTS.md` | Document the `pages/` site system for future agents and contributors |

---

## Task 1: Remove Dead MkDocs Artifacts

**Files:**
- Delete: `mkdocs.yml`
- Delete: `docs/index.md`
- Delete: `docs/user-guide/viewport.md`
- Delete: `docs/user-guide/palette-editor.md`
- Delete: `docs/user-guide/export.md`
- Delete: `docs/user-guide/favorites.md`
- Delete: `docs/user-guide/settings.md`

- [ ] **Step 1: Verify mkdocs.yml is not referenced anywhere in CI**

Run:
```powershell
rg -rn "mkdocs" .github
```
Expected:
```text
```
(No output — CI does not reference mkdocs.)

- [ ] **Step 2: Verify pages/ does not link to the docs/user-guide markdown files**

Run:
```powershell
rg -rn "user-guide/" pages
```
Expected:
```text
```
(No output — `pages/` HTML does not link to the markdown source files.)

- [ ] **Step 3: Delete dead files**

```powershell
Remove-Item mkdocs.yml
Remove-Item docs/index.md
Remove-Item docs/user-guide/viewport.md, docs/user-guide/palette-editor.md, docs/user-guide/export.md, docs/user-guide/favorites.md, docs/user-guide/settings.md
Remove-Item docs/user-guide
```

- [ ] **Step 4: Verify remaining docs/ files are exactly the ones that should stay**

Run:
```powershell
Get-ChildItem docs -Recurse -File | Select-Object -ExpandProperty FullName
```
Expected (order may vary):
```text
...\docs\architecture-design-2026-05-28.html
...\docs\architecture-design-2026-05-28.md
...\docs\codex-architectural-analysis-2026-05-30.md
...\docs\superpowers\...
```

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "chore: remove dead MkDocs artifacts (mkdocs.yml, docs/index.md, docs/user-guide/)"
```

---

## Task 2: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the documentation table**

In `README.md`, replace:

```markdown
| Document | Format |
|----------|--------|
| [Architectural Design Document](docs/architecture-design-2026-05-28.md) | Markdown + Mermaid |
| [Architectural Design Document](docs/architecture-design-2026-05-28.html) | Standalone HTML (open in browser) |
| [Architecture Analysis](docs/architecture-analysis-2026-05-27.md) | Markdown |
| [Architecture Improvement Spec](docs/superpowers/specs/2026-05-27-architecture-improvements-design.md) | Markdown |

The HTML document includes rendered diagrams and is the easiest way to read the architecture overview.
```

with:

```markdown
| Document | Format |
|----------|--------|
| [Architectural Design Document](docs/architecture-design-2026-05-28.md) | Markdown + Mermaid |
| [Architectural Design Document](docs/architecture-design-2026-05-28.html) | Standalone HTML (open in browser) |
| [Codex Architectural Analysis](docs/codex-architectural-analysis-2026-05-30.md) | Markdown |

The HTML document includes rendered diagrams and is the easiest way to read the architecture overview as a standalone file. The live documentation site at `pages/` is the canonical developer reference — see the [Developer section](pages/architecture.html) for the architecture page and the [Codex analysis](pages/codex-analysis.html) for an independent code review.
```

- [ ] **Step 2: Update the project structure listing**

In `README.md`, replace:

```text
└── docs/                        Architecture documentation
    ├── architecture-design-2026-05-28.md
    ├── architecture-design-2026-05-28.html
    └── architecture-analysis-2026-05-27.md
```

with:

```text
├── pages/                       Static documentation site (deployed to GitHub Pages via CI)
│   ├── index.html               Site home
│   ├── architecture.html        Developer — architecture design
│   ├── codex-analysis.html      Developer — independent Codex code review
│   └── styles.css               Shared stylesheet
│
└── docs/                        Architecture reference documents (GitHub-readable)
    ├── architecture-design-2026-05-28.md
    ├── architecture-design-2026-05-28.html
    └── codex-architectural-analysis-2026-05-30.md
```

- [ ] **Step 3: Update the architecture reference in Development Notes**

In `README.md`, replace:

```markdown
- **Architecture:** The Python UI follows a layered Ports & Adapters architecture with a Dependency Injection factory root. See the [architecture document](docs/architecture-design-2026-05-28.html) for full diagrams and SOLID analysis.
```

with:

```markdown
- **Architecture:** The Python UI follows a layered Ports & Adapters architecture with a Dependency Injection factory root. See the [architecture page](pages/architecture.html) on the live docs site, or open [docs/architecture-design-2026-05-28.html](docs/architecture-design-2026-05-28.html) as a standalone file.
```

- [ ] **Step 4: Verify no stale links remain**

Run:
```powershell
rg -n "architecture-analysis-2026-05-27|2026-05-27-architecture-improvements-design" README.md
```
Expected:
```text
```
(No output — stale links gone.)

- [ ] **Step 5: Commit**

```powershell
git add README.md
git commit -m "docs: fix README doc table, add Codex analysis, update project tree to include pages/"
```

---

## Task 3: Create pages/codex-analysis.html

**Files:**
- Create: `pages/codex-analysis.html`

This page converts the Codex analysis Markdown into styled HTML matching the existing `architecture.html` layout. It reuses the shared stylesheet and existing component classes (`.def`, `.prio`) with a small page-scoped `<style>` block for unique components (`.rev-meta`, `.assessment`, `.test-results`, `.sev`).

- [ ] **Step 1: Create pages/codex-analysis.html**

Create `pages/codex-analysis.html` with this exact content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Codex Analysis — Fractal Studio</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="styles.css">
<style>
  .rev-meta { display:flex; gap:30px; flex-wrap:wrap; margin:24px 0 0; padding:18px 0; border-top:1px solid var(--border); border-bottom:1px solid var(--border); }
  .rev-meta .am { display:flex; flex-direction:column; gap:4px; }
  .rev-meta .am .k { font-family:var(--mono); font-size:10.5px; letter-spacing:0.14em; text-transform:uppercase; color:var(--faint); }
  .rev-meta .am .v { font-size:14.5px; color:var(--text); }
  .assessment { display:inline-flex; align-items:flex-start; gap:14px; background:var(--bg-2); border:1px solid var(--border-2); border-left:2px solid var(--amber); padding:18px 24px; margin:24px 0; max-width:48em; }
  .assessment .icon { font-family:var(--mono); font-weight:500; font-size:13px; color:var(--amber); white-space:nowrap; padding-top:2px; }
  .assessment .at { font-size:14.5px; color:var(--muted); }
  .assessment .at strong { color:var(--text); }
  .test-results { border:1px solid var(--border); margin:18px 0; max-width:48em; }
  .test-row { display:flex; align-items:baseline; gap:16px; padding:14px 18px; border-bottom:1px solid var(--border); font-family:var(--mono); font-size:12px; flex-wrap:wrap; }
  .test-row:last-child { border-bottom:0; }
  .test-label { color:var(--muted); min-width:100px; }
  .test-cmd { color:var(--faint); flex:1; }
  .test-pass { color:var(--green); }
  .test-fail { color:var(--amber); }
  .sev { font-family:var(--mono); font-size:10px; padding:2px 7px; border:1px solid; margin-left:10px; vertical-align:middle; }
  .sev.high { color:var(--magenta); border-color:var(--magenta); }
  .sev.med-high { color:var(--amber); border-color:var(--amber); }
  .sev.med { color:var(--faint); border-color:var(--border-2); }
  @media (max-width:900px){ .rev-meta { gap:18px; } .test-row { flex-direction:column; gap:6px; } }
</style>
</head>
<body>

<header class="nav">
  <nav class="nav-inner">
    <a href="index.html" class="brand"><span class="mark"></span>Fractal Studio</a>
    <div class="nav-links">
      <a href="index.html">Home</a>
      <a href="getting-started.html">Getting&nbsp;Started</a>
      <a href="viewport.html">User&nbsp;Guide</a>
      <a href="changelog.html">Changelog</a>
      <a href="architecture.html" class="active">Developer</a>
    </div>
    <a href="https://github.com/rhyolyn/fractal-studio" class="nav-cta">/ GitHub</a>
  </nav>
</header>

<div class="docs">
  <aside class="docs-sidebar">
    <div class="ds-group">
      <a href="index.html">Home</a>
      <a href="getting-started.html">Getting Started</a>
    </div>
    <div class="ds-group">
      <span class="ds-label">User Guide</span>
      <a href="viewport.html">Fractal Viewport</a>
      <a href="palette-editor.html">Palette Editor</a>
      <a href="export.html">Export</a>
      <a href="favorites.html">Favorites</a>
      <a href="settings.html">Settings &amp; Themes</a>
    </div>
    <div class="ds-group">
      <span class="ds-label">Project</span>
      <a href="changelog.html">Changelog</a>
    </div>
    <div class="ds-group">
      <span class="ds-label">Developer</span>
      <a href="architecture.html">Architecture Design</a>
      <a href="codex-analysis.html" class="active">Codex Analysis</a>
    </div>
  </aside>

  <main class="docs-main">
    <div class="crumbs"><a href="index.html">Home</a> / Developer / Codex Analysis</div>
    <h1>Codex Architectural Analysis</h1>
    <p class="page-lead">An independent, source-code-only architectural review. Existing design documents were intentionally excluded so that findings reflect the code as-built rather than the code as-intended.</p>
    <div class="rev-meta">
      <div class="am"><span class="k">Date</span><span class="v">2026-05-30</span></div>
      <div class="am"><span class="k">Reviewer</span><span class="v">Codex</span></div>
      <div class="am"><span class="k">Scope</span><span class="v">ui/ + core/ source only</span></div>
    </div>

    <h2 data-n="01" id="summary">Executive summary</h2>
    <div class="assessment">
      <span class="icon">MID-REFACTOR</span>
      <span class="at"><strong>Structurally promising, but currently over-coupled at the UI/application boundary.</strong> The next architectural work should focus less on adding more layers and more on making the existing boundaries real.</span>
    </div>
    <p>Fractal Studio has a promising architectural direction: a Python/PySide6 desktop shell, a Rust rendering core, immutable state objects, a composition root, and an attempted ports/adapters boundary around window sections.</p>
    <p>The codebase is partway through a refactor. Several names and folders suggest a clean layered architecture, but key dependencies still flow through concrete Qt widgets, private <code>MainWindow</code> state, and synchronous backend calls. The highest-risk issues are settings persistence overwriting sibling fields, rendering/export work blocking the UI thread, and the section ports layer depending on a half-wired <code>MainWindow</code>.</p>

    <h2 data-n="02" id="method">Review method</h2>
    <p>Based on source files under <code>ui/</code> and <code>core/</code> only. Generated docs were not used as inputs.</p>
    <div class="test-results">
      <div class="test-row">
        <span class="test-label">Python</span>
        <code class="test-cmd">cd ui &amp;&amp; python -m pytest -q</code>
        <span class="test-pass">11 passed, 143 deselected</span>
      </div>
      <div class="test-row">
        <span class="test-label">Rust</span>
        <code class="test-cmd">cd core &amp;&amp; cargo test -q</code>
        <span class="test-fail">23 passed, 1 failed — legacy_palette_parser_reads_existing_repo_map (path not found from core/)</span>
      </div>
    </div>

    <h2 data-n="03" id="findings">Key findings</h2>

    <div class="def">
      <div class="dc"><span class="dcode">F1</span><span class="dname">Settings writes can erase each other<span class="sev high">HIGH</span></span></div>
      <p>Theme persistence writes a fresh <code>UiSettings(theme=name)</code>, losing any existing <code>sidebar_collapsed</code> values. Sidebar collapse persistence reads from <code>MainWindow._current_ui_settings</code>, which is not updated when the theme changes.</p>
      <p>User-visible behavior: changing the theme can erase sidebar state; toggling a sidebar section after a theme change can save the old theme back to disk.</p>
      <div class="rec"><strong>Fix</strong> &nbsp;Centralize settings updates behind one aggregate update path. Each write should load the current full <code>UiSettings</code>, replace exactly one field, and save the whole object: <code>def update_settings(repo, transform: Callable[[UiSettings], UiSettings]) -&gt; UiSettings</code></div>
    </div>

    <div class="def">
      <div class="dc"><span class="dcode">F2</span><span class="dname">Rendering and export block the UI thread<span class="sev high">HIGH</span></span></div>
      <p>Viewport rendering calls the Rust backend synchronously from the Qt event path. Export calls <code>QApplication.processEvents()</code> as a workaround. There is no Python-side worker abstraction, no cancellation, no progress reporting, and no render generation token.</p>
      <div class="rec"><strong>Fix</strong> &nbsp;Introduce a render job boundary. Components: <code>RenderRequest</code> (formula, bounds, dimensions, palette), <code>RenderResult</code> (request id, bytes, status), <code>RenderWorker</code> (off-thread Rust calls), <code>RenderScheduler</code> (coalesces viewport requests, drops stale results), <code>ExportJob</code> (long-running workflow with progress and cancellation). The existing debounce timer dispatches work rather than rendering directly.</div>
    </div>

    <div class="def">
      <div class="dc"><span class="dcode">F3</span><span class="dname">Section ports depend on a half-built MainWindow<span class="sev high">HIGH</span></span></div>
      <p>The factory builds section ports from <code>window</code> before context is attached. The base adapter reaches into <code>owner._sections_state</code>, a private object populated later. The composition root is split across <code>main_window_factory.py</code>, <code>MainWindow.attach_context()</code>, and <code>MainWindowSectionsState.bind()</code>.</p>
      <div class="rec"><strong>Fix</strong> &nbsp;Construct repositories, services, controllers, coordinators, backend, and panel states directly in <code>main_window_factory.py</code>. Build section port adapters from explicit panel state objects, not from <code>MainWindow</code>. Keep <code>MainWindow</code> responsible for shell lifecycle only.</div>
    </div>

    <div class="def">
      <div class="dc"><span class="dcode">F4</span><span class="dname">Application and service layers import concrete Qt widgets<span class="sev med-high">MED-HIGH</span></span></div>
      <p>The application/service layer accepts or imports <code>QWidget</code>, <code>QFileDialog</code>, <code>QApplication</code>, <code>FractalViewportWidget</code>, <code>FractalParamsPanel</code>, <code>ColorCubeEditor</code>, and <code>PalettePreviewWidget</code>. Export service reads viewport state and palette directly from <code>FractalViewportWidget</code>; palette service owns file dialog calls; favorites controller restores directly into widget instances.</p>
      <div class="rec"><strong>Fix</strong> &nbsp;Push widget reads/writes to the UI edge and pass data transfer objects inward. Better signatures: <code>ExportService.export_render(request: RenderRequest, destination: Path, status: Callable)</code>, <code>PaletteWorkflowService.save_palette(path, control_points, palette_size)</code>.</div>
    </div>

    <div class="def">
      <div class="dc"><span class="dcode">F5</span><span class="dname">Backend availability is a partial facade, not a null object<span class="sev med">MED</span></span></div>
      <p><code>CoreBackend.profile()</code> returns defaults when Rust is absent, but operational methods call <code>_require()</code> and raise. Other callers check <code>backend.available</code> manually. The contract is inconsistent: is it a null object with safe defaults, or a required dependency that must be guarded before use?</p>
      <div class="rec"><strong>Fix</strong> &nbsp;Split capability description from execution. Introduce <code>BackendCapabilities(can_render, can_generate_palette, ...)</code> and explicit backend protocols (<code>RenderBackend</code>, <code>PaletteBackend</code>). UI enables/disables features from capabilities; execution code depends on protocol types.</div>
    </div>

    <div class="def">
      <div class="dc"><span class="dcode">F6</span><span class="dname">MainWindowSectionsState is state holder and composition sub-root<span class="sev med">MED</span></span></div>
      <p>Stores repositories, services, controllers, coordinators, backend state, section state, and widget references. Its <code>bind()</code> method constructs six panel state machines and wires lambdas between them — at least three distinct jobs for one class. Dependencies become available through broad shared state rather than explicit constructor arguments.</p>
      <div class="rec"><strong>Fix</strong> &nbsp;Reduce to a panel-state container. Construction belongs in the composition root: <code>@dataclass class MainWindowSectionsState: viewport / sidebar / palette / colormap / favorites / export</code></div>
    </div>

    <div class="def">
      <div class="dc"><span class="dcode">F7</span><span class="dname">Rust test suite has a path assumption<span class="sev med">MED</span></span></div>
      <p><code>cargo test -q</code> fails in <code>tests::legacy_palette_parser_reads_existing_repo_map</code> because a referenced path is not found from <code>core/</code>. The Rust core cannot be verified with one standard command.</p>
      <div class="rec"><strong>Fix</strong> &nbsp;Move the fixture into <code>core/tests/fixtures/</code>, or compute the path relative to <code>CARGO_MANIFEST_DIR</code> and skip if the external sample is intentionally optional.</div>
    </div>

    <h2 data-n="04" id="strengths">Architectural strengths</h2>
    <ul>
      <li>Clear Python UI / Rust core split with a compact PyO3 bridge that is easy to locate.</li>
      <li><code>state.py</code> uses frozen dataclasses for persisted state — immutable and serializable.</li>
      <li>The UI has begun moving widget behavior into controllers and coordinators.</li>
      <li>Pytest markers configured so the default Python test run stays lightweight without PySide6.</li>
      <li>Meaningful Rust unit coverage for palette generation, rendering variants, and serialization.</li>
      <li><code>SectionPanel</code> / <code>ViewportWell</code> direction is good: focused widgets with narrow responsibilities.</li>
    </ul>

    <h2 data-n="05" id="priorities">Recommended priority order</h2>
    <table>
      <thead><tr><th>#</th><th>Work item</th><th>Severity</th></tr></thead>
      <tbody>
        <tr><td>1</td><td>Fix settings persistence so theme and sidebar state cannot overwrite each other (F1)</td><td><span class="sev high">HIGH</span></td></tr>
        <tr><td>2</td><td>Introduce a render/export job abstraction with worker execution and stale-result handling (F2)</td><td><span class="sev high">HIGH</span></td></tr>
        <tr><td>3</td><td>Move panel-state construction into <code>main_window_factory.py</code> (F3)</td><td><span class="sev high">HIGH</span></td></tr>
        <tr><td>4</td><td>Rebuild section port adapters around explicit panel state, not <code>MainWindow</code> (F3)</td><td><span class="sev high">HIGH</span></td></tr>
        <tr><td>5</td><td>Push concrete Qt widget dependencies out of application/services into the UI edge (F4)</td><td><span class="sev med-high">MED-HIGH</span></td></tr>
        <tr><td>6</td><td>Clarify backend capabilities versus execution — split facade from null object (F5, F6)</td><td><span class="sev med">MED</span></td></tr>
        <tr><td>7</td><td>Fix the failing Rust path-dependent test (F7)</td><td><span class="sev med">MED</span></td></tr>
      </tbody>
    </table>

    <h2 data-n="06" id="bottom-line">Bottom line</h2>
    <p>The app is not badly architected; it is mid-refactor. The main risk is that architectural names are currently cleaner than the actual dependency flow. The next step is to make the existing boundaries honest: one settings aggregate owner, one render job boundary, one composition root, and application services that operate on data rather than widgets.</p>

    <p style="font-family:var(--mono);font-size:12px;color:var(--faint);margin-top:40px;border-top:1px solid var(--border);padding-top:18px;">Codex code-only review · 2026-05-30 · Source files under ui/ and core/ only; generated docs intentionally excluded.</p>

    <div class="page-nav">
      <a href="architecture.html"><div class="dir">← Previous</div><div class="ttl">Architecture Design</div></a>
      <a href="https://github.com/rhyolyn/fractal-studio" class="next"><div class="dir">Next →</div><div class="ttl">Repository ↗</div></a>
    </div>
  </main>

  <aside class="docs-toc">
    <span class="ds-label">On this page</span>
    <a href="#summary" class="active">Summary</a>
    <a href="#method">Review method</a>
    <a href="#findings">Key findings</a>
    <a href="#strengths">Strengths</a>
    <a href="#priorities">Priority order</a>
    <a href="#bottom-line">Bottom line</a>
  </aside>
</div>

<div class="spectrum-rule"></div>

<script>
  const links = [...document.querySelectorAll('.docs-toc a')];
  const ids = links.map(l => l.getAttribute('href').slice(1));
  const spy = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { const id = e.target.id; links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === '#' + id)); } });
  }, { rootMargin: '-70px 0px -75% 0px' });
  ids.forEach(id => { const el = document.getElementById(id); if (el) spy.observe(el); });
</script>
</body>
</html>
```

- [ ] **Step 2: Verify file was created**

Run:
```powershell
Test-Path pages\codex-analysis.html
```
Expected:
```text
True
```

- [ ] **Step 3: Commit**

```powershell
git add pages/codex-analysis.html
git commit -m "feat: add pages/codex-analysis.html — styled Codex analysis page"
```

---

## Task 4: Wire Codex Analysis Into All Page Sidebars

**Files:**
- Modify: `pages/architecture.html` (sidebar + page-nav)
- Modify: `pages/viewport.html` (sidebar only)
- Modify: `pages/palette-editor.html` (sidebar only)
- Modify: `pages/export.html` (sidebar only)
- Modify: `pages/favorites.html` (sidebar only)
- Modify: `pages/settings.html` (sidebar only)
- Modify: `pages/getting-started.html` (sidebar only)
- Modify: `pages/changelog.html` (sidebar only)

**Background:** Every docs page has a sidebar with a Developer group that currently reads:
```html
      <span class="ds-label">Developer</span>
      <a href="architecture.html">Architecture</a>
```
(On `architecture.html` itself, the link has `class="active"`; other pages do not.)

The target state for all non-active pages is:
```html
      <span class="ds-label">Developer</span>
      <a href="architecture.html">Architecture Design</a>
      <a href="codex-analysis.html">Codex Analysis</a>
```

On `architecture.html`, the `architecture.html` link keeps `class="active"`. On `codex-analysis.html` (already created in Task 3), the `codex-analysis.html` link has `class="active"`.

- [ ] **Step 1: Update architecture.html sidebar**

In `pages/architecture.html`, replace:
```html
      <span class="ds-label">Developer</span>
      <a href="architecture.html" class="active">Architecture</a>
```
with:
```html
      <span class="ds-label">Developer</span>
      <a href="architecture.html" class="active">Architecture Design</a>
      <a href="codex-analysis.html">Codex Analysis</a>
```

- [ ] **Step 2: Update architecture.html page-nav next link**

In `pages/architecture.html`, replace:
```html
      <a href="https://github.com/rhyolyn/fractal-studio" class="next"><div class="dir">Next →</div><div class="ttl">Repository ↗</div></a>
```
with:
```html
      <a href="codex-analysis.html" class="next"><div class="dir">Next →</div><div class="ttl">Codex Analysis</div></a>
```

- [ ] **Step 3: Update the remaining 7 pages using a PowerShell replace**

The other 7 pages all share the same Developer group pattern (no `class="active"` on the architecture link). Run this script:

```powershell
$pages = @('viewport', 'palette-editor', 'export', 'favorites', 'settings', 'getting-started', 'changelog')
$old = "      <span class=""ds-label"">Developer</span>`n      <a href=""architecture.html"">Architecture</a>"
$new = "      <span class=""ds-label"">Developer</span>`n      <a href=""architecture.html"">Architecture Design</a>`n      <a href=""codex-analysis.html"">Codex Analysis</a>"
foreach ($page in $pages) {
    $path = "pages/$page.html"
    $content = Get-Content $path -Raw
    if ($content -notmatch [regex]::Escape($old)) {
        Write-Warning "$path: pattern not found — inspect manually"
    } else {
        $content = $content.Replace($old, $new)
        Set-Content $path $content -NoNewline
        Write-Host "Updated $path"
    }
}
```

Expected output:
```text
Updated pages/viewport.html
Updated pages/palette-editor.html
Updated pages/export.html
Updated pages/favorites.html
Updated pages/settings.html
Updated pages/getting-started.html
Updated pages/changelog.html
```

If any page prints a warning instead of "Updated", open that file, find the Developer `ds-group` block, and apply the replacement manually using the same target state shown above.

- [ ] **Step 4: Verify all 9 docs pages reference codex-analysis.html**

Run:
```powershell
rg -ln "codex-analysis.html" pages
```
Expected (9 files):
```text
pages/architecture.html
pages/changelog.html
pages/codex-analysis.html
pages/export.html
pages/favorites.html
pages/getting-started.html
pages/palette-editor.html
pages/settings.html
pages/viewport.html
```

- [ ] **Step 5: Verify the old single "Architecture" label is gone from all sidebars**

Run:
```powershell
rg -n ">Architecture<" pages
```
Expected:
```text
```
(No output — all instances renamed to "Architecture Design" or "Codex Analysis".)

- [ ] **Step 6: Commit**

```powershell
git add pages/
git commit -m "feat: add Codex Analysis to sidebar and update page-nav across all docs pages"
```

---

## Task 5: Document the pages/ System in AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Append a Documentation Site section to AGENTS.md**

At the end of `AGENTS.md`, add:

````markdown

## Documentation Site (`pages/`)

The live documentation site is `pages/` — static HTML deployed to GitHub Pages by `.github/workflows/docs.yml` via `peaceiris/actions-gh-pages`. There is no build step; the HTML files are the source. The CI trigger path is `pages/**`.

### Structure

```
pages/
├── index.html            Home (hero + feature cards)
├── getting-started.html  Quick start guide
├── viewport.html         User guide — fractal viewport
├── palette-editor.html   User guide — palette editor
├── export.html           User guide — export
├── favorites.html        User guide — favorites
├── settings.html         User guide — settings and themes
├── changelog.html        Changelog
├── architecture.html     Developer — architecture design (B+ grade, SOLID analysis)
├── codex-analysis.html   Developer — independent Codex code review
└── styles.css            Shared stylesheet (CSS custom properties + component classes)
```

### Page anatomy

Every docs page shares this three-column layout:

```html
<header class="nav">…</header>
<div class="docs">
  <aside class="docs-sidebar">…</aside>   <!-- left nav, duplicated in every file -->
  <main class="docs-main">…</main>        <!-- page content -->
  <aside class="docs-toc">…</aside>       <!-- right in-page TOC (optional) -->
</div>
<div class="spectrum-rule"></div>
<script>/* IntersectionObserver TOC spy — copy verbatim from any existing page */</script>
```

### Adding a new page

1. Copy the nearest existing page as a starting point.
2. Set `class="active"` on the correct top-nav link and the correct sidebar link.
3. Add the new page's sidebar link to **every** existing page's sidebar — the sidebar is duplicated across all files.
4. Update the preceding page's `page-nav` next link to point to the new page.
5. Update `README.md`'s project structure listing.

### Shared CSS conventions

Key custom properties defined in `styles.css`:

| Property | Role |
|---|---|
| `--mono` | IBM Plex Mono |
| `--display` | Bricolage Grotesque |
| `--text`, `--muted`, `--faint` | Text hierarchy |
| `--green`, `--amber`, `--magenta`, `--cyan` | Semantic accent colors |
| `--border`, `--border-2`, `--bg-2` | Surfaces and borders |

Reusable component classes for developer pages: `.def` (finding/deficiency cards with `dcode`+`dname`+`rec`), `.prio` (severity badges high/med/low), `.arch-meta` / `.rev-meta` (metadata strips), `.diagram-ph` (diagram placeholders).

### Dead artifacts — do not restore

`mkdocs.yml` and `docs/user-guide/*.md` were MkDocs source files removed when the site was replaced with `pages/`. The CI workflow has never referenced `mkdocs.yml`. The content from `docs/user-guide/` now lives in the corresponding `pages/*.html` files. Do not add these files back.
````

- [ ] **Step 2: Verify the section was appended**

Run:
```powershell
rg -n "Documentation Site" AGENTS.md
```
Expected:
```text
AGENTS.md:<line>:## Documentation Site (`pages/`)
```

- [ ] **Step 3: Commit**

```powershell
git add AGENTS.md
git commit -m "docs: document the pages/ static site system in AGENTS.md"
```

---

## Self-Review

**Spec coverage:**

- Dead MkDocs artifacts removed (`mkdocs.yml`, `docs/index.md`, `docs/user-guide/*.md`): Task 1 ✓
- Stale README doc links removed: Task 2 ✓
- Codex analysis linked from README: Task 2 ✓
- `pages/` documented in README project tree: Task 2 ✓
- Codex analysis as live HTML page (`pages/codex-analysis.html`): Task 3 ✓
- Codex analysis in sidebar of all 8 existing docs pages: Task 4 ✓
- `architecture.html` page-nav points to Codex Analysis (not dead-end to GitHub): Task 4 ✓
- `pages/` system documented for future agents/contributors: Task 5 ✓

**Placeholder scan:**

- Task 4 Step 3 uses a PowerShell script with a warning path for files that don't match the expected pattern. This is not a placeholder — it handles the real risk that whitespace/quotes differ across files, and gives the implementer a clear fallback action.
- All HTML in Task 3 is complete and self-contained.
- No TBD, TODO, or "similar to Task N" shorthand anywhere.

**Type consistency:**

- Filename `codex-analysis.html` used consistently across all tasks.
- Link label "Architecture Design" used consistently wherever the `architecture.html` link is renamed.
- Link label "Codex Analysis" used consistently for `codex-analysis.html`.
- CSS class `.sev` (with modifiers `.high`, `.med-high`, `.med`) defined in Task 3 and referenced only within that page's `<style>` block — no cross-page dependency.
