"""Tests for the shared watch_sync module (watched-status-back logic)."""
import json

from resources.lib import watch_sync


def test_library_update_reads_watched_change():
    data = json.dumps({'item': {'type': 'episode', 'id': 42}, 'playcount': 1})
    assert watch_sync.library_update(data) == ('episode', 42, True)


def test_library_update_reads_unwatched():
    data = {'item': {'type': 'movie', 'id': 7}, 'playcount': 0}
    assert watch_sync.library_update(data) == ('movie', 7, False)


def test_library_update_ignores_scan_without_playcount():
    assert watch_sync.library_update({'item': {'type': 'episode', 'id': 1}, 'added': True}) is None
    assert watch_sync.library_update({'item': {'type': 'episode', 'id': 1}}) is None


def test_library_update_ignores_other_types():
    assert watch_sync.library_update({'item': {'type': 'tvshow', 'id': 1}, 'playcount': 1}) is None


def test_watched_enough():
    assert watch_sync.watched_enough(90, 100)
    assert not watch_sync.watched_enough(50, 100)
    assert not watch_sync.watched_enough(10, 0)


def test_repeats_blocks_the_same_message_twice():
    clock = [1000.0]
    repeats = watch_sync.Repeats(seconds=600, clock=lambda: clock[0])
    assert repeats.fresh('a', True)
    assert not repeats.fresh('a', True)         # same state, too soon
    assert repeats.fresh('a', False)            # other state goes through
    clock[0] += 601
    assert repeats.fresh('a', True)             # window expired


def test_playback_watch_reports_finished_once():
    watch = watch_sync.PlaybackWatch()
    watch.start('ep1')
    watch.sample(95, 100)
    assert watch.finish() == 'ep1'
    assert watch.finish() is None               # only once


def test_playback_watch_unfinished_returns_none():
    watch = watch_sync.PlaybackWatch()
    watch.start('ep1')
    watch.sample(10, 100)
    assert watch.finish() is None


def test_strm_target_reads_plugin_line():
    files = {'/lib/a.strm': '#comment\nplugin://plugin.video.nlziet/?mode=play&id=9\n'}
    assert watch_sync.strm_target('/lib/a.strm', files.get) == 'plugin://plugin.video.nlziet/?mode=play&id=9'


def test_strm_target_passes_plugin_url_through():
    assert watch_sync.strm_target('plugin://x/?a=1', None) == 'plugin://x/?a=1'


def test_strm_target_ignores_other_files():
    assert watch_sync.strm_target('/movies/a.mkv', None) == ''


def test_plugin_params():
    params = watch_sync.plugin_params('plugin://plugin.video.nlziet/?mode=play&id=5', 'plugin.video.nlziet')
    assert params == {'mode': 'play', 'id': '5'}
    assert watch_sync.plugin_params('plugin://other/?x=1', 'plugin.video.nlziet') == {}


def test_playing_value_round_trip():
    value = watch_sync.playing_value('ep9', now=1000)
    assert watch_sync.parse_playing(value, now=1000) == 'ep9'


def test_parse_playing_rejects_stale_note():
    value = watch_sync.playing_value('ep9', now=1000)
    assert watch_sync.parse_playing(value, now=1000 + 999) == ''


def test_parse_playing_rejects_empty():
    assert watch_sync.parse_playing('', now=1) == ''
    assert watch_sync.parse_playing(None, now=1) == ''


def test_library_file_uses_rpc():
    calls = []

    def rpc(method, params):
        calls.append((method, params))
        return {'episodedetails': {'file': '/lib/a.strm'}}

    assert watch_sync.library_file('episode', 3, rpc) == '/lib/a.strm'
    assert calls[0][0] == 'VideoLibrary.GetEpisodeDetails'
