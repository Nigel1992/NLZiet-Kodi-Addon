"""Tests for the cross-device resume push (resources/lib/library_resume.py)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resources.lib import library_resume as lr

NL = 'plugin.video.nlziet'
VL = 'plugin.video.videoland.nl'


# ------------------------------------------------------------ plugin_content_id
def test_plugin_content_id_from_url():
    url = 'plugin://plugin.video.nlziet/?mode=play&id=ABC123&inlib=1'
    assert lr.plugin_content_id(url, NL, 'id') == 'ABC123'


def test_plugin_content_id_from_videoland_url():
    url = 'plugin://plugin.video.videoland.nl/?action=play&video_id=42&inlib=1'
    assert lr.plugin_content_id(url, VL, 'video_id') == '42'


def test_plugin_content_id_from_strm_contents():
    # A .strm file holds the plugin URL plus a trailing newline.
    text = 'plugin://plugin.video.nlziet/?mode=play&id=ABC123&inlib=1\n'
    assert lr.plugin_content_id(text, NL, 'id') == 'ABC123'


def test_plugin_content_id_requires_inlib():
    url = 'plugin://plugin.video.nlziet/?mode=play&id=ABC123'
    assert lr.plugin_content_id(url, NL, 'id') is None


def test_plugin_content_id_ignores_foreign_addon():
    assert lr.plugin_content_id('plugin://plugin.video.other/?id=1&inlib=1', NL, 'id') is None
    assert lr.plugin_content_id('', NL, 'id') is None
    assert lr.plugin_content_id(None, NL, 'id') is None


def test_is_strm():
    assert lr.is_strm('/path/S01E01.strm')
    assert lr.is_strm('/path/S01E01.STRM')
    assert not lr.is_strm('plugin://plugin.video.nlziet/?id=1&inlib=1')
    assert not lr.is_strm('')


# ------------------------------------------------------------ extract_progress
def test_extract_progress_position_and_duration():
    assert lr.extract_progress({'tcResume': 600, 'duration': 1800}) == (600, 1800)


def test_extract_progress_nested_dicts():
    entry = {'content': {'id': 'x'}, 'progress': {'position': 300}, 'video': {'length': 1200}}
    assert lr.extract_progress(entry) == (300, 1200)


def test_extract_progress_percentage_fraction():
    # 0.25 fraction of a 2000s video -> 500s.
    assert lr.extract_progress({'progress': 0.25, 'duration': 2000}) == (500, 2000)


def test_extract_progress_percentage_out_of_hundred():
    assert lr.extract_progress({'percentage': 50, 'duration': 2000}) == (1000, 2000)


def test_extract_progress_position_only():
    assert lr.extract_progress({'position': 450}) == (450, 0)


def test_extract_progress_none_when_empty():
    assert lr.extract_progress({'title': 'no numbers here'}) is None
    assert lr.extract_progress({}) is None


def test_extract_progress_ignores_booleans():
    assert lr.extract_progress({'position': True, 'duration': False}) is None


# -------------------------------------------------------------- resume_call
def test_resume_call_builds_setdetails():
    item = {'episodeid': 7, 'runtime': 1800, 'resume': {'position': 0}}
    call = lr.resume_call('VideoLibrary.SetEpisodeDetails', 'episodeid', item, 600, 1800)
    assert call == ('VideoLibrary.SetEpisodeDetails',
                    {'episodeid': 7, 'resume': {'position': 600, 'total': 1800}})


def test_resume_call_falls_back_to_runtime_for_total():
    # Service gave no duration (0); library runtime (seconds) is used instead.
    item = {'episodeid': 7, 'runtime': 1800, 'resume': {'position': 0}}
    call = lr.resume_call('VideoLibrary.SetEpisodeDetails', 'episodeid', item, 600, 0)
    assert call[1]['resume']['total'] == 1800


def test_resume_call_skips_tiny_position():
    item = {'episodeid': 7, 'runtime': 1800, 'resume': {'position': 0}}
    assert lr.resume_call('VideoLibrary.SetEpisodeDetails', 'episodeid', item, 30, 1800) is None


def test_resume_call_skips_near_end():
    item = {'episodeid': 7, 'runtime': 1800, 'resume': {'position': 0}}
    assert lr.resume_call('VideoLibrary.SetEpisodeDetails', 'episodeid', item, 1750, 1800) is None


def test_resume_call_skips_when_already_close():
    item = {'episodeid': 7, 'runtime': 1800, 'resume': {'position': 610}}
    assert lr.resume_call('VideoLibrary.SetEpisodeDetails', 'episodeid', item, 600, 1800) is None


def test_resume_call_none_without_total():
    item = {'episodeid': 7, 'runtime': 0, 'resume': {}}
    assert lr.resume_call('VideoLibrary.SetEpisodeDetails', 'episodeid', item, 600, 0) is None


def test_resume_call_includes_lastplayed_when_given():
    item = {'episodeid': 7, 'runtime': 1800, 'resume': {'position': 0}}
    call = lr.resume_call('VideoLibrary.SetEpisodeDetails', 'episodeid', item, 600, 1800,
                          '2026-11-14 20:15:00')
    assert call[1]['lastplayed'] == '2026-11-14 20:15:00'
    assert call[1]['resume'] == {'position': 600, 'total': 1800}


def test_resume_call_omits_lastplayed_when_absent():
    item = {'episodeid': 7, 'runtime': 1800, 'resume': {'position': 0}}
    call = lr.resume_call('VideoLibrary.SetEpisodeDetails', 'episodeid', item, 600, 1800)
    assert 'lastplayed' not in call[1]


# --------------------------------------------------------------- build_calls
def _cid_for(item):
    return lr.plugin_content_id(item.get('file'), NL, 'id')


def test_build_calls_matches_by_content_id():
    episodes = [
        {'episodeid': 1, 'file': 'plugin://plugin.video.nlziet/?id=AAA&inlib=1&x=1',
         'runtime': 1800, 'resume': {'position': 0}},
        {'episodeid': 2, 'file': 'plugin://plugin.video.nlziet/?id=BBB&inlib=1',
         'runtime': 1800, 'resume': {'position': 0}},
        # Not ours (no inlib) -> skipped even if a position exists.
        {'episodeid': 3, 'file': 'plugin://plugin.video.nlziet/?id=AAA',
         'runtime': 1800, 'resume': {'position': 0}},
    ]
    positions = {'AAA': (600, 1800)}
    calls = lr.build_calls(episodes, positions, 'episodeid',
                           'VideoLibrary.SetEpisodeDetails', _cid_for)
    assert calls == [('VideoLibrary.SetEpisodeDetails',
                      {'episodeid': 1, 'resume': {'position': 600, 'total': 1800}})]


def test_build_calls_passes_lastplayed_through():
    episodes = [{'episodeid': 1, 'file': 'plugin://plugin.video.nlziet/?id=AAA&inlib=1',
                 'runtime': 1800, 'resume': {'position': 0}}]
    calls = lr.build_calls(episodes, {'AAA': (600, 1800)}, 'episodeid',
                           'VideoLibrary.SetEpisodeDetails', _cid_for, '2026-11-14 20:15:00')
    assert calls[0][1]['lastplayed'] == '2026-11-14 20:15:00'


def test_build_calls_empty_when_no_positions():
    episodes = [{'episodeid': 1, 'file': 'plugin://plugin.video.nlziet/?id=AAA&inlib=1',
                 'runtime': 1800, 'resume': {'position': 0}}]
    assert lr.build_calls(episodes, {}, 'episodeid',
                          'VideoLibrary.SetEpisodeDetails', _cid_for) == []
    assert lr.build_calls([], {'AAA': (600, 1800)}, 'episodeid',
                          'VideoLibrary.SetEpisodeDetails', _cid_for) == []
