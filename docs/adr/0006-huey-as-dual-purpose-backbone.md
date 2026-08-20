# ADR-0006: Huey as Dual-Purpose Backbone

**Date:** 2026-08-07
**Status:** Accepted
**Deciders:** Alexander Haye, Copilot

## Context

The library needs background task execution and caching capabilities. Huey provides both task queuing and key-value storage, making it a natural fit for nmtfast's needs.

## Decision

Use **Huey as a dual-purpose backbone** for both task queuing and caching:

- **Tasks module** (`tasks/v1/huey.py`) — Huey task metadata storage and retrieval (`store_task_metadata`, `fetch_task_metadata`, `fetch_task_result`)
- **Cache module** (`cache/v1/huey.py`) — `HueyAppCache` implementation of `AppCacheBase` for general caching

The `tasks` module has no base abstraction — it interacts directly with Huey's API. The `cache` module has `AppCacheBase` as a swappable interface (see ADR-0004).

Both modules use Redis storage via Huey's `RedisStorage` backend, with manual TTL management for Redis keys.

## Consequences

- Huey is tightly coupled to the tasks module — switching task backends requires reworking `tasks/v1/huey.py`
- The cache module is decoupled via `AppCacheBase` — alternative backends can be plugged in
- Consumer apps that use both tasks and cache can share a single Huey/Redis infrastructure
- The `tasks` module should eventually have a base abstraction to match the cache module's swappability
