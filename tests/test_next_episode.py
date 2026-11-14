"""Tests for next-episode selection used by Up Next (NLZiet library)."""
from resources.lib import library as library_mod


class Store:
    def __init__(self, series):
        self._series = series

    def section(self, kind):
        return self._series if kind == 'series' else {}


def test_next_library_episode_picks_the_following_one():
    store = Store({'s1': {'title': 'Show', 'thumb': 't',
                          'episodes': {'e1': [1, 1], 'e2': [1, 2], 'e3': [1, 3]}}})
    result = library_mod.next_library_episode(store, 'e1')
    assert result is not None
    series_id, entry, current, next_id, following = result
    assert series_id == 's1'
    assert current == (1, 1)
    assert next_id == 'e2'
    assert following == (1, 2)


def test_next_library_episode_crosses_season_boundary():
    store = Store({'s1': {'episodes': {'a': [1, 1], 'b': [2, 1]}}})
    _s, _e, _c, next_id, following = library_mod.next_library_episode(store, 'a')
    assert next_id == 'b'
    assert following == (2, 1)


def test_next_library_episode_last_episode_returns_none():
    store = Store({'s1': {'episodes': {'a': [1, 1], 'b': [1, 2]}}})
    assert library_mod.next_library_episode(store, 'b') is None


def test_next_library_episode_unknown_returns_none():
    store = Store({'s1': {'episodes': {'a': [1, 1]}}})
    assert library_mod.next_library_episode(store, 'zzz') is None


def test_next_from_surrounding_list():
    data = {'episodes': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]}
    assert library_mod.next_from_surrounding(data, 'b') == {'id': 'c'}


def test_next_from_surrounding_next_key():
    data = {'next': {'content': {'id': 'z', 'title': 'Next'}}}
    assert library_mod.next_from_surrounding(data, 'y')['id'] == 'z'


def test_next_from_surrounding_last_returns_none():
    data = {'episodes': [{'id': 'a'}, {'id': 'b'}]}
    assert library_mod.next_from_surrounding(data, 'b') is None
