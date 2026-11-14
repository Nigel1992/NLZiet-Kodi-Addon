import os
import time

import xbmc
import xbmcaddon

from resources.lib import library as library_mod
from resources.lib import library_art
from resources.lib import logo_cache as logo_cache_mod
from resources.lib import metadata as metadata_mod

ADDON = xbmcaddon.Addon()


class LibraryMonitor(xbmc.Monitor):
    """Notices when Kodi finished a video library scan."""

    def __init__(self):
        super().__init__()
        self.scan_finished = False

    def onScanFinished(self, library):
        if library == 'video':
            self.scan_finished = True


MONITOR = LibraryMonitor()

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


def main():
    xbmc.log('NLZiet service: started', xbmc.LOGINFO)
    started = time.time()
    last_sync = time.time()
    last_library_trigger = 0
    legacy_checked = False
    while not MONITOR.abortRequested():
        if MONITOR.waitForAbort(60):
            break

        now = time.time()
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
