# Commands

Management commands, run as `django-admin <command>` (or `mise run dj
<command>` in the engine repository). Their usage, as `--help` prints it:

```text
check_content [--json] [--links] [--mail]
export_content [--commit] [--push] destination
fetch_feeds
import_content source
load_demo {dev,ttrpg}
setup_local [--demo {dev,ttrpg}] [--username USERNAME] [--password PASSWORD]
```

## check_content

Lists what in the published content needs a look and exits 1 when anything
does. `--json` prints one JSON list, `--links` also visits every syndication
link, `--mail` sends the list to the profile's address. The codes are in
[Operations](operations.md#check_content).

## export_content

Writes published content, its types and the files it uses to `destination` as
[export format v1](export-format.md). It touches only `types/`, `content/`,
`assets/` and the top-level files of the format, so the destination may hold
anything else, a `.git` directory included. `--commit` commits the result in
that git working copy when anything changed; `--push` pushes it.

## fetch_feeds

Reads every source in `FEED_SOURCES` and ties items to the entries they copy.
See [Operations](operations.md#fetch_feeds).

## import_content

Reads an export from `source`, checks all of it against its own types, and
writes it in one transaction: either everything goes in or nothing does.
Entries, types and assets are created or updated by their keys; nothing is
deleted.

## load_demo

Imports a bundled demo set: `ttrpg` (a game master: sessions, songs, games,
events, memes) or `dev` (a developer: repositories, talks, docs). The sets are
in export format v1, so they are also examples of it.

## setup_local

Migrates, loads a demo and makes sure an admin login exists with the given
password. Refused unless `DEBUG` is on.
