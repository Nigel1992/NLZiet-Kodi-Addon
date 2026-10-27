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


def test_browse_watch_later_shows_subtitle_from_raw(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    entries = []

    class FakeApi:
        def get_watch_later(self):
            return [{
                'id': 'p1', 'title': 'Love it or List it', 'type': 'Episode', 'group': 'episodes',
                'description': 'Een koppel zoekt een nieuw huis.',
                'raw': {'type': 'Episode', 'subtitle': 'S2:A5 Tweede helft'},
            }]

        def get_series_episodes(self, series_id, season_id=None, limit=400, offset=0):
            raise RuntimeError('offline')

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, kwargs.get('info') or {})),
    )

    default.browse_watch_later()

    title, info = entries[0]
    assert title == 'Love it or List it'
    numbering_tag = f'[COLOR {default.NUMBERING_COLOR_RAW}]Afl. 5[/COLOR]'
    expected = [numbering_tag, 'Tweede helft', 'Een koppel zoekt een nieuw huis.']
    assert info['plot'].split('\n') == expected
    assert info['plotoutline'].split('\n') == expected


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


def test_browse_watch_later_syncs_after_listing_and_refreshes_on_change(monkeypatch, kodi_recorder, tmp_path):
    import xbmc
    default = _load_default(monkeypatch)
    order = []
    builtins = []
    stored = [{'id': 'm1', 'title': 'Film', 'type': 'Movie'}]

    class FakeApi:
        watchlater_sync_file = str(tmp_path / 'watchlater_sync.json')

        def get_watch_later(self):
            return list(stored)

    def fake_sync(notify=True):
        order.append('sync')
        stored.append({'id': 'm2', 'title': 'Nieuw', 'type': 'Movie'})
        return True

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(default, '_watch_later_sync_enabled', lambda: True)
    monkeypatch.setattr(default, 'sync_watch_later', fake_sync)
    monkeypatch.setattr(default, 'add_directory_item', lambda *a, **k: order.append('item'))
    monkeypatch.setattr(xbmc, 'executebuiltin', lambda cmd, *a, **k: builtins.append(cmd))
    monkeypatch.setattr(default.xbmcplugin, 'endOfDirectory', lambda handle: order.append('end'))

    default.browse_watch_later()

    assert order == ['item', 'end', 'sync']
    assert builtins == ['Container.Refresh']

    order.clear()
    builtins.clear()
    default.browse_watch_later()
    assert order == ['item', 'item', 'end']
    assert builtins == []


def test_season_numbering_is_cached_on_disk(monkeypatch, tmp_path):
    default = _load_default(monkeypatch)
    calls = []

    class FakeApi:
        watchlater_sync_file = str(tmp_path / 'watchlater_sync.json')

        def get_series_episodes(self, series_id, season_id=None, limit=400, offset=0):
            calls.append(series_id)
            return [{'id': 'e1', 'episode_number': 1}, {'id': 'e2', 'episode_number': 2}]

    monkeypatch.setattr(default, '_EPISODE_NUMBERING_CACHE', {})
    first = default._season_numbering(FakeApi(), 'ser1', 'seas1')
    monkeypatch.setattr(default, '_EPISODE_NUMBERING_CACHE', {})
    second = default._season_numbering(FakeApi(), 'ser1', 'seas1')

    assert first == second
    assert second['numbers']['e2'] == 2
    assert calls == ['ser1']


def test_browse_my_series_syncs_after_listing(monkeypatch, kodi_recorder, tmp_path):
    default = _load_default(monkeypatch)
    order = []
    stored = [{'id': 's1', 'title': 'Show', 'type': 'Series'}]

    class FakeApi:
        watchlater_sync_file = str(tmp_path / 'watchlater_sync.json')

        def get_my_series(self):
            return list(stored)

    def fake_sync(notify=True):
        order.append('sync')
        stored.append({'id': 's2', 'title': 'Nieuw', 'type': 'Series'})

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(default, '_my_series_sync_enabled', lambda: True)
    monkeypatch.setattr(default, 'sync_my_series', fake_sync)
    monkeypatch.setattr(default, 'add_directory_item', lambda *a, **k: order.append('item'))
    monkeypatch.setattr(default.xbmcplugin, 'endOfDirectory', lambda handle: order.append('end'))

    default.browse_my_series()

    assert order == ['item', 'end', 'sync']


