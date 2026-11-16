"""Extras while a video plays: Up Next, intro/recap skipping, credits timing.

* **Up Next**: when the Up Next add-on (service.upnext) is installed, the
  next episode is announced to it; near the end Up Next shows
  "Next episode in 10 seconds".
* **Intro/recap skipping**: when the stream data carries marker times for an
  intro, recap or credits, a "Skip intro?" question appears at the right
  moment. Whether the services send such markers is logged once per video
  ("markers found: ..."), so a Kodi log shows if the data exists.

Shared by the NLZiet and Videoland add-ons (keep both copies identical).
"""

import binascii
import json
import threading
import time

try:
    import xbmc
except ImportError:  # pragma: no cover - outside Kodi
    xbmc = None

MARKER_WORDS = {
    'intro': ('intro', 'opening', 'openingcredits', 'skipintro', 'begingeneriek', 'leader', 'openingstune'),
    'recap': ('recap', 'previously', 'samenvatting', 'terugblik', 'eerderin', 'vorigeaflevering'),
    'credits': ('credits', 'outro', 'endcredits', 'closingcredits', 'aftiteling', 'eindgeneriek'),
}
START_KEYS = ('start', 'begin', 'from', 'starttime', 'start_time', 'startoffset', 'in', 'offset', 'tcin')
END_KEYS = ('end', 'stop', 'to', 'endtime', 'end_time', 'endoffset', 'out', 'tcout')


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        parts = value.strip().split(':')
        try:
            if len(parts) > 1:
                seconds = 0.0
                for part in parts:
                    seconds = seconds * 60 + float(part)
                return seconds
            return float(value)
        except ValueError:
            return None
    return None


def _kind_of(name):
    name = str(name or '').lower().replace('-', '').replace('_', '').replace(' ', '')
    for kind, words in MARKER_WORDS.items():
        if any(word in name for word in words):
            return kind
    return None


def _span(value):
    """(start, end) from a dict like {"start": 30, "end": 95}."""
    if not isinstance(value, dict):
        return None
    lowered = {str(k).lower().replace('-', '_'): v for k, v in value.items()}
    start = next((_number(lowered[k]) for k in START_KEYS if k in lowered and _number(lowered[k]) is not None), None)
    end = next((_number(lowered[k]) for k in END_KEYS if k in lowered and _number(lowered[k]) is not None), None)
    if start is None and end is None:
        return None
    return start, end


def find_markers(data, duration=None, depth=0):
    """Return {"intro": (start, end), "recap": ..., "credits": ...} found
    anywhere in ``data``. Times in milliseconds are converted to seconds."""
    found = {}
    if depth > 12:
        return found
    if isinstance(data, dict):
        marker_type = _kind_of(data.get('type') or data.get('kind') or data.get('name') or data.get('category'))
        span = _span(data)
        if marker_type and span:
            found.setdefault(marker_type, span)
        for key, value in data.items():
            kind = _kind_of(key)
            if kind:
                span = _span(value)
                if span:
                    found.setdefault(kind, span)
                elif _number(value) is not None and str(key).lower().endswith(('start', 'begin')):
                    found.setdefault(kind, (_number(value), None))
                elif _number(value) is not None and str(key).lower().endswith(('end', 'stop')):
                    start = found.get(kind, (None, None))[0]
                    found[kind] = (start, _number(value))
            for kind_found, span_found in find_markers(value, duration, depth + 1).items():
                found.setdefault(kind_found, span_found)
    elif isinstance(data, list):
        for value in data:
            for kind_found, span_found in find_markers(value, duration, depth + 1).items():
                found.setdefault(kind_found, span_found)
    if depth == 0 and found:
        limit = duration or 0
        scaled = {}
        for kind, (start, end) in found.items():
            values = [v for v in (start, end) if v is not None]
            if limit and values and max(values) > limit * 5:  # milliseconds
                start = start / 1000.0 if start is not None else None
                end = end / 1000.0 if end is not None else None
            scaled[kind] = (start, end)
        found = scaled
    return found


def markers_from_chapters(chapters):
    """Markers from a chapter list like NLZiet's ``/v7/chapters`` answer:
    ``[{"startTimeInSeconds": 0, "title": "Intro"}, ...]``. A chapter ends
    where the next one starts."""
    if isinstance(chapters, dict):
        chapters = chapters.get('chapters')
    if not isinstance(chapters, list):
        return {}
    rows = []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        start = _number(chapter.get('startTimeInSeconds', chapter.get('start')))
        if start is None:
            continue
        rows.append((start, chapter.get('title') or chapter.get('name') or chapter.get('type') or ''))
    rows.sort(key=lambda row: row[0])
    found = {}
    for index, (start, title) in enumerate(rows):
        kind = _kind_of(title)
        if not kind or kind in found:
            continue
        end = rows[index + 1][0] if index + 1 < len(rows) else None
        found[kind] = (start, end)
    return found


