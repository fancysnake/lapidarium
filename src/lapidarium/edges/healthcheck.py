"""The image's health check: GET /healthz/ under a host the site allows.

A production `ALLOWED_HOSTS` leaves out `localhost`; probing under it answers
400 and marks a working container unhealthy.
"""

from urllib.request import Request, urlopen

from django.conf import settings


def probe_host(allowed_hosts: list[str]) -> str:
    """Return the first allowed host, bare of a leading dot; `localhost` for `*`."""
    host = allowed_hosts[0].removeprefix(".") if allowed_hosts else "*"
    return "localhost" if host == "*" else host


def main() -> None:
    # urlopen raises on a 503, so a lost database fails the check.
    headers = {"Host": probe_host(settings.ALLOWED_HOSTS)}
    with urlopen(Request("http://localhost:8000/healthz/", headers=headers), timeout=5):
        pass


if __name__ == "__main__":
    main()
