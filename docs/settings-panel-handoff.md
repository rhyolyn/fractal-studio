# Settings Panel Handoff

This note is a compact pointer for future settings work. The Appearance panel is the only section in scope for now.

Reference artifacts:
- Visual mockup: [settings-theme-mockup.html](./settings-theme-mockup.html)
- Theme implementation: [theme.py](../ui/src/fractal_studio/theme.py)
- Settings dialog and wiring: [main_window.py](../ui/src/fractal_studio/main_window.py)
- Regression coverage: [test_ui_redesign.py](../ui/tests/test_ui_redesign.py)

Planning options explored:
- A: Theme only (smallest scope)
- B: Appearance plus practical defaults (recommended if scope grows)
- C: Power-user preferences across multiple categories (deferred)

Theme options already explored in the mockup:
- Light
- Dark
- Sepia

Future work to consider next:
1. Use the app for a bit and judge whether the Appearance panel layout and spacing feel right in practice.
2. If adding more settings, do one small section next, such as export defaults or reduce motion.
3. Keep advanced settings collapsed until there is a concrete user need.
4. Decide later whether the brainstorm mockup files under `.superpowers/` should stay in the repo or be archived.
