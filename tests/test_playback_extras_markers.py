"""Tests for the chapter/marker helpers added to playback_extras."""
from resources.lib import playback_extras as pe


def test_markers_from_chapters():
    chapters = [
        {'startTimeInSeconds': 0, 'title': 'Recap'},
        {'startTimeInSeconds': 30, 'title': 'Intro'},
        {'startTimeInSeconds': 95, 'title': 'Aflevering'},
    ]
    markers = pe.markers_from_chapters(chapters)
    assert markers['recap'] == (0, 30)
    assert markers['intro'] == (30, 95)


def test_markers_from_chapters_accepts_wrapper_dict():
    data = {'chapters': [{'startTimeInSeconds': 10, 'title': 'Intro'},
                         {'startTimeInSeconds': 60, 'title': 'Deel 1'}]}
    assert pe.markers_from_chapters(data)['intro'] == (10, 60)


def test_markers_from_chapters_dutch_words():
    chapters = [{'startTimeInSeconds': 0, 'title': 'Terugblik'},
                {'startTimeInSeconds': 20, 'title': 'Begingeneriek'},
                {'startTimeInSeconds': 50, 'title': 'Start'}]
    markers = pe.markers_from_chapters(chapters)
    assert 'recap' in markers and 'intro' in markers


def test_markers_from_chapters_empty():
    assert pe.markers_from_chapters([]) == {}
    assert pe.markers_from_chapters(None) == {}


def test_chapter_titles():
    assert pe.chapter_titles([{'title': 'Intro'}, {'title': 'Deel 1'}]) == ['Intro', 'Deel 1']


def test_apply_language_selects_audio_and_subtitle():
    calls = []

    def rpc(method, params):
        calls.append((method, params))
        if method == 'Player.GetProperties':
            return {'audiostreams': [{'index': 0, 'language': 'eng'}, {'index': 1, 'language': 'dut'}],
                    'subtitles': [{'index': 0, 'language': 'dut'}]}
        return {}

    result = pe.apply_language(rpc, 'nl', 'nl')
    assert 'audio=nl' in result and 'subtitle=nl' in result
    assert ('Player.SetAudioStream', {'playerid': 1, 'stream': 1}) in calls
    assert ('Player.SetSubtitle', {'playerid': 1, 'subtitle': 0, 'enable': True}) in calls


def test_apply_language_off_does_nothing():
    assert pe.apply_language(lambda m, p: {}, 'off', 'off') == 'nothing'


def test_apply_language_original_audio_skipped():
    def rpc(method, params):
        return {'audiostreams': [{'index': 0, 'language': 'eng'}], 'subtitles': []}
    assert pe.apply_language(rpc, 'original', 'off') == 'nothing'


def test_apply_language_no_match():
    def rpc(method, params):
        return {'audiostreams': [{'index': 0, 'language': 'eng'}], 'subtitles': []}
    assert pe.apply_language(rpc, 'nl', 'off') == 'no match'
