import importlib
import sys


def _load_default(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.nlziet', '42', ''])
    sys.modules.pop('default', None)
    return importlib.import_module('default')


def _isolated_api(tmp_path):
    from resources.lib.nlziet_api import NLZietAPI

    api = NLZietAPI(username='user', password='pass')
    api.mylist_file = str(tmp_path / 'mylist.json')
    api.watchlater_file = str(tmp_path / 'watchlater.json')
    api.watchlater_sync_file = str(tmp_path / 'watchlater_sync.json')
    api.myseries_file = str(tmp_path / 'myseries.json')
    api.myseries_sync_file = str(tmp_path / 'myseries_sync.json')
    api.get_access_token = lambda: 'token'
    return api


def _cloud_item(content_id, title='Cloud show', ctype='Series'):
    return {'id': content_id, 'title': title, 'type': ctype, 'thumb': 'img'}


def _patch_cloud(api, cloud_items, calls, tracked_items=None):
    """Patch the watchlist cloud side; tracked series are separate."""
    tracked_items = tracked_items if tracked_items is not None else []

    api.get_cloud_watchlist_items = lambda: [dict(i) for i in cloud_items]
    api.get_cloud_tracked_series = lambda: [dict(i) for i in tracked_items]

    def add(cid):
        calls.append(('add', cid))
        cloud_items.append(_cloud_item(cid, ctype='Episode'))
        return True

    def remove(cid):
        calls.append(('remove', cid))
        cloud_items[:] = [i for i in cloud_items if i['id'] != cid]
        return True

    api.add_to_cloud_watch_later = add
    api.remove_from_cloud_watch_later = remove
    return tracked_items


def _patch_tracked(api, tracked_items, calls):
    def add(cid):
        calls.append(('ts_add', cid))
        tracked_items.append(_cloud_item(cid, ctype='Series'))
        return True

    def remove(cid):
        calls.append(('ts_remove', cid))
        tracked_items[:] = [i for i in tracked_items if i['id'] != cid]
        return True

    api.add_to_cloud_my_series = add
    api.remove_from_cloud_my_series = remove


# --- Watch Later (episodes/movies) -----------------------------------------

def test_sync_merges_both_ways(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 'local_only', 'title': 'Local', 'type': 'Movie'})
    cloud_items = [_cloud_item('m1', 'Cloud movie', 'Movie')]
    calls = []
    _patch_cloud(api, cloud_items, calls)

    summary = api.sync_watch_later()

    assert summary['ok'] is True
    assert summary['added_local'] == 1
    assert summary['added_cloud'] == 1
    assert summary['removed_local'] == 0
    assert summary['removed_cloud'] == 0
    assert sorted(i['id'] for i in api.get_watch_later()) == ['local_only', 'm1']
    assert sorted(i['id'] for i in cloud_items) == ['local_only', 'm1']
    assert api._load_sync_snapshot() == {'local_only', 'm1'}


def test_sync_propagates_local_addition_to_cloud(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 's1', 'title': 'Show', 'type': 'Movie'})
    cloud_items = []
    calls = []
    _patch_cloud(api, cloud_items, calls)

    summary = api.sync_watch_later()

    assert summary['added_cloud'] == 1
    assert summary['added_local'] == 0
    assert [i['id'] for i in cloud_items] == ['s1']
    assert api._load_sync_snapshot() == {'s1'}


def test_sync_propagates_local_removal_to_cloud(tmp_path):
    api = _isolated_api(tmp_path)
    cloud_items = [_cloud_item('s1', 'Show', 'Movie')]
    calls = []
    _patch_cloud(api, cloud_items, calls)
    api._save_sync_snapshot({'s1'})
    calls.clear()

    summary = api.sync_watch_later()

    assert summary['removed_cloud'] == 1
    assert summary['removed_local'] == 0
    assert cloud_items == []
    assert api.get_watch_later() == []
    assert api._load_sync_snapshot() == set()


def test_sync_removes_local_when_removed_from_cloud(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 's1', 'title': 'Show', 'type': 'Movie'})
    cloud_items = [_cloud_item('s1')]
    calls = []
    _patch_cloud(api, cloud_items, calls)
    api._save_sync_snapshot({'s1'})
    cloud_items.clear()
    calls.clear()

    summary = api.sync_watch_later()

    assert summary['removed_local'] == 1
    assert api.get_watch_later() == []
    assert api._load_sync_snapshot() == set()


