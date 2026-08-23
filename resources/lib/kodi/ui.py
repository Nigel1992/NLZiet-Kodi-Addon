import os
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin


def build_url(base_url, query):
    return base_url + '?' + urllib.parse.urlencode(query)


def make_color_tag(color_raw, text):
    """Return a Kodi COLOR tag using the raw value provided by the caller."""
    if not color_raw:
        return f"[COLOR FFA500]{text}[/COLOR]"
    return f"[COLOR {color_raw}]{text}[/COLOR]"


def pick_menu_icon(addon_path, name):
    candidates = [
        os.path.join(addon_path, 'resources', 'media', f'menu_{name}.png'),
        os.path.join(addon_path, 'resources', 'media', f'menu_{name}.svg'),
        os.path.join(addon_path, 'icon.png'),
    ]
    for c in candidates:
        try:
            if c and os.path.exists(c):
                return c
        except Exception:
            continue
    return None


def pick_menu_png(addon_path, name):
    try:
        png = os.path.join(addon_path, 'resources', 'media', f'menu_{name}.png')
        if png and os.path.exists(png):
            return png
    except Exception:
        pass
    return pick_menu_icon(addon_path, name)


def add_directory_item(addon, handle, build_url_func, api_instance_getter,
                       title, query, is_folder=True, thumb=None, info=None,
                       content=None):
    url = build_url_func(query)
    li = xbmcgui.ListItem(label=title, offscreen=True)

    # Set background image on each item for skin display
    try:
        addon_path = xbmc.translatePath(addon.getAddonInfo('path')) or addon.getAddonInfo('path') or ''
        background_path = os.path.join(addon_path, 'resources', 'media', 'background.jpg')
        if os.path.exists(background_path):
            li.setArt({'fanart': background_path})
    except Exception:
        pass

    if thumb or content:
        # Use smart artwork assignment to respect aspect ratios
        # Prevents face-cutting and image stretching by assigning portraits to poster, landscapes to fanart
        set_smart_artwork(li, content, thumb=thumb)

    # For live TV (fmt='live'), display EPG without context menu options
    is_live = isinstance(query, dict) and query.get('fmt') == 'live'

    if info:
        if is_live:
            # For live TV, set video info to display EPG, but don't track resume points
            # Clear any bookmark/resume data so context menu doesn't appear
            info_copy = info.copy()
            info_copy.pop('resume', None)  # Remove any resume position
            li.setInfo('video', info_copy)
        else:
            # For on-demand content, set full video info (allows resume functionality)
            li.setInfo('video', info)
            try:
                short = info.get('plotoutline') or info.get('plot') or ''
                if short:
                    li.setLabel2(short)
            except Exception:
                pass
    # mark non-folder items as playable so Enter/Select triggers playback
    if not is_folder:
        li.setProperty('IsPlayable', 'true')

    # For live TV, prevent Kodi from showing resume/playback context menu
    if is_live:
        li.setProperty('ResumeTime', '0')
        li.setProperty('TotalTime', '3600')
        li.setProperty('IsLive', 'true')  # Mark as live for skin awareness
    # Add context-menu entry for My List when we can determine a content id
    try:
        content_id = None
        content_type = None
        # Prefer explicit content dict when provided
        if content and isinstance(content, dict):
            content_id = content.get('id') or content.get('contentId') or content.get('content_id') or content.get('seriesId') or content.get('movieId') or content.get('assetId')
            content_type = content.get('type') or content.get('contentType') or None
        # Fallback: inspect the query params for common id keys
        if not content_id and isinstance(query, dict):
            for k in ('id', 'series_id', 'seriesId', 'movieId', 'contentId', 'content_id'):
                if k in query and query.get(k):
                    content_id = query.get(k)
                    break
        # Only allow My List for top-level Series or Movies (no Seasons/Episodes)
        allow_mylist = False
        if content and isinstance(content, dict):
            ctype = (content_type or '')
            ctype_l = (str(ctype).lower() if ctype else '')
            if any(x in ctype_l for x in ('series', 'tvshow', 'movie', 'film')):
                allow_mylist = True
        elif isinstance(query, dict):
            mode = (query.get('mode') or '').lower()
            # treat explicit series_detail as a series entry
            if mode == 'series_detail' and (query.get('series_id') or query.get('seriesId')):
                allow_mylist = True

        if allow_mylist and content_id:
            try:
                # Use cached API instance instead of creating new ones for every item
                api_tmp = api_instance_getter()
                in_list = api_tmp.is_in_my_list(content_id)
            except Exception:
                in_list = False

            cm_label = 'Remove from My List' if in_list else 'Add to My List'
            cm_query = {'mode': 'toggle_mylist', 'id': str(content_id), 'title': title}
            if content_type:
                cm_query['type'] = content_type
            if thumb:
                cm_query['thumb'] = thumb
            try:
                cm_url = build_url_func(cm_query)
                li.addContextMenuItems([(cm_label, f"RunPlugin({cm_url})")])
            except Exception:
                pass
    except Exception:
        pass
    xbmcplugin.addDirectoryItem(handle, url, li, isFolder=is_folder)


