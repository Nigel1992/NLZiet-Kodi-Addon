"""Show Trakt watched status in NLZiet's own menus.

Uses the Trakt account the user already connected in Kodi's official
script.trakt add-on: its saved sign-in and its public client id are read
locally, nothing is asked again and nothing is sent anywhere but Trakt.
The watched lists are cached for 30 minutes.

Matching is by title: films by title (and year when both sides know it),
episodes by show title plus season and episode number. Daily programmes
whose numbering differs from Trakt simply stay unmarked; nothing is guessed.
"""

import json
import os
import re
import time
import unicodedata
import urllib.request

API = 'https://api.trakt.tv'
CACHE_TTL = 30 * 60
TIMEOUT = 15


def normalize(text):
    text = unicodedata.normalize('NFKD', str(text or ''))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return re.sub(r'[^0-9a-z]+', ' ', text.replace('&', ' and ')).strip()


def access_token(trakt_settings):
    """The access token script.trakt saved, or ''."""
    try:
        raw = trakt_settings.getSetting('authorization') or ''
        data = json.loads(raw) if raw else {}
        return str(data.get('access_token') or '')
    except Exception:
        return ''


def _http_get(url, headers):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))


class WatchedIndex:
    def __init__(self, movies=None, episodes=None):
        self.movies = movies or {}      # normalized title -> set of years (None = any)
        self.episodes = episodes or {}  # normalized show title -> set of (season, episode)

    @classmethod
    def from_trakt(cls, movies_payload, shows_payload):
        movies, episodes = {}, {}
        for entry in movies_payload or []:
            movie = entry.get('movie') or {}
            key = normalize(movie.get('title'))
            if key:
                movies.setdefault(key, set()).add(movie.get('year'))
        for entry in shows_payload or []:
            show = entry.get('show') or {}
            key = normalize(show.get('title'))
            if not key:
                continue
            seen = episodes.setdefault(key, set())
            for season in entry.get('seasons') or []:
                for episode in season.get('episodes') or []:
                    if episode.get('plays', 1):
                        seen.add((season.get('number'), episode.get('number')))
        return cls(movies, episodes)

    def to_json(self):
        return {'movies': {k: sorted(y for y in v if y) + ([None] if None in v else []) for k, v in self.movies.items()},
                'episodes': {k: sorted([list(p) for p in v]) for k, v in self.episodes.items()}}

    @classmethod
    def from_json(cls, data):
        movies = {k: set(v) for k, v in (data.get('movies') or {}).items()}
        episodes = {k: {tuple(p) for p in v} for k, v in (data.get('episodes') or {}).items()}
        return cls(movies, episodes)

    def movie_watched(self, title, year=None):
        years = self.movies.get(normalize(title))
        if not years:
            return False
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        return year is None or None in years or year in years

    def episode_watched(self, show_title, season, episode):
        try:
            key = (int(season), int(episode))
        except (TypeError, ValueError):
            return False
        return key in self.episodes.get(normalize(show_title), set())

    def watched(self, metadata):
        """``metadata`` as built for script.trakt (media_type, title, ...)."""
        if not metadata:
            return False
        if metadata.get('media_type') == 'movie':
            return self.movie_watched(metadata.get('title'), metadata.get('year'))
        if metadata.get('media_type') == 'episode':
            return self.episode_watched(metadata.get('showtitle'), metadata.get('season'), metadata.get('episode'))
        return False


def load_index(cache_path, token, client_id, http=None, now=None):
    """Return a WatchedIndex (cached), or None when Trakt is not usable."""
    now = time.time() if now is None else now
    try:
        with open(cache_path, 'r', encoding='utf-8') as handle:
            cached = json.load(handle)
        if cached.get('expires', 0) > now:
            return WatchedIndex.from_json(cached.get('index') or {})
    except Exception:
        pass
    if not token or not client_id:
        return None
    headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': client_id,
               'Authorization': 'Bearer ' + token, 'User-Agent': 'plugin.video.nlziet'}
    get = http or _http_get
    try:
        index = WatchedIndex.from_trakt(get(API + '/sync/watched/movies', headers),
                                        get(API + '/sync/watched/shows', headers))
    except Exception:
        return None
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as handle:
            json.dump({'expires': now + CACHE_TTL, 'index': index.to_json()}, handle)
    except Exception:
        pass
    return index