def test_sync_keeps_channel_items_local(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 'ch1', 'title': 'NPO 1',
                            'type': 'Channel', 'group': 'channels'})
    cloud_items = []
    calls = []
    _patch_cloud(api, cloud_items, calls)
    api._save_sync_snapshot({'ch1'})

    summary = api.sync_watch_later()

    assert summary['added_local'] == 0
    assert summary['added_cloud'] == 0
    assert summary['removed_local'] == 0
    assert sorted(i['id'] for i in api.get_watch_later()) == ['ch1']
    assert cloud_items == []
    assert api._load_sync_snapshot() == set()
    assert calls == []


def test_watch_later_does_not_push_series(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 'show1', 'title': 'Familie Kruys',
                            'type': 'Series', 'group': 'series'})
    cloud_items = []
    calls = []
    _patch_cloud(api, cloud_items, calls)

    summary = api.sync_watch_later()

    # Series are relocated to My Series and never sent to the watchlist.
    assert calls == []
    assert summary['added_cloud'] == 0
    assert cloud_items == []
    assert api.get_watch_later() == []
    assert [i['id'] for i in api.get_my_series()] == ['show1']


def test_sync_pushes_episode_to_watchlist(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 'ep1', 'title': 'Afl. 1',
                            'type': 'Episode', 'group': 'episodes'})
    cloud_items = []
    calls = []
    _patch_cloud(api, cloud_items, calls)

    api.sync_watch_later()

    assert calls == [('add', 'ep1')]


# --- My Series (tracked series) --------------------------------------------

def test_my_series_sync_merges_both_ways(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_my_series({'id': 'local_show', 'title': 'Local', 'type': 'Series'})
    tracked = [_cloud_item('c_show', 'Cloud show', 'Series')]
    calls = []
    _patch_cloud(api, [], calls, tracked_items=tracked)
    _patch_tracked(api, tracked, calls)

    summary = api.sync_my_series()

    assert summary['ok'] is True
    assert summary['added_local'] == 1
    assert summary['added_cloud'] == 1
    assert sorted(i['id'] for i in api.get_my_series()) == ['c_show', 'local_show']
    assert sorted(i['id'] for i in tracked) == ['c_show', 'local_show']
    assert api._load_sync_snapshot(api.myseries_sync_file) == {'c_show', 'local_show'}


def test_my_series_sync_propagates_removal(tmp_path):
    api = _isolated_api(tmp_path)
    tracked = [_cloud_item('c_show', 'Cloud show', 'Series')]
    calls = []
    _patch_cloud(api, [], calls, tracked_items=tracked)
    _patch_tracked(api, tracked, calls)
    api._save_sync_snapshot({'c_show'}, api.myseries_sync_file)

    summary = api.sync_my_series()

    assert summary['removed_cloud'] == 1
    assert tracked == []
    assert api._load_sync_snapshot(api.myseries_sync_file) == set()
    assert ('ts_remove', 'c_show') in calls


def test_my_series_sync_single_change(tmp_path):
    api = _isolated_api(tmp_path)
    tracked = []
    calls = []
    _patch_cloud(api, [], calls, tracked_items=tracked)
    _patch_tracked(api, tracked, calls)

    assert api.sync_single_my_series_change('s1', True) is True
    assert [i['id'] for i in tracked] == ['s1']
    assert api._load_sync_snapshot(api.myseries_sync_file) == {'s1'}


def test_migrate_series_from_watch_later(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 'movie1', 'title': 'Film', 'type': 'Movie'})
    api.add_to_watch_later({'id': 'show1', 'title': 'Serie',
                            'type': 'Series', 'group': 'series'})

    api.migrate_series_from_watch_later()

    assert [i['id'] for i in api.get_watch_later()] == ['movie1']
    assert [i['id'] for i in api.get_my_series()] == ['show1']


# --- Single-change verification --------------------------------------------

def test_sync_single_change_verifies_cloud(tmp_path):
    api = _isolated_api(tmp_path)
    cloud_items = []
    api.get_cloud_watchlist_items = lambda: [dict(i) for i in cloud_items]
    api.get_cloud_tracked_series = lambda: []
    api.add_to_cloud_watch_later = lambda cid: True  # accepted but dropped

    assert api.sync_single_watch_later_change('m1', True) is False
    assert api._load_sync_snapshot() == set()


def test_sync_single_change_records_when_confirmed(tmp_path):
    api = _isolated_api(tmp_path)
    cloud_items = []

    def add(cid):
        cloud_items.append(_cloud_item(cid, 'Item', 'Movie'))
        return True

    api.get_cloud_watchlist_items = lambda: [dict(i) for i in cloud_items]
    api.get_cloud_tracked_series = lambda: []
    api.add_to_cloud_watch_later = add

    assert api.sync_single_watch_later_change('m1', True) is True
    assert api._load_sync_snapshot() == {'m1'}


