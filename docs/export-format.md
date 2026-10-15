# Export format

`export_content` writes, and `import_content` reads, a directory of plain
files: the site's content as text a person can read and a diff can show.
Format version 1:

```text
lapidarium.yaml               format: 1
profile.yaml                  the profile and its links
types/<key>.yaml              one content type: settings and fields
content/<type>/<slug>.md      one entry: frontmatter, then its text parts
assets.yaml                   alt text per file path
assets/...                    the files, at the paths entries name
```

Settings left at their default are not written and may be left out by hand.

## An entry

```markdown
---
title: Ballada o łosiu
summary: Szanta o załodze, która nie sprawdziła manifestu.
date: 2026-03-20
status: published
featured: true
parts:
  - kind: audio
    url: https://soundcloud.com/example/ballada-o-losiu
  - kind: text
    caption: Słowa
relations:
  - role: inspired_by
    to: session/ucieczka-przed-kosmicznym-losiem
---
Hej, ładownia pusta była, tak mówił stary kwatermistrz,
hej, a w ładowni coś ryczało, coś większego niż my wszyscy.
```

The frontmatter holds the built-in columns, `metadata` (the type's fields),
`parts`, `relations` (`<type>/<slug>` targets) and `syndication`. A `text`
part's markdown is the body; with several text parts, `<!-- part -->`
separates them, in the order the frontmatter lists them.

## Rules on import

The whole export is checked against its own types before anything is written:
metadata against the fields, parts against the type's allowed and required
kinds, relations against roles and container types, no loops of containers, a
published entry never linking to a draft, every file an entry names present in
`assets.yaml`. Any problem stops the import and lists every file at fault.

Only published entries are exported. The format version changes only with a
major release of the engine.
