import importlib
import sys
import urllib.parse


def _import_default(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.nlziet', '42', ''])
    sys.modules.pop('default', None)
    return importlib.import_module('default')


def test_episode_directory_url_and_list_item_expose_trakt_metadata(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default.os.path, 'exists', lambda path: False)

    default.add_directory_item(
        'S1:A2 Het geheim',
        {'mode': 'play', 'id': 'episode-2'},
        is_folder=False,
        info={'plot': 'Plot'},
        content={
            'type': 'Episode',
            'title': 'Voorbeeldserie',
            'subtitle': 'S1:A2 Het geheim',
        },
    )

    _, url, item, is_folder = kodi_recorder.directory_items[-1]
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
    assert is_folder is False
    assert params == {
        'mode': 'play',
        'id': 'episode-2',
        'media_type': 'episode',
        'title': 'Het geheim',
        'showtitle': 'Voorbeeldserie',
        'season': '1',
        'episode': '2',
    }
    assert item.info['video'] == {
        'plot': 'Plot',
        'mediatype': 'episode',
        'title': 'Het geheim',
        'tvshowtitle': 'Voorbeeldserie',
        'season': 1,
        'episode': 2,
    }


def test_movie_metadata_includes_release_year(monkeypatch):
    default = _import_default(monkeypatch)

    metadata = default._build_trakt_metadata(
        'Voorbeeldfilm',
        content={'type': 'Movie', 'title': 'Voorbeeldfilm', 'releaseDate': '2024-05-03'},
    )

    assert metadata == {'media_type': 'movie', 'title': 'Voorbeeldfilm', 'year': '2024'}


def test_movie_metadata_does_not_use_broadcast_year(monkeypatch):
    default = _import_default(monkeypatch)

    metadata = default._build_trakt_metadata(
        'Oude film',
        content={
            'type': 'Movie',
            'title': 'Oude film',
            'broadcastAt': '2026-08-24T20:00:00Z',
            'availableFrom': '2026-08-24T20:00:00Z',
        },
    )

    assert metadata == {'media_type': 'movie', 'title': 'Oude film'}


def test_playback_metadata_resolves_movie_with_official_trakt(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(
        default,
        '_official_trakt_movie_match',
        lambda title: {'title': 'Live Free or Die Hard', 'year': '2007'},
    )

    metadata = default._merge_playback_metadata(
        {'media_type': 'movie', 'title': 'Die Hard 4.0'},
        {},
    )

    assert metadata == {
        'media_type': 'movie',
        'title': 'Live Free or Die Hard',
        'year': '2007',
    }


def test_playback_metadata_resolves_cached_episode_from_catalogue(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, '_official_trakt_episode_match', lambda *args: {})

    class FakeApi:
        def get_series_episodes(self, series_id, season_id=None, limit=400):
            assert (series_id, season_id, limit) == ('series-1', 'season-24', 400)
            return [{
                'id': 'episode-62',
                'type': 'Episode',
                'title': 'Pawn Stars',
                'subtitle': 'May the miniforce be with you',
                'series_title': 'Pawn Stars',
                'season_number': 24,
                'episode_number': 62,
            }]

    metadata = default._merge_playback_metadata(
        {},
        {'handshake': {
            'item': {
                'id': 'episode-62',
                'type': 'Episode',
                'seriesId': 'series-1',
                'seasonId': 'season-24',
            },
            'analytics': {
                'seriesTitle': 'Pawn Stars',
                'episodeTitle': 'May the miniforce be with you',
                'seasonNumber': 24,
            },
        }},
        api=FakeApi(),
        content_id='episode-62',
    )

    assert metadata == {
        'media_type': 'episode',
        'title': 'May the miniforce be with you',
        'showtitle': 'Pawn Stars',
        'season': '24',
        'episode': '62',
    }


def test_episode_metadata_does_not_use_nlziet_broadcast_year(monkeypatch):
    default = _import_default(monkeypatch)

    metadata = default._build_trakt_metadata(
        'S24:A61',
        content={
            'type': 'Episode',
            'title': 'Pawn Stars',
            'subtitle': 'S24:A61',
            'release_date': '2026-08-12T19:33:19+02:00',
            'available_from': '2026-08-12T19:33:19+02:00',
        },
    )

    assert metadata == {
        'media_type': 'episode',
        'title': 'Pawn Stars',
        'showtitle': 'Pawn Stars',
        'season': '24',
        'episode': '61',
    }


def test_playback_metadata_maps_named_episode_to_trakt_order(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(
        default,
        '_official_trakt_episode_match',
        lambda *args: {
            'showtitle': 'Pawn Stars',
            'title': 'May the Miniforce Be With You',
            'season': '21',
            'episode': '8',
            'year': '2009',
        },
    )

    metadata = default._merge_playback_metadata(
        {
            'media_type': 'episode',
            'title': 'Pawn Stars',
            'showtitle': 'Pawn Stars',
            'season': '24',
            'episode': '62',
            'year': '2026',
        },
        {'handshake': {
            'item': {'type': 'Episode'},
            'analytics': {'episodeTitle': 'May the miniforce be with you'},
        }},
    )

    assert metadata == {
        'media_type': 'episode',
        'title': 'May the Miniforce Be With You',
        'showtitle': 'Pawn Stars',
        'season': '21',
        'episode': '8',
        'year': '2009',
    }


def test_episode_number_inference_uses_next_older_anchor():
    from resources.lib.nlziet_api import NLZietAPI

    episodes = [
        {
            'id': 'episode-62',
            'season_id': 'season-24',
            'subtitle': 'May the miniforce be with you',
            'episode_number': None,
        },
        {
            'id': 'episode-61',
            'season_id': 'season-24',
            'subtitle': 'Afl. 61',
            'episode_number': 61,
        },
    ]

    NLZietAPI._infer_episode_numbers(episodes)

    assert [episode['episode_number'] for episode in episodes] == [62, 61]


def test_resolved_drm_item_publishes_episode_labels(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)

    class FakeApi:
        user_agent = 'test-agent'

        def get_stream_info(self, content_id, **kwargs):
            return {
                'manifest': 'https://example.test/manifest.mpd',
                'is_drm': True,
                'license_url': 'https://example.test/license',
                'license_headers': {},
                'drm_raw': {},
                'subtitles': [],
            }

        def get_access_token(self):
            return ''

    class FakeInputstreamHelper:
        inputstream_addon = 'inputstream.adaptive'

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(default, 'ensure_inputstream_for_drm', lambda: FakeInputstreamHelper())

    default.play_item(
        'episode-2',
        media_type='episode',
        title='Het geheim',
        showtitle='Voorbeeldserie',
        season='1',
        episode='2',
    )

    _, succeeded, item = kodi_recorder.resolved_items[-1]
    assert succeeded is True
    assert item.info['video'] == {
        'mediatype': 'episode',
        'title': 'Het geheim',
        'tvshowtitle': 'Voorbeeldserie',
        'season': 1,
        'episode': 2,
    }


def test_live_resolved_item_is_explicitly_excluded_from_trakt(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)

    class FakeApi:
        def get_stream_info(self, content_id, **kwargs):
            return {
                'manifest': 'https://example.test/live.m3u8',
                'is_drm': False,
                'subtitles': [],
            }

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.play_item('channel-1', fmt='live')

    item = kodi_recorder.resolved_items[-1][2]
    assert item.properties['script.trakt.exclude'] == 'true'
    assert 'video' not in item.info
