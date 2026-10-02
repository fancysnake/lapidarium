"""Admin registrations (django-unfold), model-coupled by design."""

from __future__ import annotations

import datetime as dt
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar, TypedDict, override

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html_join
from django.utils.module_loading import import_string
from django.utils.translation import gettext, ngettext
from django.utils.translation import gettext_lazy as _
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultipleWidget,
    UnfoldAdminColorInputWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminSingleDateWidget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminTextInputWidget,
    UnfoldAdminURLInputWidget,
    UnfoldBooleanSwitchWidget,
)

from lapidarium.links.db.django.models import (
    HEX_COLOUR,
    Entry,
    EntryType,
    ExternalItem,
    FieldDefinition,
    Link,
    MediaAsset,
    Part,
    Profile,
    Relation,
    SyndicationLink,
    Tag,
)
from lapidarium.links.db.django.repositories import entry_type_dto
from lapidarium.pacts import (
    BUILTIN_DEFAULTS,
    CONTAINER_ROLES,
    ROLE_BUILTINS,
    EntryStatus,
    FieldKind,
    MetadataValidationError,
    PartKind,
    RelationRole,
    TypeRole,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.contrib.admin.options import _FieldOpts, _FieldsetSpec
    from django.db.models import QuerySet
    from django.forms.utils import _FilesT
    from django.http import HttpRequest, HttpResponse, QueryDict
    from django.urls import URLPattern
    from django.utils.functional import _StrOrPromise

    from lapidarium.pacts import (
        BuiltinValues,
        MetadataInput,
        PartData,
        ServicesProtocol,
    )

    # Unfold's admin classes are Django's, restyled; type-check against Django's.
    EntryTypeAdminBase = admin.ModelAdmin[EntryType]
    EntryAdminBase = admin.ModelAdmin[Entry]
    MediaAssetAdminBase = admin.ModelAdmin[MediaAsset]
    TagAdminBase = admin.ModelAdmin[Tag]
    ProfileAdminBase = admin.ModelAdmin[Profile]
    LinkAdminBase = admin.ModelAdmin[Link]
    ExternalItemAdminBase = admin.ModelAdmin[ExternalItem]
    FieldDefinitionInlineBase = admin.TabularInline[FieldDefinition, EntryType]
    PartInlineBase = admin.StackedInline[Part, Entry]
    RelationInlineBase = admin.TabularInline[Relation, Entry]
    SyndicationInlineBase = admin.TabularInline[SyndicationLink, Entry]

    EntryTypeFormBase = forms.ModelForm[EntryType]
    FieldDefinitionFormBase = forms.ModelForm[FieldDefinition]
    EntryFormBase = forms.ModelForm[Entry]
    PartFormSetBase = forms.BaseInlineFormSet[Part, Entry, forms.ModelForm[Part]]
    RelationFormSetBase = forms.BaseInlineFormSet[
        Relation, Entry, forms.ModelForm[Relation]
    ]
else:
    from unfold.admin import ModelAdmin, StackedInline, TabularInline

    EntryTypeAdminBase = EntryAdminBase = MediaAssetAdminBase = ModelAdmin
    TagAdminBase = ProfileAdminBase = LinkAdminBase = ExternalItemAdminBase = ModelAdmin
    FieldDefinitionInlineBase = RelationInlineBase = TabularInline
    SyndicationInlineBase = TabularInline
    PartInlineBase = StackedInline

    EntryTypeFormBase = FieldDefinitionFormBase = EntryFormBase = forms.ModelForm
    PartFormSetBase = RelationFormSetBase = forms.BaseInlineFormSet

META_PREFIX = "meta_"
ROLE_COLUMNS = tuple(BUILTIN_DEFAULTS)
PART_CHOICES = [(kind.value, kind.value.capitalize()) for kind in PartKind]


def build_services() -> ServicesProtocol:
    """Services for admin forms, which never see the request the middleware fills."""
    factory: Callable[[], ServicesProtocol] = import_string(settings.SERVICES_FACTORY)
    return factory()


# Sidebar


class NavItem(TypedDict):
    title: str
    icon: str
    link: str
    permission: Callable[[HttpRequest], bool]


class NavGroup(TypedDict):
    title: str
    separator: bool
    items: list[NavItem]


def _can(permission: str) -> Callable[[HttpRequest], bool]:
    return lambda request: request.user.has_perm(f"lapidarium_db.{permission}")


def _item(title: str, *, icon: str, model: str) -> NavItem:
    return {
        "title": title,
        "icon": icon,
        "link": reverse(f"admin:lapidarium_db_{model}_changelist"),
        "permission": _can(f"view_{model}"),
    }


def sidebar_navigation(_request: HttpRequest) -> list[NavGroup]:
    """Unfold sidebar: one item per content type, then the site's own records."""
    entries = reverse("admin:lapidarium_db_entry_changelist")
    content: list[NavItem] = [
        {
            "title": entry_type.label_plural,
            "icon": entry_type.icon or "article",
            "link": f"{entries}?type__id__exact={entry_type.pk}",
            "permission": _can("view_entry"),
        }
        for entry_type in EntryType.objects.all()
    ]
    return [
        {
            "title": gettext("Content"),
            "separator": False,
            "items": [
                *content,
                _item(gettext("All entries"), icon="list", model="entry"),
            ],
        },
        {
            "title": gettext("Library"),
            "separator": True,
            "items": [
                _item(gettext("Media"), icon="image", model="mediaasset"),
                _item(gettext("Tags"), icon="sell", model="tag"),
                _item(gettext("External items"), icon="rss_feed", model="externalitem"),
            ],
        },
        {
            "title": gettext("Site"),
            "separator": True,
            "items": [
                _item(gettext("Content types"), icon="category", model="entrytype"),
                _item(gettext("Profile"), icon="person", model="profile"),
                _item(gettext("Links"), icon="link", model="link"),
            ],
        },
    ]


# Content types


class CommaSeparatedField(forms.Field):
    """A list of short strings edited as one comma-separated line."""

    widget = UnfoldAdminTextInputWidget

    @override
    def prepare_value(self, value: list[str] | str | None) -> str:
        if isinstance(value, list):
            return ", ".join(value)
        return value or ""

    @override
    def to_python(self, value: str | None) -> list[str]:
        return [item.strip() for item in (value or "").split(",") if item.strip()]


class FieldDefinitionForm(FieldDefinitionFormBase):
    choices = CommaSeparatedField(
        label=_("choices"), required=False, help_text=_("For choice fields.")
    )

    class Meta:
        model = FieldDefinition
        fields = "__all__"

    @override
    def clean(self) -> None:
        super().clean()
        kind = self.cleaned_data.get("kind")
        if kind == FieldKind.CHOICE and not self.cleaned_data.get("choices"):
            self.add_error("choices", _("A choice field needs choices."))
        if kind == FieldKind.RELATION and not self.cleaned_data.get("target_type"):
            self.add_error("target_type", _("A relation field needs a target type."))


class FieldDefinitionInline(FieldDefinitionInlineBase):
    model = FieldDefinition
    form = FieldDefinitionForm
    fk_name = "entry_type"
    extra = 0
    ordering_field = "order"
    hide_ordering_field = True
    fields = (
        "key",
        "label",
        "kind",
        "required",
        "choices",
        "url_kind",
        "target_type",
        "show_on_card",
        "show_in_metadata_panel",
        "order",
    )


def _choice_field(
    label: _StrOrPromise, choices: list[tuple[str, str]]
) -> forms.MultipleChoiceField:
    return forms.MultipleChoiceField(
        label=label,
        choices=choices,
        required=False,
        widget=UnfoldAdminCheckboxSelectMultipleWidget,
    )


class EntryTypeForm(EntryTypeFormBase):
    allowed_parts = _choice_field(_("allowed parts"), PART_CHOICES)
    required_parts = _choice_field(_("required parts"), PART_CHOICES)

    colour = forms.CharField(
        label=_("colour"), validators=[HEX_COLOUR], widget=UnfoldAdminColorInputWidget
    )
    tint = forms.CharField(
        label=_("tint"),
        required=False,
        validators=[HEX_COLOUR],
        widget=UnfoldAdminTextInputWidget,
        help_text=_("Light background; derived from the colour when blank."),
    )

    class Meta:
        model = EntryType
        fields = "__all__"

    def __init__(
        self,
        data: QueryDict | None = None,
        files: _FilesT | None = None,
        *,
        instance: EntryType | None = None,
        initial: dict[str, str] | None = None,
    ) -> None:
        super().__init__(data, files, instance=instance, initial=initial)
        filters = [("year", gettext("Year")), ("tag", gettext("Tag"))]
        if instance:
            filters.extend(
                (field.key, field.label)
                for field in instance.fields.exclude(
                    kind__in=[FieldKind.LONG_TEXT, FieldKind.URL]
                )
            )
        self.fields["list_filters"] = _choice_field(_("list filters"), filters)

    @override
    def clean(self) -> None:
        super().clean()
        data = self.cleaned_data
        if not set(data.get("required_parts", [])) <= set(
            data.get("allowed_parts", [])
        ):
            self.add_error("required_parts", _("Required parts must be allowed."))
        if colour := data.get("colour"):
            schema = build_services().schema
            data["tint"] = data.get("tint") or schema.derive_tint(colour)
            for message in schema.check_colours(colour, data["tint"]):
                self.add_error("colour", message)


@admin.register(EntryType)
class EntryTypeAdmin(EntryTypeAdminBase):
    form = EntryTypeForm
    inlines = (FieldDefinitionInline,)
    list_display = ("label_plural", "key", "route", "role", "layout", "in_menu")
    list_filter = ("role", "layout", "in_menu")
    search_fields = ("label", "label_plural", "key")
    ordering_field = "order"
    hide_ordering_field = True
    prepopulated_fields: ClassVar = {"key": ("label",), "route": ("label_plural",)}
    fieldsets = (
        (None, {"fields": ("label", "label_plural", "key", "route", "order")}),
        (_("Behaviour"), {"fields": ("role", "layout", "has_detail_page")}),
        (_("Look"), {"fields": ("colour", "tint", "icon", "in_menu")}),
        (_("Parts"), {"fields": ("allowed_parts", "required_parts", "list_filters")}),
        (
            _("Home page door"),
            {"fields": ("door_enabled", "door_label", "door_pick", "door_min_entries")},
        ),
    )


# Entries

_SCALAR_FIELDS: dict[str, tuple[type[forms.Field], type[forms.Widget]]] = {
    FieldKind.TEXT: (forms.CharField, UnfoldAdminTextInputWidget),
    FieldKind.LONG_TEXT: (forms.CharField, UnfoldAdminTextareaWidget),
    FieldKind.URL: (forms.URLField, UnfoldAdminURLInputWidget),
    FieldKind.DATE: (forms.DateField, UnfoldAdminSingleDateWidget),
    FieldKind.NUMBER: (forms.FloatField, UnfoldAdminIntegerFieldWidget),
    FieldKind.BOOL: (forms.BooleanField, UnfoldBooleanSwitchWidget),
}


def _metadata_field(field: FieldDefinition, entry: Entry | None) -> forms.Field:
    stored = entry.metadata.get(field.key) if entry else None
    if field.kind == FieldKind.CHOICE:
        return forms.ChoiceField(
            label=field.label,
            required=field.required,
            initial=stored,
            choices=[("", "---------"), *((c, c) for c in field.choices)],
            widget=UnfoldAdminSelectWidget,
        )
    field_class, widget = _SCALAR_FIELDS[field.kind]
    return field_class(
        label=field.label,
        # A switch left off is an answer, not a missing value.
        required=field.required and field.kind != FieldKind.BOOL,
        initial=(
            dt.date.fromisoformat(stored)
            if field.kind == FieldKind.DATE and stored
            else stored
        ),
        widget=widget,
    )


def _metadata_names(entry_type: EntryType) -> tuple[str, ...]:
    """Form field names of a type's metadata; relation fields are relation rows."""
    keys = entry_type.fields.exclude(kind=FieldKind.RELATION).values_list("key")
    return tuple(META_PREFIX + key for (key,) in keys)


class EntryForm(EntryFormBase):
    """An entry with one `meta_<key>` field per field of its type's schema."""

    # Carries the type of a new entry from the add page to its POST.
    entry_type = forms.SlugField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Entry
        exclude = ("type", "metadata", "search_text")

    def __init__(
        self,
        data: QueryDict | None = None,
        files: _FilesT | None = None,
        *,
        instance: Entry | None = None,
        initial: dict[str, str] | None = None,
    ) -> None:
        super().__init__(data, files, instance=instance, initial=initial)
        if instance is None:
            key = self["entry_type"].value()
            self.instance.type = get_object_or_404(EntryType, key=key)
        for field in self.instance.type.fields.exclude(kind=FieldKind.RELATION):
            self.fields[META_PREFIX + field.key] = _metadata_field(field, instance)

    @override
    def clean(self) -> None:
        super().clean()
        # Built-ins the role does not use stay empty.
        used = ROLE_BUILTINS[TypeRole(self.instance.type.role)]
        for column, default in BUILTIN_DEFAULTS.items():
            if column not in used:
                setattr(self.instance, column, default)
        services = build_services()
        self._check_builtins(services)
        self._check_metadata(services)
        self._check_slug()
        self._check_status()

    def _check_builtins(self, services: ServicesProtocol) -> None:
        data = self.cleaned_data
        values: BuiltinValues = {
            "date": data.get("date"),
            "start_at": data.get("start_at"),
            "end_at": data.get("end_at"),
            "location": data.get("location", ""),
            "is_online": data.get("is_online", False),
            "outcome": data.get("outcome", ""),
        }
        role = TypeRole(self.instance.type.role)
        for key, message in services.schema.check_builtins(role, values).items():
            self.add_error(key if key in self.fields else None, message)

    def _check_metadata(self, services: ServicesProtocol) -> None:
        dto = entry_type_dto(self.instance.type)
        values: dict[str, MetadataInput] = {
            field.key: self.cleaned_data.get(META_PREFIX + field.key)
            for field in dto.fields
            if field.kind != FieldKind.RELATION
        }
        try:
            self.instance.metadata = services.schema.validate_metadata(dto, values)
        except MetadataValidationError as exc:
            for key, message in exc.errors.items():
                if META_PREFIX + key not in self.errors:
                    self.add_error(META_PREFIX + key, message)

    def _check_slug(self) -> None:
        slug = self.cleaned_data.get("slug")
        taken = Entry.objects.filter(type=self.instance.type, slug=slug).exclude(
            pk=self.instance.pk
        )
        if slug and taken.exists():
            self.add_error("slug", _("Another entry of this type uses this slug."))

    def _check_status(self) -> None:
        published_links_here = (
            self.instance.pk
            and self.instance.backlinks.filter(
                from_entry__status=EntryStatus.PUBLISHED
            ).exists()
        )
        if (
            self.cleaned_data.get("status") == EntryStatus.DRAFT
            and published_links_here
        ):
            self.add_error(
                "status", _("Published entries link here; unlink them first.")
            )


class PartFormSet(PartFormSetBase):
    @override
    def clean(self) -> None:
        super().clean()
        if any(self.errors):
            return
        schema = build_services().schema
        kinds: list[PartKind] = []
        for form in self.forms:
            data = form.cleaned_data
            if not data or data.get("DELETE"):
                continue
            asset: MediaAsset | None = data.get("asset")
            part: PartData = {
                "kind": PartKind(data["kind"]),
                "text": data.get("text", ""),
                "url": data.get("url", ""),
                "asset": (asset.file.name or "") if asset else "",
                "caption": data.get("caption", ""),
                "options": data.get("options") or {},
            }
            for message in schema.check_part(part, asset.alt if asset else None):
                form.add_error(None, message)
            kinds.append(part["kind"])
        entry_type = entry_type_dto(self.instance.type)
        if errors := schema.check_part_kinds(entry_type, kinds):
            raise forms.ValidationError(errors)

    @override
    def save(self, commit: bool = True) -> list[Part]:
        parts = super().save(commit=commit)
        self.instance.refresh_search_text()
        return parts


class PartInline(PartInlineBase):
    model = Part
    formset = PartFormSet
    extra = 0
    ordering_field = "order"
    hide_ordering_field = True
    autocomplete_fields = ("asset",)
    fields = ("kind", "text", "url", "asset", "caption", "order")


def _reaches(start: Entry, goal: Entry) -> bool:
    """Whether `goal` is `start` or one of its `part_of` ancestors."""
    seen: set[int] = set()
    frontier = {start.pk}
    while frontier:
        if goal.pk in frontier:
            return True
        seen |= frontier
        frontier = (
            set(
                Relation.objects.filter(
                    from_entry__in=frontier, role=RelationRole.PART_OF
                ).values_list("to_entry", flat=True)
            )
            - seen
        )
    return False


class RelationFormSet(RelationFormSetBase):
    """Built-in roles plus the relation fields of the entry's type."""

    @cached_property
    def schema_fields(self) -> dict[str, FieldDefinition]:
        fields = self.instance.type.fields.filter(kind=FieldKind.RELATION)
        return {field.key: field for field in fields.select_related("target_type")}

    @override
    def add_fields(self, form: forms.ModelForm[Relation], index: int | None) -> None:
        super().add_fields(form, index)
        builtin = [(role.value, role.value.replace("_", " ")) for role in RelationRole]
        schema = [(f.key, f.label) for f in self.schema_fields.values()]
        form.fields["role"] = forms.ChoiceField(
            label=_("role"), choices=builtin + schema, widget=UnfoldAdminSelectWidget
        )

    @override
    def clean(self) -> None:
        super().clean()
        fields = self.schema_fields
        linked: set[str] = set()
        for form in self.forms:
            data = form.cleaned_data
            if not data or data.get("DELETE") or "to_entry" not in data:
                continue
            linked.add(data["role"])
            for message in self._target_errors(
                data["role"], data["to_entry"], fields=fields
            ):
                form.add_error("to_entry", message)
        if missing := [
            f.label for f in fields.values() if f.required and f.key not in linked
        ]:
            raise forms.ValidationError(
                _("Link at least one entry as: %(roles)s.")
                % {"roles": ", ".join(missing)}
            )

    def _target_errors(
        self, role: str, target: Entry, *, fields: dict[str, FieldDefinition]
    ) -> list[str]:
        entry = self.instance
        if entry.pk and target.pk == entry.pk:
            return []  # the relation_not_to_self constraint reports it
        errors: list[str] = []
        if role == RelationRole.PART_OF and target.type.role not in CONTAINER_ROLES:
            errors.append(gettext("Only containers can hold entries."))
        elif role == RelationRole.PART_OF and entry.pk and _reaches(target, entry):
            errors.append(gettext("That makes a loop of containers."))
        elif (field := fields.get(role)) and target.type_id != field.target_type_id:
            errors.append(
                gettext("%(role)s links to a %(type)s.")
                % {"role": field.label, "type": field.target_type}
            )
        if entry.status == EntryStatus.PUBLISHED != target.status:
            errors.append(gettext("A published entry cannot link to a draft."))
        return errors


class RelationInline(RelationInlineBase):
    model = Relation
    formset = RelationFormSet
    fk_name = "from_entry"
    extra = 0
    ordering_field = "order"
    hide_ordering_field = True
    autocomplete_fields = ("to_entry",)
    fields = ("to_entry", "role", "order")
    verbose_name = _("link to another entry")
    verbose_name_plural = _("links to other entries")


class SyndicationInline(SyndicationInlineBase):
    model = SyndicationLink
    extra = 0
    fields = ("platform", "url")


@admin.register(Entry)
class EntryAdmin(EntryAdminBase):
    form = EntryForm
    inlines = (PartInline, RelationInline, SyndicationInline)
    list_display = ("title", "type", "status", "featured", "updated_at")
    list_filter = ("type", "status", "featured", "tags")
    list_select_related = ("type",)
    search_fields = ("title", "summary", "slug")
    autocomplete_fields = ("cover", "tags")
    prepopulated_fields: ClassVar = {"slug": ("title",)}
    readonly_fields = ("backlinks",)
    actions = ("publish", "unpublish", "feature", "unfeature")

    @staticmethod
    def _entry_type(request: HttpRequest, obj: Entry | None) -> EntryType:
        if obj:
            return obj.type
        return get_object_or_404(EntryType, key=request.GET.get("type", ""))

    @override
    def get_urls(self) -> list[URLPattern]:
        # A new entry needs its type first; without one, offer the choice.
        add = path(
            "add/",
            self.admin_site.admin_view(self.add_or_choose_view),
            name="lapidarium_db_entry_add",
        )
        return [add, *super().get_urls()]

    def add_or_choose_view(self, request: HttpRequest) -> HttpResponse:
        if EntryType.objects.filter(key=request.GET.get("type", "")).exists():
            return self.add_view(request)
        if not self.has_add_permission(request):
            raise PermissionDenied
        context = {
            **self.admin_site.each_context(request),
            "title": gettext("Add entry"),
            "opts": self.opts,
            "entry_types": EntryType.objects.all(),
        }
        return TemplateResponse(
            request, "admin/lapidarium_db/entry/choose_type.html", context
        )

    @override
    def get_changeform_initial_data(
        self, request: HttpRequest
    ) -> dict[str, str | list[str]]:
        initial = super().get_changeform_initial_data(request)
        return {**initial, "entry_type": request.GET.get("type", "")}

    @override
    def get_exclude(
        self, request: HttpRequest, obj: Entry | None = None
    ) -> tuple[str, ...]:
        # Metadata fields are added by the form itself; the factory must skip them.
        return (
            *EntryForm.Meta.exclude,
            *_metadata_names(self._entry_type(request, obj)),
        )

    @override
    def get_fieldsets(
        self, request: HttpRequest, obj: Entry | None = None
    ) -> _FieldsetSpec:
        entry_type = self._entry_type(request, obj)
        used = ROLE_BUILTINS[TypeRole(entry_type.role)]
        meta = _metadata_names(entry_type)
        main: _FieldOpts = {
            "fields": [
                "title",
                "slug",
                "summary",
                "status",
                "featured",
                "hide_from_whats_new",
                *([] if obj else ["entry_type"]),
            ]
        }
        fieldsets: list[tuple[_StrOrPromise | None, _FieldOpts]] = [
            (entry_type.label, main),
            (_("When and where"), {"fields": [c for c in ROLE_COLUMNS if c in used]}),
        ]
        if meta:
            fieldsets.append((_("Details"), {"fields": meta}))
        fieldsets.append(
            (
                _("Presentation"),
                {"fields": ["cover", "tags", "external_url", "license"]},
            )
        )
        if obj:
            fieldsets.append((_("Backlinks"), {"fields": ["backlinks"]}))
        return fieldsets

    @staticmethod
    @admin.display(description=_("Linked from"))
    def backlinks(obj: Entry) -> str:
        links = obj.backlinks.select_related("from_entry")
        return (
            format_html_join(
                "\n",
                '<p><a href="{}">{}</a> · {}</p>',
                (
                    (
                        reverse(
                            "admin:lapidarium_db_entry_change", args=[r.from_entry_id]
                        ),
                        r.from_entry.title,
                        r.role.replace("_", " "),
                    )
                    for r in links
                ),
            )
            or "—"
        )

    @admin.action(description=_("Publish"))
    def publish(self, request: HttpRequest, queryset: QuerySet[Entry]) -> None:
        blocked = set(
            queryset.filter(relations__to_entry__status=EntryStatus.DRAFT).values_list(
                "pk", flat=True
            )
        )
        count = queryset.exclude(pk__in=blocked).update(status=EntryStatus.PUBLISHED)
        self._report(request, changed=count, blocked=len(blocked))

    @admin.action(description=_("Unpublish"))
    def unpublish(self, request: HttpRequest, queryset: QuerySet[Entry]) -> None:
        blocked = set(
            queryset.filter(
                backlinks__from_entry__status=EntryStatus.PUBLISHED
            ).values_list("pk", flat=True)
        )
        count = queryset.exclude(pk__in=blocked).update(status=EntryStatus.DRAFT)
        self._report(request, changed=count, blocked=len(blocked))

    @admin.action(description=_("Mark as featured"))
    def feature(self, request: HttpRequest, queryset: QuerySet[Entry]) -> None:
        self._report(request, changed=queryset.update(featured=True), blocked=0)

    @admin.action(description=_("Remove from featured"))
    def unfeature(self, request: HttpRequest, queryset: QuerySet[Entry]) -> None:
        self._report(request, changed=queryset.update(featured=False), blocked=0)

    def _report(self, request: HttpRequest, *, changed: int, blocked: int) -> None:
        self.message_user(
            request,
            ngettext("%d entry changed.", "%d entries changed.", changed) % changed,
        )
        if blocked:
            self.message_user(
                request,
                ngettext(
                    "%d entry skipped: a published entry may only link to"
                    " published ones.",
                    "%d entries skipped: a published entry may only link to"
                    " published ones.",
                    blocked,
                )
                % blocked,
                messages.WARNING,
            )


# Library and site


@admin.register(MediaAsset)
class MediaAssetAdmin(MediaAssetAdminBase):
    fields = ("file", "alt")
    list_display = ("__str__", "alt", "created_at")
    search_fields = ("file", "alt")


@admin.register(Tag)
class TagAdmin(TagAdminBase):
    search_fields = ("name",)


@admin.register(Profile)
class ProfileAdmin(ProfileAdminBase):
    autocomplete_fields = ("photo",)

    @override
    def has_add_permission(self, request: HttpRequest) -> bool:
        return super().has_add_permission(request) and not Profile.objects.exists()


@admin.register(Link)
class LinkAdmin(LinkAdminBase):
    list_display = ("label", "platform", "url")
    ordering_field = "order"
    hide_ordering_field = True


@admin.register(ExternalItem)
class ExternalItemAdmin(ExternalItemAdminBase):
    list_display = ("title", "source", "published_at", "entry")
    list_filter = ("source",)
    search_fields = ("title", "url")
    autocomplete_fields = ("entry",)
