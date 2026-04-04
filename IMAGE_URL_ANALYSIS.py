#!/usr/bin/env python3
"""
Analysis of image URLs for Series like "The Rookie"

This document shows what images the NLZiet API typically returns for series
and how the addon's new smart artwork assignment handles them.
"""

import json

# Example response structure from NLZiet API for a typical series
example_series_response = {
    "id": "12345",
    "title": "The Rookie",
    "type": "Series",
    "description": "An action-drama about...",
    
    # Image URLs that might be returned
    "posterUrl": "https://images.nlziet.nl/images/12345/poster.jpg",  # Portrait 2:3
    "landscapeUrl": "https://images.nlziet.nl/images/12345/landscape.jpg",  # Landscape 16:9
    "thumbnailUrl": "https://images.nlziet.nl/images/12345/thumbnail.jpg",
    
    # Nested image object (common in API responses)
    "image": {
        "posterUrl": "https://images.nlziet.nl/images/12345/poster_large.jpg",
        "landscapeUrl": "https://images.nlziet.nl/images/12345/landscape_large.jpg",
        "thumbnailUrl": "https://images.nlziet.nl/images/12345/thumb.jpg"
    },
    
    # Sometimes images have different keys
    "thumbnail": "https://images.nlziet.nl/images/12345/med.jpg",
    "cover": "https://images.nlziet.nl/images/12345/cover.jpg"
}

def analyze_images():
    """Show how the addon analyzes and uses these images."""
    
    print("""
================================================================================
IMAGE URL ANALYSIS FOR "THE ROOKIE" SERIES
================================================================================

1. API RESPONSE STRUCTURE
   ───────────────────────────────────────────────────────────────────────────
   
   When you search for "The Rookie" or view series details, the NLZiet API
   returns JSON with multiple image URLs in different formats:

   Expected fields:
   • posterUrl / poster         → Portrait image (2:3 aspect ratio)
   • landscapeUrl / landscape   → Landscape image (16:9 aspect ratio)
   • thumbnailUrl / thumbnail   → Square thumbnail
   • image.posterUrl            → Nested portrait image
   • image.landscapeUrl         → Nested landscape image
   • cover / coverUrl           → Alternative portrait image


2. OLD BEHAVIOR (Before optimization)
   ───────────────────────────────────────────────────────────────────────────
   
   The old code would:
   • Take ONE image URL (just the landscape)
   • Assign it to ALL art keys: thumb, icon, poster, fanart
   • Force Kodi to stretch/crop the image to fit each aspect ratio
   
   Result: Face-cutting because a landscape image stretched to 2:3 ratio
           would cut off the sides or face of the character.
   

3. NEW BEHAVIOR (After optimization)
   ───────────────────────────────────────────────────────────────────────────
   
   The new code will:
   
   Step 1: _pick_landscape_thumb(series_data)
           Returns: https://images.nlziet.nl/images/12345/landscape_large.jpg
           (Prefers keys containing: landscapeUrl, landscape, wide, hero, banner)
   
   Step 2: _pick_portrait_thumb(series_data)
           Returns: https://images.nlziet.nl/images/12345/poster_large.jpg
           (Prefers keys containing: posterUrl, poster, thumbnail, cover)
   
   Step 3: _set_smart_artwork() assigns them properly:
           
           artwork = {
               'fanart': 'https://images.nlziet.nl/images/12345/landscape_large.jpg',
               'landscape': 'https://images.nlziet.nl/images/12345/landscape_large.jpg',
               'poster': 'https://images.nlziet.nl/images/12345/poster_large.jpg',
               'thumb': 'https://images.nlziet.nl/images/12345/landscape_large.jpg',
               'icon': 'https://images.nlziet.nl/images/12345/landscape_large.jpg',
           }
   
   Result: Each image type is used correctly:
           • fanart & landscape keys → use wide 16:9 images (no stretching)
           • poster key → uses tall 2:3 images (perfect for movie posters)
           • thumb & icon → uses landscape with aspect preservation


4. HOW IT IMPROVES DISPLAY
   ───────────────────────────────────────────────────────────────────────────
   
   Before:                          After:
   ┌─────────────────────┐         ┌─────────────────────┐
   │ Stretched 16:9 →    │         │ Proper 16:9 fanart  │
   │ Landscape image     │         │ (no distortion)     │
   │ to 2:3 posterRatio  │         │                     │
   └─────────────────────┘         └─────────────────────┘
   
   Face cuts off on sides     Faces preserved, no cuts
   Characters distorted       Natural appearance


5. IMAGE PRIORITY SELECTION
   ───────────────────────────────────────────────────────────────────────────
   
   For landscape (16:9):
   1. landscapeUrl or landscape key
   2. heroImage / heroImageUrl
   3. widePosterUrl / wide keys
   4. Any fallback URL
   
   For portrait (2:3):
   1. posterUrl or poster key
   2. portraitUrl or portrait key
   3. coverUrl or cover key
   4. thumbnailUrl
   5. Any fallback URL


6. KODI SKIN COMPATIBILITY
   ───────────────────────────────────────────────────────────────────────────
   
   Modern Kodi skins will use:
   • 'fanart' for full-width hero/banner images (16:9)
   • 'poster' for vertical cover art (2:3)
   • 'thumb' for smaller tiles/lists (preserves aspect)
   
   The addon now provides the CORRECT image for each type
   instead of forcing skins to stretch one image everywhere.


7. TECHNICAL BENEFITS
   ───────────────────────────────────────────────────────────────────────────
   
   ✓ No more face-cutting from stretched images
   ✓ Proper aspect ratios maintained
   ✓ Better visual appearance in all skins
   ✓ Smarter image selection based on key names
   ✓ Falls back gracefully if some images missing
   ✓ Compatible with old Kodi versions

================================================================================
""")

    # Show actual function usage
    print("\nEXAMPLE FUNCTION CALLS\n")
    
    series_data = {
        "id": "12345",
        "title": "The Rookie",
        "landscapeUrl": "https://images.nlziet.nl/thumbs/TheRookie_landscape.jpg",
        "posterUrl": "https://images.nlziet.nl/thumbs/TheRookie_poster.jpg",
        "image": {
            "landscapeUrl": "https://images.nlziet.nl/full/TheRookie_landscape_large.jpg",
            "posterUrl": "https://images.nlziet.nl/full/TheRookie_poster_large.jpg"
        }
    }
    
    print("Input series_data:")
    print(json.dumps(series_data, indent=2))
    print()
    
    print("Expected _pick_landscape_thumb() result:")
    print("  → https://images.nlziet.nl/full/TheRookie_landscape_large.jpg")
    print()
    
    print("Expected _pick_portrait_thumb() result:")
    print("  → https://images.nlziet.nl/full/TheRookie_poster_large.jpg")
    print()
    
    print("Resulting artwork dict passed to Kodi:")
    print(json.dumps({
        'fanart': 'https://images.nlziet.nl/full/TheRookie_landscape_large.jpg',
        'landscape': 'https://images.nlziet.nl/full/TheRookie_landscape_large.jpg',
        'poster': 'https://images.nlziet.nl/full/TheRookie_poster_large.jpg',
        'thumb': 'https://images.nlziet.nl/full/TheRookie_landscape_large.jpg',
        'icon': 'https://images.nlziet.nl/full/TheRookie_landscape_large.jpg',
    }, indent=2))
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    analyze_images()
