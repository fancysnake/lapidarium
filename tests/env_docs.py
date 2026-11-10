"""What the tests of the configuration docs share about the settings scheme."""

import environ

REQUIRED = "required"
# Read by a library, or with a default the scheme cannot express.
EXTERNAL = {"GOOGLE_APPLICATION_CREDENTIALS", "TRUSTED_PROXY_HOPS"}


def default(cell: str, cast: type) -> object:
    """Parse a documented default the way the settings would read it."""
    if cell == REQUIRED:
        return REQUIRED
    return environ.Env.parse_value("" if cell == "empty" else cell.strip("`"), cast)
