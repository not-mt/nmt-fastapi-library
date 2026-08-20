# ADR-0008: Two-Tier Exception Propagation

**Date:** 2026-08-07
**Status:** Accepted
**Deciders:** Alexander Haye, Copilot

## Context

The library provides repository-layer API clients that communicate with upstream services. When upstream calls fail, the library needs to propagate errors through multiple layers (repository → service → controller) while preserving diagnostic information and mapping to appropriate HTTP status codes.

## Decision

Implement a **two-tier exception propagation** pattern:

1. **Repository layer** — `BaseUpstreamRepositoryException` captures raw upstream failures:
   - Stores `status_code`, `message`, and `req_id` from the `httpx.Response`
   - Thrown by repository methods when API calls fail

2. **Service layer** — `UpstreamApiException` wraps repository exceptions:
   - Extracts `status_code`, `message`, `req_id` from the repository exception
   - Infers `caller_status_code` (400 for 4xx upstream, 502 for 5xx upstream)
   - Provides a single error message for the caller

Module-specific exceptions (e.g., `WidgetApiException`, `ServiceConnectionError`) inherit from `BaseUpstreamRepositoryException` or `Exception` directly, depending on their scope.

## Consequences

- Consumer apps catch `UpstreamApiException` at the service layer to handle upstream failures uniformly
- The repository→service exception wrapping pattern with status code inference is used by consumer apps
- Changing the exception hierarchy or status code inference logic breaks error handling chains
- Module-specific exceptions live in their respective modules (see `CONTEXT.md` Deferred Decisions on unified hierarchy)
