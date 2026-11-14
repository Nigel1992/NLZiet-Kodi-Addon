"""Remembers where you stopped watching each VOD title, on this device only.

The add-on service saves the position when playback stops; the plugin reads it
back when you start the same title again and offers to continue. A title that
was watched (almost) to the end is cleared, so it does not keep resuming.

Pure logic only, so it can be tested without Kodi.
"""

import json
import os
import time

MIN_POSITION = 30          # don't bother remembering the first 30 seconds
END_MARGIN = 30            # within 30s of the end counts as finished
KEEP_DAYS = 90             # forget resume points older than this
MAX_ENTRIES = 400


def _load(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path, data):
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as handle:
            json.dump(data, handle)
        os.replace(tmp, path)
    except OSError:
        pass


def _prune(data, now):
    cutoff = now - KEEP_DAYS * 86400
    kept = {cid: row for cid, row in data.items() if (row.get('at') or 0) >= cutoff}
    if len(kept) > MAX_ENTRIES:
        newest = sorted(kept.items(), key=lambda kv: kv[1].get('at') or 0, reverse=True)[:MAX_ENTRIES]
        kept = dict(newest)
    return kept


def save(path, content_id, position, total, now=None):
    """Store the stop position for ``content_id``. A near-finished video is
    cleared instead. Returns True when a resume point was stored."""
    if not content_id:
        return False
    now = time.time() if now is None else now
    try:
        position = float(position)
        total = float(total)
    except (TypeError, ValueError):
        return False
    data = _load(path)
    cid = str(content_id)
    if position < MIN_POSITION or (total > 0 and position >= total - END_MARGIN):
        data.pop(cid, None)                      # too early, or finished
        _save(path, _prune(data, now))
        return False
    data[cid] = {'position': position, 'total': total, 'at': int(now)}
    _save(path, _prune(data, now))
    return True


def get(path, content_id):
    """(position, total) for ``content_id``, or None."""
    row = _load(path).get(str(content_id))
    if not row:
        return None
    try:
        return float(row['position']), float(row.get('total') or 0)
    except (KeyError, TypeError, ValueError):
        return None


def clear(path, content_id):
    data = _load(path)
    if str(content_id) in data:
        data.pop(str(content_id))
        _save(path, data)
        return True
    return False


def format_time(seconds):
    """A h:mm:ss / mm:ss label for a position in seconds."""
    seconds = int(max(0, seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return '{}:{:02d}:{:02d}'.format(hours, minutes, secs)
    return '{}:{:02d}'.format(minutes, secs)
