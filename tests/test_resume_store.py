"""Tests for the local resume store (continue watching)."""
from resources.lib import resume_store as rs


def test_save_and_get(tmp_path):
    p = str(tmp_path / 'r.json')
    assert rs.save(p, 'a', position=600, total=3000, now=1000) is True
    assert rs.get(p, 'a') == (600.0, 3000.0)


def test_save_too_early_not_stored(tmp_path):
    p = str(tmp_path / 'r.json')
    assert rs.save(p, 'a', position=10, total=3000, now=1000) is False
    assert rs.get(p, 'a') is None


def test_save_near_end_clears(tmp_path):
    p = str(tmp_path / 'r.json')
    rs.save(p, 'a', position=600, total=3000, now=1000)
    assert rs.save(p, 'a', position=2990, total=3000, now=2000) is False   # finished
    assert rs.get(p, 'a') is None


def test_clear(tmp_path):
    p = str(tmp_path / 'r.json')
    rs.save(p, 'a', position=600, total=3000, now=1000)
    assert rs.clear(p, 'a') is True
    assert rs.get(p, 'a') is None


def test_prune_old(tmp_path):
    p = str(tmp_path / 'r.json')
    rs.save(p, 'old', position=600, total=3000, now=1000)
    rs.save(p, 'new', position=600, total=3000, now=1000 + 200 * 86400)     # far later → prunes old
    assert rs.get(p, 'old') is None
    assert rs.get(p, 'new') is not None


def test_format_time():
    assert rs.format_time(65) == '1:05'
    assert rs.format_time(3725) == '1:02:05'
    assert rs.format_time(-5) == '0:00'


def test_save_rejects_bad_values(tmp_path):
    p = str(tmp_path / 'r.json')
    assert rs.save(p, 'a', position='x', total='y', now=1000) is False
    assert rs.save(p, '', position=600, total=3000, now=1000) is False
