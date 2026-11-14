import os

import pytest

from resources.lib import library


class FakeAPI:
    def __init__(self):
        self.series = {}
        self.episodes = {}
        self.content = {}

    def get_series_detail(self, series_id):
        return self.series.get(series_id, {})

    def get_content_detail(self, content_id):
        return self.content.get(content_id, {})


def fetcher(api, series_id, detail):
    return list(api.episodes.get(series_id, []))


class Addon:
    def __init__(self, tmp):
        self.settings = {
            'library_path': str(tmp / 'TV Shows'),
            'library_movies_path': str(tmp / 'Movies'),
        }
        self.tmp = tmp

    def getSetting(self, key):
        return self.settings.get(key, '')

    def getAddonInfo(self, key):
        return {'id': 'plugin.video.nlziet', 'profile': str(self.tmp / 'profile')}.get(key, '')


@pytest.fixture
def setup(tmp_path):
    api = FakeAPI()
    addon = Addon(tmp_path)
    clock = {'now': 1_700_000_000}
    lib = library.Library(api, addon, fetcher, now=lambda: clock['now'])
    return api, lib, tmp_path, clock


def _files(root):
    out = []
    for base, _dirs, files in os.walk(root):
        for name in files:
            out.append(os.path.relpath(os.path.join(base, name), root).replace(os.sep, '/'))
    return sorted(out)


def _daily(ep_id, date, title=None):
    return {'id': ep_id, 'title': title or ep_id, 'aired_date': date + 'T20:00:00Z', 'description': 'Plot ' + ep_id}


def test_dated_series_export_and_stable_numbers_after_expiry(setup):
    api, lib, tmp, clock = setup
    api.series['s1'] = {'title': 'Het Journaal', 'description': 'Nieuws', 'thumb': 'https://img/poster.jpg'}
    api.episodes['s1'] = [_daily('e1', '2026-11-01'), _daily('e2', '2026-11-02'), _daily('e3', '2026-11-03')]

    result = lib.add_series('s1')
    lib.store.save()

    assert result['ok'] and result['total'] == 3 and result['added'] == 3
    files = _files(tmp / 'TV Shows')
    assert 'Het Journaal/tvshow.nfo' in files
    assert 'Het Journaal/Season 2026/Het Journaal S2026E01.strm' in files
    assert 'Het Journaal/Season 2026/Het Journaal S2026E03.nfo' in files
    strm = (tmp / 'TV Shows/Het Journaal/Season 2026/Het Journaal S2026E02.strm').read_text()
    assert strm.startswith('plugin://plugin.video.nlziet/?mode=play&id=e2&media_type=episode')
    nfo = (tmp / 'TV Shows/Het Journaal/tvshow.nfo').read_text()
    assert '<thumb aspect="poster">https://img/poster.jpg</thumb>' in nfo

    # e1 expires, e4 is new: e2/e3 keep their numbers, e4 gets the next one.
    api.episodes['s1'] = [_daily('e2', '2026-11-02'), _daily('e3', '2026-11-03'), _daily('e4', '2026-11-04')]
    totals = lib.update_all()

    assert totals == {'added': 1, 'removed': 1, 'failed': 0, 'checked': 1}
    files = _files(tmp / 'TV Shows/Het Journaal/Season 2026')
    assert files == [
        'Het Journaal S2026E02.nfo', 'Het Journaal S2026E02.strm',
        'Het Journaal S2026E03.nfo', 'Het Journaal S2026E03.strm',
        'Het Journaal S2026E04.nfo', 'Het Journaal S2026E04.strm',
    ]
    assert 'id=e4' in (tmp / 'TV Shows/Het Journaal/Season 2026/Het Journaal S2026E04.strm').read_text()


def test_numbered_series_uses_api_numbers(setup):
    api, lib, tmp, _ = setup
    api.series['s2'] = {'title': 'Drama'}
    api.episodes['s2'] = [
        {'id': 'a', 'title': 'Pilot', 'season_number': 1, 'episode_number': 1},
        {'id': 'b', 'title': 'Two', 'season_number': 1, 'episode_number': 2},
        {'id': 'c', 'title': 'Back', 'season_number': 2, 'episode_number': 1},
    ]
    lib.add_series('s2')

    assert _files(tmp / 'TV Shows/Drama') == [
        'Season 1/Drama S01E01.nfo', 'Season 1/Drama S01E01.strm',
        'Season 1/Drama S01E02.nfo', 'Season 1/Drama S01E02.strm',
        'Season 2/Drama S02E01.nfo', 'Season 2/Drama S02E01.strm',
        'tvshow.nfo',
    ]


