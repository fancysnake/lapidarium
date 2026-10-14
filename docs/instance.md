# Instance guide

The engine is a package; your site is a small repository that depends on it,
holds your theme, and builds an image from the engine's.

```text
my-site/
  pyproject.toml        depends on lapidarium = "~0.1"
  themes/<name>/        theme.toml, tokens.css, theme.css, templates/, static/
  Dockerfile            FROM ghcr.io/fancysnake/lapidarium:<version>
  docker-compose.yml    web + postgres, for Coolify
```

Content types, doors, the menu and colours live in the database, so they move
with the content export, not with the code. A new site starts from a demo set
or from another site's export:

```bash
django-admin load_demo ttrpg        # a template to edit
django-admin import_content ./export
```

## The image

```dockerfile
FROM ghcr.io/fancysnake/lapidarium:0.1.0
COPY --chown=appuser:appuser themes /app/themes
ENV SITE_THEME=my-theme SITE_THEME_DIRS=/app/themes
```

The engine image starts with `migrate`, `collectstatic`, then gunicorn on port
8000; `/healthz/` answers without touching the database, for the platform's
health check.

## Settings

Everything is an environment variable; see [Configuration](configuration.md).
Write a Python settings module of your own only for what the environment
cannot express: import `lapidarium.edges.settings`, change what you need, and
point `DJANGO_SETTINGS_MODULE` at your module.

## Upgrading

Pin the engine to a minor release (`~0.1` before 1.0, `^1` after) and read the
[changelog](changelog.md) before moving: a renamed theme token or a new export
format version is a major release.
