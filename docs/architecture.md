# Architecture

lapidarium is one Django project, `src/lapidarium/`, cut into layers. Each
layer imports only the ones before it; import-linter enforces the order in
`pyproject.toml`, and `mise run lint:py` fails on a wrong import.

| Layer | Holds | May use Django |
|---|---|---|
| `pacts` | DTOs, protocols, enums, defaults | no |
| `specs` | invariants: contrast floors, slugs, relation rules | no |
| `mills` | services: the catalogue, content import and export, themes, outreach | no |
| `links` | adapters: the ORM and admin, content files, feeds, mail, newsletter, themes on disk | yes |
| `gates` | entry points: views, management commands | yes |
| `inits` | wiring: the services each request and command gets | yes |
| `edges` | settings, WSGI | yes |

## Rules that shape the code

- Views call `request.services.*` and render DTOs. ORM objects never leave
  `links`.
- Content types, their fields, doors and colours are rows of `EntryType`, not
  models: a new kind of work is data, not a migration.
- The admin is django-unfold and lives in `links/db/django/admin.py`.
- No Node: no `package.json`, no bundler. Plain CSS and vanilla ES modules in
  `static/lapidarium/`; every page works without JavaScript. A test fails on
  any Node artifact.
- Templates are semantic HTML with stable component classes, the public API
  that [themes](themes.md) build on. Type colour reaches a component only
  through `--type-color` and `--type-tint`.
- UI strings are translated (`locale/pl`, `locale/en`); `.mo` files are built,
  never committed.

## Where things live

```text
src/lapidarium/
  pacts.py, specs.py      the contracts
  mills/                  services, one module per concern
  links/
    db/django/            models, migrations, admin, repositories
    content_files/        export format v1 and the bundled demos
    themes/               reads theme directories
    feeds/, mail/, newsletter/, throttle/, …
  gates/
    web/django/           views and URLs
    cli/django/           management commands
  inits.py                per-request services
  edges/settings.py       every setting, from the environment
  templates/lapidarium/   pages, layouts, components, parts
  themes/base/            the engine's theme
  static/lapidarium/      base.css and the scripts
tests/
  unit/                   services, no database
  integration/            views, commands, the ORM
```

## Working on it

[Getting started](getting-started.md) sets up a clone. `mise run fullcheck`
is the gate before a commit; `CONTRIBUTING.md` in the repository has the rest.
