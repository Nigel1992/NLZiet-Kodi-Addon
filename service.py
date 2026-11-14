import os
import time

import xbmc
import xbmcaddon

from resources.lib import library as library_mod
from resources.lib import library_art
from resources.lib import logo_cache as logo_cache_mod
from resources.lib import metadata as metadata_mod
from resources.lib import watch_sync
from resources.lib import diagnostics as diagnostics_mod
from resources.lib import playback_extras
from resources.lib import trakt_status

ADDON = xbmcaddon.Addon()


ADDON_ID = 'plugin.video.nlziet'


def _maybe_play_next(content_id):
    """Binge: start the next episode, unless the user pressed Stop after this
    one, or the Up Next add-on is installed (then Up Next handles it)."""
    if not _setting_on('autoplay_next', False):
        return
    import xbmcgui
    if xbmcgui.Window(10000).getProperty('nlziet.stop_after') == '1':
        return
    if xbmc.getCondVisibility('System.HasAddon(service.upnext)'):
        return
    xbmc.executebuiltin('RunPlugin(plugin://{}/?mode=play_next&id={}&background=1)'.format(
        ADDON_ID, content_id))


def _send_watched(content_id, watched):
    """Ask the plugin to tell NLZiet (runs in its own process)."""
    if not content_id or not _setting_on('watched_to_service', True):
        return
    if not REPEATS.fresh(str(content_id), watched):
        return
    xbmc.log('NLZiet service: watched={} for {}'.format(watched, content_id), xbmc.LOGINFO)
    xbmc.executebuiltin('RunPlugin(plugin://{}/?mode=remote_watched&id={}&watched={}&background=1)'.format(
        ADDON_ID, content_id, 1 if watched else 0))


