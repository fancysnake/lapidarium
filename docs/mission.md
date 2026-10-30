---
description: "Why lapidarium exists, what it stands for, and what it deliberately is not."
---

# Mission

lapidarium is a home base for multi-format creators: one site, owned by the
creator, where a song, a session, a talk and an event each have a page and
point to each other.

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
  the source of truth; platforms are distribution. Content leaves the engine
  as plain files, so no one is locked in, including by lapidarium.
- **Work is a web, not a grid.** A piece of work makes sense in its context:
  what it is part of, what it relates to, what came before it.
- **New kinds of work need no new code.** Creators invent formats faster than
  software ships; a new format is configuration, not a feature request.
- **The web page is enough.** Pages work without JavaScript, load no
  third-party scripts until asked, and stay readable for every visitor.
- **Guard against mistakes.** The engine refuses to publish what would break:
  missing alt text, links to drafts, unreadable colours.
- **Say only what is true today.** This documentation describes what a fresh
  instance does now. A plan is not a feature until it ships.

The [principles](concepts.md#principles) explain how the engine puts these
into practice.

## What it does today

| Feature | What the engine does |
|---|---|
| **Content types as data** | Content types, fields, allowed parts and layouts are set in the admin. A podcast, a zine or a TTRPG campaign needs no code and no migration. |
| **Work in context** | Outcome containers (an album, a campaign), timespan containers (a role since 2019), many-to-many relations and computed backlinks build the about-page timeline. |
| **[Own site first](concepts.md#publish-on-your-own-site-syndicate-elsewhere)** | A canonical address per piece, syndication links recorded per entry, RSS of what's new, iCal of upcoming events, a newsletter form in every footer. |
| **[A way out](concepts.md#content-outlives-the-application)** | [Export](export-format.md) to markdown with YAML frontmatter and media; import checks the whole bundle before writing. Exported into git on a schedule, the published site outlives the engine. |
| **Events** | A calendar role with start, end, location and an online flag; upcoming and archive split by date; a *Next up* box on the home page; `/calendar.ics`. |
| **[Checks before publishing](concepts.md#computed-not-typed)** | Alt text on every image, type colours contrast-checked against the theme, published entries never link to drafts, containment never loops. |
| **[HTML first](concepts.md#html-first-javascript-as-an-enhancement)** | Every page works without JavaScript. Videos load the YouTube, Vimeo or PeerTube player only on click. No bundler, no `package.json`. |
| **[Every page is a first visit](concepts.md#every-page-is-a-first-visit)** | Detail pages carry the author box, their containers, related entries and the newsletter form, because traffic from posts and videos lands there. |

## What it is not

- **Not a general-purpose CMS.** It models a creator's portfolio: entries,
  containers, relations and events. It does not build arbitrary websites.
- **Not a link-in-bio page.** Each piece of work gets its own page, not a
  button on a list.
