"""Rendered public pages go stale with any content change, so they go with it."""

from __future__ import annotations

from django.apps import apps
from django.core.cache import caches
from django.db import transaction
from django.db.models import Model, QuerySet
from django.db.models.signals import m2m_changed, post_delete, post_save

from lapidarium.pacts import PAGE_CACHE

# Whatever post_save, post_delete and m2m_changed send along.
type _Sent = type[Model] | Model | QuerySet[Model] | bool | str | frozenset[str] | set[
    int
] | None


def clear_pages(**_kwargs: _Sent) -> None:
    # After commit: a page rendered before it would otherwise be cached stale.
    transaction.on_commit(caches[PAGE_CACHE].clear)


def connect(label: str) -> None:
    for model in apps.get_app_config(label).get_models():
        post_save.connect(clear_pages, sender=model, dispatch_uid=f"pages:{model}")
        post_delete.connect(clear_pages, sender=model, dispatch_uid=f"pages:{model}")
    m2m_changed.connect(
        clear_pages,
        sender=apps.get_model(label, "Entry").tags.through,
        dispatch_uid="pages:tags",
    )
