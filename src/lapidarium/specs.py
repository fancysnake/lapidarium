"""Business invariants: pure constants, read by mills only."""

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
