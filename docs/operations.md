# Running an instance

Scheduled work runs as Django management commands. On Coolify, add each as a
scheduled task on the web container (Resource → Scheduled Tasks); the command
runs inside the running container, so it sees the same environment.

| Task | Schedule (cron) | Command |
|---|---|---|
| Fetch feeds | `0 * * * *` | `mise run dj fetch_feeds` |
| Check content | `30 6 * * *` | `mise run dj check_content --mail` |
| Export | `15 3 * * *` | `mise run dj export_content /export --commit --push` |

## fetch_feeds

Reads every source in `FEED_SOURCES`, a comma-separated list:

| Item | Reads |
|---|---|
| `youtube:<channel id>` | the channel's uploads |
| `github:<owner>/<repo>` | the repository's releases |
| `atom:<url>` | any Atom feed |

New items appear under "what's new". An item whose address matches an entry's
syndication link is tied to that entry and stays out of "what's new", since
the entry already speaks for it. The command exits 1 and names any source it
could not read; the others are saved regardless.

## check_content

Lists what in the published content needs a look and exits 1 when anything
does, so a failing task is a signal, not noise. `--json` prints one JSON list,
`--mail` sends the list to the profile's e-mail, `--links` also visits every
syndication link (slow; leave it for a weekly run).

| Code | Means |
|---|---|
| `H001` | a container (project, initiative) holds nothing |
| `H002` | a home page door has fewer entries than its minimum, so it is hidden |
| `H003` | a calendar entry is over and nothing from it (a session, a recording) is linked |
| `H004` | a featured entry has no cover |
| `H005` | an ongoing container has had nothing new for six months |
| `H006` | a syndication link does not answer |

The same list, without `--links`, is on the admin dashboard and at
`<ADMIN_URL>content-health/`.

## export_content

Writes every published entry, its type and its files as export format v1. With
`--commit`, the destination must be a git working copy; the export is
committed there when anything changed. `--push` then pushes to the copy's
`origin`.

Set the working copy up once, on a persistent volume mounted at `/export`:

```bash
git clone https://<user>:<token>@github.com/<you>/<site>-content.git /export
```

The token needs write access to that repository only. Commits are made as
`lapidarium <lapidarium@localhost>`.
