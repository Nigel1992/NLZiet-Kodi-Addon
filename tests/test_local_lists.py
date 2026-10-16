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
    return api


def test_watch_later_roundtrip(tmp_path):
    api = _isolated_api(tmp_path)

    assert api.get_watch_later() == []
    assert api.is_in_watch_later('s1') is False

    assert api.add_to_watch_later({'id': 's1', 'title': 'Show', 'type': 'series', 'posterUrl': 'img'})
    assert api.is_in_watch_later('s1') is True
    assert [item['id'] for item in api.get_watch_later()] == ['s1']

    # Adding the same id again is idempotent.
    assert api.add_to_watch_later({'id': 's1', 'title': 'Show', 'type': 'series'}) is True
    assert len(api.get_watch_later()) == 1

    assert api.remove_from_watch_later('s1') is True
    assert api.get_watch_later() == []
    assert api.remove_from_watch_later('s1') is False


def test_my_list_and_watch_later_are_independent(tmp_path):
    api = _isolated_api(tmp_path)

    api.add_to_my_list({'id': 'a', 'type': 'movie'})
    api.add_to_watch_later({'id': 'b', 'type': 'series'})

    assert [item['id'] for item in api.get_my_list()] == ['a']
    assert [item['id'] for item in api.get_watch_later()] == ['b']


def test_browse_watch_later_renders_series_and_movies(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    entries = []

    class FakeApi:
        def get_watch_later(self):
            return [
                {'id': 's1', 'title': 'Show', 'type': 'series', 'posterUrl': 'p1'},
                {'id': 'm1', 'title': 'Film', 'type': 'movie', 'posterUrl': 'p2'},
            ]

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, query)),
    )

    default.browse_watch_later()

    assert entries == [
        ('Show', {'mode': 'series_detail', 'series_id': 's1'}),
        ('Film', {'mode': 'play', 'id': 'm1'}),
    ]
    assert kodi_recorder.ended == [42]


def test_browse_watch_later_empty_notifies(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)

    class FakeApi:
        def get_watch_later(self):
            return []

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.browse_watch_later()

    assert kodi_recorder.notifications == [('NLZiet', 'Kijk Later is leeg', 'info')]
    assert kodi_recorder.ended == [42]


