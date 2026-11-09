from typing import override

from django.db import Error, connection

from lapidarium.pacts.db import DatabaseProbeProtocol


def _ping() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


class DjangoDatabaseProbe(DatabaseProbeProtocol):
    @override
    def reachable(self) -> bool:
        try:
            _ping()
        except Error:
            return False
        return True