def test_update_never_deletes_on_empty_api_answer(setup):
    api, lib, tmp, _ = setup
    api.series['s1'] = {'title': 'Show'}
    api.episodes['s1'] = [_daily('e1', '2026-01-01')]
    lib.add_series('s1')
    api.episodes['s1'] = []

    totals = lib.update_all()

    assert totals['removed'] == 0 and totals['failed'] == 1
    assert 'Show/Season 2026/Show S2026E01.strm' in _files(tmp / 'TV Shows')
    assert lib.is_in_library('series', 's1')


def test_old_export_files_are_replaced(setup):
    api, lib, tmp, _ = setup
    old = tmp / 'TV Shows/Show/Season 2026'
    old.mkdir(parents=True)
    (old / 'Show S2026E09.strm').write_text('plugin://old\n')
    api.series['s1'] = {'title': 'Show'}
    api.episodes['s1'] = [_daily('e1', '2026-01-01')]

    lib.add_series('s1')

    assert _files(tmp / 'TV Shows/Show/Season 2026') == ['Show S2026E01.nfo', 'Show S2026E01.strm']


def test_movie_add_remove_and_expiry(setup):
    api, lib, tmp, clock = setup
    api.content['m1'] = {'title': 'De Film', 'description': 'Spannend', 'thumb': 'https://img/m.jpg',
                         'raw': {'year': 2021}, 'expires_at': clock['now'] + 3600}
    result = lib.add_movie('m1')

    assert result['ok']
    assert _files(tmp / 'Movies') == ['De Film (2021)/De Film (2021).nfo', 'De Film (2021)/De Film (2021).strm']
    assert 'media_type=movie' in (tmp / 'Movies/De Film (2021)/De Film (2021).strm').read_text()
    assert '<year>2021</year>' in (tmp / 'Movies/De Film (2021)/De Film (2021).nfo').read_text()

    clock['now'] += 7200
    totals = lib.update_all()
    assert totals['removed'] == 1
    assert not lib.is_in_library('movie', 'm1')
    assert _files(tmp / 'Movies') == []


def test_remove_series_deletes_folder_and_store_persists(setup):
    api, lib, tmp, _ = setup
    api.series['s1'] = {'title': 'Show'}
    api.episodes['s1'] = [_daily('e1', '2026-01-01')]
    lib.add_series('s1')
    lib.store.save()

    reloaded = library.LibraryStore(str(tmp / 'profile' / 'library.json'))
    assert reloaded.has('series', 's1')

    assert lib.remove('series', 's1') is True
    assert not (tmp / 'TV Shows' / 'Show').exists()
    assert lib.remove('series', 's1') is False


def test_update_due(setup):
    _, lib, _, clock = setup
    assert lib.update_due(12) is True
    lib.update_all()
    assert lib.update_due(12) is False
    clock['now'] += 12 * 3600
    assert lib.update_due(12) is True
    assert lib.update_due(0) is False


def test_safe_filename():
    assert library.safe_filename('Wie is: de "Mol"?') == 'Wie is de Mol'
    assert library.safe_filename('') == 'NLZiet'


# --- default.py wiring ------------------------------------------------------

import importlib
import sys


def _import_default(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.nlziet', '42', ''])
    sys.modules.pop('default', None)
    return importlib.import_module('default')


@pytest.fixture
def wired(monkeypatch, setup, kodi_recorder):
    api, lib, tmp, clock = setup
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, '_get_library', lambda: lib)
    jobs = []
    monkeypatch.setattr(default.library_mod, 'run_library_jobs', lambda scan=True, clean=False: jobs.append((scan, clean)))
    builtins = []
    monkeypatch.setattr(default.xbmc, 'executebuiltin', lambda cmd, *a: builtins.append(cmd))
    return default, api, lib, tmp, jobs, kodi_recorder


def test_toggle_adds_then_removes_movie(wired):
    default, api, lib, tmp, jobs, rec = wired
    api.content['m1'] = {'title': 'Film', 'raw': {}}

    default.library_toggle('movie', 'm1', 'Film')
    assert lib.is_in_library('movie', 'm1')
    assert jobs == [(True, False)]

    default.library_toggle('movie', 'm1', 'Film')
    assert not lib.is_in_library('movie', 'm1')
    assert jobs[-1] == (False, True)


def test_export_series_library_route_still_works(wired):
    default, api, lib, tmp, jobs, rec = wired
    api.series['s1'] = {'title': 'Show'}
    api.episodes['s1'] = [_daily('e1', '2026-01-01')]

    default.export_series_library('s1')

    assert lib.is_in_library('series', 's1')
    assert any('1' in msg for _h, msg, _i in rec.notifications)


