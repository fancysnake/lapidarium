# Commands

The engine's management commands, on top of Django's own (`migrate`,
`createsuperuser`, `check`, …). From a clone, run them as `mise run dj
<command>`; in the production container, as `docker compose exec web mise run
dj <command>`.

## `setup_local`

```bash
mise run dj setup_local [--demo ttrpg|dev] [--username admin] [--password admin]
```

Migrates, loads a demo and creates the superuser, or resets its password if it
exists, in one transaction. Defaults: the `ttrpg` demo, `admin` / `admin`.
Refused unless `DEBUG` is on, so it cannot reset a production login.

## `load_demo`

```bash
mise run dj load_demo ttrpg|dev
```

Imports a bundled demo, exactly as `import_content` would:

- `ttrpg`: a game master's site, in Polish: sessions, a campaign, songs, memes,
  events, a wiki.
- `dev`: a developer's site: projects, repos, talks, documentation sets, events.

## `export_content`

```bash
mise run dj export_content <destination>
```

Writes the content in [export format](export-format.md) v1: every content type,
every published entry, the profile, the links, the friends and every asset
they use. It
deletes and rewrites `types/`, `content/` and `assets/` in the destination,
so point it at a directory that holds nothing else.

Fails, writing nothing, when a published entry links to a draft.

## `import_content`

```bash
mise run dj import_content <source>
```

Reads an export and merges it in. It checks the whole bundle first: format
version, slugs, colour contrast, field values, role fields, parts, assets and
relations. One error refuses the import, changes nothing and lists every
problem by file.

A valid bundle is applied in one transaction, matched by key:

| Record | Matched by | On a match |
|---|---|---|
| Content type | `key` | settings updated, fields replaced |
| Entry | type and slug | fields updated; parts, relations and syndication links replaced; tags set |
| Asset | path | the file overwritten |
| Profile | there is one | updated, or created |
| Links | — | always replaced; a bundle with none removes them all |
| Friends | — | always replaced; a bundle with none removes them all |

Nothing missing from the bundle is deleted. Every entry's type and every relation
target must be in the bundle too.
