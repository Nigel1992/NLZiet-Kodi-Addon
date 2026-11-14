"""Tests for the EPG reminders module."""
from resources.lib import reminders


def test_add_and_has(tmp_path):
    p = str(tmp_path / 'r.json')
    reminders.add(p, 'p1', 'Show', 'ch1', start=2000, channel_name='NPO1', now=1000)
    assert reminders.has(p, 'p1')
    assert not reminders.has(p, 'p2')


def test_add_replaces_same_program(tmp_path):
    p = str(tmp_path / 'r.json')
    reminders.add(p, 'p1', 'Show', 'ch1', start=2000, now=1000)
    reminders.add(p, 'p1', 'Show v2', 'ch1', start=3000, now=1000)
    rows = reminders.entries(p)
    assert len(rows) == 1 and rows[0]['start'] == 3000


def test_due_fires_within_lead(tmp_path):
    p = str(tmp_path / 'r.json')
    reminders.add(p, 'p1', 'Show', 'ch1', start=2000, now=1000)
    assert reminders.due(p, now=1900, lead=60) == []          # too early
    ready = reminders.due(p, now=1950, lead=60)               # within a minute
    assert len(ready) == 1 and ready[0]['program_id'] == 'p1'
    assert reminders.due(p, now=1955, lead=60) == []          # already notified


def test_due_prunes_old(tmp_path):
    p = str(tmp_path / 'r.json')
    reminders.add(p, 'p1', 'Show', 'ch1', start=1000, now=900)
    reminders.due(p, now=100000)                              # far future → prune
    assert reminders.entries(p) == []


def test_remove(tmp_path):
    p = str(tmp_path / 'r.json')
    reminders.add(p, 'p1', 'Show', 'ch1', start=2000, now=1000)
    reminders.remove(p, 'p1')
    assert not reminders.has(p, 'p1')


def test_add_rejects_bad_start(tmp_path):
    p = str(tmp_path / 'r.json')
    reminders.add(p, 'p1', 'Show', 'ch1', start='nope', now=1000)
    assert reminders.entries(p) == []