def test_browse_library_lists_items_with_remove_option(wired):
    default, api, lib, tmp, jobs, rec = wired
    api.series['s1'] = {'title': 'Show'}
    api.episodes['s1'] = [_daily('e1', '2026-01-01')]
    lib.add_series('s1')
    api.content['m1'] = {'title': 'Film', 'raw': {}}
    lib.add_movie('m1')

    default.browse_library()

    urls = [url for _h, url, _item, _folder in rec.directory_items]
    assert any('mode=library_update' in u for u in urls)
    assert any('mode=series_detail' in u and 's1' in u for u in urls)
    assert any('mode=play' in u and 'm1' in u for u in urls)
    menus = [item.context_menu for _h, _u, item, _f in rec.directory_items]
    assert any('library_remove' in cmd for menu in menus for _label, cmd in menu)


def test_background_update_skips_while_playing(wired, monkeypatch):
    default, api, lib, tmp, jobs, rec = wired
    monkeypatch.setattr(default.xbmc, 'Player', type('P', (), {'isPlaying': lambda self: True}))
    called = []
    monkeypatch.setattr(lib, 'update_all', lambda **k: called.append(1) or {})

    default.library_update(background=True)

    assert called == []


def test_legacy_android_folder_is_moved_into_addon_folder(tmp_path):
    legacy = tmp_path / 'KodiNLZietLibrary'
    (legacy / 'TV Shows' / 'Show' / 'Season 2026').mkdir(parents=True)
    (legacy / 'TV Shows' / 'Show' / 'tvshow.nfo').write_text('<tvshow/>')
    (legacy / 'TV Shows' / 'Show' / 'Season 2026' / 'Show S2026E01.strm').write_text('plugin://x\n')
    # A show that also exists in the new folder: the new files win, old extras move.
    (tmp_path / 'TV Shows' / 'Both').mkdir(parents=True)
    (tmp_path / 'TV Shows' / 'Both' / 'tvshow.nfo').write_text('new')
    (legacy / 'TV Shows' / 'Both').mkdir()
    (legacy / 'TV Shows' / 'Both' / 'tvshow.nfo').write_text('old')
    (legacy / 'TV Shows' / 'Both' / 'extra.strm').write_text('old extra')

    class Addon:
        def __init__(self):
            self.settings = {'library_path': library.LEGACY_TV_PATH}

        def getSetting(self, key):
            return {'library_path': self.settings['library_path'] if self.settings['library_path'] != library.DEFAULT_TV_PATH else str(tmp_path / 'TV Shows')}.get(key, '')

        def setSetting(self, key, value):
            self.settings[key] = value

        def getAddonInfo(self, key):
            return {'id': 'plugin.video.nlziet', 'profile': str(tmp_path / 'profile')}.get(key, '')

    addon = Addon()
    lib = library.Library(FakeAPI(), addon, fetcher)

    moved = lib.migrate_legacy_folder(str(legacy))

    assert moved == 2
    assert addon.settings['library_path'] == library.DEFAULT_TV_PATH
    assert _files(tmp_path / 'TV Shows') == [
        'Both/extra.strm', 'Both/tvshow.nfo', 'Show/Season 2026/Show S2026E01.strm', 'Show/tvshow.nfo']
    assert (tmp_path / 'TV Shows' / 'Both' / 'tvshow.nfo').read_text() == 'new'
    assert not legacy.exists()
    assert lib.migrate_legacy_folder(str(legacy)) == 0


def test_old_legacy_setting_never_used_as_target(tmp_path):
    class Addon:
        def getSetting(self, key):
            return library.LEGACY_TV_PATH if key == 'library_path' else ''

        def getAddonInfo(self, key):
            return str(tmp_path) if key == 'profile' else 'plugin.video.nlziet'

    lib = library.Library(FakeAPI(), Addon(), fetcher)
    assert lib.tv_root() != library.LEGACY_TV_PATH


# --- artwork ----------------------------------------------------------------

from resources.lib import library_art


def test_poster_comes_from_hint_and_is_saved_as_file(tmp_path):
    api = FakeAPI()
    api.series['s1'] = {'title': 'Show', 'description': ''}  # detail without any image
    api.episodes['s1'] = [_daily('e1', '2026-01-01')]
    downloads = []

    def downloader(url):
        downloads.append(url)
        return b'IMG:' + url.encode()

    lib = library.Library(api, Addon(tmp_path), fetcher, downloader=downloader)
    lib.add_series('s1', poster='https://img/p.jpg?width=3840', fanart='https://img/f.jpg')

    show = tmp_path / 'TV Shows' / 'Show'
    assert (show / 'poster.jpg').read_bytes() == b'IMG:https://img/p.jpg?width=3840'
    assert (show / 'fanart.jpg').exists()
    assert '<thumb aspect="poster">https://img/p.jpg?width=3840</thumb>' in (show / 'tvshow.nfo').read_text()

    # An update keeps the hint and does not download again.
    lib.update_all()
    assert len(downloads) == 2


