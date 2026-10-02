"""ORM models, internal to the adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from lapidarium.pacts import (
    SUMMARY_MAX_LENGTH,
    DoorPick,
    EntryStatus,
    FieldKind,
    Layout,
    Outcome,
    PartKind,
    TypeRole,
    UrlKind,
)

if TYPE_CHECKING:
    from enum import StrEnum


def _choices(enum: type[StrEnum]) -> list[tuple[str, str]]:
    return [(m.value, m.value.replace("_", " ").capitalize()) for m in enum]


HEX_COLOUR = RegexValidator(r"^#[0-9a-fA-F]{6}$", _("Use #rrggbb."))
_SHORT = 100
_LONG = 255


class MediaAsset(models.Model):
    file = models.FileField(_("file"), upload_to="assets/%Y/%m/", unique=True)
    alt = models.CharField(
        _("alt text"),
        max_length=_LONG * 2,
        blank=True,
        help_text=_("Required for images; for memes, transcribe the text."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar = ["-created_at"]
        verbose_name = _("media asset")
        verbose_name_plural = _("media assets")

    def __str__(self) -> str:
        return self.file.name or ""


class EntryType(models.Model):
    key = models.SlugField(_("key"), max_length=_SHORT, unique=True)
    label = models.CharField(_("label"), max_length=_SHORT)
    label_plural = models.CharField(_("plural label"), max_length=_SHORT)
    route = models.SlugField(
        _("route"),
        max_length=_SHORT,
        unique=True,
        help_text=_("URL segment of the list, in the site language."),
    )
    colour = models.CharField(
        _("colour"), max_length=7, validators=[HEX_COLOUR], default="#000000"
    )
    tint = models.CharField(
        _("tint"),
        max_length=7,
        validators=[HEX_COLOUR],
        blank=True,
        help_text=_("Light background; derived from the colour when blank."),
    )
    icon = models.CharField(_("icon"), max_length=_SHORT, blank=True)
    order = models.PositiveIntegerField(_("order"), default=0)
    in_menu = models.BooleanField(_("in menu"), default=True)
    role = models.CharField(
        _("role"),
        max_length=32,
        choices=_choices(TypeRole),
        default=TypeRole.THING.value,
    )
    layout = models.CharField(
        _("layout"),
        max_length=32,
        choices=_choices(Layout),
        default=Layout.ARTICLE.value,
    )
    allowed_parts = models.JSONField(_("allowed parts"), default=list, blank=True)
    required_parts = models.JSONField(_("required parts"), default=list, blank=True)
    door_enabled = models.BooleanField(_("door on the home page"), default=False)
    door_label = models.CharField(_("door label"), max_length=_SHORT, blank=True)
    door_pick = models.CharField(
        _("door pick"),
        max_length=32,
        choices=_choices(DoorPick),
        default=DoorPick.LATEST_FEATURED.value,
    )
    door_min_entries = models.PositiveIntegerField(_("door minimum entries"), default=1)
    list_filters = models.JSONField(_("list filters"), default=list, blank=True)
    has_detail_page = models.BooleanField(_("has detail pages"), default=True)

    class Meta:
        ordering: ClassVar = ["order", "label"]
        verbose_name = _("content type")
        verbose_name_plural = _("content types")

    def __str__(self) -> str:
        return str(self.label)


class FieldDefinition(models.Model):
    entry_type = models.ForeignKey(
        EntryType, on_delete=models.CASCADE, related_name="fields"
    )
    key = models.SlugField(_("key"), max_length=_SHORT)
    label = models.CharField(_("label"), max_length=_SHORT)
    kind = models.CharField(
        _("kind"),
        max_length=32,
        choices=_choices(FieldKind),
        default=FieldKind.TEXT.value,
    )
    required = models.BooleanField(_("required"), default=False)
    choices = models.JSONField(
        _("choices"), default=list, blank=True, help_text=_("For choice fields.")
    )
    url_kind = models.CharField(
        _("URL validator"),
        max_length=32,
        choices=_choices(UrlKind),
        default=UrlKind.ANY_HOST.value,
        help_text=_("For URL fields."),
    )
    target_type = models.ForeignKey(
        EntryType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("target type"),
        help_text=_("For relation fields."),
    )
    show_on_card = models.BooleanField(_("show on card"), default=False)
    show_in_metadata_panel = models.BooleanField(
        _("show in metadata panel"), default=True
    )
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering: ClassVar = ["order", "pk"]
        verbose_name = _("field")
        verbose_name_plural = _("fields")
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["entry_type", "key"], name="field_key_unique_per_type"
            )
        ]

    def __str__(self) -> str:
        return str(self.label)


class Tag(models.Model):
    name = models.CharField(_("name"), max_length=_SHORT, unique=True)

    class Meta:
        ordering: ClassVar = ["name"]
        verbose_name = _("tag")
        verbose_name_plural = _("tags")

    def __str__(self) -> str:
        return str(self.name)


class Entry(models.Model):
    type = models.ForeignKey(
        EntryType,
        on_delete=models.PROTECT,
        related_name="entries",
        verbose_name=_("type"),
    )
    slug = models.SlugField(_("slug"), max_length=_LONG)
    title = models.CharField(_("title"), max_length=_LONG)
    summary = models.CharField(
        _("summary"),
        max_length=SUMMARY_MAX_LENGTH,
        help_text=_("One sentence for cards and link previews."),
    )
    date = models.DateField(_("date"), null=True, blank=True)
    start_at = models.DateTimeField(_("starts"), null=True, blank=True)
    end_at = models.DateTimeField(_("ends"), null=True, blank=True)
    location = models.CharField(_("location"), max_length=_LONG, blank=True)
    is_online = models.BooleanField(_("online"), default=False)
    external_url = models.URLField(
        _("external page"),
        blank=True,
        help_text=_("Canonical page elsewhere, e.g. itch.io or GitHub."),
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=_choices(EntryStatus),
        default=EntryStatus.DRAFT.value,
    )
    outcome = models.CharField(
        _("outcome"), max_length=16, choices=_choices(Outcome), blank=True
    )
    featured = models.BooleanField(_("featured"), default=False)
    hide_from_whats_new = models.BooleanField(_("hide from what's new"), default=False)
    license = models.CharField(_("license"), max_length=_SHORT, blank=True)
    cover = models.ForeignKey(
        MediaAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("cover"),
    )
    tags = models.ManyToManyField(
        Tag, blank=True, related_name="entries", verbose_name=_("tags")
    )
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)
    search_text = models.TextField(editable=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar = ["-date", "-start_at", "-created_at"]
        verbose_name = _("entry")
        verbose_name_plural = _("entries")
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["type", "slug"], name="entry_slug_unique_per_type"
            ),
            models.CheckConstraint(
                condition=Q(end_at__isnull=True)
                | Q(start_at__isnull=True)
                | Q(end_at__gte=F("start_at")),
                name="entry_ends_after_start",
                violation_error_message=_("Ends before it starts."),
            ),
        ]

    def __str__(self) -> str:
        return str(self.title)

    def refresh_search_text(self) -> None:
        """Denormalise everything worth finding into one column."""
        texts = [
            self.title,
            self.summary,
            *(str(value) for value in self.metadata.values()),
            *self.tags.values_list("name", flat=True),
            *self.parts.exclude(text="").values_list("text", flat=True),
            *self.parts.exclude(caption="").values_list("caption", flat=True),
        ]
        self.search_text = "\n".join(texts)
        Entry.objects.filter(pk=self.pk).update(search_text=self.search_text)


class Part(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="parts")
    order = models.PositiveIntegerField(_("order"), default=0)
    kind = models.CharField(
        _("kind"),
        max_length=16,
        choices=_choices(PartKind),
        default=PartKind.TEXT.value,
    )
    text = models.TextField(_("text"), blank=True, help_text=_("Markdown."))
    url = models.URLField(_("URL"), blank=True)
    asset = models.ForeignKey(
        MediaAsset,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="parts",
        verbose_name=_("file"),
    )
    caption = models.CharField(_("caption"), max_length=_LONG, blank=True)
    options = models.JSONField(_("options"), default=dict, blank=True)

    class Meta:
        ordering: ClassVar = ["order", "pk"]
        verbose_name = _("part")
        verbose_name_plural = _("parts")

    def __str__(self) -> str:
        return f"{self.kind} #{self.order}"


class Relation(models.Model):
    from_entry = models.ForeignKey(
        Entry, on_delete=models.CASCADE, related_name="relations"
    )
    to_entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="backlinks",
        verbose_name=_("entry"),
    )
    role = models.SlugField(_("role"), max_length=_SHORT)
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering: ClassVar = ["order", "pk"]
        verbose_name = _("relation")
        verbose_name_plural = _("relations")
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["from_entry", "to_entry", "role"], name="relation_unique"
            ),
            models.CheckConstraint(
                condition=~Q(from_entry=F("to_entry")),
                name="relation_not_to_self",
                violation_error_message=_("An entry cannot link to itself."),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_entry} → {self.role} → {self.to_entry}"


class SyndicationLink(models.Model):
    entry = models.ForeignKey(
        Entry, on_delete=models.CASCADE, related_name="syndication"
    )
    platform = models.CharField(_("platform"), max_length=_SHORT)
    url = models.URLField(_("URL"))

    class Meta:
        ordering: ClassVar = ["pk"]
        verbose_name = _("syndication link")
        verbose_name_plural = _("syndication links")

    def __str__(self) -> str:
        return str(self.url)


class Profile(models.Model):
    """Singleton: the person the site is about."""

    name = models.CharField(_("name"), max_length=_SHORT)
    handle = models.CharField(_("handle"), max_length=_SHORT, blank=True)
    tagline = models.CharField(_("tagline"), max_length=_LONG, blank=True)
    photo = models.ForeignKey(
        MediaAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("photo"),
    )
    bio = models.TextField(_("bio"), blank=True, help_text=_("Markdown."))
    email = models.EmailField(_("e-mail"), blank=True)

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profile")

    def __str__(self) -> str:
        return str(self.name)


class Link(models.Model):
    platform = models.CharField(_("platform"), max_length=_SHORT)
    url = models.URLField(_("URL"))
    label = models.CharField(_("label"), max_length=_SHORT)
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering: ClassVar = ["order", "pk"]
        verbose_name = _("link")
        verbose_name_plural = _("links")

    def __str__(self) -> str:
        return str(self.label)


class ExternalItem(models.Model):
    source = models.CharField(_("source"), max_length=_SHORT)
    external_id = models.CharField(_("external id"), max_length=_LONG)
    title = models.CharField(_("title"), max_length=_LONG)
    url = models.URLField(_("URL"))
    published_at = models.DateTimeField(_("published"))
    thumbnail_url = models.URLField(_("thumbnail"), blank=True)
    entry = models.ForeignKey(
        Entry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="external_items",
        verbose_name=_("entry"),
    )

    class Meta:
        ordering: ClassVar = ["-published_at"]
        verbose_name = _("external item")
        verbose_name_plural = _("external items")
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="external_item_unique"
            )
        ]

    def __str__(self) -> str:
        return str(self.title)
