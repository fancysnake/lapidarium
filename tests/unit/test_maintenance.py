import datetime as dt
from operator import itemgetter
from unittest.mock import MagicMock

import pytest

from lapidarium.mills.maintenance import MaintenanceService
from lapidarium.pacts.maintenance import MaintenanceDTO, MaintenanceNoticeDTO
from tests.factories import NOW

HOUR = dt.timedelta(hours=1)
MAINTENANCE = MaintenanceDTO(
    starts_at=NOW - HOUR,
    ends_at=NOW + HOUR,
    reasons=("feeding the mimics", "identifying player tribes"),
)


def _service(maintenance):
    repo = MagicMock()
    repo.get.return_value = maintenance
    rng = MagicMock()
    rng.choice.side_effect = itemgetter(-1)
    return MaintenanceService(maintenance=repo, clock=lambda: NOW, rng=rng)


def test_notice_shows_a_random_reason_and_the_wait_until_its_end():
    notice = _service(MAINTENANCE).notice()

    assert notice == MaintenanceNoticeDTO(
        starts_at=NOW - HOUR,
        ends_at=NOW + HOUR,
        reason="identifying player tribes",
        seconds_left=3600,
    )


def test_notice_without_end_or_reasons_gives_no_wait_and_no_reason():
    state = MAINTENANCE.model_copy(update={"ends_at": None, "reasons": ()})

    notice = _service(state).notice()

    assert notice is not None
    assert (notice.ends_at, notice.reason, notice.seconds_left) == (None, "", None)


def test_notice_rounds_the_wait_up_to_a_whole_second():
    state = MAINTENANCE.model_copy(update={"ends_at": NOW + dt.timedelta(seconds=0.2)})

    notice = _service(state).notice()

    assert notice is not None
    assert notice.seconds_left == 1


@pytest.mark.parametrize(
    "state",
    (
        None,
        MAINTENANCE.model_copy(update={"starts_at": NOW + HOUR}),
        MAINTENANCE.model_copy(update={"ends_at": NOW}),
    ),
    ids=("never-set", "not-started", "ended"),
)
def test_no_notice_outside_the_window(state):
    assert _service(state).notice() is None