def markers_from_typed_chapters(chapters):
    """Markers from a typed chapter list like Videoland's ``video.chapters``:
    ``[{"tcStart": 0, "tcEnd": 75, "type": "intro"},
       {"tcStart": 1484, "tcEnd": 1498, "type": "ending_credits"}]``.
    Each entry names its own kind and both ends; times are in seconds."""
    if isinstance(chapters, dict):
        chapters = chapters.get('chapters')
    if not isinstance(chapters, list):
        return {}
    found = {}
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        kind = _kind_of(chapter.get('type') or chapter.get('title') or chapter.get('name'))
        if not kind or kind in found:
            continue
        start = _number(chapter.get('tcStart', chapter.get('tcIn', chapter.get('start'))))
        if start is None:
            continue
        end = _number(chapter.get('tcEnd', chapter.get('tcOut', chapter.get('end'))))
        found[kind] = (start, end)
    return found


def chapter_titles(chapters):
    """The chapter titles, for the log (shows what a service calls them)."""
    if isinstance(chapters, dict):
        chapters = chapters.get('chapters')
    if not isinstance(chapters, list):
        return []
    return [str(c.get('title') or '') for c in chapters if isinstance(c, dict)]


def marker_summary(markers):
    if not markers:
        return 'none'
    return ', '.join('{} {}-{}'.format(kind, int(s) if s is not None else '?', int(e) if e is not None else '?')
                     for kind, (s, e) in sorted(markers.items()))


# ---------------------------------------------------------------- Up Next ---

def upnext_available():
    if xbmc is None:
        return False
    try:
        return bool(xbmc.getCondVisibility('System.HasAddon(service.upnext)'))
    except Exception:
        return False


def episode_info(title, showtitle, season, episode, plot='', art=None, runtime=0, firstaired='', episode_id=None):
    return {
        'episodeid': episode_id or '{}-{}x{}'.format(showtitle, season, episode),
        'tvshowid': showtitle,
        'title': title or '',
        'art': art or {},
        'season': int(season or 0),
        'episode': int(episode or 0),
        'showtitle': showtitle or '',
        'plot': plot or '',
        'playcount': 0,
        'rating': None,
        'firstaired': firstaired or '',
        'runtime': int(runtime or 0),
    }


def upnext_payload(current, following, play_url, notification_time=None):
    data = {'current_episode': current, 'next_episode': following, 'play_url': play_url}
    if notification_time:
        data['notification_time'] = int(max(5, notification_time))
    return binascii.hexlify(json.dumps(data).encode('utf-8')).decode('ascii')


def send_upnext(addon_id, current, following, play_url, notification_time=None):
    """Tell Up Next about the next episode (needs service.upnext)."""
    if xbmc is None or not upnext_available():
        return False
    message = {'jsonrpc': '2.0', 'method': 'JSONRPC.NotifyAll', 'id': 1, 'params': {
        'sender': addon_id + '.SIGNAL', 'message': 'upnext_data',
        'data': [upnext_payload(current, following, play_url, notification_time)]}}
    try:
        xbmc.executeJSONRPC(json.dumps(message))
        return True
    except Exception:
        return False


# ------------------------------------------------------------ skip markers --

def _match_language(streams, language):
    """Index of the first stream in ``language`` (iso code), or None."""
    language = str(language or '').lower()
    aliases = {'nl': ('nl', 'dut', 'nld', 'nederlands', 'dutch'),
               'en': ('en', 'eng', 'english', 'engels')}.get(language, (language,))
    for stream in streams or []:
        value = str(stream.get('language') or stream.get('name') or '').lower()
        if any(alias and alias in value for alias in aliases):
            return stream.get('index')
    return None


def apply_language(rpc, audio_lang=None, subtitle_lang=None):
    """Pick the preferred audio/subtitle language on the running player.

    ``rpc(method, params)`` runs JSON-RPC. ``audio_lang``/``subtitle_lang`` are
    'nl', 'en', 'original' or a falsy value ('off'/None) to leave it alone.
    Returns a short log string of what changed.
    """
    audio_lang = None if str(audio_lang or 'off') in ('off', 'original', '') else audio_lang
    want_sub = str(subtitle_lang or 'off') not in ('off', '')
    if not audio_lang and not want_sub:
        return 'nothing'
    try:
        props = rpc('Player.GetProperties',
                    {'playerid': 1, 'properties': ['audiostreams', 'subtitles', 'currentaudiostream']}) or {}
    except Exception:
        return 'no player'
    done = []
    if audio_lang:
        index = _match_language(props.get('audiostreams'), audio_lang)
        if index is not None:
            try:
                rpc('Player.SetAudioStream', {'playerid': 1, 'stream': int(index)})
                done.append('audio=' + str(audio_lang))
            except Exception:
                pass
    if want_sub:
        index = _match_language(props.get('subtitles'), subtitle_lang)
        if index is not None:
            try:
                rpc('Player.SetSubtitle', {'playerid': 1, 'subtitle': int(index), 'enable': True})
                done.append('subtitle=' + str(subtitle_lang))
            except Exception:
                pass
    return ', '.join(done) or 'no match'