def test_browse_watch_later_orders_episodes_by_broadcast(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    entries = []

    def episode(item_id, subtitle, broadcast_at):
        return {
            'id': item_id, 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
            'raw': {'type': 'Episode', 'subtitle': subtitle, 'broadcastAt': broadcast_at},
        }

    class FakeApi:
        def get_watch_later(self):
            return [
                episode('late', 'Born alone, die together', '2026-10-24T21:00:00+02:00'),
                episode('early', 'Home is where you park it', '2026-10-24T20:00:00+02:00'),
            ]

        def get_series_episodes(self, series_id, season_id=None, limit=400, offset=0):
            raise RuntimeError('offline')

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(default, '_get_list_api', lambda: FakeApi())
    monkeypatch.setattr(default, '_backfill_quietly', lambda api, method: None)
    monkeypatch.setattr(default, '_watch_later_sync_enabled', lambda: False)
    monkeypatch.setattr(default.xbmcplugin, 'endOfDirectory', lambda handle: None)
    monkeypatch.setattr(default.tvmaze, 'lookup_season_episode', lambda series, episode, cache=None: None)
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, query, kwargs.get('info') or {})),
    )

    default.browse_watch_later()
    assert [query['mode'] for _, query, _ in entries] == ['watch_later_collection']
    collection_id = entries[0][1]['collection_id']

    entries.clear()
    default.browse_watch_later_collection(collection_id)

    assert [query['id'] for _, query, _ in entries] == ['early', 'late']
    title, _, info = entries[0]
    assert title == 'Home is where you park it'
    assert info['aired'] == '2026-10-24'
    assert 'Uitgezonden' in info['plot'] or 'Aired' in info['plot']
    assert '24-10-2026 20:00' in info['plot']


def test_add_series_to_watch_later_stores_collection_and_skips_duplicates(tmp_path):
    api = _isolated_api(tmp_path)
    api.add_to_watch_later({'id': 'e2', 'title': 'Blue Murder Motel', 'type': 'Episode'})
    episodes = [
        {'id': 'e1', 'title': 'Blue Murder Motel', 'type': 'Episode', 'raw': {'broadcastAt': '2026-10-24T20:00:00+02:00'}},
        {'id': 'e2', 'title': 'Blue Murder Motel', 'type': 'Episode', 'raw': {'broadcastAt': '2026-10-24T21:00:00+02:00'}},
    ]

    assert api.add_series_to_watch_later('ser1', 'Blue Murder Motel', episodes) == 1

    items = {it['id']: it for it in api.get_watch_later()}
    assert set(items) == {'e1', 'e2'}
    assert items['e1']['collection'] == {'id': 'ser1', 'title': 'Blue Murder Motel'}
    assert items['e2']['collection'] == {'id': 'ser1', 'title': 'Blue Murder Motel'}


def test_browse_watch_later_shows_series_folder_and_collection_in_broadcast_order(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    folders = []
    entries = []
    collection = {'id': 'ser1', 'title': 'Blue Murder Motel'}

    class FakeApi:
        def migrate_series_from_watch_later(self):
            pass

        def get_watch_later(self):
            return [
                {'id': 'late', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                 'collection': collection, 'raw': {'subtitle': 'Born alone', 'broadcastAt': '2026-10-24T21:00:00+02:00'}},
                {'id': 'early', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                 'collection': collection, 'raw': {'subtitle': 'Home', 'broadcastAt': '2026-10-24T20:00:00+02:00'}},
                {'id': 'film', 'title': 'Film', 'type': 'Movie', 'group': 'movies'},
            ]

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(default, '_get_list_api', lambda: FakeApi())
    monkeypatch.setattr(default, '_watch_later_sync_enabled', lambda: False)
    monkeypatch.setattr(default, '_backfill_quietly', lambda api, method: None)
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: (folders if query.get('mode') == 'watch_later_collection' else entries).append((title, query)),
    )
    monkeypatch.setattr(default.xbmcplugin, 'endOfDirectory', lambda handle: None)

    default.browse_watch_later()

    assert folders == [('Blue Murder Motel', {'mode': 'watch_later_collection', 'collection_id': 'title:blue murder motel'})]
    assert [query['id'] for _, query in entries] == ['film']

    collection_entries = []
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: collection_entries.append(query['id']),
    )
    default.browse_watch_later_collection('title:blue murder motel')

    assert collection_entries == ['early', 'late']


