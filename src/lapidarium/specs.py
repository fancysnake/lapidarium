"""Business invariants: pure constants, read by mills only."""

import datetime as dt
from typing import TYPE_CHECKING

from lapidarium.pacts.content import TypeRole
from lapidarium.pacts.purposes import PurposeDTO, StarterFieldDTO

if TYPE_CHECKING:
    from collections.abc import Mapping

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


def _(text: str) -> str:
    """Mark `text` for the translation catalogue; templates translate it."""
    return text


# What the owner calls each type role.
MECHANIC_NAMES: Mapping[TypeRole, str] = {
    TypeRole.THING: _("Pieces of work"),
    TypeRole.CALENDAR: _("Events"),
    TypeRole.CONTAINER_OUTCOME: _("Projects"),
    TypeRole.CONTAINER_TIMESPAN: _("Activities"),
    TypeRole.CONTAINER_SECTION: _("Sections"),
}

PURPOSES: tuple[PurposeDTO, ...] = (
    PurposeDTO(
        key="work",
        name=_("Piece of work"),
        description=_("Something you made: a song, an article, a game."),
        role=TypeRole.THING,
        label="Work",
        label_plural="Works",
        route="works",
    ),
    PurposeDTO(
        key="event",
        name=_("Event"),
        description=_("Something that happens on a date: a concert, a convention."),
        role=TypeRole.CALENDAR,
        label="Event",
        label_plural="Events",
        route="events",
    ),
    PurposeDTO(
        key="project",
        name=_("Project"),
        description=_(
            "Work towards a result, holding its pieces: an album, a campaign."
        ),
        role=TypeRole.CONTAINER_OUTCOME,
        label="Project",
        label_plural="Projects",
        route="projects",
    ),
    PurposeDTO(
        key="job",
        name=_("Job"),
        description=_("Paid work for an employer, from a start date."),
        role=TypeRole.CONTAINER_TIMESPAN,
        label="Job",
        label_plural="Jobs",
        route="jobs",
        fields=(
            StarterFieldDTO(key="employer", label="Employer"),
            StarterFieldDTO(key="position", label="Position"),
        ),
    ),
    PurposeDTO(
        key="volunteering",
        name=_("Volunteering"),
        description=_("Unpaid work for an organisation or a community."),
        role=TypeRole.CONTAINER_TIMESPAN,
        label="Volunteering",
        label_plural="Volunteering",
        route="volunteering",
        fields=(
            StarterFieldDTO(key="organisation", label="Organisation"),
            StarterFieldDTO(key="position", label="Position"),
        ),
    ),
    PurposeDTO(
        key="craft",
        name=_("Craft"),
        description=_("Something you keep making: songwriting, game design."),
        role=TypeRole.CONTAINER_TIMESPAN,
        label="Craft",
        label_plural="Crafts",
        route="crafts",
    ),
    PurposeDTO(
        key="skill",
        name=_("Skill"),
        description=_("Something you keep practising: a language, an instrument."),
        role=TypeRole.CONTAINER_TIMESPAN,
        label="Skill",
        label_plural="Skills",
        route="skills",
    ),
    PurposeDTO(
        key="section",
        name=_("Section"),
        description=_("A part of the site that groups pages: a wiki, a set of docs."),
        role=TypeRole.CONTAINER_SECTION,
        label="Section",
        label_plural="Sections",
        route="sections",
    ),
)
