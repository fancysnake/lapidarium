import datetime as dt
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lapidarium.mills import ContentExportService, ContentImportService, SchemaService
from lapidarium.pacts import (
    BundleValidationError,
    ContentSummaryDTO,
    EntryDTO,
    EntryRefDTO,
    EntryStatus,
    EntryTypeDTO,
    FieldDefinitionDTO,
    FieldKind,
    LinkDTO,
    MediaAssetDTO,
    PartDTO,
    PartKind,
    ProfileDTO,
    RelationDTO,
    SyndicationLinkDTO,
    TypeRole,
)
from tests.factories import entry_data, field_data, type_data

NOW = dt.datetime(2026, 10, 2, 12, tzinfo=dt.UTC)
ROOT = Path("/export")
COVER = MediaAssetDTO(path="assets/moose.png", url="/m/moose.png", alt="Moose")
PHOTO = MediaAssetDTO(path="assets/me.png", url="/m/me.png", alt="Me")


def _bundle(**overrides):
    return {
        "profile": None,
        "links": [],
        "types": [type_data()],
        "entries": [entry_data()],
        "assets": [],
        **overrides,
    }


def _type_dto():
    return EntryTypeDTO(
        **{
            **type_data(tint="#eeeeee"),
            "fields": (
                FieldDefinitionDTO(**field_data("system", FieldKind.TEXT, choices=())),
            ),
        }
    )


