"""Tests for round-3 pure logic: expiring items and Trakt scrobble media."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resources.lib import trakt_status


def _default():
    sys.argv = ['plugin://plugin.video.nlziet', '1', '']
    sys.modules.pop('default', None)
    return importlib.import_module('default')


def test_expiring_items_filters_and_sorts():
    d = _default()
    now = 1_000_000
    items = [
        {'id': 'a', 'title': 'Soon', 'expires_at': now + 2 * 86400},
        {'id': 'b', 'title': 'Later', 'expires_at': now + 30 * 86400},   # out of window
        {'id': 'c', 'title': 'Sooner', 'expires_at': now + 1 * 86400},
        {'id': 'd', 'title': 'Gone', 'expires_at': now - 86400},         # already gone
        {'id': 'e', 'title': 'No date'},
    ]
    rows = d._expiring_items(items, now=now, days=14)
    assert [r['id'] for r in rows] == ['c', 'a']
    assert rows[0]['expires_days'] == 1


def test_expiring_items_dedupes():
    d = _default()
    now = 1_000_000
    items = [{'id': 'a', 'expires_at': now + 86400}, {'id': 'a', 'expires_at': now + 2 * 86400}]
    assert len(d._expiring_items(items, now=now)) == 1


def test_parse_expiry_iso_and_epoch():
    d = _default()
    assert d._parse_expiry(1700000000) == 1700000000.0
    assert d._parse_expiry('2026-01-01T00:00:00Z') is not None
    assert d._parse_expiry('') is None
    assert d._parse_expiry(None) is None


def test_scrobble_media_episode():
    media = trakt_status.scrobble_media('My Show', '1', '3', 'Episode title')
    assert media == {'show': {'title': 'My Show'}, 'episode': {'season': 1, 'number': 3}}


def test_scrobble_media_movie():
    media = trakt_status.scrobble_media('', None, None, 'A Film', year='2020')
    assert media == {'movie': {'title': 'A Film', 'year': 2020}}


def test_scrobble_media_none():
    assert trakt_status.scrobble_media('', None, None, '') is None
