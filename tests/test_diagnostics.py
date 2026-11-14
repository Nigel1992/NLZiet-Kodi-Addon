import json

from resources.lib import diagnostics, library, library_art


class Store:
    def __init__(self, series=0, movies=0, last=0):
        self.data = {'series': {str(i): {'folder': 'S%d' % i} for i in range(series)},
                     'movies': {str(i): {'folder': 'M%d' % i} for i in range(movies)}, 'last_update': last}

    def section(self, kind):
        return self.data['series' if kind == 'series' else 'movies']


class Lib:
    def __init__(self, store):
        self.store = store

    def tv_root(self):
        return '/data/library/TV Shows'

    def movies_root(self):
        return '/data/library/Movies'


def test_checks_flag_problems_and_missing_titles():
    t = diagnostics.texts('nl')
    lib = Lib(Store(series=3, movies=1))
    checks = diagnostics.run_checks(
        t, '1.0', False, [('NLZiet', 'https://x'), ('TMDb', 'https://y')], library=lib,
        library_special=('special://tv', 'special://movies'), tmdb_status='invalid',
        probe=lambda url: (url == 'https://x', 42 if url == 'https://x' else 'URLError'),
        sources=['/data/library/TV Shows/'], widevine='android', kodi_counts=(1, 0))
    by_label = {label: (status, detail) for status, label, detail in checks}
    assert by_label['Aangemeld'][0] == 'fail'
    assert by_label['Verbinding met NLZiet'] == ('ok', 'bereikbaar (42 ms)')
    assert by_label['Verbinding met TMDb'][0] == 'fail'
    assert by_label['TMDb-sleutel'][0] == 'fail'
    assert by_label['Map TV Shows'][0] == 'ok'
    assert by_label['Map Movies'][0] == 'warn' and 'special://movies' in by_label['Map Movies'][1]
    assert by_label['In Kodi-bibliotheek'][0] == 'warn'
    text = diagnostics.render(t, checks, '/tmp/report.txt')
    assert text.startswith('6 punt(en)') or 'punt(en)' in text.splitlines()[0]
    assert '[COLOR' not in diagnostics.plain(text)


def test_scan_request_waits_while_kodi_is_busy(tmp_path):
    flag = str(tmp_path / 'scan_pending.json')
    calls = []
    rpc = lambda method, params: calls.append(method)
    assert library_art.request_scan(flag, scan=True, clean=True, is_scanning=lambda: True, rpc=rpc) is False
    assert calls == [] and json.load(open(flag)) == {'scan': True, 'clean': True}
    assert library_art.run_pending_scan(flag, is_scanning=lambda: True, rpc=rpc) is False
    assert library_art.run_pending_scan(flag, is_scanning=lambda: False, rpc=rpc) is True
    assert calls == ['VideoLibrary.Clean', 'VideoLibrary.Scan']
    assert library_art.run_pending_scan(flag, is_scanning=lambda: False, rpc=rpc) is False


def test_kodi_counts_matches_our_folders():
    lib = Lib(Store(series=2, movies=1))

    def rpc(payload):
        if payload['method'] == 'VideoLibrary.GetTVShows':
            return {'result': {'tvshows': [{'file': '/data/library/TV Shows/S0/'},
                                            {'file': '/elsewhere/S1/'}]}}
        return {'result': {'movies': [{'file': '/data/library/Movies/M0/M0.strm'}]}}

    assert library_art.kodi_counts(lib, rpc=rpc) == (1, 1)


def test_folder_with_scanned_titles_counts_as_source():
    t = diagnostics.texts('nl')
    lib = Lib(Store(series=2, movies=1))
    checks = diagnostics.run_checks(t, '1.0', True, [], library=lib, sources=[], widevine='found',
                                    kodi_counts=(2, 0))
    by_label = {label: status for status, label, _detail in checks}
    assert by_label['Map TV Shows'] == 'ok'
    assert by_label['Map Movies'] == 'warn'
