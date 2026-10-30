---
description: "How lapidarium models a portfolio: content types, entries built from ordered parts, media assets, links between entries, and the principles behind the engine."
---

# How it works

lapidarium is built on a few decisions about where content lives, what it is
and how visitors reach it. This page explains them and the content model they
produced; [Content](content.md) is the field-by-field reference.

## The content model

<figure class="diagram">
--8<-- "docs/assets/content-model.svg"
<figcaption>A content type shapes its entries; entries are built from parts
and linked to each other; what is published renders as the public site and
exports as plain files.</figcaption>
</figure>

Everything on the site is one of these records:

| Record | What it is | Its page |
|---|---|---|
| Entry of a `thing` type | a finished piece: a song, a game, a session, a meme | `/<route>/<slug>/`, unless the type turns detail pages off |
| Entry of a `calendar` type | something that happens on a date: an event, a convention | the same, plus the calendar feed |
| Entry of a container type | a project or a period that other entries belong to | the same, listing its contents |
| Profile and links | who the site is about, and where else to find them | the about page and the footer |
| Friend | a site the owner likes, shown as an 88×31 button | the about page |
| Showcase | entries picked by hand, in order | a band on the home page |
| External item | a post elsewhere: a video, a game page | none; it links out from what's new |

Every entry, whatever its type, shares the same core: title, slug, a
one-sentence summary, status, tags, cover, and a sequence of parts. What
differs between types is data: the type's fields, its role, which parts it
allows, its layout and its colour. A site without songs simply has no song
type. A new kind of work is a new row in the admin, not a code change or a
migration.

### Containers

There are two kinds of container, and the difference is what ends them:

- **Outcome** (`container_outcome`): a project bounded by its result,
  `ongoing`, `finished` or `abandoned`. An album, a campaign, a series of
  memes, a game with its expansions.
- **Timespan** (`container_timespan`): a role or activity bounded by time, with
  a start and an optional end; no end means it continues. Organising a
  convention since 2019, writing songs about games since 2021.

An entry joins a container through a *part of* relation. Every level is
optional and the links are many-to-many: a song can belong to two albums, an
album to a timespan. Containers form the timeline on the about page.

### Relations

Relations connect any entry to any other. *Part of* is the containment above;
*related* is a loose link both entries show. A relation field on a type adds a
named role of its own: the demo's songs have *inspired by*, pointing at the
session behind the song.

Backlinks are never typed by hand. "Belongs to", "contains" and "linked from"
are the same relations read from the other end: the detail page shows them,
and the admin shows them read-only.

### The demo, as a worked example

The `ttrpg` demo (`load_demo ttrpg`) is a game master's site built on this
model. Sessions, songs, games, memes, articles and events are `thing` and
`calendar` types; a campaign is an outcome container that sessions are part
of; an initiative is a timespan container. Load it locally and read its types
in the admin to see each setting in use.

## Principles

### Publish on your own site, syndicate elsewhere

The site is the source of truth. Social platforms, YouTube, itch.io and
SoundCloud are distribution channels: they change their rules, cut reach and
disappear. So:

- Every piece of work has a canonical address on the site; posts elsewhere
  link to it, not the other way round.
- Every entry keeps its *syndication links*: the copies and announcements of
  it on other platforms.
- The site publishes its own feeds, RSS of what's new and iCal of upcoming
  events, so it can be followed without any platform.
- The newsletter is the channel the owner controls; social media come second.

### Content outlives the application

Content lives in PostgreSQL because that makes editing easy, but
[`export_content`](cli.md#export_content) writes the published content as
markdown with YAML frontmatter, plus the media. Run on a schedule into a git
repository, the export is a copy of the published site, a history of changes
and a way out: if the engine ever dies, the content stays readable. It is not
a full backup; drafts and users live only in the database, see
[Backups](deployment.md#backups). [`import_content`](cli.md#import_content)
reads it back, to restore an instance, move it, or start a new one from files.
The [format](export-format.md) is versioned because it is part of that
promise.

### The data model is not the navigation

The model describes what the content *is*: things, containers, relations.
Navigation answers what a visitor *wants*: "something to listen to",
"something to play". The menu and the home page doors are views over the
model, configured per type, not records of their own. Relabelling the
*Memes* door as *Graphics* changes no data.

### Every page is a first visit

Traffic from posts and videos lands on detail pages, not the home page. So
every detail page carries the author box, the containers it belongs to, the
related entries and the newsletter form in the footer.

### Computed, not typed

What can be derived is derived: creation and update dates, backlinks, what's
new, added versus updated, the split of calendar lists into upcoming and
archive, the search index, the cache. Past events move to the archive by date,
with no status to change.

What is typed is checked when it is saved, in three levels:

1. **The field.** Required fields, field kinds, choices, URL hosts (YouTube,
   itch.io, GitHub), an end on or after the start, slugs unique within a type,
   alt text on every image, a type's required parts.
2. **The graph.** *Part of* points only at containers and never loops; a
   published entry never links to a draft, so nothing public points at a
   missing page; a type's colour reads against the theme.
3. **The import.** `import_content` runs every rule above over the whole
   bundle before it writes anything.

The admin's publish and unpublish bulk actions skip the entries
a rule would refuse.

### HTML first, JavaScript as an enhancement

Every page works without JavaScript. Filters are GET parameters; interactions
use native elements. Videos load the platform's player only when played, so a
page view loads no third-party script. There is no Node: no `package.json`, no
bundler, plain CSS and a few vanilla ES modules.

## Engine and instance

The **engine** is this repository: the Django apps, the admin, the templates,
the `base` theme, the management commands and the container image.

An **instance** is one site run from that image. It owns its environment
variables (see [Configuration](configuration.md)), optionally a theme
directory, and its content, which lives in the database and in exports, never
in the engine's code. An instance needs no Python of its own.

The interface is translated into Polish and English. An instance's content is
in one language. The site has no comments, by design.
