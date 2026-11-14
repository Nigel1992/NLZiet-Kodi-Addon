"""EPG reminders, kept on this device only.

The user sets a reminder on a future programme in the TV guide; the add-on
service checks the list every minute and shows a Kodi notification when a
programme is about to start. Pure logic only, so it can be tested.
"""

import json
import os
import time

LEAD_SECONDS = 60          # notify about a minute before it starts
KEEP_PAST = 3600           # forget reminders more than an hour past


def _load(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(path, items):
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


def add(path, program_id, title, channel_id, start, channel_name='', now=None):
    """Add a reminder. ``start`` is a unix timestamp. Returns the new list."""
    now = time.time() if now is None else now
    try:
        start = float(start)
    except (TypeError, ValueError):
        return _load(path)
    items = [row for row in _load(path) if str(row.get('program_id')) != str(program_id)]
    items.append({'program_id': str(program_id), 'title': title or '', 'channel_id': str(channel_id or ''),
                  'channel_name': channel_name or '', 'start': start, 'notified': False})
    items = [row for row in items if (row.get('start') or 0) > now - KEEP_PAST]
    _save(path, items)
    return items


def remove(path, program_id):
    items = [row for row in _load(path) if str(row.get('program_id')) != str(program_id)]
    _save(path, items)
    return items


def has(path, program_id):
    return any(str(row.get('program_id')) == str(program_id) for row in _load(path))


def entries(path):
    return _load(path)


def due(path, now=None, lead=LEAD_SECONDS):
    """Reminders whose programme starts within ``lead`` seconds and that were
    not notified yet. Marks them notified and prunes old ones. Returns the due
    rows (so the caller can show one notification each)."""
    now = time.time() if now is None else now
    items = _load(path)
    ready, kept, changed = [], [], False
    for row in items:
        start = row.get('start') or 0
        if start < now - KEEP_PAST:
            changed = True
            continue                      # drop, too old
        if not row.get('notified') and now >= start - lead:
            row['notified'] = True
            changed = True
            ready.append(row)
        kept.append(row)
    if changed:
        _save(path, kept)
    return ready
