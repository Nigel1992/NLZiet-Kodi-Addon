"""Season and episode lookup via the TVmaze API (free, no API key)."""

import difflib
import json
import os
import re
import time
import urllib.parse
import urllib.request


BASE_URL = 'https://api.tvmaze.com'
TIMEOUT = 10
CACHE_TTL = 7 * 24 * 3600
RETRY_AFTER = 300

_offline_until = 0


def normalize_title(text):
    return re.sub(r'[^0-9a-z]+', ' ', str(text or '').casefold()).strip()


def _get_json(path, params=None):
    global _offline_until
    url = BASE_URL + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={'User-Agent': 'plugin.video.nlziet'})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def _request(path, params=None):
    """Return the JSON payload, or None when TVmaze is unreachable (retried later)."""
    global _offline_until
    if time.time() < _offline_until:
        return None
    try:
        return _get_json(path, params)
    except Exception:
        _offline_until = time.time() + RETRY_AFTER
        return None


def find_show_id(series_title):
    wanted = normalize_title(series_title)
    if not wanted:
        return None
    hits = _request('/search/shows', {'q': series_title}) or []
    for hit in hits:
        show = hit.get('show') or {}
        if normalize_title(show.get('name')) == wanted:
            return show.get('id')
    return None


def find_episode(episodes, episode_title):
    """Return (season, number) of the episode whose name matches episode_title."""
    wanted = normalize_title(episode_title)
    if not wanted:
        return None
    by_name = {}
    for episode in episodes:
        by_name.setdefault(normalize_title(episode.get('name')), episode)
    match = by_name.get(wanted)
    if match is None:
        close = difflib.get_close_matches(wanted, [name for name in by_name if name], n=1, cutoff=0.85)
        match = by_name.get(close[0]) if close else None
    if not match or not match.get('season') or not match.get('number'):
        return None
    return int(match['season']), int(match['number'])


def _load_cache(cache_path):
    try:
        with open(cache_path, 'r', encoding='utf-8') as handle:
            return json.load(handle) or {}
    except Exception:
        return {}


def _save_cache(cache_path, cache):
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as handle:
            json.dump(cache, handle)
    except Exception:
        pass


def lookup_season_episode(series_title, episode_title, cache_path=None):
    """Return (season, number) for an episode of a series, or None when unknown."""
    series_key = normalize_title(series_title)
    if not series_key or not normalize_title(episode_title):
        return None
    cache = _load_cache(cache_path) if cache_path else {}
    entry = cache.get(series_key) if isinstance(cache.get(series_key), dict) else None
    if not entry or time.time() - float(entry.get('ts') or 0) > CACHE_TTL:
        show_id = find_show_id(series_title)
        if _offline_until > time.time():
            return None
        if show_id is None:
            entry = {'ts': time.time(), 'show_id': None, 'episodes': []}
        else:
            episodes = _request('/shows/{}/episodes'.format(int(show_id)))
            if episodes is None:
                return None
            entry = {'ts': time.time(), 'show_id': show_id, 'episodes': [
                {'name': ep.get('name'), 'season': ep.get('season'), 'number': ep.get('number')}
                for ep in episodes if isinstance(ep, dict)
            ]}
        cache[series_key] = entry
        if cache_path:
            _save_cache(cache_path, cache)
    return find_episode(entry.get('episodes') or [], episode_title)
