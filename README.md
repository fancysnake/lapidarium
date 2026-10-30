# lapidarium

Documentation is at [https://lapidarium.fancysnake.dev](https://lapidarium.fancysnake.dev).

<!-- --8<-- [start:intro] -->
A home base for multi-format creators: one site you own, where every piece of
work has a page and links to the rest. You define the content types in the admin
(sessions, songs, repos, talks, whatever you make); every entry is a page built
from ordered parts: text, video, audio, image, file, link. The engine gives you
lists, feeds, search, calendar, themes and an export of everything to
plain markdown files.

Django, PostgreSQL, plain CSS, a little vanilla JS. No Node.
<!-- --8<-- [end:intro] -->

Status: pre-alpha, under construction. The content model and the principles
behind it are in [How it works](https://lapidarium.fancysnake.dev/concepts/).

## Development

<!-- --8<-- [start:development] -->
Requires [mise](https://mise.jdx.dev). The dev server uses SQLite (`db.sqlite3`).

```bash
mise install          # Python, Poetry
mise run dj setup_local   # migrate, ttrpg demo, admin/admin login
mise run i18n:compile # Polish UI strings (.mo files are not committed)
mise run start        # http://localhost:8000
```

Day to day:

```bash
mise run check        # format + lint
mise run test:py      # all tests
mise run fullcheck    # the commit gate
mise run site:dev     # this manual, live at http://localhost:8001
mise tasks            # everything else
```

Personal overrides go in `mise.local.toml`, which is gitignored.
<!-- --8<-- [end:development] -->

## Configuration

An instance is configured through the environment. Every variable, with its
default, is in [Configuration](https://lapidarium.fancysnake.dev/configuration/);
running one in production is in
[Deployment](https://lapidarium.fancysnake.dev/deployment/), and setting up its
content from nothing in [Content](https://lapidarium.fancysnake.dev/content/).

## Documentation

`docs/` is the manual's source. `mise run site:dev` serves it with live reload;
`mise run site:build` builds it into `site/` and fails on any broken link or
anchor.

## Rituals

`vekna cast` runs [cabinet](https://cabinet.fancysnake.dev)'s pull request
rituals (`.vekna.toml`): `refresh`, `cover`, `review`, `labels`. They push over
HTTPS with `gh` as the credential helper, so they look for a remote named
`https-origin`. Add it once per clone:

```bash
git remote add https-origin https://github.com/fancysnake/lapidarium.git
```

## License

[MIT](LICENSE).
