# lapidarium

Documentation is at [https://lapidarium.fancysnake.dev](https://lapidarium.fancysnake.dev).

<!-- --8<-- [start:intro] -->
A home base for multi-format creators: one site you own, where every piece of
work has its own address and links to the rest. You define the content types in
the admin (sessions, songs, repos, talks, whatever you make); every entry is built
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
anchor. After an edit to `docs/assets/lapidarium-card.svg`, `mise run site:card`
renders the link-preview PNG from it.

## Rituals

`vekna cast` runs [cabinet](https://cabinet.fancysnake.dev)'s pull request
rituals: `heal.this`, `heal.mine`, `merge`, `ci`, `answer`, `review`, `guide`,
`labels`. Install vekna 1.3 and cabinet 7 for your user, and add this to your
vekna user config (`~/.config/vekna/config.toml`). Change `path` to where you
cloned the repository. Cabinet's
[configuration reference](https://cabinet.fancysnake.dev/configuration/) lists
the other keys.

```toml
[rituals]
modules = ["cabinet.rituals"]

[projects.lapidarium]
path = "~/lapidarium"

[projects.lapidarium.cabinet]
remote = "https-origin"
# Commits are not signed, so a night run never stops at a key prompt.
sign_commits = false
# This repository has no `diff-cover` task, which is cabinet's default.
coverage = "mise run test:py:cov:diff"

# `fullcheck` includes the debt budget and is slow; the rituals run `pr-fix`.
[projects.lapidarium.cabinet.agent]
may_not_run = ["mise run fullcheck"]

# The job names in .github/workflows/ci.yml. The `ci` ritual repairs only the
# checks listed here.
[projects.lapidarium.cabinet.ci.jobs]
lint = { gate = "mise run lint:py" }
test = { gate = "mise run test:py:cov" }
```

The rituals push over HTTPS with `gh` as the credential helper. Add the
`https-origin` remote once per clone:

```bash
git remote add https-origin https://github.com/fancysnake/lapidarium.git
```

## License

[MIT](LICENSE).
