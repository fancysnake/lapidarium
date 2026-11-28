# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-11-28

### Added

- First boot needs no shell: `ADMIN_USERNAME` and `ADMIN_PASSWORD` create the
  admin on a database with no accounts, `DEMO_CONTENT` loads a bundled demo, and
  a restart changes neither. A missing required variable stops the container
  with one line naming it.
- `docker/compose/vps.yaml` self-hosts on one machine: the app, PostgreSQL and
  Caddy, which gets the TLS certificate for `DOMAIN` and serves uploads from a
  volume. `vps.env.example` lists every variable.
- `docker/compose/coolify.yaml` is a Coolify service template: Coolify
  generates the secrets and assigns the domain, uploads stay in a volume, and
  only `ADMIN_PASSWORD` must be set.
- `container_section` role: a container with no outcome and no dates, such as a
  wiki section or a set of docs. Sections stay off the about-page timeline.
- Content panel at `/panel/`, open to every staff account and linked from the
  admin sidebar. No theme changes its look. Desk has a button for each type,
  the drafts, the latest changes and the coming events. All entries lists every
  entry, with filters by type and status and a search by title. Structure
  groups the types as pieces of work, events, projects, activities and
  sections. Site edits the profile's texts.
- The content panel creates a type from a purpose: one form opens on the
  purpose's suggested names, address and fields, and previews the type.
- The content panel changes a type: the form renames fields and adds one,
  lists how many entries a change moves, strips of a page or leaves unsavable,
  and saves only after the owner agrees to those effects.
- The content panel removes a field and changes its kind. It refuses both
  while entries hold a value for the field or link through it, and links to a
  page that lists them.
- `import_content --demo ttrpg|dev` loads a bundled demo.
- `mise run site:card` renders the social card PNG from its SVG.

### Changed

- An entry's page takes its shape from its own parts: players on top when it
  starts with audio or video, a grid when it holds only images, text first
  otherwise. A type's list is a grid while every entry holds only images.
- The export format is version 2. Version 1 files still import; their
  `layout` type setting is ignored.
- No type can take the route `panel`.
- An unknown demo name in `setup_local --demo` or `import_content --demo` fails
  with the list of bundled ones.
- `--color-surface` must be `#rrggbb`, and a dark scheme keeps the light
  surface unless it sets its own.
- Themes declare `engine = "0.2"`; a theme built for `0.1` gets warning
  `lapidarium.W002`.

### Removed

- The layout setting of a type, in the admin and in export files.
- `load_demo`: use `import_content --demo ttrpg|dev`.
- `.vekna.toml` and the cabinet dev dependency. vekna and cabinet are
  installed per user, and the rituals read `[projects.lapidarium.cabinet]`
  from the vekna user config.

### Fixed

- A public page opens when a stored value no longer fits its field, for example
  a number left in a field changed to a url. Entry pages, lists and the home
  page leave such a value out; the admin still shows it for re-entry.
- `/healthz/` answers `503` while the database is unreachable. The image runs
  the check itself; compose files no longer wire their own.
- A type's role locks once it has entries. The admin shows the role read-only,
  and `import_content` refuses a bundle that changes it.
- `export_content` leaves out built-in fields an entry's role does not use, so
  the export imports back even after a role change made before the lock. The
  stored values stay as they are.
- Saving an entry no longer turns a link into "part of" after its relation field
  is gone. The link shows its old role as no longer defined, and the entry saves
  once an editor picks another role or removes the link.
- An entry's admin page opens after its field changes kind. A stored value the
  new kind rejects starts blank, with a note naming what was stored.
- A content type can't take a route a fixed page, the admin, uploads or
  static files already use; the admin and `import_content` name the owner,
  and the type list flags types saved on one earlier.
- `import_content` refuses a site or friend button that is not an 88×31 image
  and names the button.
- `import_content` refuses a type whose required parts are not all allowed.
- The admin refuses a type whose list filter names a field removed in the same
  save.
- Every import clears the cached pages once it commits.
- Type colours are checked against `--color-surface` too. The admin and
  `import_content` refuse a colour under 4.5:1 on it, the dark scheme lightens
  colours until they read on the dark surface, and the theme check covers
  `--color-type-default` on it.

## [0.1.0] - 2026-10-30

### Added

- Project skeleton: Poetry package, mise tasks, GLIMPSE layers with import
  contracts, Django settings from the environment, django-unfold admin,
  `/healthz/`, Docker image, CI.
- Content model: admin-defined content types with field schemas, roles and
  layouts; entries built from ordered parts (text, video, audio, image, file,
  link); relations, tags, syndication links, media assets, profile, links,
  friends, showcases, external items.
- Unfold admin: sidebar from content types, entry forms built from the type's
  schema, contrast check and derived tint for type colours, graph integrity
  (containers, no loops, published never links to draft), bulk actions.
- Export format v1 (`types/`, `content/<type>/<slug>.md`, `assets/`) with
  `export_content` and `import_content`; `load_demo ttrpg|dev` loads a bundled
  set in the same format; `setup_local` migrates, loads a demo and ensures an
  admin login, refused unless `DEBUG`.
- Public site: home page with a door per content type, showcase bands of
  hand-picked entries, what's new, a follow box and the next calendar entry;
  a list per type with filters and pages (upcoming and archive for calendar
  types); detail pages laid out as article, media first or
  gallery, with parts, metadata, containers, related entries and an author
  box; about page with a timeline of projects and a friends section of 88x31
  buttons; search; RSS and iCal feeds; a footer crediting the site owner and
  the engine apart.
- Newsletter (Mailchimp or log) and contact form, with a honeypot and a rate
  limit per sender.
- Uploads to Google Cloud Storage when `GS_BUCKET_NAME` is set, prefixed by
  `GS_LOCATION`.
- Rendered public pages cached, cleared on every content change.
- Site-wide maintenance switch: a new instance starts hidden behind one page
  (503, `Retry-After`, a title over a random reason line) for visitors who are
  not signed in, until the owner turns it off or its end time passes.
- Base theme tokens and `base.css` ported from the prototype; type colours come
  from the admin. Videos load only when played; every page works without
  JavaScript.
- Themes: `SITE_THEME` picks a theme directory (`theme.toml`, `tokens.css`,
  optional `theme.css` and template overrides) from `SITE_THEME_DIRS` or the
  engine; the base tokens always load first. System checks for required tokens,
  contrast, engine version and stale template overrides; staff-only theme
  preview; type colours checked against the active theme's background, and
  lightened for its dark scheme, with the derived colour shown in the admin.
- Polish and English UI catalogs; `mise run i18n:make` and `i18n:compile`.
- Documentation site at <https://lapidarium.fancysnake.dev>: deployment of a
  new instance, every environment variable, content setup from scratch, the
  export format, commands, themes, the mission;
  `mise run site:dev` and `site:build`.
- cabinet's pull request rituals (`refresh`, `cover`, `review`, `labels`) via
  `.vekna.toml`.

[unreleased]: https://github.com/fancysnake/lapidarium/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/fancysnake/lapidarium/releases/tag/v0.2.0
[0.1.0]: https://github.com/fancysnake/lapidarium/releases/tag/v0.1.0
