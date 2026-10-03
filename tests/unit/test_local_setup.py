from unittest.mock import MagicMock

from lapidarium.mills import LocalSetupService
from lapidarium.pacts import ContentSummaryDTO, LocalSetupDTO


def test_set_up_loads_the_demo_and_ensures_the_superuser_in_one_transaction():
    summary = ContentSummaryDTO(types=1, entries=2, assets=3)
    content_import = MagicMock()
    content_import.load_demo.return_value = summary
    accounts = MagicMock()
    accounts.ensure_superuser.return_value = True
    transaction = MagicMock()
    service = LocalSetupService(
        content_import=content_import, transaction=transaction, accounts=accounts
    )

    result = service.set_up("dev", username="admin", password="secret")

    assert result == LocalSetupDTO(content=summary, superuser_created=True)
    content_import.load_demo.assert_called_once_with("dev")
    accounts.ensure_superuser.assert_called_once_with("admin", password="secret")
    transaction.atomic.assert_called_once_with()
