"""Database port machinery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager


class TransactionProtocol(Protocol):
    def atomic(self) -> AbstractContextManager[None]: ...

    def on_commit(self, callback: Callable[[], None]) -> None:
        """Run `callback` once the outermost transaction commits; never on rollback."""
