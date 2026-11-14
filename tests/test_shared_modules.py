"""The shared modules must match SHARED.lock (see scripts/sync-shared.py).

When this fails you changed a shared module: copy it to the other add-on with
`python3 scripts/sync-shared.py <path to the other add-on>`, which also
updates SHARED.lock in both repositories.
"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shared_modules_match_the_lock_file():
    entries = [line.split('  ', 1) for line in (ROOT / 'SHARED.lock').read_text().splitlines() if line.strip()]
    assert entries
    for expected, name in entries:
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        assert actual == expected, '{} changed: run scripts/sync-shared.py'.format(name)
