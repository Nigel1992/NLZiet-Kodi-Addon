
from resources.lib import nlziet_api
"""IPTV Manager Integration module"""

import os
import json
import socket
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import xbmcvfs


class IPTVManager:
    """Interface to IPTV Manager"""

    def __init__(self, port):
        """Initialize IPTV Manager object"""
        self.port = port

    def via_socket(func):
        """Send the output of the wrapped function to socket"""

        def send(self):
            """Decorator to send over a socket"""
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect(('127.0.0.1', self.port))
            try:
                sock.sendall(json.dumps(func(self)).encode())
            finally:
                sock.close()

        return send

    @via_socket
    def send_channels(self):
        """Return JSON-STREAMS formatted python datastructure to IPTV Manager"""
        channels = list(get_channels())
        return dict(version=1, streams=channels)

    @via_socket
    def send_epg(self):
        """Return JSON-EPG formatted python data structure to IPTV Manager"""
        return dict(version=1, epg=get_epg())


def get_channels():
    nlziet = nlziet_api.NLZietAPI()
    channels = nlziet.get_channels()
    enabled_chans = read_enabled_channels(nlziet)
    if enabled_chans is None:
        # enable all
        enabled_chans = [chan['id'] for chan in channels]
    for chan in channels:
        if chan['id'] in enabled_chans:
            yield {
                'id': 'nlziet.' + chan['id'],
                'name': chan['title'],
                'logo': chan['thumb'],
                'stream': f"plugin://plugin.video.nlziet?mode=play&id={chan['id']}&fmt=live"
            }


def get_epg():
    nlziet = nlziet_api.NLZietAPI()
    enabled_chans = read_enabled_channels(nlziet)
    if enabled_chans is None:
        # enable all
        chan_ids = [chan['id'] for chan in nlziet.get_channels()]
    else:
        chan_ids = [chan['id'] for chan in nlziet.get_channels() if chan['id'] in enabled_chans]
    now = datetime.now(tz=ZoneInfo('Europe/Amsterdam'))
    epg = {}
    for day_delta in range(-7, 5):
        day_str = (now + timedelta(days=day_delta)).strftime("%Y-%m-%d")
        epg_data = nlziet.get_current_programs(chan_ids, day_str)
        for chan_id, pgm_list in epg_data.items():
            chan_epg = epg.setdefault('nlziet.' + chan_id, [])
            chan_epg.extend(pgm_list)
    return epg


def read_enabled_channels(api):
    addon_profile_dir = xbmcvfs.translatePath(api.addon.getAddonInfo('profile'))
    fpath = os.path.join(addon_profile_dir, 'iptv_channels.json')
    # Read the stored list of channel IDs from file.
    try:
        with open(fpath, 'r') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_enabled_channels(api, chan_list):
    addon_profile_dir = xbmcvfs.translatePath(api.addon.getAddonInfo('profile'))
    fpath = os.path.join(addon_profile_dir, 'iptv_channels.json')
    with open(fpath, 'w') as f:
        json.dump(chan_list, f)
