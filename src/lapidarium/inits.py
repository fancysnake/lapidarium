"""Composition root: builds the object graph and hands it to the request."""

from __future__ import annotations

from functools import cached_property
from importlib.metadata import version
from random import SystemRandom
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from lapidarium.links.content_files.markdown import ContentFilesStore
from lapidarium.links.db.django.repositories import (
    AccountRepository,
    EntryRepository,
    EntryTypeRepository,
    ExternalItemRepository,
    MediaAssetRepository,
    ProfileRepository,
)
from lapidarium.links.db.django.transaction import DjangoTransaction
from lapidarium.links.mail.django import DjangoMailer
from lapidarium.links.newsletter.log import LogNewsletter
from lapidarium.links.newsletter.mailchimp import MailchimpNewsletter
from lapidarium.links.themes.files import ThemeFiles
from lapidarium.links.throttle.django import CacheThrottle
from lapidarium.mills.catalogue import CatalogueService
from lapidarium.mills.content import (
    ContentExportService,
    ContentImportService,
    LocalSetupService,
)
from lapidarium.mills.outreach import OutreachService
from lapidarium.mills.schema import SchemaService
from lapidarium.mills.site import SiteService
from lapidarium.mills.theme import ThemeService
from lapidarium.pacts import NewsletterBackend, ServicesProtocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from lapidarium.pacts import NewsletterProtocol, RootRequestProtocol


class Process:
    """What lives as long as the process: built once, on first use."""

    @cached_property
    def themes(self) -> ThemeFiles:
        return ThemeFiles(
            base=settings.BASE_THEME_DIR,
            active=settings.THEME_DIR,
            engine_templates=settings.ENGINE_TEMPLATES,
        )


PROCESS = Process()


def newsletter_backend() -> NewsletterBackend:
    """Return `NEWSLETTER_BACKEND`; `ImproperlyConfigured` if it cannot work."""
    try:
        backend = NewsletterBackend(settings.NEWSLETTER_BACKEND)
    except ValueError as exc:
        msg = f"NEWSLETTER_BACKEND must be one of: {', '.join(NewsletterBackend)}."
        raise ImproperlyConfigured(msg) from exc
    if backend == NewsletterBackend.MAILCHIMP and not (
        settings.MAILCHIMP_API_KEY and settings.MAILCHIMP_LIST_ID
    ):
        msg = "The Mailchimp newsletter needs MAILCHIMP_API_KEY and MAILCHIMP_LIST_ID."
        raise ImproperlyConfigured(msg)
    return backend


def build_newsletter() -> NewsletterProtocol:
    """Return the provider `NEWSLETTER_BACKEND` names."""
    match newsletter_backend():
        case NewsletterBackend.MAILCHIMP:
            return MailchimpNewsletter(
                api_key=settings.MAILCHIMP_API_KEY, list_id=settings.MAILCHIMP_LIST_ID
            )
        case NewsletterBackend.LOG:
            return LogNewsletter()


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

    @cached_property
    def external_items(self) -> ExternalItemRepository:
        return ExternalItemRepository()


class Services(ServicesProtocol):
    """Flat service namespace, one `cached_property` per service, built per request."""

    def __init__(self, *, newsletter: NewsletterProtocol | None = None) -> None:
        self._repositories = Repositories()
        # Shared by the caller across requests; built here only when none is given.
        self._newsletter = newsletter

    @cached_property
    def schema(self) -> SchemaService:
        return SchemaService(background=self.theme.background())

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

    @cached_property
    def site(self) -> SiteService:
        repos = self._repositories
        return SiteService(
            schema=self.schema,
            types=repos.entry_types,
            profile=repos.profile,
            theme=self.theme,
        )

    @cached_property
    def catalogue(self) -> CatalogueService:
        repos = self._repositories
        return CatalogueService(
            types=repos.entry_types,
            entries=repos.entries,
            external=repos.external_items,
            clock=timezone.now,
            rng=SystemRandom(),
        )

    @cached_property
    def theme(self) -> ThemeService:
        return ThemeService(store=PROCESS.themes, engine_version=version("lapidarium"))

    @cached_property
    def outreach(self) -> OutreachService:
        return OutreachService(
            newsletter=self._newsletter or build_newsletter(),
            mailer=DjangoMailer(),
            throttle=CacheThrottle(),
            profile=self._repositories.profile,
        )


class ServiceInjectionMiddleware[Response]:
    """Attach `request.services` so views reach mills through protocols only."""

    def __init__(self, get_response: Callable[[RootRequestProtocol], Response]) -> None:
        # Middleware loads once, with the app: a newsletter that cannot work stops
        # the start, and one that can keeps its HTTP client across requests.
        self._newsletter = build_newsletter()
        self.get_response = get_response

    def __call__(self, request: RootRequestProtocol) -> Response:
        request.services = Services(newsletter=self._newsletter)
        return self.get_response(request)
