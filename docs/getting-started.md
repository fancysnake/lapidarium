# Getting started

The engine repository runs as a site of its own, with demo content, on SQLite.
You need [mise](https://mise.jdx.dev).

```bash
git clone https://github.com/fancysnake/lapidarium.git
cd lapidarium
mise install                # Python and Poetry; Poetry installs the rest
mise run dj setup_local     # migrate, load the ttrpg demo, admin/admin login
mise run i18n:compile       # the Polish interface strings
mise run start              # http://localhost:8000
```

`setup_local --demo dev` loads a
developer's portfolio (repositories, talks, docs) instead of a game master's
(sessions, songs, games, events). It refuses to run unless `DEBUG` is on.

Open `http://localhost:8000/admin/`, log in as `admin` / `admin`, and change
something: a type's colour, an entry's title. The public pages show it on the
next request.

For your own site, start from the [instance guide](instance.md).
