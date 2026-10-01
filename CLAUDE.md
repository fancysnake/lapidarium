# CLAUDE.md

Django engine for creator portfolio sites. Python 3.14, Poetry, mise, PostgreSQL.
Plan and content model: `PLAN.md` (local, untracked). Spec: `docs/content-model.md`.

## Commands

`mise tasks` is the source of truth. The commit gate is `mise run fullcheck`.
Narrow first: `mise run lint:ruff`, `mise run test:unit`, `mise run test:int`.
PostgreSQL must be running (`mise run db`) for integration tests and the server.
Pull request rituals: `vekna cast refresh|cover|review|labels` (cabinet, `.vekna.toml`).

## Architecture

GLIMPSE layers under `src/lapidarium/`, enforced by import-linter:
`pacts` (DTOs, protocols, enums) → `specs` (invariants) → `mills` (services, no
Django) → `links` (ORM, admin, external clients) → `gates` (views, commands) →
`inits` (DI, middleware) → `edges` (settings, wsgi). Load the `glimpse` skill
before adding or moving code.

- Views call `request.services.*` and render DTOs. ORM objects never leave `links`.
- Content types, field schemas, doors and colours are data (`EntryType`), not models.
- Admin is django-unfold, model-coupled, lives in `links/db/django/admin.py`.

## Rules

- Zero Node: no `package.json`, no bundler. Plain CSS, vanilla ES modules.
- Every page works without JavaScript; JS is progressive enhancement.
- No inline lint suppressions, no global rule disabling to get green.
- Templates: semantic HTML, stable BEM-ish component classes, type colour only
  through `--type-color` / `--type-tint` on `data-type` elements.
- Strings wrapped for i18n; schema changes get a reversible migration.
