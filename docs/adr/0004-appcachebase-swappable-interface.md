# ADR-0004: AppCacheBase Swappable Interface

**Date:** 2026-08-07
**Status:** Accepted
**Deciders:** Alexander Haye, Copilot

## Context

The library needs caching for multiple purposes: OAuth token caching (discovery module), session storage (auth module), and general application caching. Different consumer apps may prefer different cache backends (Redis, MongoDB, in-memory, etc.).

## Decision

Define `AppCacheBase` as a swappable caching interface with three methods:

- `store_app_cache(key, value, ttl)` — Store or replace cache data
- `fetch_app_cache(key)` — Fetch cached data (returns `None` if not found)
- `clear_app_cache(key)` — Clear cached data

The interface is used by:
- **Discovery module** — OAuth token caching via `HueyAppCache`
- **Sessions module** — Server-side session storage via `HueyAppCache`
- **Consumer apps** — General application caching

`HueyAppCache` is the current implementation, using Huey's `put`/`get`/`delete` with Redis storage. It supports automatic JSON serialization, zlib compression for large values, and TTL management.

## Consequences

- Consumer apps can plug in alternative cache backends by implementing `AppCacheBase`
- The cache abstraction is used by multiple modules — removing or changing the interface breaks discovery, sessions, and consumer apps
- New cache backends must implement all three methods consistently
- The `tasks` module does not use `AppCacheBase` — it interacts with Huey directly