def subtitles_present(rpc):
    """True when the running player already has one or more subtitle tracks."""
    try:
        props = rpc('Player.GetProperties', {'playerid': 1, 'properties': ['subtitles']}) or {}
        return bool(props.get('subtitles'))
    except Exception:
        return True   # on doubt, assume present and do nothing


def wait_for_playback(player, timeout=30, monitor=None):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if player.isPlayingVideo():
                return True
        except Exception:
            pass
        if monitor is not None and monitor.waitForAbort(0.5):
            return False
        if monitor is None:
            time.sleep(0.5)
    return False


def _ask_skip(ask, kind, seconds):
    """Call the skip callback, supporting both ``ask(kind)`` and
    ``ask(kind, seconds)`` signatures."""
    try:
        return ask(kind, seconds)
    except TypeError:
        return ask(kind)


def start_skip_watcher(markers, ask, player=None, monitor=None):
    """Offer to skip intro/recap while it plays. ``ask(kind, seconds)`` shows
    the button and returns True to skip; ``seconds`` is how long the part still
    lasts, so the button can stay for the whole intro/recap. Runs in a
    background thread."""
    spans = [(kind, s, e) for kind, (s, e) in markers.items() if kind in ('intro', 'recap') and e]
    if not spans or xbmc is None:
        return None
    player = player or xbmc.Player()
    monitor = monitor or xbmc.Monitor()

    def run():
        if not wait_for_playback(player, monitor=monitor):
            return
        offered = set()
        while not monitor.abortRequested():
            try:
                if not player.isPlayingVideo():
                    return
                now = player.getTime()
            except Exception:
                return
            for kind, start, end in spans:
                start = start or 0
                if kind not in offered and start <= now < end - 3:
                    offered.add(kind)
                    # Keep the button up until the part is over (at least a few
                    # seconds), so it behaves like the streaming apps.
                    seconds = max(5, int(end - now))
                    if _ask_skip(ask, kind, seconds):
                        try:
                            player.seekTime(float(end))
                        except Exception:
                            pass
            if len(offered) == len(spans) or monitor.waitForAbort(1):
                return

    return start_background(run, 'SkipMarkers')


def start_next_prompt(play_fn, ask, credits_start=None, lead=45, player=None, monitor=None):
    """Offer the next episode near the end, without the Up Next add-on.

    ``ask()`` shows the question and returns True to play the next episode;
    ``play_fn()`` then starts it. The prompt appears at ``credits_start`` when
    that marker is known, otherwise ``lead`` seconds before the end. Runs in a
    background thread and asks at most once."""
    if xbmc is None:
        return None
    player = player or xbmc.Player()
    monitor = monitor or xbmc.Monitor()

    def run():
        if not wait_for_playback(player, monitor=monitor):
            return
        asked = False
        seen_before = False  # saw the video playing before the trigger point
        while not monitor.abortRequested():
            try:
                if not player.isPlayingVideo():
                    return
                now = player.getTime()
                total = player.getTotalTime()
            except Exception:
                return
            if total and total > 0:
                # Only trust a credits marker in the back half of the video;
                # a stray early marker should not pop the prompt mid-episode.
                if credits_start and total * 0.5 < credits_start < total - 10:
                    trigger = credits_start
                else:
                    trigger = max(0, total - lead)
                # Require that the video was seen playing before the trigger, so
                # the prompt can't fire on a just-started next episode that, for
                # a moment during the hand-over, still reports the previous
                # episode's near-the-end position.
                if now < trigger - 1:
                    seen_before = True
                # Don't pop up in the last few seconds; there's no time to react.
                if not asked and seen_before and now >= trigger and total - now > 5:
                    asked = True
                    try:
                        xbmc.log('Next episode prompt at {:.0f}s of {:.0f}s'.format(now, total),
                                 xbmc.LOGINFO)
                    except Exception:
                        pass
                    try:
                        if ask():
                            play_fn()
                    except Exception:
                        pass
                    return
            if monitor.waitForAbort(1):
                return

    return start_background(run, 'NextEpisode')


def start_background(target, name):
    """Run ``target`` next to playback. Not a daemon thread: a plugin call
    ends right after it hands Kodi the stream, and Python would then stop
    daemon threads before they did anything. These threads end by themselves
    when playback stops."""
    thread = threading.Thread(target=target, name=name)
    thread.daemon = False
    thread.start()
    return thread
