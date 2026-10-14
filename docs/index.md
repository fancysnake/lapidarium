# lapidarium

lapidarium is the engine behind a creator's portfolio site. You define the
content types in the admin: sessions, songs, games, repositories, talks,
whatever you make. Every entry is a page built from ordered parts (text,
video, audio, image, file, link). The engine supplies the pages, lists, feeds,
search, calendar, themes and a nightly export of everything to plain markdown
files.

Django, PostgreSQL, plain CSS, a little vanilla JavaScript, no Node. Every page
works with scripts off.

```bash
pip install lapidarium
```

## Where to go next

- [Getting started](getting-started.md): a running site with demo content in
  five commands.
- [Content types](content-types.md): roles, layouts, fields, doors and colours.
- [Parts](parts.md): what each part kind renders and needs.
- [Themes](themes.md): tokens, component classes, template overrides, checks.
- [Export format](export-format.md): the files `export_content` writes.
- [Instance guide](instance.md): your own site, in its own repository.
- [Configuration](configuration.md): every environment variable.
- [Commands](cli.md): the management commands.
- [Operations](operations.md): scheduled tasks on Coolify.
- [Architecture](architecture.md): the code's layout, for contributors.
- [Changelog](changelog.md): what changed, and the versioning policy.
