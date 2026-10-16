"""Business invariants: pure constants, read by mills only."""

import datetime as dt

# WCAG AA for body text: type colours against the page and against their tint.
CONTRAST_FLOOR = 4.5
# Share of the type colour in a derived tint; the rest is the page background.
TINT_MIX = 0.12

YOUTUBE_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
)
ITCH_HOST = "itch.io"
GITHUB_HOSTS = frozenset({"github.com", "www.github.com"})

# Type keys and entry slugs name export files and URL segments; Django's slug alphabet.
SLUG_PATTERN = r"[-a-zA-Z0-9_]+"

# Public lists: entries per page, other entries of the same container on a page.
PAGE_SIZE = 12
SIBLINGS_LIMIT = 5

# "What's new": lines on the home page and on its own page. An entry edited
# longer than UPDATE_GAP after it was added shows as updated.
WHATS_NEW_HOME = 5
WHATS_NEW_PAGE = 50
UPDATE_GAP = dt.timedelta(days=1)

# Queries shorter than this find too much to be useful.
SEARCH_MIN_LENGTH = 2
SEARCH_LIMIT = 50

# Contact and newsletter attempts one sender may make per window.
OUTREACH_LIMIT = 5
OUTREACH_WINDOW = dt.timedelta(hours=1)
