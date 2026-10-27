# Content

A new instance has no content types, so its public site is an empty frame.
This page sets one up from nothing in the admin, in the order each step
depends on the last; [How it works](concepts.md) explains the model behind
them. To start from files instead, write a bundle in the
[export format](export-format.md) and run [`import_content`](cli.md#import_content).

1. [Profile](#profile): who the site is about.
2. [Links](#links): where else to find them.
3. [Friends](#friends): sites they like.
4. [Content types](#content-types): what kinds of work the site shows.
5. [Fields](#fields): what each kind records beyond a title.
6. [Entries](#entries): the work itself.

[What appears where](#what-appears-where) says which of these settings drive
the menu, the home page and the feeds.

## Profile

**Admin → Profile.** One per site; the admin refuses a second.

| Field | Shown as |
|---|---|
| Name | logo text, feed titles, footer copyright; until set, `SITE_NAME` |
| Handle | next to the logo |
| Tagline | the home page lead, the meta description, the RSS description |
| Photo | the logo image (else the name's first letter), the home and about pictures, the link preview image |
| Bio | the about page, in Markdown |
| E-mail | turns on the contact form; messages go here |
| Button, friends title, friends intro | the [friends](#friends) section |

Without an e-mail, `/contact/` is a 404 and every link to it disappears. The
form sends through `EMAIL_URL` (see [Configuration](configuration.md#mail-and-newsletter)).

## Links

**Admin → Links.** Platform, URL, label and order of each profile elsewhere:
YouTube, itch.io, GitHub, Mastodon. They are listed in the footer and on the
about page.

## Friends

**Admin → Friends.** Sites the owner likes, in the spirit of an old-web
webring: name, URL, an optional 88×31 button and order. A friend without a
button shows as a text button of the same size. They are listed at the end of
the about page, with `rel="external noopener"`.

Three profile fields shape the section: *friends title* (else "Friends"),
*friends intro* in Markdown, and *button*, the site's own 88×31 image. Under
the list, *Link back here* shows that button, or a text one, and the HTML a
friend can paste to link back. The admin refuses a button image of any other
size.

## Content types

**Admin → Content types.** A type is a kind of work: a session, a song, a talk,
a repository. Each gets its own list page, its own colour, and a section in
the admin sidebar. Types are data, so adding one needs no code and no
migration.

### Names and address

| Field | Rule |
|---|---|
| Label, plural label | singular and plural names, in the site's language |
| Key | slug, unique; prefilled from the label; the type's name in exports |
| Route | slug, unique; prefilled from the plural; the list is at `/<route>/` |
| Order | position in the menu, then by label |

Keep routes clear of the fixed pages: `about`, `new`, `search`, `newsletter`
and `contact` are matched first, so a type routed there is never reached.

### Role

The role says what the type's entries are in time, and which built-in date
fields they carry.

| Role | Built-in fields | Required | Use it for |
|---|---|---|---|
| `thing` | date | — | a finished piece: a song, a post, a repo |
| `calendar` | start, end, location, online | start | something that happens: events, sessions to come |
| `container_timespan` | start, end | start | a period other entries belong to: a season, a residency |
| `container_outcome` | outcome, start, end | outcome | a project that ends somewhere: ongoing, finished, abandoned |

Calendar entries feed the upcoming block on their list, the "next up" box on
the home page and `/calendar.ics`. Only container entries can be the target of
a *part of* relation, and they make up the timeline on the about page.

### Page

| Field | Choices |
|---|---|
| Layout | `article` (text first), `media_first` (video or audio above the text), `gallery` (images in a grid) |
| Has detail page | off for types too small for a page of their own: list items then link to `/<route>/#<slug>` |

### Look

| Field | Rule |
|---|---|
| Colour | `#rrggbb`; must reach 4.5:1 against the theme's background and against the tint |
| Tint | `#rrggbb`, or blank to mix 12% of the colour into the background |
| Icon | a [Material Symbols](https://fonts.google.com/icons) name, used in the admin sidebar only |
| In menu | whether the type appears in the site menu |

The admin refuses a colour that does not read, and shows the colour the dark
scheme will use, lightened where the dark background needs it.

### Parts

**Allowed parts** are the building blocks an entry of this type may use;
**required parts** must each appear at least once. A talk might allow text,
video, file and link and require video. Required parts must be allowed.

**List filters** are the filters on the type's list page: `year`, `tag`, or the
key of any of its fields except long text and URL fields.

### Home page door

A door is the type's tile on the home page, showing one entry.

| Field | Rule |
|---|---|
| Door enabled | off by default |
| Door label | the tile's heading; blank uses the plural label |
| Door pick | `latest_featured`, `latest`, `upcoming`, `random_featured` |
| Door minimum entries | the door stays hidden until the type has this many published entries |

The featured picks fall back to any entry when none is featured; `upcoming`
falls back to the newest.

## Fields

Fields are rows inline on the type. They record what an entry of that type
has beyond the common fields: a session's system, a talk's event.

| Kind | Holds |
|---|---|
| `text` | one line |
| `long_text` | several lines |
| `url` | a full http(s) address; *URL kind* restricts it to `youtube`, `itch` or `github` |
| `date` | a date |
| `number` | a number |
| `bool` | yes or no; *required* has no effect, since no is an answer |
| `choice` | one of *choices*, a comma-separated list |
| `relation` | links to entries of *target type* |

| Flag | Effect |
|---|---|
| Key | slug, unique on the type; the name in exports and list filters |
| Required | the entry cannot be saved without it |
| Show on card | the value appears on the entry's card in lists |
| Show in metadata panel | the value appears in the detail page's side panel; on by default |
| Order | position in the form and the panel |

A choice field needs its choices and a relation field its target type. A
relation field records no value of its own: each link becomes a relation with
the field's key as its role, and *required* means at least one link.

## Entries

**Admin → the type's section.** The form is built from the type: its role's
built-in fields, its own fields, and the parts it allows.

| Field | Rule |
|---|---|
| Title | the page heading |
| Slug | unique within the type; the page is at `/<route>/<slug>/` |
| Summary | one sentence, at most 200 characters, for cards and link previews |
| Status | `draft` or `published`; only published entries are public or exported |
| Featured | preferred by the featured door picks |
| Hide from what's new | keeps the entry off the home feed and RSS |
| Cover | an image for cards and the page header |
| Tags | free tags, shared across types |
| External URL | the canonical page elsewhere, if there is one |
| License | shown on the page |

### Parts

An entry is a sequence of parts, in order:

| Part | Needs | Notes |
|---|---|---|
| Text | text | Markdown |
| Video | URL | YouTube, Vimeo and PeerTube are embedded and load only when played |
| Audio | URL or asset | |
| Image | asset with alt text | the admin refuses an image without alt text |
| File | asset | a download; `download_label` in options replaces the link text |
| Link | URL | a card linking out |

Every URL must be http(s). Upload images and files under **Admin → Media
assets** first, with alt text that says what the image shows; for an image of
text, transcribe the text.

### Relations

Relations link one entry to another:

- *part of* puts an entry in a container: a session in a campaign. It must
  point at a container type and must not form a loop.
- *related* links two entries; each shows the other.
- Each relation field on the type adds a role of its own.

A published entry cannot link to a draft, and an entry cannot go back to draft
while published entries link to it. Publish the containers first.

**Syndication links** record where else the entry is posted: platform and URL.

## What appears where

| Place | Shows |
|---|---|
| Menu | every type with *in menu*, by order, then About and Search |
| Home | the profile's tagline and photo, a door per type, the next calendar entry, the five newest lines of what's new |
| What's new (`/new/`) | published entries, newest change first, marked added or updated |
| Type list (`/<route>/`) | its published entries, twelve a page, with its filters; calendar types split upcoming from archive |
| About (`/about/`) | bio, links, the timeline of container entries, and friends |
| Footer | links, the newsletter form, RSS and iCal, the contact link |
| `/rss.xml` | what's new |
| `/calendar.ics` | upcoming calendar entries |
| `/search/` | published entries whose title, summary, field values, tags, text or captions contain the query |

Every content change clears the cached pages, so an edit shows on the next
request.

## A first type, end to end

A musician's site with songs:

1. Profile: name, tagline, photo, e-mail.
2. Type *Song* / *Songs*, key `song`, route `songs`, role `thing`, layout
   `media_first`, a colour that passes, door enabled.
3. Allowed parts: text, audio, video. Required: audio.
4. Fields: `album` (`text`, show on card), `released` (`date`), list filters
   `year` and `tag`.
5. An entry: title, summary, an audio part, a text part with the lyrics,
   status published.

The home page now has a *Songs* door, the menu a *Songs* item, and
`/songs/` a list. To see a complete set, load a demo
(`load_demo dev` or `load_demo ttrpg`) on a local instance and read its types
in the admin.
