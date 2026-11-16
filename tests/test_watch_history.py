"""Tests for the shared watch_history module."""
import json
from resources.lib import watch_history as wh


def test_record_and_entries(tmp_path):
    p = str(tmp_path / 'h.json')
    wh.record(p, {'id': 'a', 'title': 'Show', 'subtitle': 'Afl 1'}, now=1000)
    wh.record(p, {'id': 'b', 'title': 'Film'}, now=2000)
    rows = wh.entries(p)
    assert [r['id'] for r in rows] == ['b', 'a']   # newest first
    assert rows[1]['title'] == 'Show'


def test_record_dedupes_within_hour(tmp_path):
    p = str(tmp_path / 'h.json')
    wh.record(p, {'id': 'a'}, now=1000)
    wh.record(p, {'id': 'a'}, now=1000 + 1800)   # same hour → ignored
    assert len(wh.entries(p)) == 1
    wh.record(p, {'id': 'a'}, now=1000 + 7200)   # later → added
    assert len(wh.entries(p)) == 2


def test_record_ignores_without_id(tmp_path):
    p = str(tmp_path / 'h.json')
    wh.record(p, {'title': 'x'}, now=1)
    assert wh.entries(p) == []


def test_record_caps_entries(tmp_path):
    p = str(tmp_path / 'h.json')
    for i in range(10):
        wh.record(p, {'id': str(i)}, now=i * 4000, limit=5)
    assert len(wh.entries(p)) == 5


def test_clear(tmp_path):
    p = str(tmp_path / 'h.json')
    wh.record(p, {'id': 'a'}, now=1)
    assert wh.clear(p) is True
    assert wh.entries(p) == []


def test_summary(tmp_path):
    p = str(tmp_path / 'h.json')
    wh.record(p, {'id': 'a'}, now=1000)
    total, today = wh.summary(p, now=1000)
    assert total == 1 and today == 1


def test_pick_random_avoids_exclude():
    eps = [{'id': '1'}, {'id': '2'}, {'id': '3'}]
    import random
    picked = {wh.pick_random(eps, exclude='1', rng=random.Random(s)).get('id') for s in range(30)}
    assert '1' not in picked


def test_pick_random_single_returns_it():
    assert wh.pick_random([{'id': '1'}], exclude='1')['id'] == '1'


def test_pick_random_empty():
    assert wh.pick_random([]) is None
