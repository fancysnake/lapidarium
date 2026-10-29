# Export format

An instance's content as plain files: YAML for types and the profile, markdown
with frontmatter for entries. [`export_content`](cli.md#export_content) writes
it, [`import_content`](cli.md#import_content) reads it, and the bundled demos
are written in it. A bundle written by hand is a way to set up a new instance's
content in a text editor and keep it in git.

This page describes format version 1.

## Layout

```text
lapidarium.yaml               format version
profile.yaml                  profile, links and friends
showcases.yaml                showcases and their entries
types/<key>.yaml              type settings and fields
content/<type>/<slug>.md      frontmatter, then the text parts as the body
assets.yaml                   alt text per asset path
assets/…                      the files, at the paths entries refer to
```

Keys left at their default are not written, and you may leave them out by
hand. Every setting is described in [Content](content.md); the keys are the
field names there in `snake_case`.

## `lapidarium.yaml`

```yaml
--8<-- "src/lapidarium/links/content_files/demos/dev/lapidarium.yaml"
```

## `profile.yaml`

The profile's fields, plus `links`, a list of `platform`, `url` and `label`,
and `friends`, a list of `name`, `url` and `button`. `photo` and both kinds of
`button` are asset paths.

```yaml
--8<-- "src/lapidarium/links/content_files/demos/dev/profile.yaml"
```

## `showcases.yaml`

A list of showcases, in order: `title`, `intro`, `hidden` and `entries`, each
entry as `<type>/<slug>`. Every entry must be in the bundle. Export leaves out
entries that are not published.

```yaml
--8<-- "src/lapidarium/links/content_files/demos/dev/showcases.yaml"
```

## `types/<key>.yaml`

A type's settings, then `fields`, in order. The file name must match `key`.

```yaml
--8<-- "src/lapidarium/links/content_files/demos/dev/types/talk.yaml"
```

A calendar type:

```yaml
--8<-- "src/lapidarium/links/content_files/demos/dev/types/event.yaml"
```

## `content/<type>/<slug>.md`

The type and the slug come from the path, not the frontmatter. Frontmatter
keys, in the order they are written:

`title`, `summary`, `date`, `start_at`, `end_at`, `location`, `is_online`,
`outcome`, `external_url`, `status`, `featured`, `hide_from_whats_new`,
`license`, `cover`, `tags`, `metadata`, `parts`, `relations`, `syndication`,
`created_at`, `updated_at`.

- `status` defaults to `draft`; write `published` for the entry to appear.
- `metadata` holds the type's own fields, by key.
- `parts` lists every part in order, each with `kind` and as needed `url`,
  `asset`, `caption` and `options`. A text part is just `- kind: text`; its
  text is the body.
- Several text parts split the body with `<!-- part -->`, one section per
  text part, in order. The counts must match.
- `relations` are `role` and `to`, where `to` is `<type>/<slug>`.
- `syndication` lists `platform` and `url`.

```markdown
--8<-- "src/lapidarium/links/content_files/demos/dev/content/talk/zero-node-django.md"
```

## `assets.yaml` and `assets/`

Each file an entry or the profile refers to sits at its path under `assets/`,
and `assets.yaml` gives its alt text. Paths stay under `assets/`; `..` is
refused.

```yaml
--8<-- "src/lapidarium/links/content_files/demos/dev/assets.yaml"
```

## Checks on import

`import_content` validates the whole bundle before it writes anything, and
reports every problem by file:

- the format version is one it reads;
- keys and slugs are `[-a-zA-Z0-9_]+`;
- type colours pass the contrast check against the active theme;
- `list_filters` name `year`, `tag` or a field of the type;
- metadata keys are fields of the type and their values fit the field kind;
- built-in fields are only those the type's role uses, with `end_at` on or
  after `start_at`;
- parts are allowed by the type, required parts are present, and their assets
  exist;
- relations point at other entries in the same bundle, `part_of` at a
  container, without loops, and never from published to draft.

The full demos are in
[`src/lapidarium/links/content_files/demos/`](https://github.com/fancysnake/lapidarium/tree/main/src/lapidarium/links/content_files/demos).
