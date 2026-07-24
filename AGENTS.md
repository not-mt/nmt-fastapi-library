# Agent Instructions

## Purpose
- This repo is the shared nmtfast library used by the sibling application repos.
- Put reusable auth, cache, HTMX, middleware, retry, settings, logging, task, discovery, error, and repository helpers here.
- Keep the package app-agnostic and reusable across multiple apps.

## Primary Goal
- Find the smallest owning package for the requested behavior and edit there first.
- Prefer additive, reusable changes over app-specific shortcuts.
- Mirror package changes with tests in the corresponding tests/ path.

## Python Standards
- PEP 8: Ensure code follows standard conventions for indention, line length, naming, imports, blank lines, etc.
- PEP 420 (implicit namespace packages): NEVER create `__init__.py` files. The project uses implicit namespace packages. Package directories exist without `__init__.py`.
- PEP 585 (built-in generic types): Use `list[str]`, `dict[str, int]`, etc. instead of `typing.List`, `typing.Dict`.
- PEP 484 (type hints): All non-test code must have PEP 484 compliant type hints.
- PEP 257 (Google style docstrings): All functions and classes must have Google-style docstrings with `"""` on their own lines.

## Hard Rules
- Do not import application code from sibling repos into this library.
- Do not add app-specific routes, templates, settings names, or business workflows here.
- Preserve public APIs when possible. Prefer additive changes over breaking ones.
- Prefer extending an existing v1 package over creating a parallel top-level namespace.
- Keep helpers generic enough to serve multiple callers, not just the current app.
- If a behavior is only needed by one app, keep it in that app repo instead of moving it here.

## Key Paths
- pyproject.toml: Poetry dependencies and tool configuration.
- src/nmtfast/auth/v1/: Authentication helpers and policies.
- src/nmtfast/cache/v1/: Cache helpers and integrations.
- src/nmtfast/discovery/v1/: Discovery and registration helpers.
- src/nmtfast/errors/v1/: Shared error types and helpers.
- src/nmtfast/htmx/v1/: HTMX helpers and response utilities.
- src/nmtfast/logging/v1/: Logging helpers.
- src/nmtfast/middleware/v1/: Reusable middleware.
- src/nmtfast/repositories/gadgets/: Shared gadget repository helpers.
- src/nmtfast/repositories/widgets/: Shared widget repository helpers.
- src/nmtfast/retry/v1/: Retry utilities.
- src/nmtfast/settings/v1/: Shared settings and configuration helpers.
- src/nmtfast/tasks/v1/: Shared task helpers and integrations.
- tests/: Test tree mirrors src/nmtfast/.
- tests/auth/: Authentication tests.
- tests/cache/: Cache tests.
- tests/discovery/: Discovery tests.
- tests/errors/: Error tests.
- tests/htmx/: HTMX helper tests.
- tests/logging/: Logging tests.
- tests/middleware/: Middleware tests.
- tests/repositories/: Shared repository helper tests.
- tests/retry/: Retry tests.
- tests/settings/: Settings tests.
- tests/tasks/: Task tests.

## How To Route Changes
- Authentication behavior: start in src/nmtfast/auth/v1/.
- Cache behavior: start in src/nmtfast/cache/v1/.
- Discovery or registration behavior: start in src/nmtfast/discovery/v1/.
- Shared HTMX helpers: start in src/nmtfast/htmx/v1/.
- Logging, middleware, retry, settings, or task helpers: start in the matching src/nmtfast/*/v1/ package.
- Shared repository adapters or helper clients: start in src/nmtfast/repositories/.
- Shared error contracts or error translation: start in src/nmtfast/errors/v1/.
- If a proposed change needs app-specific branching, stop and keep that behavior in the app repo instead.

## Test Mapping
- src/nmtfast/auth/ -> tests/auth/
- src/nmtfast/cache/ -> tests/cache/
- src/nmtfast/discovery/ -> tests/discovery/
- src/nmtfast/errors/ -> tests/errors/
- src/nmtfast/htmx/ -> tests/htmx/
- src/nmtfast/logging/ -> tests/logging/
- src/nmtfast/middleware/ -> tests/middleware/
- src/nmtfast/repositories/ -> tests/repositories/
- src/nmtfast/retry/ -> tests/retry/
- src/nmtfast/settings/ -> tests/settings/
- src/nmtfast/tasks/ -> tests/tasks/
- Add new tests for new shared behavior and update existing tests when behavior changes.

## Workspace Boundaries
- nmt-fastapi-library/: Reusable cross-app infrastructure belongs here.
- ../nmt-fastapi-reference/: Backend API-specific behavior stays there.
- ../nmt-fastapi-reference-web/: Web UI, HTMX page flows, and templates stay there.
- Do not move app-specific logic into this repo just to avoid duplication in a single change.

## Conventions That Matter Most
- Design for reuse across apps instead of the current caller only.
- Keep public APIs stable unless the requested change requires a breaking change.
- Prefer versioned modules under v1/ for new shared functionality when the existing structure allows it.
- Keep external integrations wrapped behind narrow helpers or adapters.
- Tool-driven docstring, lint, and type-check behavior are defined by pyproject.toml and the commands below.

## Validation Workflow
- Prefer poetry run commands instead of relying on shell activation state.
- During iteration, run the narrowest relevant pytest target for the touched package first.
- After the first passing focused test, run the full project test suite.
- If you add or change Python code, also run coverage, lint, and type checks before finishing.
- If you change a shared public surface, make sure tests cover both success and failure behavior.

## Commands
- Activate local environment: source .venv/Scripts/activate || source .venv/bin/activate
- Focused tests: poetry run pytest tests/path/to/test_file.py -k expression
- Full tests: poetry run pytest
- Coverage: poetry run pytest --cov --cov-report term-missing tests
- Lint: poetry run invoke lint
- Fix formatting and imports: poetry run invoke fixers
- Type hints: poetry run invoke mypy
