# ADR-0001: Domain Model and Architectural Rules

**Date:** 2026-08-06
**Status:** Accepted
**Deciders:** Alexander Haye, Copilot

## Context

The nmt-fastapi-library is a shared library consumed by sibling FastAPI applications. It needed foundational domain documentation to establish vocabulary, bounded contexts, and architectural rules before planning future changes.

## Decision

Establish the following domain model and architectural rules:

### Library Identity
- nmtfast is a **horizontal concern library** (cross-cutting infrastructure) with a **vertical repository layer** (pre-built API client repositories)

### Module Versioning
- Each module uses versioned subdirectories (`v1/`, `v2/`, etc.)
- Breaking changes add new version directories; old versions co-exist for gradual migration

### Two-Tier Ownership
- Core modules (auth, cache, discovery, errors, logging, middleware, retry, settings, tasks) are library-owned
- Repository modules (widgets, gadgets) are co-owned with the upstream APIs they wrap

### Two-Layer Dependency Rule
- Core modules may depend on each other organically
- Repository modules may depend on core modules
- Core modules must NEVER depend on repository modules

### Configuration Contract
- Consumer apps provide YAML config content
- Library provides Pydantic schemas that apps must conform to

### Auth is a Toolbox
- Auth strategies (OAuth2, JWT, API keys, sessions, ACLs) are independent and composable
- No unified auth pipeline is enforced

### Discovery is a DI Factory
- `create_api_client()` produces long-lived HTTP clients
- Apps load clients eagerly or lazily at startup

### Cache is Swappable
- `AppCacheBase` is an abstraction over caching backends
- Huey is the current implementation, not the only implementation

### HTMX/UI are Transitional
- These modules will be spun off to a separate library
- New HTMX/UI features should target the future library, not this one

### PEP 420 is Mandatory
- No `__init__.py` files, ever
- Imports use explicit long paths (e.g., `nmtfast.auth.v1.acl.check_acl`)

## Consequences

- Consumer apps have a stable, versioned API to depend on
- Breaking changes can be rolled out gradually without forcing coordinated upgrades
- The library's scope is clear: horizontal concerns + canonical reference repositories
- New contributors can understand the module structure and dependencies via `CONTEXT.md`
- HTMX/UI work is directed to the appropriate future repository

## References

- `CONTEXT.md` — Full domain documentation, glossary, and bounded contexts
