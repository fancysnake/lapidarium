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


def gettext_noop(text: str) -> str:
    """Mark `text` for the translation catalogue without translating it.

    makemessages extracts the call; every consumer must translate the value,
    as templates do with `{% translate value %}`.
    """
    return text


# What the owner calls each type role.
MECHANIC_NAMES: Mapping[TypeRole, str] = {
    TypeRole.THING: gettext_noop("Pieces of work"),
    TypeRole.CALENDAR: gettext_noop("Events"),
    TypeRole.CONTAINER_OUTCOME: gettext_noop("Projects"),
    TypeRole.CONTAINER_TIMESPAN: gettext_noop("Activities"),
    TypeRole.CONTAINER_SECTION: gettext_noop("Sections"),
}

PURPOSES: tuple[PurposeDTO, ...] = (
    PurposeDTO(
        key="work",
        name=gettext_noop("Piece of work"),
        description=gettext_noop("Something you made: a song, an article, a game."),
        role=TypeRole.THING,
        label="Work",
        label_plural="Works",
        route="works",
    ),
    PurposeDTO(
        key="event",
        name=gettext_noop("Event"),
        description=gettext_noop(
            "Something that happens on a date: a concert, a convention."
        ),
        role=TypeRole.CALENDAR,
        label="Event",
        label_plural="Events",
        route="events",
    ),
    PurposeDTO(
        key="project",
        name=gettext_noop("Project"),
        description=gettext_noop(
            "Work towards a result, holding its pieces: an album, a campaign."
        ),
        role=TypeRole.CONTAINER_OUTCOME,
        label="Project",
        label_plural="Projects",
        route="projects",
    ),
    PurposeDTO(
        key="job",
        name=gettext_noop("Job"),
        description=gettext_noop("Paid work for an employer, from a start date."),
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
        name=gettext_noop("Volunteering"),
        description=gettext_noop("Unpaid work for an organisation or a community."),
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
        name=gettext_noop("Craft"),
        description=gettext_noop(
            "Something you keep making: songwriting, game design."
        ),
        role=TypeRole.CONTAINER_TIMESPAN,
        label="Craft",
        label_plural="Crafts",
        route="crafts",
    ),
    PurposeDTO(
        key="skill",
        name=gettext_noop("Skill"),
        description=gettext_noop(
            "Something you keep practising: a language, an instrument."
        ),
        role=TypeRole.CONTAINER_TIMESPAN,
        label="Skill",
        label_plural="Skills",
        route="skills",
    ),
    PurposeDTO(
        key="section",
        name=gettext_noop("Section"),
        description=gettext_noop(
            "A part of the site that groups pages: a wiki, a set of docs."
        ),
        role=TypeRole.CONTAINER_SECTION,
        label="Section",
        label_plural="Sections",
        route="sections",
    ),
)
