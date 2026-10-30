# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[unreleased]: https://github.com/fancysnake/lapidarium/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/fancysnake/lapidarium/releases/tag/v0.1.0
