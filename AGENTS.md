# AGENTS.md

This file captures collaboration preferences, engineering standards, and working defaults for this repository. It is written for AI coding agents first, but it should also be readable and useful to human collaborators.

## Purpose

- Preserve user preferences across sessions.
- Reduce repeated onboarding and avoid re-litigating known working agreements.
- Favor good architecture, safe change management, and direct communication.

## How To Work With The User

- Treat the user as a technical collaborator, not just a requester.
- Be direct. Do not sugarcoat real risks, weak architecture, or bad tradeoffs.
- Optimize for a balance of speed, caution, and explanation.
- When requirements are ambiguous, present options with a recommendation before acting.
- Adapt response depth to the task, but include enough reasoning and verification detail that the result can be trusted.
- If a broader improvement is nearby but not strictly required, present the tradeoff and let the user choose.

## Decision-Making Defaults

- Do not ignore architecture in the name of short-term speed.
- Prefer solutions with strong boundaries, clear responsibilities, and clean abstractions.
- If existing local patterns are weak, prefer the better pattern even if it introduces some inconsistency.
- If language or framework conventions conflict with preferred structure, call out the conflict and recommend a path rather than resolving it silently.
- For build, rollout, verification, and operationally sensitive work, recommend the workflow based on blast radius, rerun cost, and system risk.

## Git And Change Safety

- Avoid risky git moves.
- Be proactive about commits and pull requests when work is truly ready.
- Do not make destructive or hard-to-undo source control changes without clear justification.
- Existing local changes may be reorganized when it clearly helps complete the task, but call out conflicts or risky rewrites first.
- Treat shared workspace state carefully. Preserve user intent when touching in-progress work.

## Architecture Principles

- Follow SOLID principles.
- If SOLID principles conflict in a given design, analyze the tradeoff explicitly and present it to the user before committing to a direction.
- Introduce interfaces or abstract base classes early when they clarify boundaries and intent.
- Split classes into smaller collaborators as soon as a class has more than one clear responsibility.
- Prefer aggressive decomposition into smaller focused files and units when it improves understanding.
- Favor strong architecture even when it leads to larger refactors, but present the scope and payoff before making broad structural changes.
- Start from a clean design, then compromise where real engine, toolchain, or build constraints require it.
- For dependencies and reuse decisions, present the tradeoff and recommend whether to reuse, wrap, replace, or introduce a new abstraction.

## Coding Style Preferences

- Names should be clear, human-readable, and grammatically sensible.
- Use clean coding conventions for concrete grammar and parts of speech in names.
- Prefer the repository guard/logging macros such as `RETURN_FALSE_IF`, `RETURN_FALSE_QUIETLY_IF`, `RETURN_IF_FALSE`, `RETURN_QUIETLY_IF`, `CONTINUE_IF`, and `CONTINUE_QUIETLY_IF` for simple early-exit checks instead of introducing long 5+ line `if` blocks with manual logging and returns.
- Log failures at the lowest level that has enough context to diagnose the problem, then propagate failure silently through callers with quiet guard macros so the same error is not duplicated up the stack.
- Prefer explicit, descriptive names over short names.
- Prefer very small functions.
- Strongly prefer functions under 5 lines when practical, but favor clarity over mechanical splitting.
- Keep function parameter counts at 2 or fewer when practical.
- Favor clear code first, then document non-obvious intent and constraints.
- Refactor duplication early. If a meaningful pattern appears twice, look for the right abstraction.
- Prefer keeping prototypes, function definitions, and function calls on a single line when practical.
- Avoid splitting lines unless a single line becomes genuinely hard to read or conflicts with tooling.
- In `.cpp` files, prefer core class functionality near the top and local helper function bodies at the bottom; use compact forward declarations when C++ requires names before use.

## Class Organization

When language and local style make it reasonable, organize classes in this order:

1. Dunder methods or language-equivalent lifecycle methods
2. Properties and field-like declarations
3. Public methods
4. Protected methods
5. Private methods

If this ordering conflicts with strong local framework conventions, surface the conflict and recommend the best path.

- Keep function and prototype ordering tidy and intention-revealing.
- Group declarations by role and audience so public runtime or user-facing APIs are not interrupted by persistence-only or internal support methods.
- Within a visibility section, prefer stable, readable ordering over accidental insertion order.
- Put Blueprint-callable functions at the top of their class section so editor-facing APIs are easy to find.
- Put helper and persistence-only prototypes below the user-facing or Blueprint-facing APIs.
- Use a blank line between Blueprint-callable function declarations for readability.
- Do not add blank lines between adjacent non-Blueprint function prototypes; keep non-BP prototype blocks tight.
- Keep `.cpp` function definition order aligned with the corresponding `.h` prototype order.

## Error Handling

- Do not apply one blanket rule everywhere.
- Analyze the code path and recommend the right balance between fail-fast behavior, assertions, graceful handling, and defensive checks.
- Keep the happy path simple when possible, but do not hide important failure modes.

## Testing And Verification

- Prefer TDD when practical.
- Keep tests small and focused.
- Prefer parameterized tests when they reduce duplication without making intent harder to read.
- Prioritize catching regressions aggressively before merge.
- In review, balance bugs, maintainability, and test gaps, but call out the highest-risk issue first.
- For verification level, present options and recommend the right level based on the scope and risk of the change.

## Review Priorities

- First priority: correctness, regressions, and behavioral risk.
- Second priority: architecture and maintainability.
- Third priority: test coverage gaps, rollout concerns, and operational risk.
- Do not let style comments crowd out material engineering risks.

## Build And Release Work

- Recommend workflows based on what can break and how expensive reruns are.
- Favor repeatable and understandable release steps.
- Be explicit about assumptions, artifact names, paths, and verification steps when working on build or release tasks.

## Repo Builder Commands

- Prefer the Builder-based scripts in `root/builder/src` instead of calling Unreal build tools directly.
- From the shared workspace root (`d:\p4\ss`), call scripts as `python root/builder/src/<script>.py`.
- From the Unreal repo root (`d:\p4\ss\root`), call scripts as `python builder/src/<script>.py`.
- `Builder` discovers the Unreal repo root through `UnrealPathFinder` and writes default logs under `<repo-root>/scout_logs`.
- Build the game/editor target with `python root/builder/src/build_game.py`.
- Run all Scout automation tests with `python root/builder/src/run_automation_tests.py --repo-root root`.
- Run focused automation tests by passing test names or prefixes as positional args, for example `python root/builder/src/run_automation_tests.py --repo-root root Scout.AssetTracker`.
- Generate project files with `python root/builder/src/generate_project_files.py --repo-root root`.
- If a build reports Live Coding is active even after Unreal is closed, check for stale Unreal/editor processes before retrying.

## Communication Preferences

- Be concise when the task is simple.
- Go deep on reasoning, tradeoffs, and verification details when the task is complex or risky.
- Use a direct tone for code review and technical critique.
- When uncertain, show the options, recommend one, and explain why.

## Repo-Specific Guidance

- Add concrete repository conventions here as they become stable enough to standardize.
- Prefer updating this file when recurring guidance appears in multiple sessions.

## Anti-Patterns To Avoid

- Ignoring architecture to get to a quick patch.
- Making risky git moves without necessity.
- Letting duplication spread when a real abstraction is already visible.
- Hiding important tradeoffs instead of surfacing them.
- Asking unnecessary questions when a recommendation would unblock the work.
