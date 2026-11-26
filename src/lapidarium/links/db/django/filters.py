"""Admin list filters."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from lapidarium.links.db.django.models import EntryType

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

    from lapidarium.links.db.django.models import Entry


class EntryTypeKeyFilter(admin.SimpleListFilter):
    """Entries of one type, named in the address by its key: `?type=song`."""

    title = _("type")
    parameter_name = "type"

    @override
    def lookups(
        self, request: HttpRequest, _model_admin: admin.ModelAdmin[Entry]
    ) -> list[tuple[str, str]]:
        return [(t.key, t.label) for t in EntryType.objects.all()]

    @override
    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Entry]
    ) -> QuerySet[Entry] | None:
        if key := self.value():
            return queryset.filter(type__key=key)
        return None
