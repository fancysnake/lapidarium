import pytest

from lapidarium.gates.web.django.embeds import video_embed

YT = "https://www.youtube-nocookie.com/embed/abc_-1?autoplay=1"


@pytest.mark.parametrize(
    ("url", "expected"),
    (
        ("https://www.youtube.com/watch?v=abc_-1", YT),
        ("https://youtube.com/watch?feature=x", ""),
        ("https://youtu.be/abc_-1", YT),
        ("https://m.youtube.com/shorts/abc_-1", YT),
        ("https://www.youtube.com/live/abc_-1", YT),
        ("https://www.youtube.com/@channel", ""),
        (
            "https://vimeo.com/123456",
            "https://player.vimeo.com/video/123456?autoplay=1",
        ),
        ("https://vimeo.com/channels/staff", ""),
        (
            "https://tube.example.org/w/9c9de5e8",
            "https://tube.example.org/videos/embed/9c9de5e8?autoplay=1",
        ),
        (
            "https://tube.example.org/videos/watch/9c9de5e8",
            "https://tube.example.org/videos/embed/9c9de5e8?autoplay=1",
        ),
        ("http://youtu.be/abc", ""),
        ("https:///nohost", ""),
        ("https://example.com/video.mp4", ""),
    ),
)
def test_video_embed(url, expected):
    assert video_embed(url) == expected
