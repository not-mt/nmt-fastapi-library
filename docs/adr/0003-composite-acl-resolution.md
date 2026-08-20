# ADR-0003: Composite ACL Resolution

**Date:** 2026-08-07
**Status:** Accepted
**Deciders:** Alexander Haye, Copilot

## Context

The library needs a flexible authorization model that supports multiple identity types (OAuth clients, API keys, static users, groups) while allowing fine-grained, section-based permissions. Consumer apps configure access rules via YAML files.

## Decision

Implement a **three-layer composite ACL resolution** model:

1. **Client ACLs** — Granted to the authenticated principal (OAuth client or API key)
2. **User ACLs** — Granted to static users matched by JWT claims
3. **Group ACLs** — Granted to groups matched by the JWT groups claim

All three layers are merged into a single `list[SectionACL]` in `AuthSuccess.acls`. The `check_acl()` function evaluates the composite list — if any ACL grants the requested permission, access is allowed.

Each `SectionACL` is stamped with `principal_name` (the source of the ACL) and `resolved_user_label` (the human-readable username for group-granted ACLs) for audit logging.

## Consequences

- Consumer apps configure ACLs at three granularity levels in their YAML configs
- The three-layer model is baked into `authenticate_token()`, `SectionACL` schema, and YAML config structure
- Changing the permission model would break all consumer auth configs
- Filter-based ACLs are deferred (commented out in schema and `check_acl()`)
