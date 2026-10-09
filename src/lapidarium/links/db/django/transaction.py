from __future__ import annotations

from typing import TYPE_CHECKING, override

from django.db import transaction

from lapidarium.pacts import TransactionProtocol

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager


class DjangoTransaction(TransactionProtocol):
    @override
    def atomic(self) -> AbstractContextManager[None]:
        return transaction.atomic()

    @override
    def on_commit(self, callback: Callable[[], None]) -> None:
        transaction.on_commit(callback)
