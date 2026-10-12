import sys

import xbmcaddon


class AddonContext:
    """Small holder for Kodi plugin state used during dispatch."""

    def __init__(self, addon, handle, base_url, paramstring=''):
        self.addon = addon
        self.addon_id = addon.getAddonInfo('id')
        self.handle = handle
        self.base_url = base_url
        self.paramstring = paramstring
        self.plugin_path = addon.getAddonInfo('path')

    @classmethod
    def from_kodi(cls):
        addon = xbmcaddon.Addon()
        handle = int(sys.argv[1])
        base_url = sys.argv[0]
        paramstring = sys.argv[2][1:] if len(sys.argv) > 2 else ''
        return cls(addon, handle, base_url, paramstring)