def test_toggle_my_series_adds_then_removes(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {}

        def is_in_my_series(self, item_id):
            return any(item['id'] == item_id for item in state['items'])

        def add_to_my_series(self, item):
            state['items'].append(item)
            return True

        def remove_from_my_series(self, item_id):
            before = len(state['items'])
            state['items'] = [i for i in state['items'] if i['id'] != item_id]
            return len(state['items']) < before

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_my_series('s1', 'Show', 'series', 'img')
    assert [item['id'] for item in state['items']] == ['s1']
    assert kodi_recorder.notifications[-1] == ('NLZiet', 'Toegevoegd aan Mijn Series', 'info')

    default.toggle_my_series('s1', 'Show', 'series', 'img')
    assert state['items'] == []
    assert kodi_recorder.notifications[-1] == ('NLZiet', 'Verwijderd uit Mijn Series', 'info')


def test_toggle_watch_later_adds_then_removes(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {}

        def is_in_watch_later(self, item_id):
            return any(item['id'] == item_id for item in state['items'])

        def add_to_watch_later(self, item):
            state['items'].append(item)
            return True

        def remove_from_watch_later(self, item_id):
            before = len(state['items'])
            state['items'] = [i for i in state['items'] if i['id'] != item_id]
            return len(state['items']) < before

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_watch_later('m1', 'Film', 'movie', 'img')
    assert [item['id'] for item in state['items']] == ['m1']
    assert kodi_recorder.notifications[-1] == ('NLZiet', 'Toegevoegd aan Kijk Later', 'info')

    default.toggle_watch_later('m1', 'Film', 'movie', 'img')
    assert state['items'] == []
    assert kodi_recorder.notifications[-1] == ('NLZiet', 'Verwijderd uit Kijk Later', 'info')


def test_toggle_watch_later_rejects_series(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
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

    default.toggle_watch_later('s1', 'Show', 'series', 'img')

    assert state['items'] == []
    assert kodi_recorder.notifications[-1] == (
        'NLZiet', 'Alleen afleveringen en films kunnen in Kijk Later worden opgeslagen', 'info'
    )


def test_toggle_watch_later_accepts_non_series_movies(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {}

        def is_in_watch_later(self, item_id):
            return any(item['id'] == item_id for item in state['items'])

        def add_to_watch_later(self, item):
            state['items'].append(item)
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    # Watch Later (Kijk Later) accepts any content, not just Series/Films.
    default.toggle_watch_later('c1', 'Clip', 'clip')

    assert [item['id'] for item in state['items']] == ['c1']
    assert state['items'][0]['type'] == 'clip'
    assert kodi_recorder.notifications[-1] == ('NLZiet', 'Toegevoegd aan Kijk Later', 'info')


def test_toggle_my_series_resolves_type_from_detail(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {'raw': {'type': 'Series'}}

        def is_in_my_series(self, item_id):
            return any(item['id'] == item_id for item in state['items'])

        def add_to_my_series(self, item):
            state['items'].append(item)
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    # No type supplied: it must be resolved from the content detail.
    default.toggle_my_series('s1', 'Show', None, 'img')

    assert state['items'][0]['type'] == 'Series'
    assert default._content_group(state['items'][0]) == 'series'


def test_toggle_my_series_uses_series_detail_for_series(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    state = {'items': []}
    calls = []

    class FakeApi:
        def get_content_detail(self, item_id):
            calls.append('content')
            return {}

        def get_series_detail(self, item_id):
            calls.append('series')
            return {
                'title': 'Ghosts',
                'description': 'Een berooid jong stel',
                'thumb': 'landscape.jpg',
                'seasons': [{'id': '1'}],
                'raw': {'content': {'description': 'Een berooid jong stel'}},
            }

        def is_in_my_series(self, item_id):
            return False

        def add_to_my_series(self, item):
            state['items'].append(item)
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_my_series('s1', 'Ghosts', 'series', None)

    assert 'series' in calls
    saved = state['items'][0]
    assert saved['description'] == 'Een berooid jong stel'
    assert saved['thumb'] == 'landscape.jpg'
    assert saved['raw'] == {'content': {'description': 'Een berooid jong stel'}}


def test_toggle_my_series_resolves_series_without_type(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {}

        def get_series_detail(self, item_id):
            return {'title': 'Ghosts', 'description': 'Een serie', 'seasons': [{'id': '1'}]}

        def is_in_my_series(self, item_id):
            return False

        def add_to_my_series(self, item):
            state['items'].append(item)
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_my_series('s1', 'Ghosts', None, None)

    assert default._content_group(state['items'][0]) == 'series'
    assert state['items'][0]['group'] == 'series'
    assert state['items'][0]['description'] == 'Een serie'


def test_backfill_enriches_existing_entries(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 's1', 'title': 'Ghosts', 'type': 'series'})

    assert api.get_watch_later()[0]['description'] == ''

    api.get_series_detail = lambda cid: {
        'title': 'Ghosts',
        'description': 'Een serie',
        'thumb': 'img',
        'raw': {'content': {'description': 'Een serie'}},
        'seasons': [{'id': '1'}],
    }
    api.backfill_watch_later()

    item = api.get_watch_later()[0]
    assert item['description'] == 'Een serie'
    assert item['raw'] == {'content': {'description': 'Een serie'}}


def test_add_to_local_list_preserves_metadata(tmp_path):
    api = _isolated_api(tmp_path)

    api.add_to_watch_later({
        'id': 's1',
        'title': 'Show',
        'type': 'series',
        'description': 'Een mooie serie',
        'thumb': 'landscape.jpg',
        'raw': {'description': 'Een mooie serie', 'type': 'series', 'image': {'landscapeUrl': 'x'}},
    })

    item = api.get_watch_later()[0]
    assert item['description'] == 'Een mooie serie'
    assert item['thumb'] == 'landscape.jpg'
    assert item['raw']['description'] == 'Een mooie serie'


def test_toggle_my_series_saves_full_detail(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {
                'title': 'Show',
                'description': 'Een mooie serie',
                'thumb': 'landscape.jpg',
                'raw': {'description': 'Een mooie serie', 'type': 'series'},
            }

        def is_in_my_series(self, item_id):
            return any(item['id'] == item_id for item in state['items'])

        def add_to_my_series(self, item):
            state['items'].append(item)
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.toggle_my_series('s1', 'Show', 'series', None)

    saved = state['items'][0]
    assert saved['description'] == 'Een mooie serie'
    assert saved['thumb'] == 'landscape.jpg'
    assert saved['raw']['type'] == 'series'


def test_render_list_items_passes_plot_info(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    captured = {}

    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: captured.update(kwargs) or captured.update({'title': title}),
    )

    default._render_list_items([
        {'id': 's1', 'title': 'Show', 'type': 'series', 'description': 'Een mooie serie'},
    ])

    assert captured['info']['plot'] == 'Een mooie serie'


def test_toggle_mylist_accepts_any_content(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    state = {'items': []}

    class FakeApi:
        def get_content_detail(self, item_id):
            return {}

        def is_in_my_list(self, item_id):
            return any(item['id'] == item_id for item in state['items'])

        def add_to_my_list(self, item):
            state['items'].append(item)
            return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    # My List accepts any content, e.g. a live channel.
    default.toggle_mylist('c1', 'Kanaal 1', 'channel')

    assert [item['id'] for item in state['items']] == ['c1']
    assert state['items'][0]['type'] == 'channel'
    assert kodi_recorder.notifications[-1] == ('NLZiet', 'Toegevoegd aan Mijn lijst (alleen Kodi)', 'info')


def test_render_list_items_marks_channels_live(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    captured = {}

    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: captured.update({'title': title, 'query': query}),
    )

    default._render_list_items([
        {'id': 'c1', 'title': 'Kanaal 1', 'type': 'channel'},
    ])

    assert captured['query'] == {'mode': 'play', 'id': 'c1', 'fmt': 'live'}


def test_main_menu_lists_my_list_and_watch_later_when_logged_in(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    entries = []

    monkeypatch.setattr(default, '_check_and_handle_token_expiry', lambda: True)
    monkeypatch.setattr(default, '_is_logged_in', lambda: True)
    monkeypatch.setattr(default.os.path, 'exists', lambda path: False)
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, query)),
    )

    default.main_menu()

    modes = [query.get('mode') for _, query in entries]
    assert 'my_list' in modes
    assert 'watch_later' in modes
    assert 'my_series' in modes
    assert 'my_movies' not in modes
