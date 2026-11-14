import os
import time

import xbmc
import xbmcaddon

from resources.lib import library as library_mod

ADDON = xbmcaddon.Addon()
MONITOR = xbmc.Monitor()

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
    if not store.section('series') and not store.section('movie'):
        return False
    hours = max(1, _int_setting('library_update_hours', 12))
    last = store.data.get('last_update') or 0
    return (time.time() - last) >= hours * 3600


def main():
    xbmc.log('NLZiet service: started', xbmc.LOGINFO)
    started = time.time()
    last_sync = time.time()
    last_library_trigger = 0
    while not MONITOR.abortRequested():
        if MONITOR.waitForAbort(60):
            break

        now = time.time()
        interval = _int_setting('auto_sync_interval', 0)
        if interval > 0 and now - last_sync >= interval * 60:
            last_sync = now
            _sync_now()

        # Retry at most once an hour if an update did not record itself.
        if (now - started >= LIBRARY_STARTUP_DELAY and now - last_library_trigger >= 3600
                and not xbmc.Player().isPlaying() and _library_update_due()):
            last_library_trigger = now
            xbmc.log('NLZiet service: starting library update', xbmc.LOGINFO)
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.nlziet/?mode=library_update&background=1)')

    xbmc.log('NLZiet service: stopped', xbmc.LOGINFO)


if __name__ == '__main__':
    main()
