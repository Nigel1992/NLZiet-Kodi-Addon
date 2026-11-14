"""Push the streaming service's own resume points into the Kodi library.

When you watch an episode on your phone, tablet or TV app, the service knows
how far you got, but Kodi does not. The skin's "Afleveringen die je kijkt" row
reads the Kodi library, so those cross-device episodes never show up there
until you open them again in Kodi.

This module turns a watch position the service reports into a Kodi resume
point (``VideoLibrary.SetEpisodeDetails`` / ``SetMovieDetails``), so an episode
you started elsewhere also appears in Kodi's continue-watching rows.

Only the add-on's own library items are touched: every ``.strm`` the add-on
writes carries ``inlib=1`` and the service content id in its plugin URL, so an
item is matched by reading that id straight back out of the file path. No TMDb
lookup is needed.

Pure logic only, so it can be tested without Kodi. Shared by the NLZiet and
Videoland add-ons (keep both copies identical).
"""

import math
from urllib.parse import parse_qsl, urlparse

# A position below this (seconds) is not really "in progress" yet.
MIN_RESUME = 60
# Within this many seconds of the end counts as finished, not as a resume point.
END_MARGIN = 120
# Don't rewrite a resume point that already sits this close to the new one.
NEAR = 30

# Field names different services use for a playback position (seconds).
POSITION_KEYS = (
    'tcresume', 'position', 'bookmark', 'offset', 'resumeposition',
    'resumetime', 'resumepoint', 'secondswatched', 'playbackposition',
    'timecode', 'currenttime', 'elapsed', 'progressseconds', 'watchedseconds',
    'stoptime', 'lastposition',
)
# Field names for the total length (seconds).
DURATION_KEYS = (
    'duration', 'length', 'runtime', 'totalduration', 'totaltime', 'tctotal',
    'videoduration', 'durationseconds', 'totallength',
)
# Field names for a 0..1 fraction or 0..100 percentage watched.
PERCENT_KEYS = (
    'progress', 'percentage', 'percent', 'completion', 'watchedpercentage',
    'percentwatched', 'ratio', 'progresspercentage',
)


def plugin_content_id(text, addon_id, param):
    """Service content id from a plugin URL, or ``None``.

    ``text`` may be the plugin URL itself (when Kodi reports the resolved link
    as an item's ``file``) or the contents of a ``.strm`` file. Only our own
    managed items count: the URL must be for ``addon_id`` and carry ``inlib=1``.
    ``param`` is the query key that holds the id (``id`` for NLZiet,
    ``video_id`` for Videoland).
    """
    text = str(text or '')
    marker = 'plugin://' + str(addon_id)
    start = text.find(marker)
    if start == -1:
        return None
    url = text[start:].splitlines()[0].strip()
    try:
        query = dict(parse_qsl(urlparse(url).query))
    except (ValueError, TypeError):
        return None
    if query.get('inlib') != '1':
        return None
    value = query.get(param)
    return str(value) if value else None


def is_strm(file_path):
    """True when a library item's ``file`` points at a ``.strm`` on disk (so
    its plugin URL has to be read from the file itself)."""
    return str(file_path or '').lower().endswith('.strm')


def _number(value):
    """A finite, non-boolean number from ``value``, or ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return None
    return None


def extract_progress(entry):
    """Best-effort ``(position_seconds, duration_seconds)`` from a service
    continue-watching entry whose exact shape is not known in advance.

    Scans the entry and its nested dictionaries for a position, a duration and
    a percentage under the common field names above. Returns ``None`` when
    nothing usable is found. ``duration`` may be ``0`` when only a position is
    known; the caller then falls back to the library runtime.
    """
    position = duration = percent = None
    stack = [entry]
    visited = 0
    while stack and visited < 100:
        node = stack.pop()
        visited += 1
        if not isinstance(node, dict):
            continue
        for key, value in node.items():
            if isinstance(value, dict):
                stack.append(value)
                continue
            low = str(key).lower()
            number = _number(value)
            if number is None:
                continue
            if position is None and low in POSITION_KEYS and number > 0:
                position = number
            elif duration is None and low in DURATION_KEYS and number > 0:
                duration = number
            elif percent is None and low in PERCENT_KEYS and 0 < number <= 100:
                percent = number
    if position and duration:
        return int(position), int(duration)
    if percent and duration:
        fraction = percent / 100.0 if percent > 1 else percent
        return int(duration * fraction), int(duration)
    if position:
        return int(position), 0
    return None


def _total(item, duration):
    """The length (seconds) to store with a resume point: the service duration
    when known, otherwise the library runtime."""
    for value in (duration, (item.get('runtime') or 0)):
        number = _number(value)
        if number and number > 0:
            return int(number)
    return 0


def resume_call(method, id_name, item, position, duration, lastplayed=None):
    """A JSON-RPC ``(method, params)`` to store this resume point, or ``None``.

    ``item`` is a library row with ``runtime`` and the current ``resume``.
    Returns ``None`` when the position is too small, too close to the end, or
    barely different from what Kodi already has (so nothing churns).

    ``lastplayed`` (``'YYYY-MM-DD HH:MM:SS'``) is stored alongside the resume
    point so the item sorts to the front of the skin's continue-watching row,
    which orders by last-played. It is only written when the position actually
    changes, so a once-an-hour sync does not keep shuffling Home.
    """
    total = _total(item, duration)
    position = _number(position)
    if position is None:
        return None
    position = int(position)
    if total <= 0 or position < MIN_RESUME or position >= total - END_MARGIN:
        return None
    current = (item.get('resume') or {}).get('position') or 0
    if abs(current - position) < NEAR:
        return None
    params = {id_name: item[id_name], 'resume': {'position': position, 'total': total}}
    if lastplayed:
        params['lastplayed'] = str(lastplayed)
    return method, params


def build_calls(items, positions, id_name, method, cid_for, lastplayed=None):
    """Resume JSON-RPC calls for the library ``items`` that the service has a
    position for.

    * ``items``: rows from ``VideoLibrary.GetEpisodes`` / ``GetMovies`` with
      ``file``, ``runtime``, ``resume`` and ``<id_name>``.
    * ``positions``: ``{str(content_id): (position_seconds, duration_seconds)}``.
    * ``id_name``: ``'episodeid'`` or ``'movieid'``.
    * ``method``: the matching ``Set...Details`` method.
    * ``cid_for``: callable mapping one item to its service content id (or
      ``None``). The caller supplies this so it can read a ``.strm`` file when
      Kodi reports a path rather than the plugin URL.
    * ``lastplayed``: optional ``'YYYY-MM-DD HH:MM:SS'`` stored with every
      changed item, so freshly-progressed episodes sort to the front.
    """
    calls = []
    for item in items or []:
        cid = cid_for(item)
        if not cid or cid not in positions:
            continue
        position, duration = positions[cid]
        call = resume_call(method, id_name, item, position, duration, lastplayed)
        if call:
            calls.append(call)
    return calls
