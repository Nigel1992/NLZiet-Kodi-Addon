import xbmc
import xbmcaddon
import time

ADDON = xbmcaddon.Addon()
MONITOR = xbmc.Monitor()


def _sync_now():
    """Trigger both cloud syncs through the plugin (runs in its own process)."""
    try:
        if ADDON.getSetting('watch_later_sync') in ('true', '1', 'yes', True):
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.nlziet/?mode=sync_watch_later)')
    except Exception as exc:
        xbmc.log('NLZiet service: watch-later sync trigger failed: {}'.format(exc), xbmc.LOGWARNING)
    try:
        if ADDON.getSetting('watch_later_sync') in ('true', '1', 'yes', True):
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.nlziet/?mode=sync_my_series)')
    except Exception as exc:
        xbmc.log('NLZiet service: my-series sync trigger failed: {}'.format(exc), xbmc.LOGWARNING)


def main():
    xbmc.log('NLZiet service: started', xbmc.LOGINFO)
    while not MONITOR.abortRequested():
        try:
            interval = int(ADDON.getSetting('auto_sync_interval') or '0')
        except (ValueError, TypeError):
            interval = 0

        if interval and interval > 0:
            # Wait for the configured interval; abort promptly on shutdown.
            if MONITOR.waitForAbort(interval * 60):
                break
            if MONITOR.abortRequested():
                break
            _sync_now()
        else:
            # Nothing to do; poll settings once a minute.
            if MONITOR.waitForAbort(60):
                break

    xbmc.log('NLZiet service: stopped', xbmc.LOGINFO)


if __name__ == '__main__':
    main()
PY