def test_sync_single_series_change_routes_to_my_series(tmp_path):
    api = _isolated_api(tmp_path)
    tracked = []
    calls = []
    _patch_cloud(api, [], calls, tracked_items=tracked)
    _patch_tracked(api, tracked, calls)

    assert api.sync_single_watch_later_change('show1', True, is_series=True) is True
    assert ('ts_add', 'show1') in calls
    assert api._load_sync_snapshot(api.myseries_sync_file) == {'show1'}


# --- Snapshot / normalization ----------------------------------------------

def test_sync_updates_snapshot_to_merged_state(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 'local_only', 'title': 'Local', 'type': 'Movie'})
    cloud_items = [_cloud_item('m1', 'Cloud movie', 'Movie')]
    calls = []
    _patch_cloud(api, cloud_items, calls)

    api.sync_watch_later()

    assert api._load_sync_snapshot() == {'local_only', 'm1'}


def test_sync_is_idempotent(tmp_path):
    api = _isolated_api(tmp_path)
    cloud_items = [_cloud_item('m1', 'Cloud movie', 'Movie')]
    calls = []
    _patch_cloud(api, cloud_items, calls)

    first = api.sync_watch_later()
    second = api.sync_watch_later()

    assert first['added_local'] == 1
    assert second['added_local'] == 0
    assert second['removed_local'] == 0
    assert second['added_cloud'] == 0
    assert second['removed_cloud'] == 0


def test_sync_not_logged_in(tmp_path):
    api = _isolated_api(tmp_path)
    api.get_access_token = lambda: None
    _patch_cloud(api, [], [])

    summary = api.sync_watch_later()

    assert summary['ok'] is False
    assert summary['reason'] == 'not_logged_in'


def test_sync_cloud_unavailable(tmp_path):
    api = _isolated_api(tmp_path)
    api.get_cloud_watchlist_items = lambda: None

    summary = api.sync_watch_later()

    assert summary['ok'] is False
    assert summary['reason'] == 'cloud_unavailable'


def test_normalize_cloud_item_maps_fields():
    from resources.lib.nlziet_api import NLZietAPI

    api = NLZietAPI(username='u', password='p')
    entry = {
        'content': {
            'id': 'e1',
            'type': 'Episode',
            'title': 'Aflevering',
            'description': 'Beschrijving',
            'seriesId': 'ser1',
            'image': {'portraitUrl': 'port.jpg', 'landscapeUrl': 'land.jpg'},
        }
    }

    item = api._normalize_cloud_item(entry)

    assert item['id'] == 'e1'
    assert item['title'] == 'Aflevering'
    assert item['group'] == 'episodes'
    assert item['posterUrl'] == 'port.jpg'
    assert item['thumb'] == 'land.jpg'
    assert item['seriesId'] == 'ser1'


def test_normalize_cloud_item_requires_id():
    from resources.lib.nlziet_api import NLZietAPI

    api = NLZietAPI(username='u', password='p')
    assert api._normalize_cloud_item({'content': {'title': 'No id'}}) is None


def test_update_sync_snapshot_tracks_changes(tmp_path):
    api = _isolated_api(tmp_path)

    api.update_sync_snapshot('s1', True)
    api.update_sync_snapshot('s2', True)
    assert api._load_sync_snapshot() == {'s1', 's2'}

    api.update_sync_snapshot('s1', False)
    assert api._load_sync_snapshot() == {'s2'}


# --- default.py wiring ------------------------------------------------------

def test_default_sync_watch_later_notifies(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)

    class FakeApi:
        def sync_watch_later(self):
            return {
                'ok': True,
                'added_local': 1,
                'added_cloud': 0,
                'removed_local': 0,
                'removed_cloud': 0,
            }

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    assert default.sync_watch_later(notify=True) is True
    assert kodi_recorder.notifications[-1][0] == 'NLZiet'
    assert 'gesynchroniseerd' in kodi_recorder.notifications[-1][1]


def test_default_sync_my_series_notifies(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)

    class FakeApi:
        def sync_my_series(self):
            return {
                'ok': True,
                'added_local': 0,
                'added_cloud': 1,
                'removed_local': 0,
                'removed_cloud': 0,
            }

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    assert default.sync_my_series(notify=True) is True
    assert kodi_recorder.notifications[-1][0] == 'NLZiet'
    assert 'Mijn Series' in kodi_recorder.notifications[-1][1]


