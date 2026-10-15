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
mise tasks            # everything else
```

Personal overrides go in `mise.local.toml`, which is gitignored.

## Configuration

An instance is configured through the environment. Beyond the Django basics
(`SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `LANGUAGE_CODE`, `TIME_ZONE`):

| Variable | Default | What it sets |
|---|---|---|
| `SITE_NAME` | `lapidarium` | Site title when no profile exists |
| `CACHE_URL` | `locmemcache://` | Default cache; rate limits count here |
| `PAGE_CACHE_URL` | `filecache:///tmp/lapidarium-pages` | Rendered public pages, shared by all workers |
| `PAGE_CACHE_SECONDS` | `600` | How long a rendered page lives; any content change clears them all |
| `EMAIL_URL` | `consolemail://` | Mail backend for the contact form, e.g. `smtp+tls://user:pass@host:587` |
| `DEFAULT_FROM_EMAIL` | `webmaster@localhost` | Sender of contact form mail |
| `NEWSLETTER_BACKEND` | `log` | `log` or `mailchimp` |
| `MAILCHIMP_API_KEY`, `MAILCHIMP_LIST_ID` | empty | Mailchimp audience, required with `mailchimp`; new subscribers confirm by mail |
| `TRUSTED_PROXY_HOPS` | `1` in production, else `0` | Proxies in front that append to `X-Forwarded-For`; rate limits key on the address the outermost one saw |
| `AWS_STORAGE_BUCKET_NAME` | empty | Turns on S3 media storage |

The contact form appears once the profile has an e-mail address.

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
