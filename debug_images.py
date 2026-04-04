#!/usr/bin/env python3
"""Debug script to inspect image URLs found for a specific series.
This version mocks Kodi dependencies so it can run standalone.
"""

import sys
import json
from unittest.mock import MagicMock

# Mock Kodi modules
sys.modules['xbmc'] = MagicMock()
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcvfs'] = MagicMock()
sys.modules['xbmcgui'] = MagicMock()
sys.modules['xbmcplugin'] = MagicMock()

sys.path.insert(0, 'resources/lib')

from nlziet_api import NLZietAPI

def inspect_series_images(search_term="The Rookie"):
    """Search for a series and display all image URLs found."""
    
    # Initialize API (no credentials needed for search)
    api = NLZietAPI(username='', password='')
    
    print(f"\n{'='*80}")
    print(f"Searching for: {search_term}")
    print(f"{'='*80}\n")
    
    # Search for the series
    try:
        results = api.search(search_term) or {}
    except Exception as e:
        print(f"Search error: {e}")
        return
    
    if not results:
        print("No results found")
        return
    
    print(f"Search returned groups: {list(results.keys())}\n")
    
    # Find series in results
    series_group = None
    for group_name, group_data in results.items():
        print(f"Checking group '{group_name}'...")
        if isinstance(group_data, list):
            for idx, item in enumerate(group_data):
                if isinstance(item, dict):
                    title = item.get('title') or item.get('name') or ''
                    if search_term.lower() in title.lower():
                        series_group = item
                        print(f"  ✓ Found matching series at index {idx}: {title}\n")
                        break
    
    if not series_group:
        print(f"Series matching '{search_term}' not found in results")
        return
    
    title = series_group.get('title') or series_group.get('name') or 'Unknown'
    series_id = series_group.get('id')
    
    print(f"{'SERIES DETAILS:':-^80}")
    print(f"  Title:      {title}")
    print(f"  Type:       {series_group.get('type')}")
    print(f"  Series ID:  {series_id}")
    print(f"  Keys found: {list(series_group.keys())}\n")
    
    # Display all image URLs
    print(f"{'IMAGE URLS IN SEARCH RESULT:':-^80}\n")
    
    landscape_urls = []
    portrait_urls = []
    all_urls = []
    
    # Check direct keys for images
    for key in sorted(series_group.keys()):
        value = series_group[key]
        if isinstance(value, str) and ('http' in value or 'https' in value):
            print(f"  {key:30s}: {value}")
            all_urls.append(value)
            
            # Categorize by likely aspect ratio
            key_lower = key.lower()
            if any(x in key_lower for x in ['landscape', 'wide', 'hero', 'banner']):
                landscape_urls.append((key, value))
            elif any(x in key_lower for x in ['portrait', 'poster', 'cover', 'thumbnail']):
                portrait_urls.append((key, value))
    
    # Check nested image objects
    for img_key in ('image', 'images', 'artwork'):
        img_obj = series_group.get(img_key)
        if isinstance(img_obj, dict):
            print(f"\n  Nested '{img_key}' object:")
            for k, v in sorted(img_obj.items()):
                if isinstance(v, str) and ('http' in v or 'https' in v):
                    print(f"    {k:28s}: {v}")
                    all_urls.append(v)
                    
                    k_lower = k.lower()
                    if any(x in k_lower for x in ['landscape', 'wide', 'hero', 'banner']):
                        landscape_urls.append((k, v))
                    elif any(x in k_lower for x in ['portrait', 'poster', 'cover', 'thumbnail']):
                        portrait_urls.append((k, v))
    
    # Summary
    print(f"\n{'CATEGORIZED URLS:':-^80}\n")
    
    if landscape_urls:
        print("Landscape (16:9 - for fanart/hero):")
        for key, url in landscape_urls:
            print(f"  {key:28s}: {url}")
    else:
        print("Landscape (16:9): NOT FOUND")
    
    print()
    if portrait_urls:
        print("Portrait (2:3 - for posters):")
        for key, url in portrait_urls:
            print(f"  {key:28s}: {url}")
    else:
        print("Portrait (2:3): NOT FOUND")
    
    # Try to fetch content details
    if series_id:
        print(f"\n{'FETCHING DETAILED CONTENT INFO:':-^80}\n")
        try:
            print(f"Calling get_content_detail('{series_id}')...")
            detail = api.get_content_detail(series_id)
            if detail:
                print("✓ Content detail retrieved successfully\n")
                print(f"  Keys in detail response: {list(detail.keys())}\n")
                
                # Show image-related fields from detail
                detail_urls = []
                for key in sorted(detail.keys()):
                    value = detail[key]
                    if isinstance(value, str) and ('http' in value or 'https' in value):
                        print(f"  {key:30s}: {value}")
                        detail_urls.append(value)
                    elif isinstance(value, dict) and key in ('image', 'images', 'artwork'):
                        print(f"  Nested '{key}':")
                        for k, v in sorted(value.items()):
                            if isinstance(v, str) and ('http' in v or 'https' in v):
                                print(f"    {k:28s}: {v}")
                                detail_urls.append(v)
                
                if detail_urls:
                    print(f"\n  Total URLs in detail: {len(detail_urls)}")
            else:
                print("✗ Content detail returned empty")
        except Exception as e:
            print(f"✗ Could not fetch detail: {e}")
    
    print(f"\n{'='*80}\n")

if __name__ == '__main__':
    search_term = sys.argv[1] if len(sys.argv) > 1 else "The Rookie"
    inspect_series_images(search_term)
