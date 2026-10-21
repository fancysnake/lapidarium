from __future__ import annotations

from typing import TYPE_CHECKING

from django.urls import reverse

if TYPE_CHECKING:
    from collections.abc import Iterable

    from lapidarium.pacts.schema import EntryTypeDTO


def entry_path(types: Iterable[EntryTypeDTO], *, type_key: str, slug: str) -> str:
    """Path of an entry's page, or of its place on the list for list-only types."""
    entry_type = next(t for t in types if t.key == type_key)
    if entry_type.has_detail_page:
        return reverse("detail", kwargs={"route": entry_type.route, "slug": slug})
    return reverse("listing", kwargs={"route": entry_type.route}) + f"#{slug}"
