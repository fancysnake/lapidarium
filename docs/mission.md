---
description: "What lapidarium is for, where it beats the alternatives, and how to describe it: the mission statement and the rules for advertising the engine."
---

# Mission

lapidarium is a home base for multi-format creators: the one canonical place
where a song, a session, a talk and an event each have a page and point to
each other.

It is not a CMS and not a link-in-bio page. Most rivals pick one format:
links, posts or a gallery. lapidarium models a creator's whole output and the
links between the pieces.

## Where it wins

Each claim below is true of the engine today. The comparison names what
creators use instead.

| Edge | What the engine does | Instead |
|---|---|---|
| **A new kind of work is a row, not a release** | Content types, fields, allowed parts and layouts are data in the admin. A podcast, a zine or a TTRPG campaign needs no code and no migration. | Ghost has posts and pages. Kirby and Wagtail need blueprints or Python models written by a developer. |
| **Work that knows its context** | Outcome containers (an album, a campaign), timespan containers (a role since 2019), many-to-many relations and computed backlinks build the about-page timeline. | Portfolio builders and link-in-bio tools show flat grids with no relationships. |
| **POSSE in every entry** | A canonical address per piece, syndication links recorded per entry, RSS of what's new, iCal of upcoming events, a newsletter form in every footer. | Micro.blog does POSSE, but everything is a blog post. Squarespace-style builders treat the site as a brochure. |
| **A versioned exit door** | [Export](export-format.md) to markdown with YAML frontmatter and media; import checks the whole bundle before writing. Exported into git on a schedule, the published site outlives the engine. | Bento closed on 13 February 2026; pages not exported by then were deleted. |
| **Events are first-class** | A calendar role with start, end, location and an online flag; upcoming and archive split by date; a *Next up* box on the home page; `/calendar.ics`. | Rare outside event platforms; portfolio tools bolt it on with embeds. |
| **Hard to publish something broken** | Alt text on every image, type colours contrast-checked against the theme, published entries never link to drafts, containment never loops. | WordPress and Ghost leave accessibility and link integrity to the author. |
| **HTML first, nothing sent to Google** | Every page works without JavaScript. Videos load the YouTube, Vimeo or PeerTube player only on click. No bundler, no `package.json`. | Ghost 6 runs analytics and ActivityPub as extra services; most builders ship heavy JavaScript. |
| **Every page is a first visit** | Detail pages carry the author box, their containers, related entries and the newsletter form, because traffic from posts and videos lands there. | Blog engines optimise the home page and leave posts as dead ends. |

[How it works](concepts.md) explains the content model and principles behind
each edge.

## How to describe it

One message per audience. Lead with the headline; the proof backs it.

| Audience | Headline | Proof |
|---|---|---|
| Creators | All your work, on one site you own. | Songs, sessions, talks, events: each with a page, all linked. |
| The indie web | Publish here. Syndicate everywhere. Leave anytime. | POSSE, RSS, iCal, 88×31 friends, markdown export. |
| Developers | A portfolio engine with zero Node. | Django, PostgreSQL, plain CSS. Works without JavaScript. |

## Rules for claims

- Claim only what a fresh instance does today. A planned feature is not an
  edge until it ships.
- Say "home base" or "portfolio engine". Never "CMS", never "link in bio".
- Name a rival only with a fact a reader can check, and date facts that
  change: "Ghost 6", "13 February 2026".
- The export is a copy of the published site, not a backup: drafts and users
  stay in the database. Don't promise more.
- Show the pieces linking to each other; a screenshot of a flat grid sells
  the thing lapidarium replaces.
