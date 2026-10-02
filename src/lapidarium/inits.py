"""Composition root: builds the object graph and hands it to the request."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from lapidarium.links.content_files.markdown import ContentFilesStore
from lapidarium.links.db.django.repositories import (
    AccountRepository,
    EntryRepository,
    EntryTypeRepository,
    MediaAssetRepository,
    ProfileRepository,
)
from lapidarium.links.db.django.transaction import DjangoTransaction
from lapidarium.mills import (
    ContentExportService,
    ContentImportService,
    LocalSetupService,
    SchemaService,
)
from lapidarium.pacts import ServicesProtocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from lapidarium.pacts import RootRequestProtocol

# Page background of the base theme, until themes supply their own.
THEME_BACKGROUND = "#ffffff"


class Repositories:
    """Flat repository registry; mills receive single protocols from it."""

    @cached_property
    def entry_types(self) -> EntryTypeRepository:
        return EntryTypeRepository()

    @cached_property
    def entries(self) -> EntryRepository:
        return EntryRepository()

    @cached_property
    def media_assets(self) -> MediaAssetRepository:
        return MediaAssetRepository()

    @cached_property
    def profile(self) -> ProfileRepository:
        return ProfileRepository()

    @cached_property
    def content_files(self) -> ContentFilesStore:
        return ContentFilesStore()

    @cached_property
    def accounts(self) -> AccountRepository:
        return AccountRepository()


class Services(ServicesProtocol):
    """Flat service namespace, one `cached_property` per service, built per request."""

    def __init__(self) -> None:
        self._repositories = Repositories()

    @cached_property
    def schema(self) -> SchemaService:
        return SchemaService(background=THEME_BACKGROUND)

    @cached_property
    def content_export(self) -> ContentExportService:
        repos = self._repositories
        return ContentExportService(
            types=repos.entry_types,
            entries=repos.entries,
            assets=repos.media_assets,
            profile=repos.profile,
            store=repos.content_files,
        )

    @cached_property
    def content_import(self) -> ContentImportService:
        repos = self._repositories
        return ContentImportService(
            schema=self.schema,
            transaction=DjangoTransaction(),
            types=repos.entry_types,
            entries=repos.entries,
            assets=repos.media_assets,
            profile=repos.profile,
            store=repos.content_files,
        )

    @cached_property
    def local_setup(self) -> LocalSetupService:
        return LocalSetupService(
            content_import=self.content_import,
            transaction=DjangoTransaction(),
            accounts=self._repositories.accounts,
        )


class ServiceInjectionMiddleware[Response]:
    """Attach `request.services` so views reach mills through protocols only."""

    def __init__(self, get_response: Callable[[RootRequestProtocol], Response]) -> None:
        self.get_response = get_response

    def __call__(self, request: RootRequestProtocol) -> Response:
        request.services = Services()
        return self.get_response(request)
