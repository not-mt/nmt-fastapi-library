# ADR-0007: Request ID via ContextVars

**Date:** 2026-08-07
**Status:** Accepted
**Deciders:** Alexander Haye, Copilot

## Context

The library needs request tracing for log correlation in async FastAPI applications. Request IDs must be accessible throughout the request lifecycle, including in background tasks and async handlers.

## Decision

Use **`contextvars.ContextVar`** for request ID propagation:

- `REQUEST_ID_CONTEXTVAR` is a module-level `ContextVar[str | None]` in `middleware/v1/request_id.py`
- `RequestIDMiddleware` generates a unique ID per request and sets it in the context
- `RequestIDFilter` (in `logging/v1/filters.py`) reads the context var and adds it to log records
- The request ID is also returned in the `x-nmtfast-request-id` response header

ContextVars are used instead of thread-local storage because they work correctly with async/await and task switching, which is essential for FastAPI's async request handling.

## Consequences

- Request ID is accessible anywhere in the request lifecycle via `REQUEST_ID_CONTEXTVAR.get()`
- Changing to thread-local or request-scoped storage would break async log correlation
- The middleware and logging filter are tightly coupled via the shared context var
- Consumer apps must install both `RequestIDMiddleware` and `RequestIDFilter` for the feature to work
