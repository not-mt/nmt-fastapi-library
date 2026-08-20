# ADR-0002: Versioned Submodule Directories

**Date:** 2026-08-07
**Status:** Accepted
**Deciders:** Alexander Haye, Copilot

## Context

The nmtfast library is consumed by multiple sibling FastAPI applications. Breaking changes in the library must support gradual migration — consumer apps should be able to upgrade at their own pace without being forced into coordinated, simultaneous upgrades.

## Decision

Every submodule uses versioned directories (`v1/`, `v2/`, etc.) beneath its domain namespace:

```
nmtfast/
  auth/
    v1/           ← current stable API
    v2/           ← next major version (when breaking changes are needed)
  cache/
    v1/
  repositories/
    widgets/
      v1/
```

- Breaking changes add a new version directory alongside the existing one
- Old versions co-exist and remain importable
- Consumer apps migrate by updating their import paths when ready
- Deprecated versions are only removed after all known consumers have migrated

## Consequences

- Import paths are explicit and versioned: `from nmtfast.auth.v1.acl import check_acl`
- Consumer apps control their migration timeline
- Library maintainers can develop breaking changes without disrupting active consumers
- Increases directory depth but provides clear API stability signals
- All imports, tests, and consumer apps reference versioned paths — changing this structure later would require mass refactoring across all repos
