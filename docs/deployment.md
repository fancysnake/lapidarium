# Deployment

A production instance is one web container from the published image, a
PostgreSQL database and a TLS-terminating reverse proxy in front. This page
takes a new instance from nothing to the first admin login; filling it with
content is [Content](content.md).

## What you need

- A host that runs containers: plain Docker Compose, or a platform such as
  Coolify that runs a compose file.
- PostgreSQL 16. The compose file below brings its own.
- A domain, and a reverse proxy that terminates TLS and forwards
  `X-Forwarded-Proto` and `X-Forwarded-Host`. Production redirects every
  plain HTTP request to HTTPS.
- Somewhere for uploads: a Google Cloud Storage bucket with public read, or a
  volume your proxy serves (see [Uploads](#uploads)).
- Optional: an SMTP account for the contact form, a Mailchimp audience for the
  newsletter.

## The image

`ghcr.io/fancysnake/lapidarium` is built on every push to `main` and every
`v*` tag:

| Tag | Points at |
|---|---|
| `sha-<commit>` | one exact build; what to deploy |
| `<version>` | a release, e.g. `0.1.0` |
| `latest` | the newest build of `main` |

Pin `sha-<commit>` or a version in production, so that a restart never
upgrades the site behind your back.

On start the container runs `migrate`, `collectstatic`, then gunicorn on port
8000 with three workers of two threads. `/healthz/` answers `ok` without
touching the database; use it for the health check. Because migrations run on
start, run one web container: two starting at once would migrate at once.

## Compose

`docker/compose/prod.yaml` is the production shape: the image, PostgreSQL with a
named volume, a health check, and the web port bound to `127.0.0.1` for a proxy
on the same host. Copy it to the host and put the values in a `.env` next to
it:

```dotenv
IMAGE_TAG=sha-<commit>
SECRET_KEY=<a long random string>
ALLOWED_HOSTS=example.com,www.example.com
DB_PASSWORD=<a database password>
DATABASE_URL=postgres://lapidarium:<the same password>@db:5432/lapidarium
SITE_NAME=Example
ADMIN_URL=<a path of your own>/
GS_BUCKET_NAME=<bucket>
GS_LOCATION=media
GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcs.json
```

Generate the secret key once and keep it; changing it logs everyone out:

```bash
openssl rand -base64 48
```

Then start it:

```bash
docker compose -f prod.yaml up -d
docker compose -f prod.yaml logs -f web
```

The compose file passes only the variables it names. To set others from
[Configuration](configuration.md), such as `EMAIL_URL`, `LANGUAGE_CODE` or
`SITE_THEME`, add them under `web.environment`.

On Coolify, create a Docker Compose resource from the same file, set the values
as environment variables in Coolify, and mount the service-account key as a
file. Coolify's proxy is one hop, which is the production default of
`TRUSTED_PROXY_HOPS`.

## Uploads

`prod.yaml` requires a bucket. Create a Google Cloud Storage bucket, allow
public read on its objects, and give a service account write access. Mount the
account's key into the container and point `GOOGLE_APPLICATION_CREDENTIALS` at
it; on GCP with an attached account, leave it empty.

Without a bucket, uploads go to `MEDIA_ROOT` inside the container. Django does
not serve them in production, so mount a volume there, have your proxy serve it
at `MEDIA_URL`, and drop `GS_*` from the compose file.

## Mail and newsletter

The contact form sends through `EMAIL_URL`; the default only prints to the log.
For SMTP:

```dotenv
EMAIL_URL=smtp+tls://user:password@smtp.example.com:587
DEFAULT_FROM_EMAIL=site@example.com
```

The newsletter form logs sign-ups until you set `NEWSLETTER_BACKEND=mailchimp`
with `MAILCHIMP_API_KEY` and `MAILCHIMP_LIST_ID`.

## A theme of your own

Mount a directory of themes into the container, then name it and the theme:

```dotenv
SITE_THEME_DIRS=/themes
SITE_THEME=<theme directory name>
```

`collectstatic` picks up the theme's static files on the next start. The system
checks that run with `migrate` validate the theme's tokens and contrast; an
error stops the start, so read the log after a theme change. See
[Themes](themes.md).

## First login

Create the admin account inside the running container:

```bash
docker compose -f prod.yaml exec web mise run dj createsuperuser
```

Log in at `https://<your domain>/<ADMIN_URL>`. The site is empty until it has
content types and entries; [Content](content.md) sets them up, or imports a
bundle exported from another instance.

## Backups

Two things hold an instance: the database and the uploads. Back up both:

- `pg_dump` of the database, on the database's own schedule.
- The bucket, or the `MEDIA_ROOT` volume.

`export_content` also writes every published entry, type, the profile and
the assets they use as plain files (see [Export format](export-format.md)).
It does not run by itself; schedule it from the host. `prod.yaml` mounts
nothing at `/app/export`, so without a volume there the export is lost when
the container is recreated. Add one under `web`:

```yaml
    volumes:
      - ./export:/app/export
```

The container runs as an unprivileged user, so create `export/` on the host
first and give it to that user's UID, which
`docker compose -f prod.yaml exec web id -u` prints. Then run it:

```bash
docker compose -f prod.yaml exec -T web mise run dj export_content /app/export
```

The export holds published content only: drafts, users and sign-ups live in
the database dump alone.

## Upgrades

Change `IMAGE_TAG` and recreate the container:

```bash
docker compose -f prod.yaml up -d
```

Migrations run on start. Read the [changelog](changelog.md) first: a theme
built for an older engine release raises warning `lapidarium.W002`, and a
template override the engine no longer has raises `lapidarium.W003`.

## Checklist

- `ENV` is `production` and `DEBUG` is `false` (both are the defaults).
- `SECRET_KEY` is random and kept outside the repository.
- `ALLOWED_HOSTS` lists every domain the site answers to.
- `ADMIN_URL` is not `admin/`.
- The proxy terminates TLS and forwards `X-Forwarded-Proto`.
- `TRUSTED_PROXY_HOPS` matches the proxies in front.
- Uploads go to a bucket or a served volume.
- `EMAIL_URL` points at a real mail server, if the profile has an e-mail.
- The database and the uploads are backed up.
