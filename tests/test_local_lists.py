import importlib
import sys
import time


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


def test_browse_watch_later_shows_numbering_and_days_in_description(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    expiry = int(time.time()) + 5 * 86400 + 60
    entries = []

    class FakeApi:
        def get_watch_later(self):
            return [
                {
                    'id': 'e1', 'title': 'Sisi', 'type': 'Episode', 'group': 'episodes',
                    'seriesId': 'ser1', 'expires_at': expiry,
                    'description': 'Een oorlog voltrekt zich.',
                    'raw': {'type': 'Episode', 'seriesId': 'ser1', 'seasonId': 'seas1',
                            'subtitle': 'Afl. 6'},
                },
                {'id': 'm1', 'title': 'Film', 'type': 'Movie', 'expires_at': expiry},
            ]

        def get_series_episodes(self, series_id, season_id=None, limit=400, offset=0):
            return [{'id': 'e1', 'episode_number': 1}, {'id': 'e2', 'episode_number': 2}]

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, kwargs.get('info') or {})),
    )

    default.browse_watch_later()

    # The title stays clean; numbering and availability each get their own
    # accent-colored line in the description, above the actual plot text.
    episode_title, episode_info = entries[0]
    assert episode_title == 'Sisi'
    numbering_tag = f'[COLOR {default.NUMBERING_COLOR_RAW}]Afl. 1 van 2[/COLOR]'
    availability_tag = f'[COLOR {default.EXPIRY_COLOR_RAW}]nog 5 dagen beschikbaar[/COLOR]'
    assert episode_info['plot'].split('\n') == [
        numbering_tag, availability_tag, 'Een oorlog voltrekt zich.',
    ]
    assert episode_info['plotoutline'].split('\n') == [
        numbering_tag, availability_tag, 'Een oorlog voltrekt zich.',
    ]

    # Movies only carry the availability line, no numbering.
    movie_title, movie_info = entries[1]
    assert movie_title == 'Film'
    assert movie_info['plot'].split('\n') == [availability_tag]
    assert movie_info['plotoutline'].split('\n') == [availability_tag]


def test_browse_watch_later_numbering_falls_back_to_subtitle(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    entries = []

    class FakeApi:
        def get_watch_later(self):
            return [{
                'id': 'e9', 'title': 'Shetland', 'type': 'Episode', 'group': 'episodes',
                'seriesId': 'serX',
                'raw': {'type': 'Episode', 'seriesId': 'serX', 'seasonId': 'seasX',
                        'subtitle': 'S6:A1 Shetland'},
            }]

        def get_series_episodes(self, series_id, season_id=None, limit=400, offset=0):
            raise RuntimeError('offline')

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, kwargs.get('info') or {})),
    )

    default.browse_watch_later()

    # Without a catalogue we still show the numbering from the subtitle,
    # accent-colored on its own line (no description and no availability).
    colored = f'[COLOR {default.NUMBERING_COLOR_RAW}]Afl. 1[/COLOR]'
    assert entries == [('Shetland', {'plot': colored, 'plotoutline': colored})]


def test_my_list_descriptions_stay_plain(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    expiry = int(time.time()) + 5 * 86400
    entries = []

    class FakeApi:
        def get_my_list(self):
            return [{'id': 'm1', 'title': 'Film', 'type': 'movie', 'expires_at': expiry,
                     'description': 'Gewone beschrijving'}]

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, kwargs.get('info') or {})),
    )

    default.browse_my_list_group('movies')

    # Only Kijk Later is enriched; My List keeps its plain descriptions.
    assert entries == [('Film', {'plot': 'Gewone beschrijving',
                                 'plotoutline': 'Gewone beschrijving'})]


def test_render_list_items_exposes_stored_poster_to_artwork(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    calls = []

    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: calls.append((title, kwargs)),
    )

    default._render_list_items([
        {
            'id': 'e1', 'title': 'Sisi', 'type': 'Episode', 'group': 'episodes',
            'posterUrl': 'https://images.nlziet.nl/poster.jpeg',
            'raw': {'type': 'Episode',
                    'logoUrl': 'https://cdn.nlziet.nl/npo.png',
                    'image': {'landscapeUrl': 'https://images.nlziet.nl/still.jpeg'}},
        },
        {
            'id': 'e2', 'title': 'Zonder poster', 'type': 'Movie', 'group': 'movies',
            'raw': {'type': 'Movie', 'logoUrl': 'https://cdn.nlziet.nl/npo.png'},
        },
    ])

    with_poster = calls[0][1]
    without_poster = calls[1][1]
    # The stored poster is exposed as an explicit portrait key so the channel
    # logo in the raw payload cannot take its portrait slot; the landscape
    # still keeps priority for the landscape/thumb slots.
    assert with_poster['content']['portraitUrl'] == 'https://images.nlziet.nl/poster.jpeg'
    assert with_poster['thumb'] == 'https://images.nlziet.nl/still.jpeg?width=3840'
    # Without any stored poster nothing is invented; the logo stays the
    # pickers' last resort.
    assert 'portraitUrl' not in without_poster['content']
