# lapidarium

Engine for a creator's portfolio site. You define the content types in the admin
(sessions, songs, repos, talks, whatever you make); every entry is a page built
from ordered parts: text, video, audio, image, file, link. The engine gives you
lists, feeds, search, calendar, themes and a nightly export of everything to
plain markdown files.

Django, PostgreSQL, plain CSS, a little vanilla JS. No Node.

Status: pre-alpha, under construction. The original spec (Polish) is in
[docs/content-model.md](docs/content-model.md).

## Development

Requires [mise](https://mise.jdx.dev) and Docker (for PostgreSQL).

```bash
mise install          # Python, Poetry
mise run db           # PostgreSQL on :5432
mise run dj setup_local   # migrate, ttrpg demo, admin/admin login
mise run start        # http://localhost:8000
```

Day to day:

```bash
mise run check        # format + lint
mise run test:py      # all tests
mise run fullcheck    # the commit gate
mise tasks            # everything else
```

Personal overrides go in `mise.local.toml`, which is gitignored.

### Rituals

`vekna cast` runs [cabinet](https://cabinet.fancysnake.dev)'s pull request
rituals (`.vekna.toml`): `refresh`, `cover`, `review`, `labels`. They push over
HTTPS with `gh` as the credential helper, so they look for a remote named
`https-origin`. Add it once per clone:

```bash
git remote add https-origin https://github.com/fancysnake/lapidarium.git
```

## License

[MIT](LICENSE).
