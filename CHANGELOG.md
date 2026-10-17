# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Project skeleton: Poetry package, mise tasks, GLIMPSE layers with import
  contracts, Django settings from the environment, django-unfold admin,
  `/healthz/`, Docker image, CI.
- Content model: admin-defined content types with field schemas, roles and
  layouts; entries built from ordered parts (text, video, audio, image, file,
  link); relations, tags, syndication links, media assets, profile, links,
  external items.
- Unfold admin: sidebar from content types, entry forms built from the type's
  schema, contrast check and derived tint for type colours, graph integrity
  (containers, no loops, published never links to draft), bulk actions.
- Export format v1 (`types/`, `content/<type>/<slug>.md`, `assets/`) with
  `export_content` and `import_content`; `load_demo ttrpg|dev` loads a bundled
  set in the same format; `setup_local` migrates, loads a demo and ensures an
  admin login, refused unless `DEBUG`.
- Public site: home page with a door per content type, what's new and the next
  calendar entry; a list per type with filters and pages (upcoming and archive
  for calendar types); detail pages laid out as article, media first or
  gallery, with parts, metadata, containers, related entries and an author
  box; about page with a timeline of projects; search; RSS and iCal feeds.
- Newsletter (Mailchimp or log) and contact form, with a honeypot and a rate
  limit per sender.
- Rendered public pages cached, cleared on every content change.
- Base theme tokens and `base.css` ported from the prototype; type colours come
  from the admin. Videos load only when played; every page works without
  JavaScript.
- Themes: `SITE_THEME` picks a theme directory (`theme.toml`, `tokens.css`,
  optional `theme.css` and template overrides) from `SITE_THEME_DIRS` or the
  engine; the base tokens always load first. System checks for required tokens,
  contrast, engine version and stale template overrides; staff-only theme
  preview; type colours checked against the active theme's background.
- Polish and English UI catalogs; `mise run i18n:make` and `i18n:compile`.
- cabinet's pull request rituals (`refresh`, `cover`, `review`, `labels`) via
  `.vekna.toml`.
