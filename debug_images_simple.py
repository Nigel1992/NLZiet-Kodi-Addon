#!/usr/bin/env python3
"""Simple debug script to inspect image URLs without relying on Kodi modules."""

import json
import urllib.request
import urllib.error
import sys

def search_nlziet(search_term="The Rookie"):
    """Search NLZiet API directly and display image URLs."""
    
    api_url = "https://api.nlziet.nl"
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    
    print(f"\n{'='*80}")
    print(f"Searching NLZiet API for: {search_term}")
    print(f"{'='*80}\n")
    
    try:
        # Try the /v9/search endpoint
        search_url = f"{api_url}/v9/search?q={urllib.parse.quote(search_term)}"
        print(f"API Request: GET {search_url}\n")
        
        req = urllib.request.Request(
            search_url,
            headers={'User-Agent': user_agent}
        )
        
        print("Fetching search results...")
        with urllib.request.urlopen(req, timeout=10) as response:
            results = json.load(response)
        
        print(f"✓ Response received\n")
        
        if isinstance(results, dict):
            print(f"Top-level keys: {list(results.keys())}\n")
        
        # Find series
        series_found = []
        
        if isinstance(results, dict):
            for key, value in results.items():
                if isinstance(value, list):
                    for idx, item in enumerate(value):
                        if isinstance(item, dict):
                            title = item.get('title') or item.get('name') or ''
                            if search_term.lower() in title.lower():
                                series_found.append({
                                    'group': key,
                                    'item': item,
                                    'index': idx,
                                    'title': title
                                })
        
        if not series_found:
            print(f"✗ No series matching '{search_term}' found\n")
            return
        
        print(f"✓ Found {len(series_found)} matching series\n")
        
        for match in series_found:
            print(f"{'='*80}")
            print(f"Series: {match['title']}")
            print(f"Group: {match['group']}")
            print(f"Series ID: {match['item'].get('id')}")
            print(f"{'='*80}\n")
            
            item = match['item']
            
            # Extract all URLs
            print("Image URLs found in search response:\n")
            
            urls_found = []
            for key in sorted(item.keys()):
                value = item[key]
                if isinstance(value, str) and ('http://' in value or 'https://' in value):
                    print(f"  {key:30s}: {value}")
                    urls_found.append((key, value))
                elif isinstance(value, dict):
                    for k, v in sorted(value.items()):
                        if isinstance(v, str) and ('http://' in v or 'https://' in v):
                            print(f"  {key}.{k:24s}: {v}")
                            urls_found.append((f"{key}.{k}", v))
            
            if not urls_found:
                print("  [No image URLs found in search result]\n")
            
            # Try content detail endpoint
            series_id = item.get('id')
            if series_id:
                print(f"\nFetching detailed content info...\n")
                try:
                    detail_url = f"{api_url}/v9/content/detail/{series_id}"
                    print(f"API Request: GET {detail_url}\n")
                    
                    req = urllib.request.Request(
                        detail_url,
                        headers={'User-Agent': user_agent}
                    )
                    
                    with urllib.request.urlopen(req, timeout=10) as response:
                        detail = json.load(response)
                    
                    print(f"✓ Detail response received\n")
                    print("Image URLs found in detail response:\n")
                    
                    detail_urls_found = []
                    if isinstance(detail, dict):
                        for key in sorted(detail.keys()):
                            value = detail[key]
                            if isinstance(value, str) and ('http://' in value or 'https://' in value):
                                print(f"  {key:30s}: {value}")
                                detail_urls_found.append((key, value))
                            elif isinstance(value, dict):
                                for k, v in sorted(value.items()):
                                    if isinstance(v, str) and ('http://' in v or 'https://' in v):
                                        print(f"  {key}.{k:24s}: {v}")
                                        detail_urls_found.append((f"{key}.{k}", v))
                    
                    if not detail_urls_found:
                        print("  [No image URLs found in detail]\n")
                    
                    # Summary
                    all_urls = urls_found + detail_urls_found
                    if all_urls:
                        print(f"\nTotal URLs found: {len(all_urls)}")
                
                except urllib.error.HTTPError as e:
                    print(f"✗ HTTP Error {e.code}: {e.reason}")
                except urllib.error.URLError as e:
                    print(f"✗ Connection Error: {e.reason}")
                except Exception as e:
                    print(f"✗ Error: {e}")
            
            print()
    
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error {e.code}: {e.reason}\n")
    except urllib.error.URLError as e:
        print(f"✗ Connection Error: {e.reason}\n")
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON response: {e}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    print(f"{'='*80}\n")

if __name__ == '__main__':
    search_term = sys.argv[1] if len(sys.argv) > 1 else "The Rookie"
    search_nlziet(search_term)
