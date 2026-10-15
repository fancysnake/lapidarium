# Architecture

The code follows [GLIMPSE](https://glimpse.fancysnake.dev): layers with one
direction of imports, checked by import-linter on every lint run.

```text
src/lapidarium/
  pacts.py        DTOs, write shapes, protocols, enums, errors: the contracts
  specs.py        business constants only mills read (page size, contrast floor)
  mills/          services: schema, content (import, export), catalogue (the
                  public site), site, outreach, theme, feeds, health
  links/          adapters: db/django (models, repositories, admin), content_files,
                  themes, newsletter, mail, throttle, feeds, linkcheck, archive
  gates/          entry points: web/django (views, template tags, checks) and
                  cli/django (management commands)
  inits.py        the composition root: builds services, attaches them to requests
  edges/          settings and WSGI
  templates/      the engine's templates; themes override them by path
  static/         base.css, enhance.js
  themes/         base and gm-screen
```

- Views call `request.services.<service>` and render DTOs; ORM objects never
  leave `links`.
- Content types, field schemas, doors and colours are rows (`EntryType`), not
  models: a new type needs no migration.
- The admin is django-unfold, model-coupled, in `links/db/django/admin.py`.
- No Node: no `package.json`, no bundler. A test fails if one appears.

## Working on it

```bash
mise run check        # format, then lint
mise run test:py      # every test
mise run fullcheck    # the commit gate: lint, tests, 100% diff coverage, debt budget
mise run site:dev     # this manual, with live reload
```

Unit tests cover mills with mocked protocols; integration tests drive gates
through Django's test client against both demo sets, with templates that fail
on any undefined variable.
