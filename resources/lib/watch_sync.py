"""Send "watched" back to the streaming service.

Two moments count as "watched":

* you watch a video to (almost) the end in Kodi, or
* you choose "Mark as watched" / "Mark as unwatched" on a title in Kodi's
  own library.

The add-on's background service notices both and asks the plugin to tell
the service (NLZiet: ``/v7/content/watched``; Videoland: its progress API).
This module holds the pure logic, so it can be tested without Kodi.

Shared by the NLZiet and Videoland add-ons (keep both copies identical).
"""

import json
import time
from urllib.parse import parse_qsl, urlparse

WATCHED_SHARE = 0.9          # 90% seen counts as watched
REPEAT_SECONDS = 600         # the same message is not sent twice in 10 minutes
PLAYING_PROPERTY = '{}.now_playing'


def plugin_params(path, addon_id):
    """Query parameters of ``plugin://<addon_id>/?...``, else ``{}``."""
    text = str(path or '').strip()
    prefix = 'plugin://' + addon_id
    if not text.startswith(prefix):
        return {}
    return dict(parse_qsl(urlparse(text).query))


def library_update(data):
    """Read a ``VideoLibrary.OnUpdate`` notification.

    Returns ``(media_type, dbid, watched)`` when the watched state changed
    (playcount present), else ``None``. Library scans ("added") are ignored.
    """
    try:
        info = json.loads(data) if isinstance(data, str) else dict(data or {})
    except (TypeError, ValueError):
        return None
    if not isinstance(info, dict) or info.get('added') or 'playcount' not in info:
        return None
    item = info.get('item') or {}
    media_type = item.get('type')
    dbid = item.get('id')
    if media_type not in ('episode', 'movie') or not isinstance(dbid, int):
        return None
    try:
        watched = int(info.get('playcount') or 0) > 0
    except (TypeError, ValueError):
        return None
    return media_type, dbid, watched


def playing_value(key, now=None):
    """Value the plugin leaves for the service when it starts a video."""
    return '{}|{}'.format(key, int(now if now is not None else time.time()))


def parse_playing(value, now=None, max_age=120):
    """The key from :func:`playing_value`, or '' when missing or too old
    (a note from a video that never started must not stick to the next one)."""
    text = str(value or '')
    key, _sep, stamp = text.rpartition('|')
    if not key:
        return ''
    try:
        age = (now if now is not None else time.time()) - int(stamp)
    except ValueError:
        return ''
    return key if 0 <= age <= max_age else ''


def watched_enough(position, total, share=WATCHED_SHARE):
    try:
        return float(total) > 0 and float(position) / float(total) >= share
    except (TypeError, ValueError, ZeroDivisionError):
        return False


class Repeats:
    """Remembers what was sent recently, so one action is sent once."""

    def __init__(self, seconds=REPEAT_SECONDS, clock=time.time):
        self.seconds = seconds
        self.clock = clock
        self.sent = {}

    def fresh(self, key, watched):
        now = self.clock()
        self.sent = {k: v for k, v in self.sent.items() if now - v[1] < self.seconds}
        previous = self.sent.get(key)
        if previous and previous[0] == watched:
            return False
        self.sent[key] = (watched, now)
        return True


class PlaybackWatch:
    """Follows one video the add-on started and says if it was finished."""

    def __init__(self):
        self.key = None
        self.position = 0.0
        self.total = 0.0

    def start(self, key):
        self.key = key or None
        self.position = 0.0
        self.total = 0.0

    def sample(self, position, total):
        if self.key and position is not None and position >= 0:
            self.position = float(position)
            if total and total > 0:
                self.total = float(total)

    def finish(self):
        """Return the key when the video counts as watched, then forget it."""
        key, done = self.key, watched_enough(self.position, self.total)
        self.key = None
        return key if done else None


# ------------------------------------------------------------- Kodi side --

def strm_target(path, read):
    """The plugin URL inside a ``.strm`` file (``read(path)`` returns text)."""
    text = str(path or '')
    if text.startswith('plugin://'):
        return text
    if not text.lower().endswith('.strm'):
        return ''
    try:
        content = read(text) or ''
    except Exception:
        return ''
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            return line
    return ''


def library_file(media_type, dbid, rpc):
    """File path of a library item through JSON-RPC (``rpc(method, params)``)."""
    method, key, field = (('VideoLibrary.GetEpisodeDetails', 'episodeid', 'episodedetails')
                          if media_type == 'episode' else
                          ('VideoLibrary.GetMovieDetails', 'movieid', 'moviedetails'))
    try:
        result = rpc(method, {key: dbid, 'properties': ['file']}) or {}
        return (result.get(field) or {}).get('file') or ''
    except Exception:
        return ''
