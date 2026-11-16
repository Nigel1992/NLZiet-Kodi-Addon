"""A small corner button overlay (bottom right), like the Videoland app's
"Overslaan" / next-episode button, instead of a full-screen yes/no dialog.

``ask(label, seconds)`` shows the button and returns True when the user presses
it, or False when it closes by itself (timeout) or is dismissed. The video
keeps playing behind the small card.

Shared by the NLZiet and Videoland add-ons (keep both copies identical). The
window skin (corner_skip.xml + media/pill.png) lives in each add-on's own
resources/skins/Default.
"""

import threading

try:
    import xbmc
    import xbmcgui
    import xbmcaddon
except ImportError:  # tests run without Kodi
    xbmc = xbmcgui = xbmcaddon = None

# Action ids that dismiss the card (back / escape / nav-back).
_BACK = (9, 10, 92, 110, 216, 247, 257, 275)


def _card_class():
    class _Card(xbmcgui.WindowXMLDialog):
        def __init__(self, *args, **kwargs):
            self._label = kwargs.pop('label', '')
            xbmcgui.WindowXMLDialog.__init__(self, *args)
            self.result = False

        def onInit(self):
            try:
                self.setProperty('label', self._label)
            except Exception:
                pass
            try:
                self.setFocusId(10)
            except Exception:
                pass

        def onClick(self, control_id):
            if control_id == 10:
                self.result = True
            self.close()

        def onAction(self, action):
            try:
                if action.getId() in _BACK:
                    self.close()
            except Exception:
                self.close()

    return _Card


def ask(label, seconds=10):
    """Show the corner button with ``label`` and return True if pressed.

    It closes itself after ``seconds`` (then returns False), so it never blocks
    playback for long.
    """
    if xbmcgui is None:
        return False
    try:
        path = xbmcaddon.Addon().getAddonInfo('path')
        card = _card_class()('corner_skip.xml', path, 'Default', '1080i', label=label)
    except Exception:
        return False
    monitor = xbmc.Monitor()
    state = {'open': True}

    def closer():
        waited = 0.0
        while state['open'] and waited < seconds:
            if monitor.waitForAbort(0.5):
                break
            waited += 0.5
        if state['open']:
            try:
                card.close()
            except Exception:
                pass

    worker = threading.Thread(target=closer, name='CornerButton', daemon=True)
    worker.start()
    try:
        card.doModal()
    except Exception:
        return False
    finally:
        state['open'] = False
    result = bool(getattr(card, 'result', False))
    del card
    return result
