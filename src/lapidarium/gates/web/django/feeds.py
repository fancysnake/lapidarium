"""Feeds for readers and calendars: what's new as RSS, upcoming entries as iCal."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils.feedgenerator import Rss201rev2Feed
from django.utils.translation import get_language

from lapidarium.gates.web.django import ical
from lapidarium.gates.web.django.paths import entry_path
from lapidarium.gates.web.django.rendering import RootRequest, cached


@cached
def rss(request: RootRequest) -> HttpResponse:
    site = request.services.site.chrome()
    feed = Rss201rev2Feed(
        title=site.profile.name if site.profile else settings.SITE_NAME,
        link=request.build_absolute_uri(reverse("home")),
        description=site.profile.tagline if site.profile else "",
        language=get_language(),
        feed_url=request.build_absolute_uri(),
    )
    for item in request.services.catalogue.whats_new():
        link = (
            request.build_absolute_uri(
                entry_path(
                    site.types, type_key=item.entry.type_key, slug=item.entry.slug
                )
            )
            if item.entry
            else item.url
        )
        feed.add_item(
            title=item.title,
            link=link,
            description=item.type_label,
            pubdate=item.when,
            unique_id=link,
        )
    return HttpResponse(feed.writeString("utf-8"), content_type=feed.content_type)


@cached
def ical_feed(request: RootRequest) -> HttpResponse:
    site = request.services.site.chrome()
    host = request.get_host()
    events = [
        ical.Event(
            uid=f"{card.entry.type_key}-{card.entry.slug}@{host}",
            stamp=card.entry.updated_at,
            start=card.entry.start_at,
            end=card.entry.end_at,
            summary=card.entry.title,
            description=card.entry.summary,
            location=card.entry.location,
            url=request.build_absolute_uri(
                entry_path(
                    site.types, type_key=card.entry.type_key, slug=card.entry.slug
                )
            ),
        )
        for card in request.services.catalogue.upcoming()
        if card.entry.start_at
    ]
    name = site.profile.name if site.profile else settings.SITE_NAME
    return HttpResponse(
        ical.calendar(name, events), content_type="text/calendar; charset=utf-8"
    )
