import importlib
import os
import sys

from resources.lib import subtitles


TELETEXT_VTT = """WEBVTT

00:00:00.320 --> 00:00:01.800 line:90% position:50% align:center
<c.white>888</c>

00:00:20.040 --> 00:00:23.080 line:90% position:50% align:center
<c.yellow>Goedenavond,</c>
<c.yellow>hartelijk welkom bij 2 voor 12.</c>

00:00:37.240 --> 00:00:39.240 line:90% position:50% align:center
<c.yellow>Hallo, hartelijk welkom. </c><c.white>Hallo.</c>

00:34:43.480 --> 00:34:47.240 line:90% position:50% align:center
<c.white>NPO ONDERTITELING TT888, 2026,</c>
<c.white>informatie: service.npo.nl</c>
"""

CLEAN_VTT = """WEBVTT

00:00:00.366 --> 00:00:03.566 align:center line:75% position:50% size:80%
Wat voorafging
in Goede Tijden,Slechte Tijden:

00:00:03.666 --> 00:00:05.500 align:center line:83% position:50% size:80%
Te hoge bloeddruk.
"""


def test_clean_webvtt_strips_page_number_and_colour_tags():
    cleaned = subtitles.clean_webvtt(TELETEXT_VTT)

    assert cleaned is not None
    assert '888' not in cleaned
    assert '<c.' not in cleaned
    assert '</c>' not in cleaned
    assert 'Goedenavond,' in cleaned
    assert 'hartelijk welkom bij 2 voor 12.' in cleaned
    # Inline colour switch keeps both spoken parts on the same line.
    assert 'Hallo, hartelijk welkom. Hallo.' in cleaned
    # Timings of the real dialogue are preserved, the page-number cue is gone.
    assert '00:00:20.040 --> 00:00:23.080' in cleaned
    assert '00:00:00.320 --> 00:00:01.800' not in cleaned
    # The teletext service banner at the end is dropped as well.
    assert 'TT888' not in cleaned
    assert 'service.npo.nl' not in cleaned
    assert '00:34:43.480 --> 00:34:47.240' not in cleaned


def test_clean_webvtt_returns_none_when_nothing_to_clean():
    assert subtitles.clean_webvtt(CLEAN_VTT) is None
    assert subtitles.clean_webvtt('') is None
    assert subtitles.clean_webvtt('1\n00:00:01,000 --> 00:00:02,000\nHallo\n') is None


class _FakeResponse:
    def __init__(self, body):
        self._body = body.encode('utf-8')

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_prepare_subtitle_urls_cleans_and_caches(tmp_path, monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request.full_url)
        return _FakeResponse(TELETEXT_VTT)

    monkeypatch.setattr(subtitles.urllib.request, 'urlopen', fake_urlopen)

    url = 'https://cdn.npoplayer.nl/subtitles/nl/BV_1.vtt'
    prepared = subtitles.prepare_subtitle_urls([url], cache_dir=str(tmp_path))

    assert len(prepared) == 1
    local = prepared[0]
    assert local != url
    assert os.path.exists(local)
    with open(local, encoding='utf-8') as handle:
        content = handle.read()
    assert '888' not in content and '<c.' not in content

    # Second call reuses the cached file instead of downloading again.
    prepared_again = subtitles.prepare_subtitle_urls([url], cache_dir=str(tmp_path))
    assert prepared_again == [local]
    assert calls == [url]


def test_prepare_subtitle_urls_passes_through_untouched_files(tmp_path, monkeypatch):
    monkeypatch.setattr(
        subtitles.urllib.request, 'urlopen',
        lambda request, timeout=None: _FakeResponse(CLEAN_VTT),
    )

    url = 'https://assets.rtl.nl/subtitle_nl.vtt'
    assert subtitles.prepare_subtitle_urls([url], cache_dir=str(tmp_path)) == [url]
    # Non-WebVTT sources are never downloaded.
    other = 'https://example.test/subtitle.srt'
    assert subtitles.prepare_subtitle_urls([other], cache_dir=str(tmp_path)) == [other]


def test_prepare_subtitle_urls_falls_back_on_error(tmp_path, monkeypatch):
    def boom(request, timeout=None):
        raise OSError('network down')

    monkeypatch.setattr(subtitles.urllib.request, 'urlopen', boom)

    url = 'https://cdn.npoplayer.nl/subtitles/nl/BV_2.vtt'
    assert subtitles.prepare_subtitle_urls([url], cache_dir=str(tmp_path)) == [url]


def _import_default(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.nlziet', '42', ''])
    sys.modules.pop('default', None)
    return importlib.import_module('default')


def test_play_item_attaches_cleaned_teletext_subtitle(monkeypatch, kodi_recorder, tmp_path):
    default = _import_default(monkeypatch)
    default.ADDON.settings['subtitles_default'] = 'true'

    class FakeApi:
        user_agent = 'test-agent'

        def get_stream_info(self, content_id, **kwargs):
            return {
                'manifest': 'https://example.test/manifest.mpd',
                'is_drm': False,
                'subtitles': [{'url': 'https://cdn.npoplayer.nl/subtitles/nl/BV_3.vtt'}],
            }

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(
        subtitles.urllib.request, 'urlopen',
        lambda request, timeout=None: _FakeResponse(TELETEXT_VTT),
    )
    monkeypatch.setattr(
        default.xbmcvfs, 'translatePath',
        lambda path: str(tmp_path) if path.startswith('special://') else path,
    )

    default.play_item('episode-3')

    _, succeeded, item = kodi_recorder.resolved_items[-1]
    assert succeeded is True
    assert len(item.subtitles) == 1
    subtitle_path = item.subtitles[0]
    assert subtitle_path != 'https://cdn.npoplayer.nl/subtitles/nl/BV_3.vtt'
    with open(subtitle_path, encoding='utf-8') as handle:
        content = handle.read()
    assert '888' not in content
    assert 'Goedenavond,' in content