def test_art_picker_beats_detail_thumb(tmp_path):
    api = FakeAPI()
    api.series['s1'] = {'title': 'Show', 'thumb': 'https://raw/logo.png', 'raw': {'image': {'portraitUrl': 'x'}}}
    api.episodes['s1'] = [_daily('e1', '2026-01-01')]
    lib = library.Library(api, Addon(tmp_path), fetcher,
                          art_picker=lambda item: ('https://img/portrait.jpg?width=3840', 'https://img/land.jpg'))
    lib.add_series('s1')
    nfo = (tmp_path / 'TV Shows' / 'Show' / 'tvshow.nfo').read_text()
    assert 'portrait.jpg' in nfo and 'land.jpg' in nfo


def test_movie_art_files_use_movie_name(tmp_path):
    api = FakeAPI()
    api.content['m1'] = {'title': 'Film', 'raw': {'year': 2020}}
    lib = library.Library(api, Addon(tmp_path), fetcher, downloader=lambda url: b'x')
    lib.add_movie('m1', poster='https://img/m.jpg')
    assert (tmp_path / 'Movies' / 'Film (2020)' / 'Film (2020)-poster.jpg').exists()


def test_repair_fills_only_missing_art(tmp_path):
    api = FakeAPI()
    api.series['s1'] = {'title': 'Show'}
    api.episodes['s1'] = [_daily('e1', '2026-01-01')]
    api.content['m1'] = {'title': 'Film', 'raw': {}}
    lib = library.Library(api, Addon(tmp_path), fetcher, downloader=lambda url: b'x')
    lib.add_series('s1', poster='https://img/p.jpg')
    lib.add_movie('m1', poster='https://img/m.jpg', fanart='https://img/mf.jpg')
    tv = str(tmp_path / 'TV Shows')
    calls = []

    def rpc(payload):
        calls.append(payload)
        method = payload['method']
        if method == 'VideoLibrary.GetTVShows':
            return {'result': {'tvshows': [
                {'tvshowid': 1, 'file': tv + '/Show/', 'art': {}},
                {'tvshowid': 2, 'file': '/other/Show/', 'art': {}},
            ]}}
        if method == 'VideoLibrary.GetMovies':
            return {'result': {'movies': [
                {'movieid': 9, 'file': 'special://profile/addon_data/plugin.video.nlziet/library/Movies/Film/Film.strm',
                 'art': {'poster': 'chosen-by-user'}},
            ]}}
        return {'result': 'OK'}

    fixed = library_art.repair_kodi_art(lib, marker='plugin.video.nlziet/library', rpc=rpc)

    sets = [c for c in calls if c['method'].startswith('VideoLibrary.Set')]
    assert fixed == 2
    assert sets[0]['params']['tvshowid'] == 1
    assert sets[0]['params']['art']['poster'].endswith('poster.jpg')
    assert sets[1]['params']['movieid'] == 9
    assert 'poster' not in sets[1]['params']['art']  # the user's own choice stays
    assert sets[1]['params']['art']['fanart'].endswith('-fanart.jpg')


def test_lists_sync_adds_series_and_films(wired, monkeypatch):
    default, api, lib, tmp, jobs, rec = wired

    class ListAPI:
        def get_my_series(self):
            return [{'id': 's1', 'title': 'Show', 'type': 'series'}]

        def get_watch_later(self):
            return [{'id': 'm1', 'title': 'Film', 'type': 'movie'},
                    {'id': 'e9', 'title': 'Show', 'type': 'episode', 'seriesId': 's1'},
                    {'id': 'e7', 'title': 'Other', 'type': 'episode', 'raw': {'seriesId': 's2'}}]

    api.series.update({'s1': {'title': 'Show'}, 's2': {'title': 'Other'}})
    api.episodes.update({'s1': [_daily('a', '2026-01-01')], 's2': [_daily('b', '2026-01-02')]})
    api.content['m1'] = {'title': 'Film', 'raw': {}}
    monkeypatch.setattr(default, '_setting_on', lambda name, default_value=False: name == 'library_lists_remove')
    lib.store.section('series')['gone'] = {'title': 'Weg', 'source': 'lists'}

    added, removed, failed = default.sync_lists_to_library(lib, api=ListAPI())

    assert (added, removed, failed) == (3, 1, 0)
    assert lib.is_in_library('series', 's1') and lib.is_in_library('series', 's2')
    assert lib.is_in_library('movie', 'm1') and not lib.is_in_library('series', 'gone')
    assert lib.store.get('series', 's1')['source'] == 'lists'
