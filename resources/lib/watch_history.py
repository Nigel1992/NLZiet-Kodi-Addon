"""A small local list of what was played, kept on this device only.

The add-on service writes one line per finished video; the plugin shows it
back as a plain list under "Kijkgeschiedenis". Nothing leaves the device.

Shared by the NLZiet and Videoland add-ons (keep both copies identical).
"""

import json
import os
import time

MAX_ENTRIES = 200


def _load(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def record(path, entry, now=None, limit=MAX_ENTRIES):
    """Add one watched item. ``entry`` needs at least an ``id``.

    The same id within an hour is not added twice (resume counts once).
    Returns the new list.
    """
    if not isinstance(entry, dict) or not entry.get('id'):
        return _load(path)
    now = time.time() if now is None else now
    items = _load(path)
    recent = next((row for row in items
                   if row.get('id') == entry['id'] and now - (row.get('at') or 0) < 3600), None)
    if recent:
        return items
    row = {'id': str(entry['id']), 'title': entry.get('title') or '',
           'subtitle': entry.get('subtitle') or '', 'thumb': entry.get('thumb') or '',
           'media_type': entry.get('media_type') or '', 'at': int(now)}
    items.insert(0, row)
    items = items[:limit]
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as handle:
            json.dump(items, handle, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass
    return items


def entries(path):
    return _load(path)


def clear(path):
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def summary(path, now=None):
    """(count, total titles today) for a short header line."""
    items = _load(path)
    now = time.time() if now is None else now
    today = sum(1 for row in items if now - (row.get('at') or 0) < 86400)
    return len(items), today


def pick_random(episodes, exclude=None, rng=None):
    """A random episode from ``episodes`` (list of dicts with ``id``),
    avoiding ``exclude`` when possible. Returns the dict or None."""
    import random
    pool = [ep for ep in episodes if isinstance(ep, dict) and ep.get('id')]
    if not pool:
        return None
    if exclude and len(pool) > 1:
        pool = [ep for ep in pool if str(ep.get('id')) != str(exclude)] or pool
    return (rng or random).choice(pool)
