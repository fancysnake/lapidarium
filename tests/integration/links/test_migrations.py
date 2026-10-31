import importlib

import pytest
from django.apps import apps
from django.db.migrations.exceptions import IrreversibleError

from lapidarium.links.db.django.models import EntryType
from lapidarium.pacts.content import TypeRole

pytestmark = pytest.mark.django_db


def test_unapplying_the_section_role_waits_until_no_type_has_it():
    migration = importlib.import_module(
        "lapidarium.links.db.django.migrations.0007_type_role_section"
    )
    section = EntryType.objects.create(
        key="wiki", route="wiki", role=TypeRole.CONTAINER_SECTION
    )

    with pytest.raises(IrreversibleError, match="wiki"):
        migration.refuse_while_sections_exist(apps, None)

    section.role = TypeRole.CONTAINER_OUTCOME
    section.save()
    migration.refuse_while_sections_exist(apps, None)