def test_browse_watch_later_shows_tvmaze_season_and_episode(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    entries = []

    class FakeApi:
        watchlater_sync_file = '/tmp/unused/watchlater_sync.json'

        def get_watch_later(self):
            return [{
                'id': 'e3', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                'raw': {'type': 'Episode', 'subtitle': 'Home is where you park it',
                        'broadcastAt': '2026-10-24T20:00:00+02:00'},
            }]

        def get_series_episodes(self, series_id, season_id=None, limit=400, offset=0):
            raise RuntimeError('offline')

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(default.tvmaze, 'lookup_season_episode', lambda series, episode, cache=None: (1, 3))
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, kwargs.get('info') or {})),
    )

    default.browse_watch_later()

    title, info = entries[0]
    assert info['season'] == 1
    assert info['episode'] == 3
    assert f'[COLOR {default.NUMBERING_COLOR_RAW}]S1E03[/COLOR]' in info['plot'].split('\n')


def test_add_series_watch_later_falls_back_to_episode_search_without_series_id(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    stored = {}

    class FakeApi:
        def search(self, query, content_type='all'):
            if content_type == 'episodes':
                return [
                    {'id': 'e1', 'title': 'Blue Murder Motel', 'type': 'Episode', 'raw': {'broadcastAt': '2026-10-24T20:00:00+02:00'}},
                    {'id': 'e2', 'title': 'Blue Murder Motel', 'type': 'Episode', 'raw': {'broadcastAt': '2026-10-24T21:00:00+02:00'}},
                    {'id': 'x', 'title': 'Andere serie', 'type': 'Episode'},
                ]
            return []

        def get_series_list(self, limit=999):
            return []

        def add_series_to_watch_later(self, collection_id, collection_title, episodes):
            stored['args'] = (collection_id, collection_title, [ep['id'] for ep in episodes])
            return len(episodes)

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.add_series_watch_later(None, 'Blue Murder Motel')

    assert stored['args'] == ('Blue Murder Motel', 'Blue Murder Motel', ['e1', 'e2'])


def test_collection_shows_season_folders_then_episodes(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    entries = []
    seasons = {'Home is where you park it': (1, 3), 'Born alone, die together': (1, 4), 'Party boy': (2, 1)}

    class FakeApi:
        def get_watch_later(self):
            return [
                {'id': 'e4', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                 'raw': {'subtitle': 'Born alone, die together', 'broadcastAt': '2026-10-24T21:00:00+02:00'}},
                {'id': 'e3', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                 'raw': {'subtitle': 'Home is where you park it', 'broadcastAt': '2026-10-24T20:00:00+02:00'}},
                {'id': 'e9', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                 'raw': {'subtitle': 'Party boy', 'broadcastAt': '2026-10-31T20:00:00+01:00'}},
            ]

    monkeypatch.setattr(default, '_get_list_api', lambda: FakeApi())
    monkeypatch.setattr(default.xbmcplugin, 'endOfDirectory', lambda handle: None)
    monkeypatch.setattr(
        default.tvmaze, 'lookup_season_episode',
        lambda series, episode, cache=None: seasons.get(episode),
    )
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, query)),
    )

    default.browse_watch_later_collection('title:blue murder motel')
    assert entries == [
        ('Seizoen 1', {'mode': 'watch_later_collection', 'collection_id': 'title:blue murder motel', 'season': '1'}),
        ('Seizoen 2', {'mode': 'watch_later_collection', 'collection_id': 'title:blue murder motel', 'season': '2'}),
    ]

    entries.clear()
    default.browse_watch_later_collection('title:blue murder motel', '1')
    assert [query['id'] for _, query in entries] == ['e3', 'e4']