def test_default_sync_watch_later_reports_not_logged_in(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)

    class FakeApi:
        def sync_watch_later(self):
            return {'ok': False, 'reason': 'not_logged_in'}

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    assert default.sync_watch_later(notify=True) is False
    assert kodi_recorder.notifications[-1] == (
        'NLZiet', 'Log in om Kijk Later te synchroniseren', 'info'
    )


def test_toggle_propagates_to_cloud_when_sync_enabled(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    default.ADDON.settings['watch_later_sync'] = 'true'
    calls = []
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {}

        def is_in_watch_later(self, item_id):
            return any(i['id'] == item_id for i in state['items'])

        def add_to_watch_later(self, item):
            state['items'].append(item)
            return True

        def remove_from_watch_later(self, item_id):
            state['items'] = [i for i in state['items'] if i['id'] != item_id]
            return True

        def sync_single_watch_later_change(self, content_id, present, is_series=False):
            calls.append(('single', content_id, present, is_series))
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_watch_later('s1', 'Show', 'movie')
    default.toggle_watch_later('s1', 'Show', 'movie')

    assert calls == [('single', 's1', True, False), ('single', 's1', False, False)]


def test_toggle_my_series_propagates_to_cloud(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    default.ADDON.settings['watch_later_sync'] = 'true'
    calls = []
    state = {'items': []}

    class FakeApi:
        def get_series_detail(self, item_id):
            return {}

        def is_in_my_series(self, item_id):
            return any(i['id'] == item_id for i in state['items'])

        def add_to_my_series(self, item):
            state['items'].append(item)
            return True

        def remove_from_my_series(self, item_id):
            state['items'] = [i for i in state['items'] if i['id'] != item_id]
            return True

        def sync_single_my_series_change(self, content_id, present):
            calls.append(('ts_single', content_id, present))
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_my_series('show1', 'Serie', 'series')
    default.toggle_my_series('show1', 'Serie', 'series')

    assert calls == [('ts_single', 'show1', True), ('ts_single', 'show1', False)]


def test_toggle_watch_later_rejects_series(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    default.ADDON.settings['watch_later_sync'] = 'true'
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {}

        def is_in_watch_later(self, item_id):
            return False

        def add_to_watch_later(self, item):
            state['items'].append(item)
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_watch_later('show1', 'Serie', 'series')

    assert state['items'] == []


def test_toggle_propagates_using_legacy_api(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    default.ADDON.settings['watch_later_sync'] = 'true'
    calls = []
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {}

        def is_in_watch_later(self, item_id):
            return any(i['id'] == item_id for i in state['items'])

        def add_to_watch_later(self, item):
            state['items'].append(item)
            return True

        def remove_from_watch_later(self, item_id):
            state['items'] = [i for i in state['items'] if i['id'] != item_id]
            return True

        def add_to_cloud_watch_later(self, content_id):
            calls.append(('cloud_add', content_id))
            return True

        def remove_from_cloud_watch_later(self, content_id):
            calls.append(('cloud_remove', content_id))
            return True

        def update_sync_snapshot(self, content_id, present, snapshot_file=None):
            calls.append(('snapshot', content_id, present))

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_watch_later('s1', 'Show', 'movie')
    default.toggle_watch_later('s1', 'Show', 'movie')

    assert calls == [
        ('cloud_add', 's1'), ('snapshot', 's1', True),
        ('cloud_remove', 's1'), ('snapshot', 's1', False),
    ]


def test_toggle_does_not_touch_cloud_when_sync_disabled(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    default.ADDON.settings['watch_later_sync'] = 'false'
    calls = []
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {}

        def is_in_watch_later(self, item_id):
            return any(i['id'] == item_id for i in state['items'])

        def add_to_watch_later(self, item):
            state['items'].append(item)
            return True

        def sync_single_watch_later_change(self, content_id, present):
            calls.append('single')
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_watch_later('s1', 'Show', 'movie')

    assert calls == []


def test_cloud_list_paginates_past_default_page(tmp_path):
    """The cloud endpoints return 10 items by default; we must page past that."""
    api = _isolated_api(tmp_path)
    seen = []
    total = 1200

    def fake_request(method, content_id=None, path='/v9/watchlist', params=None):
        seen.append(dict(params or {}))
        limit = (params or {}).get('limit', 10)
        offset = (params or {}).get('offset', 0)
        ids = ['id{}'.format(i) for i in range(offset, min(offset + limit, total))]
        entries = [{'content': {'id': cid, 'title': 'T' + cid, 'type': 'Series'}}
                   for cid in ids]
        return {'data': entries}

    api._watchlist_request = fake_request

    items = api.get_cloud_tracked_series()

    assert len(items) == total
    assert seen[0].get('limit') == 500
    assert seen[-1].get('offset') == 1000
