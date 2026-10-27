from resources.lib import tvmaze


EPISODES = [
    {'name': 'Party Boy', 'season': 1, 'number': 1},
    {'name': 'Home Is Where You Park It', 'season': 1, 'number': 3},
    {'name': 'Born Alone, Die Together', 'season': 1, 'number': 4},
]


def test_find_episode_matches_title_ignoring_case_and_punctuation():
    assert tvmaze.find_episode(EPISODES, 'home is where you park it') == (1, 3)
    assert tvmaze.find_episode(EPISODES, 'Born alone die together') == (1, 4)


def test_find_episode_accepts_close_spelling_and_rejects_unknown():
    assert tvmaze.find_episode(EPISODES, 'Home is where you parked it') == (1, 3)
    assert tvmaze.find_episode(EPISODES, 'Onbekende aflevering') is None
    assert tvmaze.find_episode(EPISODES, '') is None


def test_lookup_season_episode_uses_search_and_caches(monkeypatch, tmp_path):
    calls = []

    def fake_request(path, params=None):
        calls.append(path)
        if path == '/search/shows':
            return [{'show': {'id': 89610, 'name': 'Blue Murder Motel'}}]
        return [{'name': e['name'], 'season': e['season'], 'number': e['number']} for e in EPISODES]

    monkeypatch.setattr(tvmaze, '_request', fake_request)
    cache = str(tmp_path / 'tvmaze_cache.json')

    assert tvmaze.lookup_season_episode('Blue Murder Motel', 'Born alone, die together', cache) == (1, 4)
    assert tvmaze.lookup_season_episode('Blue Murder Motel', 'Party Boy', cache) == (1, 1)
    assert calls == ['/search/shows', '/shows/89610/episodes']


def test_lookup_season_episode_does_not_cache_when_offline(monkeypatch, tmp_path):
    import time

    def offline(path, params=None):
        monkeypatch.setattr(tvmaze, '_offline_until', time.time() + 300)
        return None

    monkeypatch.setattr(tvmaze, '_request', offline)
    cache = str(tmp_path / 'tvmaze_cache.json')

    assert tvmaze.lookup_season_episode('Blue Murder Motel', 'Party Boy', cache) is None
    assert not (tmp_path / 'tvmaze_cache.json').exists()
