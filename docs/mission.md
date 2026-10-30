---
description: "Why lapidarium exists, what it stands for, and what it deliberately is not."
---

# Mission

lapidarium is a home base for multi-format creators: one site, owned by the
creator, where every song, session, talk and event has its own address and
links to the rest.

## Why it exists

A creator who records music, runs games, gives talks and organises events
leaves that work scattered across platforms. Each platform shows one format,
sets its own rules and can cut reach or close at any time. None of them shows
the whole body of work, or how the pieces connect: the album a song belongs
to, the campaign a session was part of, the talk that grew out of a project.

lapidarium gives that work one canonical home that the creator controls: the
single source of truth at the centre, linking out to every copy elsewhere, so
the record of the work outlives any one platform.

## What we believe

- **Publish here, syndicate everywhere, leave anytime.** The creator's site is
  the source of truth; platforms are distribution. Every piece has a canonical
  address and records where it is syndicated; RSS carries what's new and iCal
  the upcoming events. Content [exports](export-format.md) to markdown with
  YAML frontmatter and media, so no one is locked in, including by
  lapidarium.
  See [own site first](concepts.md#publish-on-your-own-site-syndicate-elsewhere)
  and [a way out](concepts.md#content-outlives-the-application).
- **Work is a web, not a grid.** A piece of work makes sense in its context:
  what it is part of, what it relates to, what came before it. Outcome
  containers (an album, a campaign), timespan containers (a role since 2019),
  relations and computed backlinks build the about-page timeline.
  See [containers](concepts.md#containers) and
  [relations](concepts.md#relations).
- **New kinds of work need no new code.** Creators invent formats faster than
  software ships. Content types, fields, allowed parts and layouts are set in
  the admin; a podcast, a zine or a TTRPG campaign needs no code and no
  migration. See [the content model](concepts.md#the-content-model).
- **The web page is enough.** Every page works without JavaScript. Videos load
  the YouTube, Vimeo or PeerTube player only on click, so a page view loads no
  third-party script. No bundler, no `package.json`.
  See [HTML first](concepts.md#html-first-javascript-as-an-enhancement).
- **Refuse to save what would break.** An image without alt text, a published
  entry that links to a draft, a type colour unreadable against the theme,
  containment that loops: each is refused when saved, and bulk publishing
  skips the entries a rule would refuse.
  See [computed, not typed](concepts.md#computed-not-typed).

## What it is not

- **Not a general-purpose CMS.** It models a creator's portfolio: entries,
  containers, relations and events. It does not build arbitrary websites.
- **Not a link-in-bio page.** Each piece of work gets its own address, not a
  button on a list.
