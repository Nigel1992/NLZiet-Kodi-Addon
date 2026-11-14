"""Clearlogos for titles that are not in the library, without slowing lists.

Browsing never waits for TMDb: a list shows the logos it already knows and
puts unknown titles in a small queue file. The background service looks those
up a few at a time (TMDb, needs the TMDb key) and stores the result, so the
next time the list is opened the logos are there.

Shared by the NLZiet and Videoland add-ons (keep both copies identical).
"""

import json
import os
import time

from . import metadata

FOUND_TTL = 90 * 24 * 3600
MISS_TTL = 30 * 24 * 3600
MAX_QUEUE = 300


def _key(kind, title, year=None):
    key = '{}:{}'.format('movie' if kind == 'movie' else 'series', metadata.normalize_title(title))
    return key + ':{}'.format(year) if kind == 'movie' and year else key


def _read(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception:
        return default


def _write(path, data):
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        temporary = path + '.tmp'
        with open(temporary, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False)
        os.replace(temporary, path)
    except Exception:
        pass


class LogoCache:
    def __init__(self, folder, now=None):
        self.logos_path = os.path.join(folder, 'logos.json')
        self.queue_path = os.path.join(folder, 'logo_queue.json')
        self.now = now or time.time
        self._logos = None
        self._new = {}

    def _load(self):
        if self._logos is None:
            data = _read(self.logos_path, {})
            self._logos = data if isinstance(data, dict) else {}
        return self._logos

    def get(self, kind, title, year=None):
        """The logo url, '' when TMDb has none, or None (queued for lookup)."""
        if not title:
            return None
        key = _key(kind, title, year)
        entry = self._load().get(key)
        if isinstance(entry, dict) and entry.get('expires', 0) > self.now():
            return entry.get('url') or ''
        self._new[key] = [kind, title, year]
        return None

    def flush(self):
        """Write the titles this list asked about to the queue."""
        if not self._new:
            return
        queue = _read(self.queue_path, {})
        if not isinstance(queue, dict):
            queue = {}
        for key, value in self._new.items():
            if len(queue) >= MAX_QUEUE:
                break
            queue.setdefault(key, value)
        _write(self.queue_path, queue)
        self._new = {}

    def process(self, enricher, limit=15, should_stop=None):
        """Look up queued titles (service). Returns the number looked up."""
        queue = _read(self.queue_path, {})
        if not isinstance(queue, dict) or not queue:
            return 0
        if enricher is None or not enricher.tmdb_key:
            # Without a TMDb key there is nothing to look up: drop the queue.
            try:
                os.remove(self.queue_path)
            except OSError:
                pass
            return 0
        logos = self._load()
        done = 0
        for key in list(queue)[:limit]:
            if should_stop is not None and should_stop():
                break
            kind, title, year = (list(queue[key]) + [None, None, None])[:3]
            try:
                url = enricher.logo_for(kind, title, year)
            except Exception:
                url = None
            if url is None:
                break  # TMDb unreachable: keep the queue and try again later
            queue.pop(key)
            logos[key] = {'url': url, 'expires': self.now() + (FOUND_TTL if url else MISS_TTL)}
            done += 1
        _write(self.logos_path, logos)
        if queue:
            _write(self.queue_path, queue)
        else:
            try:
                os.remove(self.queue_path)
            except OSError:
                pass
        return done
