---
description: "Deploy a lapidarium portfolio site to production: the Docker image, Compose, PostgreSQL, uploads, mail, backups and upgrades, through to the first admin login."
---

# Deployment

A production instance is one web container from the published image, a
PostgreSQL database and a TLS-terminating reverse proxy in front. This page
takes a new instance from nothing to the first admin login; filling it with
content is [Content](content.md).

## What you need

- A machine with Docker and Compose and ports 80 and 443 open, or a platform
  such as Coolify that runs a compose file.
- A domain whose DNS points at that machine; `localhost` to try it out.
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

On start the container checks its configuration, stopping with one line if a
required variable is missing, then runs `migrate`, `first_boot`,
`collectstatic` and gunicorn on port 8000 with three workers of two threads.
`/healthz/` answers `ok` while the database answers a query and `503` while it
does not; the image runs it as its own health check every 30 seconds. Because
migrations run on start, run one web container: two starting at once would
migrate at once.

## Compose

`docker/compose/vps.yaml` runs the whole instance on one machine: the image,
PostgreSQL, and Caddy in front. Caddy gets and renews a Let's Encrypt
certificate for the domain and serves uploads from a volume. Put three files
in one directory on the machine:

```bash
mkdir lapidarium && cd lapidarium
base=https://raw.githubusercontent.com/fancysnake/lapidarium/main/docker/compose
curl -fsSLO "$base/vps.yaml"
curl -fsSLO "$base/Caddyfile"
curl -fsSL "$base/vps.env.example" -o .env
```

Fill in the first block of `.env`: the domain, a secret key, a database
password and the first login. Generate both secrets once and keep them; a new
secret key logs everyone out:

```bash
openssl rand -base64 48   # SECRET_KEY
openssl rand -hex 32      # DB_PASSWORD
```

Then start it:

```bash
docker compose -f vps.yaml up -d
docker compose -f vps.yaml logs -f web
```

The site answers on `https://<DOMAIN>` once the web container is healthy,
usually within a minute. Any variable from [Configuration](configuration.md)
goes in `.env` as well; the example lists each one, commented out at its
default. The compose file sets `ENV`, `DEBUG`, `DATABASE_URL`, `MEDIA_ROOT`
and `MEDIA_URL` itself, and reads these on its own:

| Variable | Default | What it sets |
|---|---|---|
| `DOMAIN` | required | Domain Caddy gets a certificate for; also `ALLOWED_HOSTS` unless that is set |
| `DB_PASSWORD` | required | Database password; it goes into a URL, so letters and digits only |
| `DB_NAME` | `lapidarium` | Database name; fixed once the database volume exists |
| `DB_USER` | `lapidarium` | Database user; fixed once the database volume exists |
| `IMAGE_TAG` | `latest` | Image tag to run |

With `DOMAIN=localhost`, Caddy signs the certificate with its own authority,
so the browser warns about it. To serve a second name, such as `www.`, add it
to `ALLOWED_HOSTS` and after `{$DOMAIN}` in the `Caddyfile`, comma-separated.

Data lives in named volumes: `postgres_data`, `media`, and Caddy's
certificates in `caddy_data`. `docker compose down` keeps them; `down -v`
deletes them.

## Coolify

`docker/compose/coolify.yaml` is a Coolify service template for the same
instance. Coolify generates the secret key and the database password, assigns
the domain and gets its certificate; you choose only the first login.

