# CONTEXT.md — nmt-fastapi-library

## Library Identity

**nmtfast** (not-MT for FastAPI) is a **horizontal concern library** with a **vertical repository layer**, consumed by sibling FastAPI applications (e.g., `nmt-fastapi-reference`).

It provides cross-cutting infrastructure modules (auth, caching, service discovery, middleware, etc.) that any nmt FastAPI app can import, plus pre-built API client repositories for canonical reference domains (widgets, gadgets).

## Bounded Contexts

### Core Modules (library-owned)

| Module | Responsibility | Status |
|---|---|---|
| `auth` | Toolbox of independent, composable authentication strategies: OAuth2 (client credentials + PKCE auth code), JWT validation, API keys, sessions, Argon2 password hashing, and section-based ACL evaluation via `SectionACL`. Not a unified pipeline — apps compose the strategies they need. | Stable |
| `cache` | Swappable caching interface (`AppCacheBase`) with Huey as the current implementation. Apps may plug in alternative backends. | Stable |
| `discovery` | DI factory for long-lived `httpx.AsyncClient` instances. Apps call `create_api_client()` at startup (eager or lazy) to get configured clients with OAuth2 token caching, timeouts, retries, and connection limits. | Stable |
| `errors` | Generic library exceptions. Module-specific exceptions (e.g., `AuthorizationError`, `ServiceConnectionError`) live in their respective modules. Unified exception hierarchy is deferred. | Stable |
| `htmx` | HTMX helpers and `PaginationMeta` schema. Temporary convenience — destined for a separate library. | Transitional |
| `logging` | Structured logging config and filters. Optional convenience — apps may bring their own logging. | Stable |
| `middleware` | Pick-and-choose FastAPI middleware utilities: `request_id` (request tracing), `request_duration` (performance monitoring). No prescribed stack or ordering. | Stable |
| `retry` | Tenacity utility helpers (e.g., `tenacity_retry_log` callback). Apps configure their own retry policies via Tenacity directly. | Stable |
| `settings` | YAML config loading with deep merge. Pydantic schemas define a **public contract** — consumer apps must structure their YAML to match these models. Config file paths and merge logic are library-owned; config content is consumer-owned. | Stable |
| `tasks` | Huey task queue integration. | Stable |
| `ui` | UI components. Temporary convenience — destined for a separate library. | Transitional |

### Repository Modules (co-owned with upstream APIs)

| Module | Responsibility | Status |
|---|---|---|
| `repositories/widgets` | Pre-built async API client repository for the canonical "widgets" domain. Full CRUD + zap tasks + pagination + retries. Consumed by `nmt-fastapi-reference` and potentially other apps. | Stable |
| `repositories/gadgets` | Pre-built async API client repository for the canonical "gadgets" domain. Same pattern as widgets. | Stable |

Repository modules are **first-class bounded contexts**, not examples. They are real reusable components that consumer apps import directly. Breaking changes in the upstream API trigger new version directories (`v2/`) in the corresponding repository submodule.

## Glossary

| Term | Definition |
|---|---|
| **Horizontal concern** | Cross-cutting infrastructure (auth, caching, middleware) shared across multiple apps |
| **Vertical repository** | Pre-built API client repository for a specific domain (widgets, gadgets) |
| **SectionACL** | Access control rule that grants permissions (`*` or specific methods) for a section (regex-matched path) to a principal |
| **AuthSuccess** | Common result type for successful authentication: `name`, `username`, and `acls` |
| **AppCacheBase** | Swappable caching interface. Current implementation: Huey |
| **ServiceDiscoverySettings** | Pydantic model that maps service names to `DiscoveredService` configs (base URL, timeouts, auth method, auth principal) |
| **OutgoingAuthClient** | OAuth2 client credentials config for service-to-service authentication |
| **OutgoingAuthHeaders** | Static auth headers for service-to-service authentication |
| **PaginationMeta** | Schema for paginated API responses (total, page, page_size, sort_by, sort_order, search) |
| **nmtfast-config-default.yaml** | Consumer app's default config file (library-provided defaults) |
| **nmtfast-config.yaml** | Consumer app's override config file (merged on top of defaults) |

## Architectural Rules

1. **PEP 420 implicit namespace packages** — Never create `__init__.py` files. Imports use explicit long paths (e.g., `nmtfast.auth.v1.acl.check_acl`).
2. **Versioned subdirectories** — Each module uses `v1/`, `v2/`, etc. Breaking changes add a new version directory; old versions co-exist for gradual migration.
3. **Two-tier ownership** — Core modules are library-owned. Repository modules are co-owned with the upstream APIs they wrap.
4. **Two-layer dependency rule** — Core modules may depend on each other organically. Repository modules may depend on core modules. Core modules must NEVER depend on repository modules.
5. **Configuration contract** — Consumer apps provide YAML config content. Library provides Pydantic schemas that apps must conform to.
6. **Auth is a toolbox** — Auth strategies are independent and composable. No unified auth pipeline is enforced.
7. **Discovery is a DI factory** — `create_api_client()` produces long-lived clients. Apps load them eagerly or lazily.
8. **Cache is swappable** — `AppCacheBase` is an abstraction. Huey is the current implementation, not the only implementation.
9. **HTMX/UI are transitional** — These modules will be spun off to a separate library. New HTMX/UI features should be considered for the target library, not this one.
10. **PEP 484 type hints** — All non-test code must have type hints.
11. **PEP 257 Google-style docstrings** — All functions and classes must have Google-style docstrings with `"""` on their own lines.
12. **PEP 585 built-in generics** — Use `list[str]`, `dict[str, int]`, etc. instead of `typing.List`, `typing.Dict`.

## Deferred Decisions

- **Unified exception hierarchy** — Consider introducing `NmtFastException` as a base class for all library exceptions. Deferred until consumer apps express need.
