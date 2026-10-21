"""Video links: which video a link names, and the player that plays it."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, quote, urlsplit

_YOUTUBE = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})
_YOUTUBE_PATH = re.compile(r"/(?:embed|shorts|live)/([\w-]+)")
_VIMEO = frozenset({"vimeo.com", "www.vimeo.com"})
_PEERTUBE_PATH = re.compile(r"/(?:w|videos/watch)/([\w-]+)")


def youtube_id(url: str) -> str:
    """Return the id of the YouTube video `url` names, or "" when it names none."""
    parts = urlsplit(url)
    host, path = parts.hostname or "", parts.path
    if host == "youtu.be":
        return path.strip("/")
    if host not in _YOUTUBE:
        return ""
    if path == "/watch":
        return next(iter(parse_qs(parts.query).get("v", [])), "")
    match = _YOUTUBE_PATH.fullmatch(path)
    return match.group(1) if match else ""


def video_embed(url: str) -> str:
    """Return the player address for `url`, or "" for a host with no known player."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.scheme != "https" or not host:
        return ""
    if video := youtube_id(url):
        return f"https://www.youtube-nocookie.com/embed/{quote(video)}?autoplay=1"
    if host in _VIMEO and parts.path.strip("/").isdigit():
        return f"https://player.vimeo.com/video/{parts.path.strip('/')}?autoplay=1"
    if match := _PEERTUBE_PATH.fullmatch(parts.path):
        return f"https://{host}/videos/embed/{match.group(1)}?autoplay=1"
    return ""
