"""Admin for content types and entries: dynamic forms, inlines, graph integrity."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model

from lapidarium.links.db.django.models import (
    Entry,
    EntryType,
    FieldDefinition,
    Profile,
    Relation,
)

TYPES = "/admin/lapidarium_db/entrytype/"
ENTRIES = "/admin/lapidarium_db/entry/"

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


@pytest.fixture(name="admin")
def admin_fixture(client):
    user = get_user_model().objects.create_superuser("curator", password="pw")
    client.defaults["HTTP_ACCEPT_LANGUAGE"] = "en"
    client.force_login(user)
    return client


def _inline(prefix, rows=()):
    data = {
        f"{prefix}-TOTAL_FORMS": str(len(rows)),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for index, row in enumerate(rows):
        data.update({f"{prefix}-{index}-{key}": value for key, value in row.items()})
    return data


def _part(kind="text", order=0, **values):
    return {
        "kind": kind,
        "text": "",
        "url": "",
        "asset": "",
        "caption": "",
        "order": str(order),
        **values,
    }


def _relation(target, *, role="part_of", order=0):
    return {"to_entry": str(target.pk), "role": role, "order": str(order)}


def _entry(*, parts=(), relations=(), **values):
    return {
        "title": "Moose",
        "slug": "moose",
        "summary": "One sentence.",
        "status": "draft",
        **values,
        **_inline("parts", parts),
        **_inline("relations", relations),
        **_inline("syndication"),
    }


def _type(**values):
    return {
        "label": "Talk",
        "label_plural": "Talks",
        "key": "talk",
        "route": "talks",
        "order": "0",
        "role": "thing",
        "layout": "article",
        "colour": "#6b3fa0",
        "tint": "",
        "icon": "",
        "allowed_parts": ["text"],
        "door_pick": "latest",
        "door_min_entries": "1",
        **values,
        **_inline("fields", values.pop("fields", ())),
    }


def _field(key, kind, **values):
    return {
        "key": key,
        "label": key.title(),
        "kind": kind,
        "choices": "",
        "url_kind": "any",
        "target_type": "",
        "order": "0",
        **values,
    }


def _errors(response):
    form = response.context["adminform"].form
    inlines = {
        inline.formset.prefix: (
            [dict(f.errors) for f in inline.formset.forms if f.errors],
            list(inline.formset.non_form_errors()),
        )
        for inline in response.context["inline_admin_formsets"]
    }
    return dict(form.errors), inlines


# Sidebar


@pytest.mark.usefixtures("demo")
def test_sidebar_lists_content_types_then_site_records(admin):
    response = admin.get("/admin/")

    groups = response.context["sidebar_navigation"]
    session = EntryType.objects.get(key="session")
    assert [group["title"] for group in groups] == ["Content", "Library", "Site"]
    assert [item["title"] for item in groups[0]["items"]] == [
        *EntryType.objects.values_list("label_plural", flat=True),
        "All entries",
    ]
    assert groups[0]["items"][0]["link"] == f"{ENTRIES}?type__id__exact={session.pk}"
    assert groups[0]["items"][0]["icon"] == "casino"
    assert groups[0]["items"][0]["has_permission"] is True
    assert [item["link"] for item in groups[2]["items"]] == [
        TYPES,
        "/admin/lapidarium_db/profile/",
        "/admin/lapidarium_db/link/",
    ]


def test_sidebar_hides_what_staff_may_not_see(client):
    user = get_user_model().objects.create_user("intern", password="pw", is_staff=True)
    EntryType.objects.create(key="note", label="Note", label_plural="Notes", route="n")
    client.force_login(user)

    response = client.get("/admin/")

    items = response.context["sidebar_navigation"][0]["items"]
    assert [item["has_permission"] for item in items] == [False, False]


# Content types


def test_type_gets_a_derived_tint_and_its_fields(admin):
    response = admin.post(
        f"{TYPES}add/",
        _type(
            required_parts=["text"],
            fields=[
                _field("event", "text"),
                _field("format", "choice", choices="talk, workshop"),
            ],
        ),
    )

    assert response.status_code == HTTPStatus.FOUND
    talk = EntryType.objects.get(key="talk")
    assert talk.tint == "#ede8f4"
    assert talk.allowed_parts == ["text"]
    assert list(talk.fields.values_list("key", "choices")) == [
        ("event", []),
        ("format", ["talk", "workshop"]),
    ]


def test_type_refuses_low_contrast_and_unallowed_required_parts(admin):
    response = admin.post(
        f"{TYPES}add/",
        _type(
            colour="#999999",
            required_parts=["video"],
            fields=[_field("format", "choice"), _field("inspired_by", "relation")],
        ),
    )

    form_errors, inlines = _errors(response)
    assert form_errors == {
        "colour": [
            "Contrast with the page background is 2.85:1, needs 4.5:1.",
            "Contrast with the tint is 2.57:1, needs 4.5:1.",
        ],
        "required_parts": ["Required parts must be allowed."],
    }
    assert inlines["fields"] == (
        [
            {"choices": ["A choice field needs choices."]},
            {"target_type": ["A relation field needs a target type."]},
        ],
        [],
    )


@pytest.mark.usefixtures("demo")
def test_type_change_offers_its_own_fields_as_list_filters(admin):
    session = EntryType.objects.get(key="session")

    response = admin.get(f"{TYPES}{session.pk}/change/")

    form = response.context["adminform"].form
    assert form.fields["list_filters"].choices == [
        ("year", "Year"),
        ("tag", "Tag"),
        ("system", "System"),
        ("format", "Format"),
        ("players", "Gracze"),
    ]
    assert form.initial["list_filters"] == ["year", "tag", "system", "format"]


# Adding entries


def test_add_without_a_type_asks_for_one(admin):
    EntryType.objects.create(key="note", label="Note", label_plural="Notes", route="n")

    response = admin.get(f"{ENTRIES}add/")

    assert response.templates[0].name == "admin/lapidarium_db/entry/choose_type.html"
    assert [t.key for t in response.context["entry_types"]] == ["note"]
    assert f'href="{ENTRIES}add/?type=note"' in response.content.decode()


def test_add_with_no_types_points_to_defining_one(admin):
    response = admin.get(f"{ENTRIES}add/?type=nope")

    assert not response.context["entry_types"]
    assert f'href="{TYPES}add/"' in response.content.decode()


@pytest.mark.usefixtures("demo")
def test_add_form_follows_the_type_schema(admin):
    response = admin.get(f"{ENTRIES}add/?type=event")

    fieldsets = response.context["adminform"].fieldsets
    fields = {name: list(opts["fields"]) for name, opts in fieldsets}
    assert list(fields) == ["Wydarzenie", "When and where", "Details", "Presentation"]
    assert fields["Wydarzenie"][0] == "title"
    assert fields["Wydarzenie"][-1] == "hide_from_whats_new"
    assert fields["When and where"] == ["start_at", "end_at", "location", "is_online"]
    assert fields["Details"] == ["meta_role"]
    roles = response.context["inline_admin_formsets"][1].formset.empty_form
    assert roles.fields["role"].choices == [
        ("part_of", "part of"),
        ("related", "related"),
    ]


@pytest.mark.usefixtures("demo")
def test_add_post_needs_a_known_type(admin):
    response = admin.post(f"{ENTRIES}add/?type=nope", _entry())

    assert response.templates[0].name == "admin/lapidarium_db/entry/choose_type.html"
    assert not Entry.objects.filter(slug="moose").exists()


def test_choosing_a_type_needs_permission_to_add(client):
    user = get_user_model().objects.create_user("intern", password="pw", is_staff=True)
    client.force_login(user)

    assert client.get(f"{ENTRIES}add/").status_code == HTTPStatus.FORBIDDEN


@pytest.mark.usefixtures("demo")
def test_add_saves_metadata_relations_and_search_text(admin):
    session = Entry.objects.get(slug="bal-w-zamku")
    project = Entry.objects.get(slug="klatwa-strahda")

    response = admin.post(
        f"{ENTRIES}add/?type=song",
        _entry(
            title="Walc hrabiego",
            slug="walc-hrabiego",
            status="published",
            parts=[
                _part("audio", url="https://soundcloud.com/x/walc"),
                _part("text", 1, text="Raz, dwa, trzy, ugryzienie."),
                _part(),
            ],
            relations=[
                _relation(project),
                _relation(session, role="inspired_by", order=1),
                _relation(
                    Entry.objects.get(slug="pyrkon-2027"), role="related", order=2
                ),
            ],
        ),
    )

    assert response.status_code == HTTPStatus.FOUND
    song = Entry.objects.get(slug="walc-hrabiego")
    assert song.type.key == "song"
    assert song.metadata == {}
    assert list(song.relations.values_list("role", "to_entry__slug")) == [
        ("part_of", "klatwa-strahda"),
        ("inspired_by", "bal-w-zamku"),
        ("related", "pyrkon-2027"),
    ]
    assert (
        song.search_text == "Walc hrabiego\nOne sentence.\nRaz, dwa, trzy, ugryzienie."
    )


@pytest.mark.usefixtures("demo")
def test_add_checks_role_builtins_metadata_and_slug(admin):
    response = admin.post(
        f"{ENTRIES}add/?type=event",
        _entry(slug="pyrkon-2027", start_at_0="", meta_role=""),
    )

    form_errors, _ = _errors(response)
    assert form_errors == {
        "start_at": ["This field is required."],
        "meta_role": ["This field is required."],
        "slug": ["Another entry of this type uses this slug."],
    }


@pytest.mark.usefixtures("demo")
def test_add_checks_parts_against_the_type(admin):
    response = admin.post(
        f"{ENTRIES}add/?type=session",
        _entry(
            meta_format="one-shot",
            parts=[_part("video", caption="Recording"), _part("image", 1)],
        ),
    )

    _, inlines = _errors(response)
    assert inlines["parts"] == (
        [
            {"__all__": ["A video part needs a URL."]},
            {"__all__": ["The image part needs an uploaded file."]},
        ],
        ["Sesja needs at least one text part."],
    )


@pytest.mark.usefixtures("demo")
def test_add_checks_allowed_and_required_part_kinds(admin):
    response = admin.post(
        f"{ENTRIES}add/?type=session",
        _entry(parts=[_part("link", url="https://example.com")]),
    )

    _, inlines = _errors(response)
    assert inlines["parts"] == (
        [],
        ["Sesja does not allow link parts.", "Sesja needs at least one text part."],
    )


@pytest.mark.usefixtures("demo")
def test_published_entries_link_to_published_containers_only(admin):
    draft_project = Entry.objects.create(
        type=EntryType.objects.get(key="project"),
        slug="draft",
        title="Draft",
        summary="S",
        outcome="ongoing",
    )
    session = Entry.objects.get(slug="bal-w-zamku")

    response = admin.post(
        f"{ENTRIES}add/?type=song",
        _entry(
            status="published",
            parts=[_part("audio", url="https://soundcloud.com/x/y")],
            relations=[
                _relation(draft_project),
                _relation(session, order=1),
                {"to_entry": "", "role": "related", "order": "2"},
                _relation(draft_project, role="inspired_by", order=3),
            ],
        ),
    )

    _, inlines = _errors(response)
    assert inlines["relations"] == (
        [
            {"to_entry": ["A published entry cannot link to a draft."]},
            {"to_entry": ["Only containers can hold entries."]},
            {"to_entry": ["This field is required."]},
            {
                "to_entry": [
                    "Zainspirowana przez cannot link to a Projekt.",
                    "A published entry cannot link to a draft.",
                ]
            },
        ],
        [],
    )


@pytest.mark.usefixtures("demo")
def test_required_relation_fields_need_a_link(admin):
    FieldDefinition.objects.filter(key="inspired_by").update(required=True)

    response = admin.post(
        f"{ENTRIES}add/?type=song",
        _entry(parts=[_part("audio", url="https://soundcloud.com/x/y")]),
    )

    _, inlines = _errors(response)
    assert inlines["relations"] == (
        [],
        ["Link at least one entry as: Zainspirowana przez."],
    )


# Changing entries


@pytest.mark.usefixtures("demo")
def test_change_shows_backlinks_and_stored_metadata(admin):
    session = Entry.objects.get(slug="ucieczka-przed-kosmicznym-losiem")

    response = admin.get(f"{ENTRIES}{session.pk}/change/")

    form = response.context["adminform"].form
    assert form.initial == form.initial | {"title": session.title}
    assert form.fields["meta_format"].initial == "one-shot"
    assert form.fields["meta_system"].initial == "Mothership"
    content = response.content.decode()
    song = Entry.objects.get(slug="ballada-o-losiu")
    assert f'href="{ENTRIES}{song.pk}/change/">Ballada o łosiu</a> · inspired by' in (
        content
    )


@pytest.mark.usefixtures("demo")
def test_change_without_backlinks_shows_a_dash(admin):
    entry = Entry.objects.get(slug="sesje-online")

    response = admin.get(f"{ENTRIES}{entry.pk}/change/")

    assert response.context["adminform"].form.fields["meta_role"].initial == "organizer"
    assert "—" in response.content.decode()


def test_change_renders_every_field_kind(admin):
    entry_type = EntryType.objects.create(
        key="note", label="Note", label_plural="Notes", route="n"
    )
    for order, (key, kind) in enumerate(
        (
            ("body", "long_text"),
            ("link", "url"),
            ("seen", "date"),
            ("score", "number"),
            ("liked", "bool"),
        )
    ):
        FieldDefinition.objects.create(
            entry_type=entry_type, key=key, label=key, kind=kind, order=order
        )
    entry = Entry.objects.create(
        type=entry_type,
        slug="n",
        title="N",
        summary="S",
        metadata={"seen": "2026-03-14", "score": 2.5, "liked": True},
    )

    response = admin.get(f"{ENTRIES}{entry.pk}/change/")

    fields = response.context["adminform"].form.fields
    assert [type(fields[f"meta_{k}"]).__name__ for k in ("body", "link", "seen")] == [
        "CharField",
        "URLField",
        "DateField",
    ]
    assert str(fields["meta_seen"].initial) == "2026-03-14"
    assert fields["meta_score"].initial == pytest.approx(2.5)
    assert fields["meta_liked"].required is False

    response = admin.post(
        f"{ENTRIES}{entry.pk}/change/",
        _entry(
            slug="n",
            meta_body="Long",
            meta_link="https://example.com",
            meta_seen="2026-03-15",
            meta_score="3",
        ),
    )

    assert response.status_code == HTTPStatus.FOUND
    entry.refresh_from_db()
    assert entry.metadata == {
        "body": "Long",
        "link": "https://example.com",
        "seen": "2026-03-15",
        "score": 3,
        "liked": False,
    }


@pytest.mark.usefixtures("demo")
def test_change_clears_built_ins_the_role_does_not_use(admin):
    session = Entry.objects.get(slug="bal-w-zamku")
    Entry.objects.filter(pk=session.pk).update(location="Barovia", outcome="finished")
    session.relations.all().delete()
    project = Entry.objects.get(slug="klatwa-strahda")

    response = admin.post(
        f"{ENTRIES}{session.pk}/change/",
        _entry(
            title=session.title,
            slug=session.slug,
            date="2026-05-02",
            meta_system="D&D 5e",
            meta_format="campaign-session",
            parts=[_part("text", text="Świeże AAR.")],
            relations=[_relation(project)],
        ),
    )

    assert response.status_code == HTTPStatus.FOUND
    session.refresh_from_db()
    assert (session.location, session.outcome) == ("", "")
    assert list(session.relations.values_list("to_entry__slug", flat=True)) == [
        "klatwa-strahda"
    ]


@pytest.mark.usefixtures("demo")
def test_change_refuses_self_links_and_container_loops(admin):
    saga = Entry.objects.get(slug="kampania-mothership")
    initiative = Entry.objects.get(slug="sesje-science-fiction")
    Relation.objects.filter(from_entry=saga).delete()
    Relation.objects.create(from_entry=initiative, to_entry=saga, role="part_of")

    response = admin.post(
        f"{ENTRIES}{saga.pk}/change/",
        _entry(
            title=saga.title,
            slug=saga.slug,
            outcome="finished",
            start_at_0="2026-01-10",
            start_at_1="19:00",
            relations=[_relation(saga), _relation(initiative, order=1)],
        ),
    )

    _, inlines = _errors(response)
    assert inlines["relations"] == (
        [
            {"__all__": ["An entry cannot link to itself."]},
            {"to_entry": ["That makes a loop of containers."]},
        ],
        [],
    )


@pytest.mark.usefixtures("demo")
def test_unpublishing_refuses_entries_published_ones_link_to(admin):
    project = Entry.objects.get(slug="klatwa-strahda")

    response = admin.post(
        f"{ENTRIES}{project.pk}/change/",
        _entry(
            title=project.title,
            slug=project.slug,
            status="draft",
            outcome="ongoing",
            start_at_0="2026-04-18",
            start_at_1="18:00",
        ),
    )

    form_errors, _ = _errors(response)
    assert form_errors == {
        "status": ["Published entries link here; unlink them first."]
    }


# Actions


@pytest.mark.usefixtures("demo")
def test_publish_skips_entries_linking_to_drafts(admin):
    session = Entry.objects.get(slug="bal-w-zamku")
    project = Entry.objects.get(slug="klatwa-strahda")
    Entry.objects.filter(pk__in=[session.pk, project.pk]).update(status="draft")

    response = admin.post(
        ENTRIES,
        {"action": "publish", "_selected_action": [session.pk, project.pk]},
        follow=True,
    )

    assert [str(m) for m in response.context["messages"]] == [
        "1 entry changed.",
        "1 entry skipped: a published entry may only link to published ones.",
    ]
    assert Entry.objects.get(pk=project.pk).status == "published"
    assert Entry.objects.get(pk=session.pk).status == "draft"


@pytest.mark.usefixtures("demo")
def test_unpublish_skips_entries_published_ones_link_to(admin):
    project = Entry.objects.get(slug="klatwa-strahda")
    meme = Entry.objects.get(slug="los-w-kosmosie")

    response = admin.post(
        ENTRIES,
        {"action": "unpublish", "_selected_action": [project.pk, meme.pk]},
        follow=True,
    )

    assert [str(m) for m in response.context["messages"]] == [
        "1 entry changed.",
        "1 entry skipped: a published entry may only link to published ones.",
    ]
    assert Entry.objects.get(pk=meme.pk).status == "draft"


@pytest.mark.usefixtures("demo")
def test_feature_and_unfeature(admin):
    entries = list(Entry.objects.values_list("pk", flat=True)[:2])

    admin.post(
        ENTRIES, {"action": "unfeature", "_selected_action": entries}, follow=True
    )
    assert not Entry.objects.filter(pk__in=entries, featured=True).exists()
    response = admin.post(
        ENTRIES, {"action": "feature", "_selected_action": entries}, follow=True
    )

    assert [str(m) for m in response.context["messages"]] == ["2 entries changed."]
    assert Entry.objects.filter(pk__in=entries, featured=True).count() == 2


# Site records


@pytest.mark.usefixtures("demo")
def test_profile_is_a_singleton(admin):
    response = admin.get("/admin/lapidarium_db/profile/add/")

    assert response.status_code == HTTPStatus.FORBIDDEN
    Profile.objects.all().delete()
    assert admin.get("/admin/lapidarium_db/profile/add/").status_code == HTTPStatus.OK


@pytest.mark.usefixtures("demo")
@pytest.mark.parametrize(
    "model", ("mediaasset", "tag", "link", "externalitem", "entrytype", "entry")
)
def test_changelists_render(admin, model):
    response = admin.get(f"/admin/lapidarium_db/{model}/")

    assert response.status_code == HTTPStatus.OK


def test_type_refuses_a_malformed_colour(admin):
    response = admin.post(f"{TYPES}add/", _type(colour="red"))

    form_errors, _ = _errors(response)
    assert form_errors == {"colour": ["Use #rrggbb."]}


def test_metadata_meaning_is_checked_after_its_format(admin):
    entry_type = EntryType.objects.create(
        key="repo", label="Repo", label_plural="Repos", route="r"
    )
    FieldDefinition.objects.create(
        entry_type=entry_type,
        key="source",
        label="Source",
        kind="url",
        url_kind="github",
    )

    response = admin.post(
        f"{ENTRIES}add/?type=repo", _entry(meta_source="https://gitlab.com/x/y")
    )

    form_errors, _ = _errors(response)
    assert form_errors == {"meta_source": ["Enter a GitHub address."]}


@pytest.mark.usefixtures("demo")
def test_change_offers_schema_roles_beside_built_in_ones(admin):
    song = Entry.objects.get(slug="ballada-o-losiu")

    response = admin.get(f"{ENTRIES}{song.pk}/change/")

    [relation] = response.context["inline_admin_formsets"][1].formset.forms
    assert relation.initial["role"] == "inspired_by"
    assert relation.fields["role"].choices == [
        ("part_of", "part of"),
        ("related", "related"),
        ("inspired_by", "Zainspirowana przez"),
    ]
    assert "meta_inspired_by" not in response.context["adminform"].form.fields


@pytest.mark.usefixtures("demo")
def test_part_format_errors_come_before_part_kind_rules(admin):
    response = admin.post(
        f"{ENTRIES}add/?type=session",
        _entry(meta_format="one-shot", parts=[_part("video", url="not a url")]),
    )

    _, inlines = _errors(response)
    assert inlines["parts"] == ([{"url": ["Enter a valid URL."]}], [])