def optimize_image_url(url):
    """Optimize image URLs to request higher-resolution versions for fanart.

    The NLZiet image service returns low-res images (1280x720) by default.
    Request a larger resolution to avoid pixelation when displayed as fanart.
    """
    if not url or not isinstance(url, str):
        return url

    # Remove any existing width/crop parameters
    if '?' in url:
        url = url.split('?')[0]

    # Request a much larger width for fanart (3840px = 4K width)
    return url + '?width=3840'


def pick_landscape_thumb(src):
    """Return the best landscape-oriented thumbnail or path for an item."""
    if not src:
        return None
    if isinstance(src, str):
        return optimize_image_url(src)
    try:
        # Prefer explicit landscape / wide keys first
        for k in ('landscapeUrl', 'landscape', 'thumbnailLandscape', 'thumbnail_landscape', 'posterLandscape', 'poster_landscape', 'heroImage', 'heroImageUrl', 'widePosterUrl'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return optimize_image_url(v)

        # Common poster/thumbnail fields (posterUrl may be portrait but is a useful fallback)
        for k in ('posterUrl', 'poster', 'thumbnail', 'thumb'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return optimize_image_url(v)

        # Check nested image dicts for landscape keys
        for img_key in ('image', 'images'):
            img = src.get(img_key)
            if isinstance(img, dict):
                for k in ('landscapeUrl', 'landscape', 'landscape_url', 'wide', 'wideUrl', 'large', 'largeUrl', 'posterUrl', 'thumbnail', 'thumb'):
                    v = img.get(k)
                    if isinstance(v, str) and v:
                        return optimize_image_url(v)
                for kk, vv in img.items():
                    if isinstance(kk, str) and 'landscape' in kk.lower() and isinstance(vv, str) and vv:
                        return vv

        # Any key name containing 'landscape' on the top-level
        for kk, vv in src.items():
            if isinstance(kk, str) and 'landscape' in kk.lower() and isinstance(vv, str) and vv:
                return optimize_image_url(vv)

        # As a final fallback, return any url-like string value
        for vv in src.values():
            if isinstance(vv, str) and (vv.startswith('http://') or vv.startswith('https://') or vv.startswith('file://')):
                return optimize_image_url(vv)
    except Exception:
        pass
    return None


def pick_portrait_thumb(src):
    """Return the best portrait-oriented thumbnail or path for an item."""
    if not src:
        return None
    if isinstance(src, str):
        return optimize_image_url(src)
    try:
        # Prefer explicit portrait / tall keys first
        for k in ('portraitUrl', 'portrait', 'posterUrl', 'poster', 'thumbnailPortrait', 'thumbnail_portrait', 'coverUrl', 'cover'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return optimize_image_url(v)
        # Check nested image dicts for portrait keys
        for img_key in ('image', 'images'):
            img = src.get(img_key)
            if isinstance(img, dict):
                for k in ('portraitUrl', 'portrait', 'portrait_url', 'posterUrl', 'poster', 'coverUrl', 'cover', 'thumbnail', 'thumb'):
                    v = img.get(k)
                    if isinstance(v, str) and v:
                        return optimize_image_url(v)
        # Fallback to any image URL
        for vv in src.values():
            if isinstance(vv, str) and (vv.startswith('http://') or vv.startswith('https://') or vv.startswith('file://')):
                return optimize_image_url(vv)
    except Exception:
        pass
    return None


def set_smart_artwork(li, src, thumb=None):
    """Set artwork on a ListItem with proper aspect ratio handling."""
    if not thumb and not src:
        return

    # Extract different image types from content object
    landscape_img = None
    portrait_img = None

    if src and isinstance(src, dict):
        landscape_img = pick_landscape_thumb(src)
        portrait_img = pick_portrait_thumb(src)

    # Fallback: use provided thumb for both if we don't have separate images
    if not landscape_img and not portrait_img:
        landscape_img = thumb
        portrait_img = thumb
    elif not landscape_img:
        landscape_img = portrait_img
    elif not portrait_img:
        portrait_img = landscape_img

    # Build artwork dict with proper aspect ratio handling
    art = {}

    # Landscape images work best for fanart (16:9 aspect ratio)
    if landscape_img:
        art['fanart'] = landscape_img
        art['landscape'] = landscape_img

    # Portrait images for poster art (2:3 aspect ratio)
    if portrait_img:
        art['poster'] = portrait_img

    # Use landscape for thumb/icon with aspect ratio preservation
    # Kodi will letterbox/pillarbox to fit rather than stretch
    if landscape_img:
        art['thumb'] = landscape_img
        art['icon'] = landscape_img
    elif portrait_img:
        art['thumb'] = portrait_img
        art['icon'] = portrait_img

    # Apply artwork with fallback for older Kodi versions
    if art:
        try:
            li.setArt(art)
        except Exception:
            # Fallback: try simple thumb/icon only
            try:
                if landscape_img:
                    li.setArt({'thumb': landscape_img, 'icon': landscape_img})
            except Exception:
                pass
