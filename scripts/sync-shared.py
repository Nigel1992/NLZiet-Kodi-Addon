#!/usr/bin/env python3
"""Keep the modules shared by the NLZiet and Videoland add-ons identical.

Usage, from this repository:
    python3 scripts/sync-shared.py ../Videoland-Kodi-Addon          # copy ours there
    python3 scripts/sync-shared.py ../Videoland-Kodi-Addon --check  # only compare

The list below is the single source of truth; tests/test_shared_modules.py
fails when a shared file is edited here without updating SHARED.lock.
"""
import hashlib
import shutil
import sys
from pathlib import Path

SHARED = [
    'resources/lib/metadata.py',
    'resources/lib/library_art.py',
    'resources/lib/errors.py',
    'resources/lib/diagnostics.py',
    'resources/lib/search_filters.py',
    'resources/lib/logo_cache.py',
]
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_lock():
    lines = ['{}  {}'.format(digest(ROOT / name), name) for name in SHARED]
    (ROOT / 'SHARED.lock').write_text('\n'.join(lines) + '\n')


def main(argv):
    if len(argv) < 2:
        write_lock()
        print('SHARED.lock updated')
        return 0
    other = Path(argv[1]).resolve()
    check = '--check' in argv
    different = []
    for name in SHARED:
        mine, theirs = ROOT / name, other / name
        if not theirs.exists() or digest(mine) != digest(theirs):
            different.append(name)
            if not check:
                theirs.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(mine, theirs)
    write_lock()
    if not check:
        shutil.copy2(ROOT / 'SHARED.lock', other / 'SHARED.lock')
    for name in different:
        print(('differs: ' if check else 'copied:  ') + name)
    return 1 if (check and different) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