1. In a Coolify project, add a resource of the kind **Docker Compose Empty**
   and paste in the
   [template](https://raw.githubusercontent.com/fancysnake/lapidarium/main/docker/compose/coolify.yaml).
2. To use a domain of your own, set it on the `caddy` service, as
   `https://example.com`, with its DNS pointing at the Coolify server.
   Otherwise Coolify generates one.
3. Under the environment variables, set `ADMIN_PASSWORD`; Coolify refuses to
   deploy without it.
4. Deploy. The site answers on the domain once the web container is healthy,
   usually within a minute.

The template asks for these; all but the password have a default:

| Variable | Default | What it sets |
|---|---|---|
| `ADMIN_PASSWORD` | required | Password of the login created on the first start |
| `ADMIN_USERNAME` | `admin` | Login created on the first start |
| `ADMIN_URL` | `admin/` | Path of the admin, with a trailing slash; pick one of your own |
| `SITE_NAME` | `lapidarium` | Site title until the profile has a name |
| `LANGUAGE_CODE` | `pl` | Interface language, `pl` or `en` |
| `TIME_ZONE` | `Europe/Warsaw` | Time zone for calendar entries and feeds |
| `DEMO_CONTENT` | empty | Bundled demo loaded on the first start, `ttrpg` or `dev` |
| `EMAIL_URL` | `consolemail://` | Mail backend for the contact form |
| `DEFAULT_FROM_EMAIL` | `webmaster@localhost` | Sender of contact form mail |
| `IMAGE_TAG` | `latest` | Image tag to run |

Coolify passes a container only the variables the template names. To set
another one from [Configuration](configuration.md), add it under
`web.environment` in the resource's compose file.

Coolify's proxy routes the domain to Caddy, which serves uploads from the
`media` volume and passes everything else to the web container. Caddy keeps
the `X-Forwarded-For` and `X-Forwarded-Proto` headers of Coolify's proxy and
appends to the first. That makes two proxies, so the template sets
`TRUSTED_PROXY_HOPS` to `2`. The database and the uploads live in named
volumes, which a redeploy keeps.

`docker/compose/prod.yaml` is the shape for your own bucket, without Caddy:
every value is set by hand, and uploads need a bucket. The
`deploy-coolify.yml` workflow deploys to a resource made from it.

## Uploads

`vps.yaml` and `coolify.yaml` keep uploads in the `media` volume, and Caddy
serves them at `/media/`.

To keep them in Google Cloud Storage instead, create a bucket, allow public
read on its objects, and give a service account write access. Set
`GS_BUCKET_NAME` and `GS_LOCATION`, mount the account's key into the web
container, and point `GOOGLE_APPLICATION_CREDENTIALS` at it; on GCP with an
attached account, leave it empty. `prod.yaml` requires a bucket, because it
has no Caddy, so nothing serves the `media` volume.

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

The first start creates the admin from `ADMIN_USERNAME` and `ADMIN_PASSWORD`.
Later starts leave accounts alone, so change the password in the admin, not in
`.env`. Without `ADMIN_PASSWORD`, create the admin yourself:

```bash
docker compose -f vps.yaml exec web mise run dj createsuperuser
```

Log in at `https://<your domain>/<ADMIN_URL>`. The site is empty until it has
content types and entries; [Content](content.md) sets them up, or imports a
bundle exported from another instance. To start from a demo instead, set
`DEMO_CONTENT` before the first start (see
[Configuration](configuration.md#first-boot)).

## Backups

Two things hold an instance: the database and the uploads. Back up both:

- `pg_dump` of the database, on the database's own schedule.
- The `media` volume, or the bucket.

`export_content` also writes every published entry, type, the profile and
the assets they use as plain files (see [Export format](export-format.md)).
It does not run by itself; schedule it from the host. `vps.yaml` mounts
nothing at `/app/export`, so without a volume there the export is lost when
the container is recreated. Add one under `web`:

```yaml
    volumes:
      - ./export:/app/export
```

The container runs as an unprivileged user, so create `export/` on the host
first and give it to that user's UID, which
`docker compose -f vps.yaml exec web id -u` prints. Then run it:

```bash
docker compose -f vps.yaml exec -T web mise run dj export_content /app/export
```

The export holds published content only: drafts, users and sign-ups live in
the database dump alone.

## Upgrades

On a VPS, change `IMAGE_TAG` and recreate the container:

```bash
docker compose -f vps.yaml up -d
```

On Coolify, change `IMAGE_TAG` under the resource's environment variables,
then redeploy.

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
