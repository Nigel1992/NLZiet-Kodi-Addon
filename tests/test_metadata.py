import urllib.parse

import pytest

from resources.lib import library, metadata


class FakeHTTP:
    """Answers TMDb/TVmaze URLs from a dict keyed by path (query ignored)."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, headers):
        self.calls.append(url)
        parsed = urllib.parse.urlsplit(url)
        key = parsed.netloc.split('.')[-2] + parsed.path.replace('/3/', '/')
        value = self.routes.get(key)
        if isinstance(value, Exception):
            raise value
        if value is None:
            error = Exception('not found')
            error.code = 404
            raise error
        return value(urllib.parse.parse_qs(parsed.query)) if callable(value) else value


TVMAZE_SHOW = {
    'id': 7, 'name': 'Wie is de Mol?', 'summary': '<p>Spel met een <b>mol</b>.</p>',
    'image': {'original': 'https://maze/poster.jpg'}, 'premiered': '1999-01-02',
    'genres': ['Reality'], 'rating': {'average': 8.1}, 'network': {'name': 'AVROTROS'},
    'externals': {'thetvdb': 12345, 'imdb': 'tt0123'},
}
TVMAZE_EPISODES = [
    {'season': 2026, 'number': 1, 'airdate': '2026-01-03', 'name': 'De start', 'summary': '<p>Eerste.</p>',
     'image': {'original': 'https://maze/e1.jpg'}},
    {'season': 2026, 'number': 2, 'airdate': '2026-01-10', 'name': 'Twee', 'summary': '', 'image': None},
]


def maze_routes():
    return {
        'tvmaze/search/shows': [{'show': {'id': 99, 'name': 'Wie is de Mol 2'}}, {'show': {'id': 7, 'name': 'Wie is de Mol?'}}],
        'tvmaze/shows/7': TVMAZE_SHOW,
        'tvmaze/shows/7/episodes': TVMAZE_EPISODES,
    }


def make(tmp_path, routes, key=''):
    http = FakeHTTP(routes)
    return metadata.Enricher(str(tmp_path / 'cache.json'), tmdb_key=key, http=http, now=lambda: 1_000), http


def test_merge_keeps_local_and_fills_gaps():
    local = {'title': 'Aflevering 3', 'plot': 'Eigen tekst', 'thumb': ''}
    extra = {'title': 'De val', 'plot': 'TMDb tekst', 'thumb': 'https://x/t.jpg'}
    assert metadata.merge(local, extra) == {'title': 'De val', 'plot': 'Eigen tekst', 'thumb': 'https://x/t.jpg'}


def test_tvmaze_show_without_key_uses_exact_title_match(tmp_path):
    enricher, _http = make(tmp_path, maze_routes())
    data = enricher.show('Wie is de Mol?')
    assert data['plot'] == 'Spel met een mol.'
    assert data['poster'] == 'https://maze/poster.jpg'
    assert data['ids'] == {'tvmaze': '7', 'tvdb': '12345', 'imdb': 'tt0123'}
    assert data['studio'] == 'AVROTROS' and data['year'] == 1999


def test_unknown_title_returns_nothing(tmp_path):
    enricher, _http = make(tmp_path, maze_routes())
    assert enricher.show('Een programma dat niet bestaat') == {'ids': {}}


def test_episode_matched_by_airdate_and_cached(tmp_path):
    enricher, http = make(tmp_path, maze_routes())
    ids = {'tvmaze': '7'}
    first = enricher.episode(ids, 2026, 9, airdate='2026-01-03', by_number=False)
    assert first['title'] == 'De start' and first['thumb'] == 'https://maze/e1.jpg'
    calls = len(http.calls)
    assert enricher.episode(ids, 2026, 9, airdate='2026-01-10', by_number=False)['title'] == 'Twee'
    assert len(http.calls) == calls  # episode list came from the cache
    assert enricher.episode(ids, 2026, 2, airdate=None, by_number=False) == {}


def test_tmdb_show_and_episode_with_key(tmp_path):
    routes = maze_routes()
    routes.update({
        'themoviedb/search/tv': {'results': [{'id': 55, 'name': 'Wie is de Mol?', 'first_air_date': '1999-01-02'}]},
        'themoviedb/tv/55': {'overview': 'NL tekst', 'poster_path': '/p.jpg', 'backdrop_path': '/b.jpg',
                             'first_air_date': '1999-01-02', 'genres': [{'name': 'Reality'}],
                             'networks': [{'name': 'NPO 1'}], 'vote_average': 7.5,
                             'external_ids': {'tvdb_id': 12345, 'imdb_id': 'tt0123'}},
        'tvmaze/lookup/shows': {'id': 7},
        'themoviedb/tv/55/season/1': {'episodes': [{'episode_number': 2, 'name': 'Tweede', 'overview': 'Over twee',
                                                   'still_path': '/s2.jpg', 'air_date': '1999-01-09'}]},
    })
    enricher, http = make(tmp_path, routes, key='abc')
    data = enricher.show('Wie is de Mol?')
    assert data['plot'] == 'NL tekst'
    assert data['fanart'] == 'https://image.tmdb.org/t/p/original/b.jpg'
    assert data['ids']['tmdb'] == '55' and data['ids']['tvmaze'] == '7' and data['ids']['tvdb'] == '12345'
    assert 'api_key=abc' in http.calls[0]
    ep = enricher.episode(data['ids'], 1, 2)
    assert ep['title'] == 'Tweede' and ep['thumb'].endswith('/s2.jpg')


def test_tmdb_movie_requires_matching_year(tmp_path):
    routes = {
        'themoviedb/search/movie': {'results': [{'id': 1, 'title': 'Soof', 'release_date': '2013-12-05'}]},
        'themoviedb/movie/1': {'overview': 'Komedie', 'poster_path': '/m.jpg', 'release_date': '2013-12-05',
                               'runtime': 101, 'imdb_id': 'tt3', 'genres': [{'name': 'Komedie'}]},
    }
    enricher, _http = make(tmp_path, routes, key='x' * 50)
    assert enricher.movie('Soof', 1990) == {}
    data = enricher.movie('Soof', 2013)
    assert data['plot'] == 'Komedie' and data['runtime'] == 101 and data['ids']['imdb'] == 'tt3'
    assert enricher.movie('Soof') ['ids']['tmdb'] == '1'


def test_offline_service_is_skipped_for_a_while(tmp_path):
    routes = maze_routes()
    routes['tvmaze/search/shows'] = OSError('offline')
    enricher, http = make(tmp_path, routes)
    assert enricher.show('Wie is de Mol?') == {'ids': {}}
    calls = len(http.calls)
    enricher.show('Iets anders')
    assert len(http.calls) == calls


def test_cache_survives_restart(tmp_path):
    enricher, http = make(tmp_path, maze_routes())
    enricher.show('Wie is de Mol?')
    enricher.save()
    again, http2 = make(tmp_path, {})
    assert again.show('Wie is de Mol?')['ids']['tvmaze'] == '7'
    assert http2.calls == []


# --- library integration ----------------------------------------------------

class FakeAPI:
    def __init__(self):
        self.series = {'s1': {'title': 'Wie is de Mol?', 'description': ''}}
        self.episodes = {'s1': [{'id': 'e1', 'title': 'Aflevering 1', 'aired_date': '2026-01-03T20:00:00Z'}]}
        self.content = {'m1': {'title': 'Soof', 'description': 'Eigen beschrijving', 'raw': {'year': 2013}}}

    def get_series_detail(self, series_id):
        return self.series.get(series_id, {})

    def get_content_detail(self, content_id):
        return self.content.get(content_id, {})


class Addon:
    def __init__(self, tmp):
        self.tmp = tmp

    def getSetting(self, key):
        return {'library_path': str(self.tmp / 'TV'), 'library_movies_path': str(self.tmp / 'Movies')}.get(key, '')

    def getAddonInfo(self, key):
        return {'id': 'plugin.video.nlziet', 'profile': str(self.tmp / 'profile')}.get(key, '')


def test_library_nfo_uses_local_first_and_fills_gaps(tmp_path):
    routes = maze_routes()
    routes.update({
        'themoviedb/search/movie': {'results': [{'id': 1, 'title': 'Soof', 'release_date': '2013-12-05'}]},
        'themoviedb/movie/1': {'overview': 'TMDb tekst', 'poster_path': '/m.jpg', 'release_date': '2013-12-05',
                               'imdb_id': 'tt3', 'genres': [{'name': 'Komedie'}]},
        'themoviedb/search/tv': {'results': []},
    })
    enricher, _http = make(tmp_path, routes, key='abc')
    api = FakeAPI()
    lib = library.Library(api, Addon(tmp_path), lambda a, sid, d: a.episodes[sid], enricher=enricher)

    lib.add_series('s1')
    show = (tmp_path / 'TV/Wie is de Mol/tvshow.nfo').read_text()
    assert '<plot>Spel met een mol.</plot>' in show
    assert '<uniqueid type="tvdb">12345</uniqueid>' in show
    assert '<uniqueid type="nlziet" default="true">s1</uniqueid>' in show
    episode = (tmp_path / 'TV/Wie is de Mol/Season 2026/Wie is de Mol S2026E01.nfo').read_text()
    assert '<title>De start</title>' in episode  # placeholder title replaced
    assert '<thumb>https://maze/e1.jpg</thumb>' in episode
    assert lib.store.get('series', 's1')['ids']['tvmaze'] == '7'

    lib.add_movie('m1')
    movie = (tmp_path / 'Movies/Soof (2013)/Soof (2013).nfo').read_text()
    assert '<plot>Eigen beschrijving</plot>' in movie  # local plot wins
    assert '<thumb aspect="poster">https://image.tmdb.org/t/p/original/m.jpg</thumb>' in movie
    assert '<genre>Komedie</genre>' in movie and '<uniqueid type="imdb">tt3</uniqueid>' in movie


def test_tmdb_key_check_reports_the_real_problem():
    def refuse(url, headers):
        error = Exception('unauthorized')
        error.code = 401
        raise error

    def offline(url, headers):
        raise OSError('network down')

    seen = []
    assert metadata.test_tmdb_key('') == ('missing', '')
    assert metadata.test_tmdb_key('  abc  ', http=lambda url, headers: seen.append(url) or {})[0] == 'ok'
    assert seen[0].endswith('/configuration?api_key=abc')
    assert metadata.test_tmdb_key('k' * 32, http=refuse)[0] == 'invalid'
    assert metadata.test_tmdb_key('k' * 32, http=offline)[0] == 'offline'
    token_headers = []
    metadata.test_tmdb_key('t' * 200, http=lambda url, headers: token_headers.append(headers) or {})
    assert token_headers[0]['Authorization'] == 'Bearer ' + 't' * 200


def test_clearlogo_prefers_dutch_png_then_english(tmp_path):
    routes = {
        'themoviedb/search/tv': {'results': [{'id': 9, 'name': 'Flikken Maastricht'}]},
        'themoviedb/tv/9': {'overview': 'x', 'external_ids': {}},
        'themoviedb/tv/9/images': {'logos': [
            {'file_path': '/en.png', 'iso_639_1': 'en', 'vote_average': 9},
            {'file_path': '/nl.svg', 'iso_639_1': 'nl', 'vote_average': 8},
            {'file_path': '/nl.png', 'iso_639_1': 'nl', 'vote_average': 5},
        ]},
    }
    enricher, _http = make(tmp_path, routes, key='abc')
    data = enricher.show('Flikken Maastricht')
    assert data['clearlogo'] == 'https://image.tmdb.org/t/p/original/nl.png'
    routes['themoviedb/tv/9/images'] = {'logos': [{'file_path': '/en.png', 'iso_639_1': 'en'}]}
    other, _ = make(tmp_path / 'b', routes, key='abc')
    assert other.show('Flikken Maastricht')['clearlogo'].endswith('/en.png')


def test_library_saves_clearlogo_file(tmp_path):
    routes = {
        'themoviedb/search/tv': {'results': [{'id': 9, 'name': 'Show'}]},
        'themoviedb/tv/9': {'overview': '', 'external_ids': {}},
        'themoviedb/tv/9/images': {'logos': [{'file_path': '/logo.png', 'iso_639_1': 'nl'}]},
    }
    enricher, _http = make(tmp_path, routes, key='abc')
    api = FakeAPI()
    api.series['s9'] = {'title': 'Show'}
    api.episodes['s9'] = [{'id': 'e', 'title': 'Aflevering 1', 'aired_date': '2026-01-03'}]
    lib = library.Library(api, Addon(tmp_path), lambda a, sid, d: a.episodes[sid], enricher=enricher,
                          downloader=lambda url: b'PNG')
    lib.add_series('s9')
    show = tmp_path / 'TV' / 'Show'
    assert (show / 'clearlogo.png').read_bytes() == b'PNG'
    assert '<thumb aspect="clearlogo">https://image.tmdb.org/t/p/original/logo.png</thumb>' in (show / 'tvshow.nfo').read_text()
    assert lib.store.get('series', 's9')['clearlogo'].endswith('clearlogo.png')
