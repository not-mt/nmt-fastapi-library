# ADR-0005: Manual Service Discovery with Outgoing Auth Principal Indirection

**Date:** 2026-08-07
**Status:** Accepted
**Deciders:** Alexander Haye, Copilot

## Context

Consumer apps need to communicate with upstream services. Each service may require different authentication methods (OAuth2 client credentials, static headers). The library provides a factory pattern for creating configured HTTP clients.

## Decision

Implement **manual service discovery** with a **two-hop outgoing auth principal indirection**:

1. `ServiceDiscoverySettings.services[service_name]` → `DiscoveredService` (base URL, timeouts, auth method, auth principal)
2. `DiscoveredService.auth_method` + `DiscoveredService.auth_principal` → outgoing auth config:
   - `client_credentials` → `auth.outgoing.clients[auth_principal]` → `OutgoingAuthClient` (client ID, secret, provider, cache TTL)
   - `headers` → `auth.outgoing.headers[auth_principal]` → `OutgoingAuthHeaders` (static headers dict)

The `create_api_client()` function performs both lookups and returns a configured `httpx.AsyncClient` (or `AsyncOAuth2Client` for OAuth2 services).

## Consequences

- Consumer apps configure services and auth principals separately in YAML, enabling auth config reuse across services
- The two-hop lookup is embedded in `create_api_client()`, Pydantic schemas, and YAML configs
- Changing the discovery or auth indirection model breaks service-to-service authentication for all consumers
- Service discovery mode is currently `manual` only (hardcoded in `ServiceDiscoverySettings.mode`)
