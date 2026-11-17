# ADR-0009: Pagination, the before-image, and rollback
- **Status:** Accepted
- **Date:** 2026-11-17
- **Rung/Module:** End-to-end incident workflow

## Context
`main` leaves `ServiceNowClient.list_all`, `ServiceNowClient.update_with_before_image`, and `writes.rollback` as `TODO(student)`. The end-to-end writes go through the registry, and every executed write stores a before-image. Rollback is how that image is put back. This branch is the one that implements them.

## Decision
Implement the three functions as the lectures specify. `list_all` pages until a short page. `update_with_before_image` reads the fields about to change, then patches them. `rollback` patches those old values through `update`, and it is not a registered tool. The course tests that were skipped on `main` now run.

## Alternatives considered
- Leave the TODOs and write incidents through a private client — that would skip the before-image the audit log stores.
- Register rollback as a model tool — a human, or a later explicit step, decides that a change was wrong. The model does not call it.

## Consequences
`main` is unchanged and still has the TODOs. This branch has the implementations. A failed patch happens after the read, so a change is not stored without its before-image.

## Action-tier impact
None. Rollback stays outside the registry.
