---
description: "Every environment variable a lapidarium instance reads: core, files, caching, mail and newsletter, proxies and themes, each with its type, default and effect."
---

# Configuration

An instance is configured through the environment. The settings module,
`lapidarium.edges.settings`, reads every value below and needs no edits of
its own.

In the tables, *required* means the start fails without it and *empty* means
an empty string or list. Lists are comma-separated.

## Core

| Variable | Default | What it sets |
|---|---|---|
| `ENV` | `production` | `production` turns on the hardening below; `development` and `test` leave it off |
| `DEBUG` | `false` | Django debug pages; also serves uploads from `MEDIA_ROOT` and allows `setup_local` |
| `SECRET_KEY` | required | Django's signing key; a long random string, never shared between instances |
| `ALLOWED_HOSTS` | `localhost` | Host names the site answers to; a leading dot matches every subdomain |
| `DATABASE_URL` | required | Database, e.g. `postgres://user:password@host:5432/name`; `sqlite:///db.sqlite3` for development |
| `ADMIN_URL` | `admin/` | Path of the admin, with a trailing slash; the theme preview lives under it |
| `SITE_NAME` | `lapidarium` | Site title until the profile has a name; the admin header always |
| `LANGUAGE_CODE` | `pl` | Default interface language, `pl` or `en`; a browser asking for the other gets it |
| `TIME_ZONE` | `Europe/Warsaw` | Time zone for calendar entries and feeds |

With `ENV=production` the site redirects to HTTPS (except `/healthz/`), sends
HSTS for a year with subdomains and preload, marks session and CSRF cookies
secure, denies framing, serves static files through WhiteNoise, and trusts
`https://<host>` for every entry in `ALLOWED_HOSTS` as a CSRF origin. It reads
`X-Forwarded-Proto` and `X-Forwarded-Host`, so a TLS-terminating proxy in front
is expected.

## Files

| Variable | Default | What it sets |
|---|---|---|
| `STATIC_ROOT` | `staticfiles` | Where `collectstatic` writes the engine's and the theme's static files |
| `MEDIA_ROOT` | `media` | Uploads on the filesystem, when no bucket is set |
| `MEDIA_URL` | `/media/` | URL prefix of uploads |
| `GS_BUCKET_NAME` | empty | Turns on Google Cloud Storage for uploads; the bucket must allow public read |
| `GS_LOCATION` | empty | Path prefix for uploads inside the bucket |
| `GOOGLE_APPLICATION_CREDENTIALS` | empty | Service-account key file for the bucket; unneeded on GCP with an attached account |

Django serves uploads only with `DEBUG` on. In production, either set a bucket
or have the proxy serve `MEDIA_ROOT` at `MEDIA_URL`.

## Caching

| Variable | Default | What it sets |
|---|---|---|
| `CACHE_URL` | `locmemcache://` | Default cache; rate limits count here |
| `PAGE_CACHE_URL` | `filecache:///tmp/lapidarium-pages` | Rendered public pages; must be shared by all workers |
| `PAGE_CACHE_SECONDS` | `600` | How long a rendered page lives; any content change clears them all |

Both URLs take the [django-environ cache
schemes](https://django-environ.readthedocs.io/en/latest/types.html#environ-env-cache-url),
e.g. `rediscache://host:6379/1`. With more than one container, point both at a
shared cache: a per-container cache keeps stale pages after an edit and counts
rate limits per container.

## Mail and newsletter

| Variable | Default | What it sets |
|---|---|---|
| `EMAIL_URL` | `consolemail://` | Mail backend for the contact form, e.g. `smtp+tls://user:password@host:587` |
| `DEFAULT_FROM_EMAIL` | `webmaster@localhost` | Sender of contact form mail |
| `NEWSLETTER_BACKEND` | `log` | `log` writes sign-ups to the log; `mailchimp` adds them to an audience |
| `MAILCHIMP_API_KEY` | empty | Mailchimp API key, required with `mailchimp` |
| `MAILCHIMP_LIST_ID` | empty | Mailchimp audience ID, required with `mailchimp`; new subscribers confirm by mail |

The contact form appears once the profile has an e-mail address; messages go
there, with the sender as reply-to, at most five per sender an hour.

## Proxies

| Variable | Default | What it sets |
|---|---|---|
| `TRUSTED_PROXY_HOPS` | `1` in production, else `0` | Proxies in front that append to `X-Forwarded-For`; rate limits key on the address the outermost one saw |

Set it to the number of proxies that append to the header: `1` behind one
reverse proxy, `2` behind a CDN and a proxy. Too high and a client can forge
its address; `0` ignores the header.

## Themes

| Variable | Default | What it sets |
|---|---|---|
| `SITE_THEME` | `base` | Active theme, by directory name |
| `SITE_THEME_DIRS` | empty | Extra theme directories, searched before the engine's |

A theme name with no directory stops the start. See [Themes](themes.md).
