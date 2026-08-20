import sys
import types

import pytest


class Recorder:
    def __init__(self):
        self.set_content = []
        self.ended = []
        self.notifications = []

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

    xbmcplugin = types.ModuleType('xbmcplugin')
    xbmcplugin.setContent = lambda handle, content: RECORDER.set_content.append((handle, content))
    xbmcplugin.endOfDirectory = lambda handle: RECORDER.ended.append(handle)

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