def _entry_dto():
    container = EntryRefDTO(
        type_key="project", slug="saga", title="Saga", status="published"
    )
    return EntryDTO(
        type_key="session",
        slug="moose",
        title="Moose",
        summary="One sentence.",
        date=dt.date(2026, 3, 14),
        start_at=None,
        end_at=None,
        location="",
        is_online=False,
        external_url="",
        status=EntryStatus.PUBLISHED,
        featured=True,
        hide_from_whats_new=False,
        license="",
        outcome="",
        cover=COVER,
        tags=("sci-fi",),
        metadata={"system": "Mothership"},
        parts=(
            PartDTO(
                kind=PartKind.TEXT,
                text="AAR",
                url="",
                asset=None,
                caption="",
                options={},
            ),
            PartDTO(
                kind=PartKind.IMAGE,
                text="",
                url="",
                asset=COVER,
                caption="It",
                options={},
            ),
        ),
        relations=(RelationDTO(role="part_of", target=container),),
        syndication=(SyndicationLinkDTO(platform="youtube", url="https://youtu.be/x"),),
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture(name="repos")
def repos_fixture():
    repos = MagicMock()
    repos.profile.get.return_value = ProfileDTO(
        name="Mira",
        handle="@mira",
        tagline="GM",
        photo=PHOTO,
        bio="",
        email="mira@example.com",
    )
    repos.profile.list_links.return_value = [
        LinkDTO(platform="itch", url="https://mira.itch.io", label="itch")
    ]
    repos.types.list_all.return_value = [_type_dto()]
    repos.entries.list_published.return_value = [_entry_dto()]
    repos.assets.read.side_effect = lambda path: path.encode()
    return repos


def _export_service(repos):
    return ContentExportService(
        types=repos.types,
        entries=repos.entries,
        assets=repos.assets,
        profile=repos.profile,
        store=repos.store,
    )


def _import_service(repos):
    return ContentImportService(
        schema=SchemaService(background="#ffffff"),
        transaction=repos.transaction,
        types=repos.types,
        entries=repos.entries,
        assets=repos.assets,
        profile=repos.profile,
        store=repos.store,
    )


def test_export_writes_published_content_and_the_assets_it_uses(repos):
    summary = _export_service(repos).export(ROOT)

    assert summary == ContentSummaryDTO(types=1, entries=1, assets=2)
    repos.store.write.assert_called_once_with(
        ROOT,
        {
            "profile": {
                "name": "Mira",
                "handle": "@mira",
                "tagline": "GM",
                "photo": "assets/me.png",
                "bio": "",
                "email": "mira@example.com",
            },
            "links": [
                {"platform": "itch", "url": "https://mira.itch.io", "label": "itch"}
            ],
            "types": [
                {
                    **type_data(tint="#eeeeee"),
                    "fields": [field_data("system", FieldKind.TEXT)],
                }
            ],
            "entries": [
                entry_data(
                    date=dt.date(2026, 3, 14),
                    featured=True,
                    cover="assets/moose.png",
                    tags=["sci-fi"],
                    metadata={"system": "Mothership"},
                    parts=[
                        {
                            "kind": PartKind.TEXT,
                            "text": "AAR",
                            "url": "",
                            "asset": "",
                            "caption": "",
                            "options": {},
                        },
                        {
                            "kind": PartKind.IMAGE,
                            "text": "",
                            "url": "",
                            "asset": "assets/moose.png",
                            "caption": "It",
                            "options": {},
                        },
                    ],
                    relations=[
                        {
                            "role": "part_of",
                            "target_type": "project",
                            "target_slug": "saga",
                        }
                    ],
                    syndication=[{"platform": "youtube", "url": "https://youtu.be/x"}],
                    created_at=NOW,
                    updated_at=NOW,
                )
            ],
            "assets": [
                {"path": "assets/me.png", "alt": "Me", "content": b"assets/me.png"},
                {
                    "path": "assets/moose.png",
                    "alt": "Moose",
                    "content": b"assets/moose.png",
                },
            ],
        },
    )


def test_export_without_a_profile(repos):
    repos.profile.get.return_value = None
    repos.entries.list_published.return_value = []

    summary = _export_service(repos).export(ROOT)

    assert summary == ContentSummaryDTO(types=1, entries=0, assets=0)
    bundle = repos.store.write.call_args.args[1]
    assert bundle["profile"] is None
    assert bundle["assets"] == []


def test_export_refuses_a_published_link_to_a_draft(repos):
    draft = EntryRefDTO(type_key="session", slug="draft", title="D", status="draft")
    entry = _entry_dto()
    repos.entries.list_published.return_value = [
        entry.model_copy(
            update={
                "relations": (
                    *entry.relations,
                    RelationDTO(role="related", target=draft),
                )
            }
        )
    ]

    with pytest.raises(BundleValidationError) as caught:
        _export_service(repos).export(ROOT)

    assert caught.value.errors == {
        "content/session/moose.md": ["Links to the draft session/draft."]
    }
    repos.store.write.assert_not_called()


def test_import_saves_everything_in_one_transaction(repos):
    profile = {
        "name": "Mira",
        "handle": "",
        "tagline": "",
        "photo": "assets/me.png",
        "bio": "",
        "email": "",
    }
    asset = {"path": "assets/me.png", "alt": "Me", "content": b"png"}
    project = type_data("project", role=TypeRole.CONTAINER_OUTCOME, tint="#f0f0f0")
    session = type_data(
        fields=[
            field_data("players", FieldKind.NUMBER),
            field_data("inspired_by", FieldKind.RELATION, target_type="session"),
        ]
    )
    moose = entry_data(
        metadata={"players": 4.0},
        relations=[
            {"role": "part_of", "target_type": "project", "target_slug": "saga"}
        ],
    )
    saga = entry_data("saga", "project", outcome="ongoing")
    repos.store.read.return_value = _bundle(
        profile=profile,
        links=[{"platform": "itch", "url": "https://x.itch.io", "label": "itch"}],
        types=[session, project],
        entries=[moose, saga],
        assets=[asset],
    )

    summary = _import_service(repos).import_from(ROOT)

    assert summary == ContentSummaryDTO(types=2, entries=2, assets=1)
    repos.store.read.assert_called_once_with(ROOT)
    repos.transaction.atomic.assert_called_once_with()
    repos.assets.save.assert_called_once_with(asset)
    repos.types.save_all.assert_called_once_with(
        [{**session, "tint": "#ede8f4"}, project]
    )
    assert [c.args[0] for c in repos.entries.save.call_args_list] == [
        {**moose, "metadata": {"players": 4}},
        saga,
    ]
    assert [(c.args, c.kwargs) for c in repos.entries.set_relations.call_args_list] == [
        (("session", "moose"), {"relations": moose["relations"]}),
        (("project", "saga"), {"relations": []}),
    ]
    repos.profile.save.assert_called_once_with(profile)
    repos.profile.replace_links.assert_called_once_with(
        [{"platform": "itch", "url": "https://x.itch.io", "label": "itch"}]
    )


def test_import_rejects_entries_of_unknown_types(repos):
    repos.store.read.return_value = _bundle(entries=[entry_data(entry_type="song")])

    with pytest.raises(BundleValidationError) as caught:
        _import_service(repos).import_from(ROOT)

    assert caught.value.errors == {"content/song/moose.md": ["Unknown type 'song'."]}
    repos.transaction.atomic.assert_not_called()


def test_import_reports_every_problem_by_file(repos):
    session = type_data(
        colour="#999999",
        required_parts=[PartKind.TEXT],
        fields=[field_data("players", FieldKind.NUMBER, required=True)],
    )
    entry = entry_data(
        location="Poznań",
        cover="assets/gone.png",
        metadata={"players": "four"},
        parts=[
            {
                "kind": PartKind.IMAGE,
                "text": "",
                "url": "",
                "asset": "assets/gone.png",
                "caption": "",
                "options": {},
            },
            {
                "kind": PartKind.IMAGE,
                "text": "",
                "url": "",
                "asset": "assets/blank.png",
                "caption": "",
                "options": {},
            },
        ],
        relations=[
            {"role": "related", "target_type": "session", "target_slug": "nope"},
            {"role": "part_of", "target_type": "session", "target_slug": "other"},
        ],
    )
    repos.store.read.return_value = _bundle(
        profile={
            "name": "Mira",
            "handle": "",
            "tagline": "",
            "photo": "assets/missing.png",
            "bio": "",
            "email": "",
        },
        types=[session],
        entries=[entry, entry_data("other", parts=[])],
        assets=[{"path": "assets/blank.png", "alt": "", "content": b""}],
    )

    with pytest.raises(BundleValidationError) as caught:
        _import_service(repos).import_from(ROOT)

    assert caught.value.errors == {
        "types/session.yaml": [
            "Contrast with the page background is 2.85:1, needs 4.5:1.",
            "Contrast with the tint is 2.57:1, needs 4.5:1.",
        ],
        "content/session/moose.md": [
            "metadata.players: Expected a number.",
            "location: Not used by the thing role.",
            "Cover 'assets/gone.png' is not among the assets.",
            "Asset 'assets/gone.png' is not among the assets.",
            "An image part needs alt text on its asset.",
            "Session needs at least one text part.",
            "Relation to missing session/nope.",
            "Relation to session/other: Only containers can hold entries.",
        ],
        "content/session/other.md": [
            "metadata.players: This field is required.",
            "Session needs at least one text part.",
        ],
        "profile.yaml": ["Photo is not among the assets."],
    }
    assert "profile.yaml: Photo is not among the assets." in str(caught.value)


def _relation(role, target_slug, *, target_type="session"):
    return {"role": role, "target_type": target_type, "target_slug": target_slug}


def test_import_holds_relations_to_the_relation_rules(repos):
    project = type_data("project", role=TypeRole.CONTAINER_OUTCOME, tint="#f0f0f0")
    session = type_data(
        fields=[
            field_data(
                "inspired_by", FieldKind.RELATION, target_type="session", required=True
            )
        ]
    )
    repos.store.read.return_value = _bundle(
        types=[session, project],
        entries=[
            entry_data(
                relations=[
                    _relation("related", "draft"),
                    _relation("inspired_by", "saga", target_type="project"),
                    _relation("sequel_of", "other"),
                    _relation("related", "moose"),
                ]
            ),
            entry_data("draft", status="draft"),
            entry_data("other", relations=[_relation("inspired_by", "draft")]),
            entry_data(
                "saga",
                "project",
                outcome="ongoing",
                relations=[_relation("part_of", "arc", target_type="project")],
            ),
            entry_data(
                "arc",
                "project",
                outcome="ongoing",
                relations=[_relation("part_of", "saga", target_type="project")],
            ),
        ],
    )

    with pytest.raises(BundleValidationError) as caught:
        _import_service(repos).import_from(ROOT)

    assert caught.value.errors == {
        "content/session/moose.md": [
            "Relation to session/draft: A published entry cannot link to a draft.",
            "Relation to project/saga: Inspired_By cannot link to a Project.",
            "Relation to session/other: Unknown relation role 'sequel_of'.",
            "Relation to itself.",
        ],
        "content/session/draft.md": ["Link at least one entry as: Inspired_By."],
        "content/session/other.md": [
            "Relation to session/draft: A published entry cannot link to a draft."
        ],
        "content/project/saga.md": [
            "Relation to project/arc: That makes a loop of containers."
        ],
        "content/project/arc.md": [
            "Relation to project/saga: That makes a loop of containers."
        ],
    }
    repos.transaction.atomic.assert_not_called()


def test_import_refuses_keys_and_slugs_that_are_not_file_names(repos):
    repos.store.read.return_value = _bundle(
        types=[type_data("../x"), type_data()], entries=[entry_data("../../evil")]
    )

    with pytest.raises(BundleValidationError) as caught:
        _import_service(repos).import_from(ROOT)

    assert caught.value.errors == {
        "types/../x.yaml": ["Key '../x' may hold only letters, digits, - and _."],
        "content/session/../../evil.md": [
            "Slug '../../evil' may hold only letters, digits, - and _."
        ],
    }
    repos.transaction.atomic.assert_not_called()


def test_demos_come_from_the_store(repos):
    repos.store.demo_names.return_value = ("dev", "ttrpg")
    repos.store.read_demo.return_value = _bundle(types=[], entries=[])
    service = _import_service(repos)

    assert service.demo_names() == ("dev", "ttrpg")
    assert service.load_demo("dev") == ContentSummaryDTO(types=0, entries=0, assets=0)
    repos.store.read_demo.assert_called_once_with("dev")
    repos.profile.save.assert_not_called()
