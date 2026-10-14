# Configuration

An instance is configured through the environment; `lapidarium.edges.settings`
is the settings module and reads everything from there. Every variable with
its default (an empty value is required, or empty by default):

```dotenv
ADMIN_URL=admin/
ALLOWED_HOSTS=localhost
AWS_STORAGE_BUCKET_NAME=
CACHE_URL=locmemcache://
DATABASE_URL=
DEBUG=false
DEFAULT_FROM_EMAIL=webmaster@localhost
EMAIL_URL=consolemail://
ENV=production
FEED_SOURCES=
LANGUAGE_CODE=pl
MAILCHIMP_API_KEY=
MAILCHIMP_LIST_ID=
MEDIA_ROOT=media
MEDIA_URL=/media/
NEWSLETTER_BACKEND=log
PAGE_CACHE_SECONDS=600
PAGE_CACHE_URL=filecache:///tmp/lapidarium-pages
SECRET_KEY=
SITE_NAME=lapidarium
SITE_THEME=base
SITE_THEME_DIRS=
STATIC_ROOT=staticfiles
TIME_ZONE=Europe/Warsaw
```

## Site

| Variable | What it sets |
|---|---|
| `SECRET_KEY` | Django's signing key. Required |
| `DATABASE_URL` | Required. `postgres://user:pass@host:5432/name`; `sqlite:///db.sqlite3` works for a trial |
| `ALLOWED_HOSTS` | Comma-separated host names; a leading dot allows subdomains |
| `ENV` | `production` turns on HTTPS redirects, HSTS, secure cookies and WhiteNoise |
| `DEBUG` | Django's debug pages; never in production |
| `ADMIN_URL` | Path of the admin, with a trailing slash |
| `SITE_NAME` | Title of the site until a profile exists, and of the admin |
| `LANGUAGE_CODE`, `TIME_ZONE` | The site's one language (`pl` or `en`) and its time zone |
| `SITE_THEME`, `SITE_THEME_DIRS` | The active [theme](themes.md) and extra directories to find themes in, comma-separated |

## Files

| Variable | What it sets |
|---|---|
| `MEDIA_ROOT`, `MEDIA_URL` | Uploaded files on local disk, and where they are served |
| `AWS_STORAGE_BUCKET_NAME` | Turns on S3 (or any S3-compatible) storage for uploads; `django-storages` reads `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT_URL` and the rest of its `AWS_*` settings from the environment |
| `STATIC_ROOT` | Where `collectstatic` gathers CSS and JavaScript |

## Caching

| Variable | What it sets |
|---|---|
| `CACHE_URL` | Default cache; the contact and newsletter rate limits count here |
| `PAGE_CACHE_URL` | Rendered public pages. Every content change clears it, so it must be shared by all workers: the default is a directory, not memory |
| `PAGE_CACHE_SECONDS` | Longest a rendered page lives, for what changes with time alone (upcoming events) |

## Mail and newsletter

| Variable | What it sets |
|---|---|
| `EMAIL_URL` | Mail backend for the contact form and the health digest, e.g. `smtp+tls://user:pass@host:587` |
| `DEFAULT_FROM_EMAIL` | Sender of that mail |
| `NEWSLETTER_BACKEND` | `log` (subscriptions go to the log) or `mailchimp` |
| `MAILCHIMP_API_KEY`, `MAILCHIMP_LIST_ID` | The Mailchimp audience; new subscribers confirm by mail |

The contact form appears once the profile has an e-mail address.

## Automation

| Variable | What it sets |
|---|---|
| `FEED_SOURCES` | Feeds `fetch_feeds` reads, see [Operations](operations.md#fetch_feeds) |