def test_collection_labels_episodes_by_subtitle_and_reads_nested_payload(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    entries = []

    class FakeApi:
        def get_watch_later(self):
            return [{
                'id': 'e3', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                'raw': {'id': 'e3', 'subtitle': 'Home is where you park it',
                        'raw': {'broadcastAt': '2026-10-24T20:00:00+02:00'}},
            }, {
                'id': 'e4', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                'raw': {'id': 'e4', 'subtitle': 'Born alone, die together',
                        'raw': {'broadcastAt': '2026-10-24T21:00:00+02:00'}},
            }]

    monkeypatch.setattr(default, '_get_list_api', lambda: FakeApi())
    monkeypatch.setattr(default.xbmcplugin, 'endOfDirectory', lambda handle: None)
    monkeypatch.setattr(default.tvmaze, 'lookup_season_episode', lambda series, episode, cache=None: None)
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, kwargs.get('info') or {})),
    )

    default.browse_watch_later_collection('title:blue murder motel')

    assert [title for title, _ in entries] == ['Home is where you park it', 'Born alone, die together']
    assert entries[0][1]['aired'] == '2026-10-24'


def test_season_episodes_sorted_by_episode_number(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    entries = []
    numbers = {'Party boy': (1, 1), 'Home is where you park it': (1, 3), 'Born alone, die together': (1, 4)}

    class FakeApi:
        def get_watch_later(self):
            return [
                {'id': 'e4', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                 'raw': {'subtitle': 'Born alone, die together', 'broadcastAt': '2026-10-24T20:00:00+02:00'}},
                {'id': 'e1', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                 'raw': {'subtitle': 'Party boy', 'broadcastAt': '2026-10-25T20:00:00+02:00'}},
                {'id': 'e3', 'title': 'Blue Murder Motel', 'type': 'Episode', 'group': 'episodes',
                 'raw': {'subtitle': 'Home is where you park it', 'broadcastAt': '2026-10-26T20:00:00+02:00'}},
            ]

    monkeypatch.setattr(default, '_get_list_api', lambda: FakeApi())
    monkeypatch.setattr(default.xbmcplugin, 'endOfDirectory', lambda handle: None)
    monkeypatch.setattr(
        default.tvmaze, 'lookup_season_episode',
        lambda series, episode, cache=None: numbers.get(episode, (1, 1)) if episode != 'Born alone, die together' else (1, 4),
    )
    monkeypatch.setattr(default, 'add_directory_item', lambda title, query, **kwargs: entries.append((title, query)))

    default.browse_watch_later_collection('title:blue murder motel', '1')

    def prefix(number):
        return f'[COLOR {default.EPISODE_PREFIX_COLOR_RAW}]Aflevering {number}[/COLOR]: '

    assert [title for title, _ in entries] == [
        prefix(1) + 'Party boy',
        prefix(3) + 'Home is where you park it',
        prefix(4) + 'Born alone, die together',
    ]


def test_episodes_with_empty_title_still_group_under_series_folder(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    folders = []
    standalone = []

    def episode(item_id, subtitle, broadcast_at):
        return {
            'id': item_id, 'title': '', 'type': 'Episode', 'group': None,
            'raw': {'title': 'Marie Antoinette', 'subtitle': subtitle, 'broadcastAt': broadcast_at},
        }

    items = [
        episode('a1', 'S1:A1 The Slap', '2026-10-01T20:00:00+02:00'),
        episode('a2', 'S1:A2 Rival Queens', '2026-10-08T20:00:00+02:00'),
    ]
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: folders.append((title, query)) if query.get('mode') == 'watch_later_collection' else standalone.append(query),
    )
    monkeypatch.setattr(default, '_pick_landscape_thumb', lambda item: None)

    default._render_watch_later_top(items, None)

    assert folders == [('Marie Antoinette', {'mode': 'watch_later_collection', 'collection_id': 'title:marie antoinette'})]
    assert standalone == []


def test_season_folders_use_nlziet_season_code_before_tvmaze(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    folders = []
    episodes = []

    def episode(item_id, subtitle, broadcast_at):
        return {
            'id': item_id, 'title': '', 'type': 'Episode', 'group': None,
            'raw': {'title': 'Marie Antoinette', 'subtitle': subtitle, 'broadcastAt': broadcast_at},
        }

    items = [
        episode('s2a1', 'S2:A1 The Worst Winter', '2026-10-01T20:00:00+02:00'),
        episode('s1a2', 'S1:A2 Rival Queens', '2026-10-08T20:00:00+02:00'),
        episode('s1a1', 'S1:A1 The Slap', '2026-10-15T20:00:00+02:00'),
    ]
    monkeypatch.setattr(default.tvmaze, 'lookup_season_episode', lambda series, episode, cache=None: None)
    monkeypatch.setattr(default.xbmcplugin, 'endOfDirectory', lambda handle: None)
    monkeypatch.setattr(default, '_get_list_api', lambda: type('A', (), {'get_watch_later': lambda self: items})())
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: folders.append((title, query)) if query.get('mode') == 'watch_later_collection' and 'season' in query
        else episodes.append((title, query['id'])),
    )

    default.browse_watch_later_collection('title:marie antoinette')
    assert [title for title, _ in folders] == ['Seizoen 1', 'Seizoen 2']

    episodes.clear()
    default.browse_watch_later_collection('title:marie antoinette', '1')
    assert [query_id for _, query_id in episodes] == ['s1a1', 's1a2']


def test_episodes_without_top_level_type_are_grouped_by_payload_type(monkeypatch, kodi_recorder):
    default = _load_default(monkeypatch)
    folders = []
    standalone = []
    items = [
        {'id': 'a1', 'title': '', 'type': '', 'group': None,
         'raw': {'title': 'Marie Antoinette', 'type': 'Episode', 'subtitle': 'S1:A1 The Slap',
                 'broadcastAt': '2026-10-01T20:00:00+02:00'}},
        {'id': 'a2', 'title': '', 'type': '', 'group': None,
         'raw': {'title': 'Marie Antoinette', 'type': 'Episode', 'subtitle': 'S1:A2 Rival Queens',
                 'broadcastAt': '2026-10-08T20:00:00+02:00'}},
    ]
    monkeypatch.setattr(
        default, 'add_directory_item',
        lambda title, query, **kwargs: folders.append((title, query)) if query.get('mode') == 'watch_later_collection' else standalone.append(query),
    )
    monkeypatch.setattr(default, '_pick_landscape_thumb', lambda item: None)

    default._render_watch_later_top(items, None)

    assert folders == [('Marie Antoinette', {'mode': 'watch_later_collection', 'collection_id': 'title:marie antoinette'})]
    assert standalone == []


def test_auto_add_first_run_records_then_adds_only_new_episodes(monkeypatch, tmp_path):
    default = _load_default(monkeypatch)
    episodes = [{'id': 'e1', 'title': 'Show'}, {'id': 'e2', 'title': 'Show'}]
    added_calls = []

    class FakeApi:
        watchlater_sync_file = str(tmp_path / 'watchlater_sync.json')

        def get_my_series(self):
            return [{'id': 'ser1', 'title': 'Show'}]

        def get_watch_later(self):
            return []

        def add_series_to_watch_later(self, sid, title, new_eps):
            added_calls.append([ep['id'] for ep in new_eps])
            return len(new_eps)

    monkeypatch.setattr(default, '_collect_series_episodes', lambda api, sid: ('Show', list(episodes)))

    api = FakeApi()
    assert default._run_auto_add(api) == 0
    assert added_calls == []

    episodes.append({'id': 'e3', 'title': 'Show'})
    monkeypatch.setattr(default, '_auto_add_due', lambda api: True)
    assert default._run_auto_add(api) == 1
    assert added_calls == [['e3']]

    assert default._run_auto_add(api) == 0
    assert added_calls == [['e3']]


def test_expiry_notifies_once_for_items_inside_the_window(monkeypatch, tmp_path, kodi_recorder):
    from datetime import datetime, timedelta, timezone
    default = _load_default(monkeypatch)
    now = datetime.now(timezone.utc)
    soon = (now + timedelta(hours=2)).isoformat()
    later = (now + timedelta(days=3)).isoformat()

    class FakeApi:
        watchlater_sync_file = str(tmp_path / 'watchlater_sync.json')

        def get_watch_later(self):
            return [
                {'id': 'a', 'title': 'Shetland', 'type': 'Episode', 'group': 'episodes', 'expires_at': soon},
                {'id': 'b', 'title': 'Sisi', 'type': 'Episode', 'group': 'episodes', 'expires_at': later},
            ]

        def get_my_series(self):
            return []

    monkeypatch.setattr(default.ADDON, 'getSetting', lambda key: {
        'expiry_notify_hours': '24', 'expiry_notify_watch_later': 'true', 'expiry_notify_my_series': 'false',
    }.get(key, ''))

    api = FakeApi()
    assert default._expiry_due_names(api) == ['Shetland']
    assert default._expiry_due_names(api) == []
