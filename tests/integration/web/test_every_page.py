"""Every public page of both demo sets renders, with no undefined variable."""

from http import HTTPStatus

import pytest

from lapidarium.links.db.django.repositories import EntryRepository, EntryTypeRepository

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]

FIXED = ("/", "/about/", "/new/", "/search/?q=e", "/newsletter/", "/contact/")


@pytest.mark.parametrize("demo", ("ttrpg", "dev"))
def test_every_page_of_the_demo_renders(load, demo):
    client = load(demo)

    types = {t.key: t for t in EntryTypeRepository().list_all()}
    entries = EntryRepository().list_published()
    paths = [
        *FIXED,
        *(f"/{t.route}/" for t in types.values()),
        *(
            f"/{types[e.type_key].route}/{e.slug}/"
            for e in entries
            if types[e.type_key].has_detail_page
        ),
    ]

    statuses = {path: client.get(path).status_code for path in paths}

    assert statuses == dict.fromkeys(paths, HTTPStatus.OK)
