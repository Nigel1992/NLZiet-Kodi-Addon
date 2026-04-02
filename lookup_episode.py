#!/usr/bin/env python3
"""Quick script to look up NOS Voetbal episode info"""

import sys
import os
import json
import urllib.request
import http.cookiejar

# Mock Kodi modules for standalone execution
class MockModule:
    class LOGINFO:
        pass
    class LOGERROR:
        pass
    def log(self, msg, level):
        print(f"[LOG] {msg}")
    def translatePath(self, path):
        return path.replace('special://profile', os.path.expanduser('~/.kodi/profile'))

class MockVFS:
    @staticmethod
    def translatePath(path):
        return path.replace('special://profile', os.path.expanduser('~/.kodi/profile'))

class MockAddon:
    def __init__(self):
        pass
    def getSetting(self, key):
        return ''
    def getAddonInfo(self, key):
        return 'plugin.video.nlziet'
    def getProperty(self, key):
        return ''
    def setProperty(self, key, val):
        pass

sys.modules['xbmc'] = MockModule()
sys.modules['xbmcvfs'] = MockVFS()
sys.modules['xbmcaddon'] = type('module', (), {'Addon': MockAddon})()
sys.modules['xbmcgui'] = type('module', (), {})()
sys.modules['xbmcplugin'] = type('module', (), {})()

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))

from nlziet_api import NLZietAPI

# Initialize API
api = NLZietAPI()

print("=" * 70)
print("Searching for 'NOS Voetbal'...")
print("=" * 70)

# Search for NOS Voetbal
results = api.search('NOS Voetbal', content_type='all')

# Find the main "NOS Voetbal" series
nos_voetbal_id = None
for item in results:
    if item.get('title') == 'NOS Voetbal' and item.get('type') == 'Series':
        nos_voetbal_id = item.get('id')
        print(f"\n✓ Found 'NOS Voetbal' series (ID: {nos_voetbal_id})")
        break

if nos_voetbal_id:
    print(f"\nGetting series details...")
    detail = api.get_series_detail(nos_voetbal_id)
    
    if detail:
        print(f"\nSeries has {len(detail.get('seasons', []))} seasons")
        
        # Get all episodes
        print(f"\nFetching episodes...")
        episodes = api.get_series_episodes(nos_voetbal_id)
        
        print(f"Found {len(episodes)} total episodes")
        
        # Look for "Tweede helft" episode
        print(f"\nSearching for 'Tweede helft' episode...")
        for ep in episodes:
            title = ep.get('title') or ''
            if 'Tweede helft' in title:
                print(f"\n{'='*70}")
                print(f"✓ FOUND: {title}")
                print(f"{'='*70}")
                print(json.dumps(ep, indent=2, default=str))
                break
        else:
            print(f"\n'Tweede helft' not found. Showing first 5 episodes:")
            for ep in episodes[:5]:
                print(f"\n  - {ep.get('title')}")
else:
    print(f"\nCould not find 'NOS Voetbal' series")


