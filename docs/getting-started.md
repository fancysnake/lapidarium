---
description: "Run a lapidarium portfolio site locally from a clone: SQLite, a demo site loaded, the public pages and the admin up in four commands, PostgreSQL optional."
---

# Getting started

This runs the engine from a clone, on SQLite, with a demo site loaded. It is
the fastest way to see what an instance looks like before you deploy one.

--8<-- "README.md:development"

## What you get

`setup_local` migrates the database, imports the `ttrpg` demo and creates the
`admin` user with password `admin`. It refuses to run unless `DEBUG` is on, and
`env/development.env` turns it on.

- <http://localhost:8000/> is the public site: a door per content type on the
  home page, a list per type, detail pages, about, search and feeds.
- <http://localhost:8000/admin/> is the admin. The sidebar lists one section
  per content type.

To start from the other demo, a developer's portfolio of repos and talks:

```bash
mise run dj setup_local --demo dev
```

To start from nothing instead, skip `setup_local` and follow
[Content](content.md):

```bash
mise run dj migrate
mise run dj createsuperuser
mise run start
```

## PostgreSQL

Production runs on PostgreSQL. To develop against it, `mise run db` starts a
container on `127.0.0.1:5432`; point the dev server at it in `mise.local.toml`:

```toml
[env]
DATABASE_URL = "postgres://lapidarium:lapidarium@127.0.0.1:5432/lapidarium"
```
