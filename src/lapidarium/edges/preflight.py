"""Stop a misconfigured start in one line, before Django prints a traceback."""

import os
import sys
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured


def main() -> None:
    try:
        import_module(os.environ["DJANGO_SETTINGS_MODULE"])
    except ImproperlyConfigured as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
