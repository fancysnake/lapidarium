# Content types

A content type is data, not code: you add one in the admin under
**Site → Content types**, and its list page, detail pages, door on the home page
and menu item exist from the next request. No restart, no migration.

## What a type sets

| Setting | Means |
|---|---|
| key | Identity in exports and colours (`session`); letters, digits, `-`, `_` |
| label, plural label | How the site names one and many |
| route | URL segment of the list (`/sesje/`), in the site's language |
| colour, tint | The type's colour and its light background; tint is derived when blank. Both must have 4.5:1 contrast against the theme's background |
| icon, order, in menu | The admin sidebar icon, position, and whether the public menu lists it |
| role | What the engine may assume; see below |
| layout | `article`, `media_first` or `gallery`; picks the detail template |
| allowed parts, required parts | Which [part kinds](parts.md) an entry may and must have |
| door | Whether the home page shows a door, its label, how it picks an entry, and the fewest entries it needs to appear |
| list filters | `year`, `tag`, or field keys; each becomes a filter on the list page |
| has detail pages | Off for list-only types such as memes: entries live as anchors on the list |

## Roles

The engine never infers meaning from field names. A type's role says which
built-in columns its entries use and how the site treats them.

| Role | Built-ins | Treated as |
|---|---|---|
| `thing` | date | A thing made: a session, a song, a talk |
| `calendar` | starts (required), ends, location, online | Upcoming and archive on its list; the home page's next entry; the iCal feed |
| `container_timespan` | starts (required), ends | Holds other entries; a span on the about page's timeline |
| `container_outcome` | outcome (required), starts, ends | Holds other entries; ongoing, finished or abandoned |

Entries link to a container with the built-in relation `part_of`; a container
page lists what it holds, and each entry in it lists its siblings. `related`
links two entries either way.

## Fields

A type's fields are its schema. Values live in the entry's metadata and are
validated on save.

| Kind | Holds |
|---|---|
| `text`, `long_text` | Text |
| `url` | An address; optionally only YouTube, itch.io or GitHub |
| `date`, `number`, `bool` | What the name says |
| `choice` | One of the listed choices |
| `relation` | Links to entries of one target type, stored as relations whose role is the field's key |

A field can show on cards and in the detail page's panel.

## Doors

A door shows one entry of its type on the home page. Its pick is
`latest_featured`, `latest`, `upcoming` (calendar types) or `random_featured`.
A door with fewer published entries than its minimum stays hidden, and
`check_content` reports it.
