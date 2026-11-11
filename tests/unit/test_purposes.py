from unittest.mock import MagicMock

import pytest

from lapidarium.mills.purposes import PurposeService
from lapidarium.pacts.content import TypeRole
from lapidarium.specs import MECHANIC_NAMES, PURPOSES
from tests.factories import type_dto


def test_every_role_has_a_name_and_a_purpose():
    assert (
        set(MECHANIC_NAMES) == {purpose.role for purpose in PURPOSES} == set(TypeRole)
    )


@pytest.mark.parametrize(
    "key", ("job", "volunteering", "craft", "skill", "project", "work", "section")
)
def test_catalogue_lists_the_purposes_the_panel_needs(key):
    assert key in {purpose.key for purpose in PURPOSES}


def test_overview_groups_types_by_role_with_counts_and_containment():
    song = type_dto("song")
    meme = type_dto("meme")
    album = type_dto("album", role=TypeRole.CONTAINER_OUTCOME)
    types = MagicMock()
    types.list_all.return_value = [song, meme, album]
    types.entry_counts.return_value = {"song": 3, "album": 1}
    types.containment.return_value = {("song", "album")}

    overview = PurposeService(types=types).overview()

    assert [(m.role, m.name) for m in overview] == list(MECHANIC_NAMES.items())
    by_role = {m.role: m for m in overview}
    assert [
        (use.entry_type, use.entries, use.containers, use.contents)
        for use in by_role[TypeRole.THING].types
    ] == [(song, 3, (album,), ()), (meme, 0, (), ())]
    assert [
        (use.entry_type, use.entries, use.containers, use.contents)
        for use in by_role[TypeRole.CONTAINER_OUTCOME].types
    ] == [(album, 1, (), (song,))]
    assert by_role[TypeRole.CALENDAR].types == ()
    assert [p.key for p in by_role[TypeRole.CONTAINER_TIMESPAN].purposes] == [
        "job",
        "volunteering",
        "craft",
        "skill",
    ]
