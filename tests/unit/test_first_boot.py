from unittest.mock import MagicMock

from lapidarium.mills.content import FirstBootService
from lapidarium.pacts.content import ContentSummaryDTO, FirstBootDTO

SUMMARY = ContentSummaryDTO(types=1, entries=2, assets=3)


def _service(*, accounts_exist=False, types=()):
    content_import = MagicMock()
    content_import.seed_demo.return_value = SUMMARY
    accounts = MagicMock()
    accounts.any_exist.return_value = accounts_exist
    entry_types = MagicMock()
    entry_types.list_all.return_value = list(types)
    transaction = MagicMock()
    service = FirstBootService(
        content_import=content_import,
        transaction=transaction,
        accounts=accounts,
        types=entry_types,
    )
    return service, content_import, accounts, transaction


def test_fresh_database_gets_the_demo_and_the_admin_in_one_transaction():
    service, content_import, accounts, transaction = _service()

    result = service.run("dev", username="owner", password="secret")

    assert result == FirstBootDTO(content=SUMMARY, superuser_created=True)
    content_import.seed_demo.assert_called_once_with("dev")
    accounts.ensure_superuser.assert_called_once_with("owner", password="secret")
    transaction.atomic.assert_called_once_with()


def test_an_existing_account_keeps_its_password_and_blocks_the_demo():
    service, content_import, accounts, _ = _service(accounts_exist=True)

    result = service.run("dev", username="owner", password="secret")

    assert result == FirstBootDTO(content=None, superuser_created=False)
    content_import.seed_demo.assert_not_called()
    accounts.ensure_superuser.assert_not_called()


def test_existing_types_block_the_demo_but_not_the_admin():
    service, content_import, accounts, _ = _service(types=[MagicMock()])

    result = service.run("dev", username="owner", password="secret")

    assert result == FirstBootDTO(content=None, superuser_created=True)
    content_import.seed_demo.assert_not_called()
    accounts.ensure_superuser.assert_called_once_with("owner", password="secret")


def test_no_password_means_no_admin():
    service, _, accounts, _ = _service()

    result = service.run("dev", username="owner", password="")

    assert result == FirstBootDTO(content=SUMMARY, superuser_created=False)
    accounts.ensure_superuser.assert_not_called()


def test_no_demo_named_loads_nothing():
    service, content_import, _, _ = _service()

    result = service.run("", username="owner", password="secret")

    assert result == FirstBootDTO(content=None, superuser_created=True)
    content_import.seed_demo.assert_not_called()
