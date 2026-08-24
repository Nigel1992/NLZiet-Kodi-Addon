import sys
import types
from pathlib import Path

import pytest


ADDON_ROOT = str(Path(__file__).resolve().parents[1])
if ADDON_ROOT not in sys.path:
    sys.path.insert(0, ADDON_ROOT)


class Recorder:
    def __init__(self):
        self.set_content = []
        self.ended = []
        self.notifications = []
        self.directory_items = []
        self.resolved_items = []

    def reset(self):
        self.__init__()


RECORDER = Recorder()


class FakeAddon:
    def __init__(self):
        self.settings = {}

    def getAddonInfo(self, key):
        return {'id': 'plugin.video.nlziet', 'path': 'C:/addon'}.get(key, '')

    def getSetting(self, key):
        return self.settings.get(key, '')

    def setSetting(self, key, value):
        self.settings[key] = value


class FakeDialog:
    def notification(self, heading, message, icon=None):
        RECORDER.notifications.append((heading, message, icon))


class FakeListItem:
    def __init__(self, label='', path='', offscreen=False):
        self.label = label
        self.path = path
        self.offscreen = offscreen
        self.info = {}
        self.properties = {}
        self.art = {}
        self.subtitles = []
        self.context_menu = []

    def setInfo(self, media_type, info):
        self.info[media_type] = dict(info)

    def setProperty(self, key, value):
        self.properties[key] = value

    def setArt(self, art):
        self.art.update(art)

    def setLabel2(self, value):
        self.label2 = value

    def addContextMenuItems(self, items):
        self.context_menu.extend(items)

    def setSubtitles(self, subtitles):
        self.subtitles = list(subtitles)

    def setMimeType(self, mime_type):
        self.mime_type = mime_type


@pytest.fixture(autouse=True)
def reset_recorder():
    RECORDER.reset()
    yield
    RECORDER.reset()


@pytest.fixture
def kodi_recorder():
    return RECORDER


def _install_kodi_stubs():
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGDEBUG = 0
    xbmc.LOGINFO = 1
    xbmc.LOGWARNING = 2
    xbmc.LOGERROR = 3
    xbmc.translatePath = lambda path: path
    xbmc.log = lambda *args, **kwargs: None
    xbmc.executebuiltin = lambda *args, **kwargs: None
    xbmc.Player = type('Player', (), {})

    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.NOTIFICATION_INFO = 'info'
    xbmcgui.NOTIFICATION_ERROR = 'error'
    xbmcgui.Dialog = FakeDialog
    xbmcgui.ListItem = FakeListItem

    xbmcplugin = types.ModuleType('xbmcplugin')
    xbmcplugin.setContent = lambda handle, content: RECORDER.set_content.append((handle, content))
    xbmcplugin.endOfDirectory = lambda handle: RECORDER.ended.append(handle)
    xbmcplugin.addDirectoryItem = lambda handle, url, item, isFolder=False: RECORDER.directory_items.append(
        (handle, url, item, isFolder)
    )
    xbmcplugin.setResolvedUrl = lambda handle, succeeded, item: RECORDER.resolved_items.append(
        (handle, succeeded, item)
    )

    xbmcaddon = types.ModuleType('xbmcaddon')
    xbmcaddon.Addon = lambda *args, **kwargs: FakeAddon()

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda path: path

    sys.modules.setdefault('xbmc', xbmc)
    sys.modules.setdefault('xbmcgui', xbmcgui)
    sys.modules.setdefault('xbmcplugin', xbmcplugin)
    sys.modules.setdefault('xbmcaddon', xbmcaddon)
    sys.modules.setdefault('xbmcvfs', xbmcvfs)


_install_kodi_stubs()