def _rpc(method, params):
    import json
    answer = json.loads(xbmc.executeJSONRPC(json.dumps(
        {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    return answer.get('result') or {}


def _read_text(path):
    import xbmcvfs
    handle = xbmcvfs.File(path)
    try:
        return handle.read()
    finally:
        handle.close()


class LibraryMonitor(xbmc.Monitor):
    """Notices library scans and watched/unwatched changes in Kodi's library."""

    def __init__(self):
        super().__init__()
        self.scan_finished = False

    def onScanFinished(self, library):
        if library == 'video':
            self.scan_finished = True

    def onNotification(self, sender, method, data):
        if method != 'VideoLibrary.OnUpdate':
            return
        change = watch_sync.library_update(data)
        if not change:
            return
        media_type, dbid, watched = change
        try:
            path = watch_sync.library_file(media_type, dbid, _rpc)
            params = watch_sync.plugin_params(watch_sync.strm_target(path, _read_text), ADDON_ID)
            if params.get('mode') == 'play' and params.get('id'):
                _send_watched(params['id'], watched)
        except Exception as exc:
            xbmc.log('NLZiet service: library watched check failed: {}'.format(exc), xbmc.LOGWARNING)


class PlaybackFollower(xbmc.Player):
    """Follows videos the add-on starts, to send "watched" at the end."""

    def __init__(self):
        super().__init__()
        self.watch = watch_sync.PlaybackWatch()

    def onAVStarted(self):
        import xbmcgui
        window = xbmcgui.Window(10000)
        prop = watch_sync.PLAYING_PROPERTY.format('nlziet')
        self.watch.start(watch_sync.parse_playing(window.getProperty(prop)))
        window.clearProperty(prop)
        window.clearProperty('nlziet.stop_after')
        self.sample()
        self._scrobble('start')
        # Preferred audio/subtitle language.
        audio = _setting('preferred_audio', 'off')
        sub = _setting('preferred_subtitle', 'off')
        if audio not in ('', 'off') or sub not in ('', 'off'):
            try:
                result = playback_extras.apply_language(_rpc, audio, sub)
                xbmc.log('NLZiet service: language {}'.format(result), xbmc.LOGINFO)
            except Exception as exc:
                xbmc.log('NLZiet service: language select failed: {}'.format(exc), xbmc.LOGWARNING)

    def sample(self):
        if not self.watch.key:
            return
        try:
            if self.isPlayingVideo():
                self.watch.sample(self.getTime(), self.getTotalTime())
        except RuntimeError:
            pass

    def _done(self, natural):
        self._scrobble('stop')
        key = self.watch.key
        try:
            share = max(0.5, min(0.99, _int_setting('watched_threshold', 90) / 100.0))
        except Exception:
            share = 0.9
        watched = self.watch.finish(share)
        if watched:
            _send_watched(watched, True)
        if natural and key:
            _maybe_play_next(key)

    def onPlayBackStopped(self):
        self._done(False)

    def onPlayBackEnded(self):
        self._done(True)

    def _scrobble(self, action):
        if not _setting_on('trakt_scrobble', False):
            return
        try:
            import json, xbmcaddon, xbmcgui
            trakt_addon = xbmcaddon.Addon('script.trakt')
        except Exception:
            return
        token = trakt_status.access_token(trakt_addon)
        client_id = trakt_status.official_client_id(trakt_addon.getAddonInfo('path') or '')
        if not token or not client_id:
            return
        raw = xbmcgui.Window(10000).getProperty('nlziet.now_meta')
        try:
            meta = json.loads(raw) if raw else {}
        except ValueError:
            meta = {}
        media = trakt_status.scrobble_media(meta.get('showtitle'), meta.get('season'),
                                            meta.get('episode'), meta.get('title'), meta.get('year'))
        if not media:
            return
        progress = 0.0
        if self.watch.total:
            progress = max(0.0, min(100.0, self.watch.position / self.watch.total * 100.0))
        try:
            trakt_status.scrobble(token, client_id, action, media, progress)
        except Exception:
            pass


MONITOR = LibraryMonitor()
REPEATS = watch_sync.Repeats()

# Give Kodi time to finish starting before the first library update.
LIBRARY_STARTUP_DELAY = 120


def _setting(name, default=''):
    try:
        value = ADDON.getSetting(name)
    except Exception:
        return default
    return default if value in ('', None) else value


def _setting_on(name, default=False):
    value = _setting(name, None)
    if value is None:
        return default
    return value in ('true', '1', 'yes', True)


def _int_setting(name, default=0):
    try:
        return int(_setting(name, default))
    except (ValueError, TypeError):
        return default


def _sync_now():
    """Trigger both cloud syncs through the plugin (runs in its own process)."""
    try:
        if _setting_on('watch_later_sync'):
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.nlziet/?mode=sync_watch_later&background=1)')
    except Exception as exc:
        xbmc.log('NLZiet service: watch-later sync trigger failed: {}'.format(exc), xbmc.LOGWARNING)
    try:
        if _setting_on('watch_later_sync'):
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.nlziet/?mode=sync_my_series&background=1)')
    except Exception as exc:
        xbmc.log('NLZiet service: my-series sync trigger failed: {}'.format(exc), xbmc.LOGWARNING)


def _library_update_due():
    """True when the library has items and the last update is old enough."""
    if not _setting_on('library_auto_update', True):
        return False
    try:
        profile = library_mod.translate_path(ADDON.getAddonInfo('profile')) or ''
        store = library_mod.LibraryStore(os.path.join(profile, 'library.json'))
    except Exception:
        return False
    if not store.section('series') and not store.section('movie') and not _setting_on('library_lists_sync', False):
        return False
    hours = max(1, _int_setting('library_update_hours', 12))
    last = store.data.get('last_update') or 0
    return (time.time() - last) >= hours * 3600


def _daily_check_due():
    if not _setting_on('daily_check', True):
        return False
    path = os.path.join(library_mod.translate_path(ADDON.getAddonInfo('profile')) or '', 'daily_check.json')
    try:
        last = os.path.getmtime(path)
    except OSError:
        last = 0
    return diagnostics_mod.daily_due(last, time.time())


def main():
    xbmc.log('NLZiet service: started', xbmc.LOGINFO)
    started = time.time()
    last_sync = time.time()
    last_library_trigger = 0
    last_minute = 0
    last_daily = 0
    last_notify = 0
    legacy_checked = False
    player = PlaybackFollower()
    while not MONITOR.abortRequested():
        # Short ticks so the playback position is known when a video stops.
        if MONITOR.waitForAbort(5):
            break
        player.sample()
        now = time.time()
        if now - last_minute < 60:
            continue
        last_minute = now

        if (now - started >= LIBRARY_STARTUP_DELAY + 300 and now - last_daily >= 6 * 3600
                and not xbmc.Player().isPlaying() and _daily_check_due()):
            last_daily = now
            xbmc.executebuiltin('RunPlugin(plugin://{}/?mode=daily_check&background=1)'.format(ADDON_ID))

        if (now - started >= LIBRARY_STARTUP_DELAY and now - last_notify >= 3 * 3600
                and not xbmc.Player().isPlaying() and _setting_on('notify_new_episodes', True)):
            last_notify = now
            xbmc.executebuiltin('RunPlugin(plugin://{}/?mode=notify_new&background=1)'.format(ADDON_ID))

        # A scan asked for while Kodi was busy runs as soon as it is free.
        library_art.run_pending_scan(library_mod.scan_flag_path())

        # Look up logos for titles seen in browse lists, a few at a time.
        if not xbmc.Player().isPlaying():
            try:
                folder = library_mod.translate_path(ADDON.getAddonInfo('profile')) or ''
                if os.path.isfile(os.path.join(folder, 'logo_queue.json')):
                    enricher = metadata_mod.Enricher(os.path.join(folder, 'metadata_cache.json'),
                                                     tmdb_key=_setting('tmdb_api_key', ''),
                                                     user_agent='plugin.video.nlziet')
                    logo_cache_mod.LogoCache(folder).process(enricher, limit=15,
                                                             should_stop=MONITOR.abortRequested)
                    enricher.save()
            except Exception as exc:
                xbmc.log('NLZiet service: logo lookup failed: {}'.format(exc), xbmc.LOGWARNING)

        if MONITOR.scan_finished:
            MONITOR.scan_finished = False
            library_file = os.path.join(library_mod.translate_path(ADDON.getAddonInfo('profile')) or '', 'library.json')
            if os.path.isfile(library_file):
                # New titles were just scanned: give them their posters.
                xbmc.executebuiltin('RunPlugin(plugin://plugin.video.nlziet/?mode=repair_library_art&background=1)')

        interval = _int_setting('auto_sync_interval', 0)
        if interval > 0 and now - last_sync >= interval * 60:
            last_sync = now
            _sync_now()

        # Move a library exported by 1.6.x into the add-on folder once.
        if not legacy_checked and now - started >= LIBRARY_STARTUP_DELAY and not xbmc.Player().isPlaying():
            legacy_checked = True
            if os.path.isdir(library_mod.LEGACY_TV_PATH):
                last_library_trigger = now
                xbmc.executebuiltin('RunPlugin(plugin://plugin.video.nlziet/?mode=library_update&background=1)')
                continue

        # Retry at most once an hour if an update did not record itself.
        if (now - started >= LIBRARY_STARTUP_DELAY and now - last_library_trigger >= 3600
                and not xbmc.Player().isPlaying() and _library_update_due()):
            last_library_trigger = now
            xbmc.log('NLZiet service: starting library update', xbmc.LOGINFO)
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.nlziet/?mode=library_update&background=1)')

    xbmc.log('NLZiet service: stopped', xbmc.LOGINFO)


if __name__ == '__main__':
    main()
