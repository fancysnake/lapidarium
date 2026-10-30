# lapidarium

--8<-- "README.md:intro"

An instance is one site: one owner, one database, one theme. The engine is a
container image; everything that makes the site yours is environment variables
and content you enter in the admin or import from files.

## Install

The image is built from `main` and every release tag:

```bash
docker pull ghcr.io/fancysnake/lapidarium:latest
```

It needs PostgreSQL and a handful of environment variables.
[Deployment](deployment.md) walks through a production instance;
[Getting started](getting-started.md) runs one on your machine with a demo
loaded.

## Where to go next

- [Getting started](getting-started.md): a local instance with demo content,
  in four commands.
- [Deployment](deployment.md): a new production instance, from the image to the
  first login.
- [Configuration](configuration.md): every environment variable, its default
  and what it changes.
- [Commands](cli.md): the management commands for setup, import and export.
- [How it works](concepts.md): the content model, in one picture, and the
  principles behind it.
- [Content](content.md): profile, content types, fields and entries, set up
  from nothing.
- [Export format](export-format.md): the markdown files an instance exports and
  imports.
- [Themes](themes.md): tokens, component classes and template overrides.
- [Mission](mission.md): why lapidarium exists, what it stands for, and what
  it is not.
- [Architecture](architecture.md): how the code is laid out, for contributors.
- [Changelog](changelog.md): what changed in each release.
