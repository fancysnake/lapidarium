"""Contracts crossing layer boundaries: DTOs, protocols, enums, errors."""

from typing import Protocol


class ServicesProtocol(Protocol):
    """The flat service namespace a gate reaches as `request.services`."""


class RootRequestProtocol(Protocol):
    """The slice of the framework request the middleware touches."""

    services: ServicesProtocol
