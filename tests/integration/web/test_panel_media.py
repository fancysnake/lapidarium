"""The content panel's Media page: staff list and upload files, and describe them."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from lapidarium.links.db.django.models import MediaAsset
from lapidarium.specs import PANEL_PAGE_SIZE

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05"
    b"\xfe\x02\xfe\xa75\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(name="staff")
def staff_fixture(browser):
    browser.force_login(
        get_user_model().objects.create_user("helper", password="pw", is_staff=True)
    )
    return browser


def _upload(client, name="cover.png", *, alt="A moose"):
    return client.post(
        "/panel/media/",
        {"file": SimpleUploadedFile(name, _PNG), "alt": alt, "upload": ""},
    )


def test_the_media_page_is_for_staff(browser):
    response = browser.get("/panel/media/")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


def test_the_media_page_of_a_site_without_files_says_so(staff):
    response = staff.get("/panel/media/")

    assert response.status_code == HTTPStatus.OK
    files = response.context["files"]
    assert (files.rows, files.page, files.pages, files.total) == ((), 1, 1, 0)
    assert not response.context["saved"]
    assert not response.context["upload"].is_bound
    assert not response.context["alt"].is_bound
    assert "No file yet." in response.text
    assert 'aria-current="page">Media</a>' in response.text


def test_the_media_page_lists_the_newest_file_first(staff):
    _upload(staff, "rules.pdf", alt="")
    _upload(staff, "cover.png")

    response = staff.get("/panel/media/")

    rows = response.context["files"].rows
    cover, rules = (MediaAsset.objects.get(alt=alt) for alt in ("A moose", ""))
    assert [(row.path, row.url, row.alt) for row in rows] == [
        (cover.file.name, cover.file.url, "A moose"),
        (rules.file.name, rules.file.url, ""),
    ]
    assert f'<img class="media-thumb" src="{cover.file.url}"' in response.text
    assert '<span class="media-thumb">PDF</span>' in response.text
    assert f'href="{rules.file.url}">rules.pdf</a>' in response.text
    assert 'value="A moose"' in response.text


def test_an_upload_stores_the_file_and_returns_to_the_first_page(staff):
    response = _upload(staff)

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/panel/media/?saved=file"
    asset = MediaAsset.objects.get()
    assert asset.alt == "A moose"
    assert asset.file.name.startswith("assets/")
    assert asset.file.name.endswith("/cover.png")
    assert asset.file.read() == _PNG
    saved = staff.get(response["Location"])
    assert saved.context["saved"] == "file"
    assert "The file is uploaded." in saved.text


def test_an_upload_without_a_file_keeps_the_form(staff):
    response = staff.post("/panel/media/", {"alt": "A moose", "upload": ""})

    assert response.status_code == HTTPStatus.OK
    assert response.context["upload"].errors == {"file": ["This field is required."]}
    assert not response.context["alt"].is_bound
    assert not MediaAsset.objects.exists()


def test_a_row_saves_its_alt_text_and_returns_to_its_page(staff):
    _upload(staff, alt="")
    path = MediaAsset.objects.get().file.name

    response = staff.post("/panel/media/?page=1", {"path": path, "alt": "A moose"})

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"] == "/panel/media/?page=1&saved=alt"
    assert MediaAsset.objects.get().alt == "A moose"
    saved = staff.get(response["Location"])
    assert saved.context["saved"] == "alt"
    assert "The alt text is saved." in saved.text


def test_alt_text_too_long_to_store_is_refused(staff):
    _upload(staff)
    path = MediaAsset.objects.get().file.name

    response = staff.post("/panel/media/", {"path": path, "alt": "a" * 511})

    assert response.status_code == HTTPStatus.OK
    assert response.context["alt"].errors == {
        "alt": ["Ensure this value has at most 510 characters (it has 511)."]
    }
    assert "at most 510 characters" in response.text
    assert MediaAsset.objects.get().alt == "A moose"


def test_a_file_that_is_gone_has_no_alt_text_to_save(staff):
    response = staff.post("/panel/media/", {"path": "assets/gone.png", "alt": "x"})

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_the_media_page_comes_a_page_at_a_time(staff):
    MediaAsset.objects.bulk_create(
        MediaAsset(file=f"assets/{index}.png") for index in range(PANEL_PAGE_SIZE + 1)
    )

    response = staff.get("/panel/media/?page=2")

    files = response.context["files"]
    assert (len(files.rows), files.page, files.pages) == (1, 2, 2)
    assert 'rel="prev"' in response.text


@pytest.mark.parametrize("page", ("3", "0", "x"))
def test_the_media_page_has_no_page_it_cannot_read(staff, page):
    assert staff.get(f"/panel/media/?page={page}").status_code == HTTPStatus.NOT_FOUND
