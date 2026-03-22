import sys
import re
import urllib.parse
import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import time

from resources.lib.nlziet_api import NLZietAPI

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

# Raw expiry color to test — change this to 'orange' or a hex like 'FFA500' or
# try the exact raw tag you suggested ('ffoooo66') to experiment.
EXPIRY_COLOR_RAW = 'ffoooo66'

def _make_color_tag(color_raw, text):
    """Return a COLOR tag using the raw value provided by the user.

    We intentionally use the raw value so you can test named colors or hex
    variants; if the skin ignores color tags, we also prefix label2 with an
    emoji marker as a fallback (see code below).
    """
    if not color_raw:
        return f"[COLOR FFA500]{text}[/COLOR]"
    return f"[COLOR {color_raw}]{text}[/COLOR]"


def build_url(query):
    return BASE_URL + '?' + urllib.parse.urlencode(query)


def add_directory_item(title, query, is_folder=True, thumb=None, info=None, content=None):
    url = build_url(query)
    li = xbmcgui.ListItem(label=title)
    if thumb:
        # Provide multiple art keys so different skins can pick the one they use
        try:
            li.setArt({'thumb': thumb, 'icon': thumb, 'poster': thumb, 'fanart': thumb})
        except Exception:
            try:
                li.setArt({'thumb': thumb, 'icon': thumb})
            except Exception:
                pass
    if info:
        li.setInfo('video', info)
        # set a short summary for skins that display a second label
        try:
            short = info.get('plotoutline') or info.get('plot') or ''
            if short:
                li.setLabel2(short)
        except Exception:
            pass
    # mark non-folder items as playable so Enter/Select triggers playback
    if not is_folder:
        li.setProperty('IsPlayable', 'true')
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
                api_tmp = NLZietAPI(username=ADDON.getSetting('username'), password=ADDON.getSetting('password'))
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
                cm_url = build_url(cm_query)
                li.addContextMenuItems([(cm_label, f"RunPlugin({cm_url})")])
            except Exception:
                pass
    except Exception:
        pass
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)


def _pick_landscape_thumb(src):
    """Return the best landscape-oriented thumbnail or path for an item.

    Accepts either a string URL/path or a dict-like content item. Prefers
    explicit landscape keys, then common wide/hero/poster keys, and finally
    falls back to any url-like string found on the object.
    """
    if not src:
        return None
    if isinstance(src, str):
        return src
    try:
        # Prefer explicit landscape / wide keys first
        for k in ('landscapeUrl', 'landscape', 'thumbnailLandscape', 'thumbnail_landscape', 'posterLandscape', 'poster_landscape', 'heroImage', 'heroImageUrl', 'widePosterUrl'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return v

        # Common poster/thumbnail fields (posterUrl may be portrait but is a useful fallback)
        for k in ('posterUrl', 'poster', 'thumbnail', 'thumb'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return v

        # Check nested image dicts for landscape keys
        for img_key in ('image', 'images'):
            img = src.get(img_key)
            if isinstance(img, dict):
                for k in ('landscapeUrl', 'landscape', 'landscape_url', 'wide', 'wideUrl', 'large', 'largeUrl', 'posterUrl', 'thumbnail', 'thumb'):
                    v = img.get(k)
                    if isinstance(v, str) and v:
                        return v
                for kk, vv in img.items():
                    if isinstance(kk, str) and 'landscape' in kk.lower() and isinstance(vv, str) and vv:
                        return vv

        # Any key name containing 'landscape' on the top-level
        for kk, vv in src.items():
            if isinstance(kk, str) and 'landscape' in kk.lower() and isinstance(vv, str) and vv:
                return vv

        # As a final fallback, return any url-like string value
        for vv in src.values():
            if isinstance(vv, str) and (vv.startswith('http://') or vv.startswith('https://') or vv.startswith('file://')):
                return vv
    except Exception:
        pass
    return None


def main_menu():
    try:
        addon_path = ADDON.getAddonInfo('path') or ''
    except Exception:
        addon_path = ''

    # prefer png then svg then fallback to addon's icon.png
    def _pick_icon(name):
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

    # Explicit PNG-first picker (prefer exact menu_{name}.png when available)
    def _pick_png(name):
        try:
            png = os.path.join(addon_path, 'resources', 'media', f'menu_{name}.png')
            if png and os.path.exists(png):
                return png
        except Exception:
            pass
        return _pick_icon(name)

    add_directory_item('Login (set credentials in settings)', {'mode': 'login'}, thumb=_pick_png('login'))
    add_directory_item('Manage profiles', {'mode': 'profiles'}, thumb=_pick_png('profiles'))
    add_directory_item('Search', {'mode': 'search'}, thumb=_pick_png('search'))
    add_directory_item('My List', {'mode': 'my_list'}, thumb=_pick_png('mylist'))
    add_directory_item('Series', {'mode': 'series'}, thumb=_pick_png('series'))
    add_directory_item('Movies', {'mode': 'browse', 'type': 'movies'}, thumb=_pick_png('movies'))
    # Some icon sets use 'tv' instead of 'channels' (we check menu_tv.png)
    add_directory_item('Channels', {'mode': 'browse', 'type': 'channels'}, thumb=_pick_png('tv'))
    xbmcplugin.endOfDirectory(HANDLE)


def browse_series():
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)

    # Prefer placement rows (home/explore layout) when available
    try:
        comps = api.get_placement_rows('explore-series') or []
    except Exception:
        comps = []

    if comps:
        for idx, comp in enumerate(comps):
            try:
                comp_title = comp.get('title') or comp.get('name') or comp.get('id') or f"Row {idx+1}"
                # Skip placement rows we don't want in the Series submenu
                try:
                    comp_id = comp.get('id') or comp.get('placementId') or comp.get('name') or ''
                except Exception:
                    comp_id = ''
                lower_title = str(comp_title).strip().lower()
                if lower_title == 'series' or str(comp_id).lower() == 'explore-series-genres':
                    continue
                items_url = comp.get('itemsUrl') or comp.get('url') or (comp.get('link', {}) or {}).get('href') if isinstance(comp.get('link', {}), dict) else comp.get('itemsUrl')
                # Provide a folder that opens the row contents. If the component
                # exposes an itemsUrl we pass it directly; otherwise we pass the
                # placement id + index so the handler can re-fetch inline items.
                query = {'mode': 'placement_row'}
                if items_url:
                    query['items_url'] = items_url
                else:
                    query['placement_id'] = 'explore-series'
                    query['comp_index'] = str(idx)
                add_directory_item(comp_title, query, is_folder=True)
            except Exception:
                continue
        xbmcplugin.endOfDirectory(HANDLE)
        return

    # Fallback: simple series list when placements are unavailable
    results = api.get_series_list()
    for item in results:
        info = None
        try:
            desc = item.get('description') or item.get('subtitle') or ''
            if desc:
                title_for_info = item.get('title') or ''
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                info = {
                    'title': title_for_info,
                    'plot': desc,
                    'plotoutline': truncated,
                }
        except Exception:
            info = None
        add_directory_item(item.get('title') or item.get('id') or 'Series', {'mode': 'series_detail', 'series_id': item.get('id')}, is_folder=True, thumb=_pick_landscape_thumb(item), info=info, content=item)
    xbmcplugin.endOfDirectory(HANDLE)


def show_series_detail(series_id):
    if not series_id:
        xbmcgui.Dialog().notification('NLZiet', 'Missing series id', xbmcgui.NOTIFICATION_ERROR)
        return
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    detail = api.get_series_detail(series_id)
    if not detail:
        xbmcgui.Dialog().notification('NLZiet', 'Unable to fetch series details', xbmcgui.NOTIFICATION_ERROR)
        return
    seasons = detail.get('seasons') or []
    # If no seasons discovered, offer direct episode listing
    if not seasons:
        add_directory_item('All episodes', {'mode': 'series_season', 'series_id': series_id, 'season_id': ''}, is_folder=True)
    else:
        for s in seasons:
            title = s.get('title') or f"Season {s.get('id')}"
            add_directory_item(title, {'mode': 'series_season', 'series_id': series_id, 'season_id': s.get('id')}, is_folder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def show_series_season(series_id, season_id):
    if not series_id:
        xbmcgui.Dialog().notification('NLZiet', 'Missing series id', xbmcgui.NOTIFICATION_ERROR)
        return
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    xbmc.log(f"NLZiet show_series_season: series_id={series_id} season_id={season_id}", xbmc.LOGDEBUG)
    episodes = api.get_series_episodes(series_id, season_id=season_id or None, limit=400)
    # If the API returned no episodes, but the `season_id` appears to be
    # an items/episodes URL, attempt to fetch items directly from that URL
    # (some detail payloads expose an `episodes_url` instead of numeric ids).
    if not episodes and season_id and isinstance(season_id, str) and (season_id.startswith('http') or '/episodes' in season_id or 'items' in season_id):
        try:
            xbmc.log(f"NLZiet attempting fallback get_items_from_url for season_id={season_id}", xbmc.LOGDEBUG)
            episodes = api.get_items_from_url(season_id) or []
        except Exception:
            episodes = []
    if not episodes:
        xbmcgui.Dialog().notification('NLZiet', 'No episodes found', xbmcgui.NOTIFICATION_INFO)
        return
    for ep in episodes:
        info = None
        try:
            desc = ep.get('description') or ep.get('subtitle') or ''
            if desc:
                title_for_info = ep.get('title') or ''
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                info = {
                    'title': title_for_info,
                    'plot': desc,
                    'plotoutline': truncated,
                }
        except Exception:
            info = None

        # Prefer an already-formatted episode numbering string when available.
        # First, prefer subtitle patterns like 'S1:A2' (some payloads include
        # this canonical format in `subtitle`). If present, use it as
        # "S1:A2 <Episode Title>". Otherwise fall back to the API's
        # formatted label or numeric SxxExx formatting.
        formatted_label = ep.get('formatted_episode_numbering') or ep.get('formattedEpisodeNumbering') or (ep.get('raw') or {}).get('formattedEpisodeNumbering')
        label_title = ep.get('title') or ''

        # Check subtitle for the canonical 'S{n}:A{m}' pattern (e.g. 'S1:A2 Secrets').
        # If present, extract the remainder of the subtitle after the code and
        # prefer that as the human-friendly episode title ("S1:A2 <ep title>").
        subtitle_code = None
        try:
            sub = ep.get('subtitle') or ''
            if sub and isinstance(sub, str):
                m = re.search(r"\bS\d+:A\d+\b", sub, re.I)
                if m:
                    subtitle_code = m.group(0)
                    # remainder after the matched code
                    remainder = sub[m.end():].strip()
                    # strip common separators (colon, dash, en-dash, em-dash)
                    remainder = re.sub(r'^[\s\-:\u2013\u2014]+', '', remainder)
                else:
                    remainder = ''
            else:
                remainder = ''
        except Exception:
            subtitle_code = None
            remainder = ''

        if subtitle_code:
            if remainder:
                label = f"{subtitle_code} {remainder}"
            else:
                # no explicit episode title in subtitle, show code and fall back to series title if available
                label = f"{subtitle_code} - {label_title}" if label_title else subtitle_code
        elif sub and isinstance(sub, str) and sub.strip():
            # subtitle exists but contains no S#:A# code — use the subtitle as
            # the human-friendly episode title (e.g. 'Korfspiracy').
            label = sub.strip()
        elif formatted_label:
            # Use the canonical formatted label from the API/app when present
            label = f"{formatted_label} - {label_title}" if label_title else formatted_label
        else:
            # Prefer normalized episode_number/season_number when available
            ep_num = ep.get('episode_number') or ep.get('episodeNumber') or ep.get('number') or ep.get('episode')
            season_num = ep.get('season_number') or ep.get('seasonNumber') or None
            label = label_title or ''
            try:
                n = int(ep_num) if ep_num is not None and str(ep_num).isdigit() else None
            except Exception:
                n = None
            try:
                s = int(season_num) if season_num is not None and str(season_num).isdigit() else None
            except Exception:
                s = None

            if n is not None:
                if s is not None:
                    label = f"S{s:02d}E{n:02d} - {label}" if label else f"S{s:02d}E{n:02d}"
                else:
                    label = f"Episode {n} - {label}" if label else f"Episode {n}"
            else:
                label = label or ep.get('id') or 'Episode'

        add_directory_item(label, {'mode': 'play', 'id': ep.get('id')}, is_folder=False, thumb=_pick_landscape_thumb(ep), info=info, content=ep)
    xbmcplugin.endOfDirectory(HANDLE)


def browse_placement_row(items_url=None, placement_id=None, comp_index=None):
    """List items for a placement row. Accepts either `items_url` or a
    `placement_id` + `comp_index` to locate inline items.
    """
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    items = []

    # Direct items URL
    if items_url:
        try:
            items = api.get_items_from_url(items_url) or []
        except Exception:
            items = []
    # Fallback: fetch placement and use inline items by index
    elif placement_id is not None and comp_index is not None:
        try:
            comps = api.get_placement_rows(placement_id) or []
            idx = int(comp_index)
            comp = comps[idx] if 0 <= idx < len(comps) else None
            if comp:
                if isinstance(comp.get('items'), list) and comp.get('items'):
                    for itm in comp.get('items'):
                        src = itm.get('item') if isinstance(itm, dict) and itm.get('item') else itm.get('content') if isinstance(itm, dict) and itm.get('content') else itm
                        if isinstance(src, dict):
                            items.append(src)
                else:
                    u = comp.get('itemsUrl') or comp.get('url') or (comp.get('link', {}) or {}).get('href')
                    if u:
                        items = api.get_items_from_url(u) or []
        except Exception:
            items = []

    if not items:
        xbmcgui.Dialog().notification('NLZiet', 'No items found', xbmcgui.NOTIFICATION_INFO)
        return

    for src in items:
        try:
            content_id = src.get('id') or src.get('contentId') or src.get('content_id') or src.get('seriesId') or src.get('movieId') or src.get('assetId')
            title = src.get('title') or src.get('name') or ''
            thumb = _pick_landscape_thumb(src)
            desc = src.get('description') or src.get('summary') or ''
            info = None
            if desc:
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                info = {'title': title, 'plot': desc, 'plotoutline': truncated}

            if content_id:
                # Treat as series when possible
                add_directory_item(title, {'mode': 'series_detail', 'series_id': content_id}, is_folder=True, thumb=thumb, info=info, content=src)
            else:
                add_directory_item(title, {'mode': 'play', 'id': src.get('playUrl') or src.get('streamUrl') or src.get('id')}, is_folder=False, thumb=thumb, info=info, content=src)
        except Exception:
            continue
    xbmcplugin.endOfDirectory(HANDLE)


def do_login():
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    ok = api.login()
    if ok:
        # attempt PKCE authorize + token exchange (uses the saved cookie session)
        tokens = api.perform_pkce_authorize_and_exchange()
        if tokens:
            xbmcgui.Dialog().notification('NLZiet', 'Login successful (tokens acquired)', xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification('NLZiet', 'Login successful (no tokens)', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('NLZiet', 'Login failed — running in demo mode', xbmcgui.NOTIFICATION_INFO)


def manage_profiles():
    """List available profiles and let the user switch the active profile.

    This renders a directory of profiles where the currently active profile
    is displayed in green. Selecting a profile will activate it and re-open
    the list so the active profile remains highlighted until another is
    chosen.
    """
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    profiles = api.get_profiles()
    # Try to obtain tokens if profiles empty
    if not profiles:
        try:
            api.perform_pkce_authorize_and_exchange()
            profiles = api.get_profiles() or []
        except Exception:
            profiles = profiles or []

    if not profiles:
        xbmcgui.Dialog().notification('NLZiet', 'No profiles available. Please login first.', xbmcgui.NOTIFICATION_INFO)
        return

    current_pid = ADDON.getSetting('profile_id') or ''
    # Build a directory listing: active profile is colored/marked
    for p in profiles:
        name = p.get('displayName') or p.get('name') or p.get('profileName') or p.get('id') or str(p)
        pid = p.get('id') or p.get('profileId') or p.get('profile_id') or name
        try:
            # Compare as strings to be tolerant of types
            is_active = str(pid) == str(current_pid)
        except Exception:
            is_active = False

        # Build a local path to bundled icons
        try:
            addon_path = ADDON.getAddonInfo('path') or ''
        except Exception:
            addon_path = ''

        # Prefer a PNG asset, then SVG, then the addon's icon.png
        candidates = [
            os.path.join(addon_path, 'resources', 'media', 'emoji_google_active.png'),
            os.path.join(addon_path, 'resources', 'media', 'emoji_google_active.svg'),
            os.path.join(addon_path, 'icon.png'),
        ]
        active_icon = None
        for c in candidates:
            try:
                if c and os.path.exists(c):
                    active_icon = c
                    break
            except Exception:
                continue

        # For active profile use the bundled Google-style icon as the thumb
        if is_active:
            # Keep the color tag when an icon is available; no emoji prefix
            title = _make_color_tag('FF27AE60', name) if active_icon else name
            thumb = active_icon
            info_obj = {'plotoutline': 'Active'}
        else:
            # Use bundled inactive icon when available so inactive profiles show an icon
            candidates_inactive = [
                os.path.join(addon_path, 'resources', 'media', 'emoji_google_inactive.png'),
                os.path.join(addon_path, 'resources', 'media', 'emoji_google_inactive.svg'),
                os.path.join(addon_path, 'icon.png'),
            ]
            inactive_icon = None
            for c in candidates_inactive:
                try:
                    if c and os.path.exists(c):
                        inactive_icon = c
                        break
                except Exception:
                    continue
            title = name
            thumb = inactive_icon
            info_obj = None

        # Selecting an item triggers the 'select_profile' route with the profile id
        add_directory_item(title, {'mode': 'select_profile', 'profile_id': str(pid)}, is_folder=True, thumb=thumb, info=info_obj)

    xbmcplugin.endOfDirectory(HANDLE)


def browse_my_list():
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    try:
        items = api.get_my_list() or []
    except Exception:
        items = []

    if not items:
        xbmcgui.Dialog().notification('NLZiet', 'My List is empty', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    # Group My List items into Series/Movies/Other so the My List top-level
    # shows folders the user can open to view each category.
    groups = {'Series': [], 'Movies': [], 'Other': []}
    for itm in items:
        try:
            typ = (itm.get('type') or '').lower()
            if 'series' in typ or 'tvshow' in typ:
                groups['Series'].append(itm)
            elif 'movie' in typ or 'film' in typ:
                groups['Movies'].append(itm)
            else:
                groups['Other'].append(itm)
        except Exception:
            groups['Other'].append(itm)

    # Present folders for each non-empty group (Series and Movies prioritized)
    folder_order = ['Series', 'Movies', 'Other']
    any_folder = False
    for g in folder_order:
        lst = groups.get(g) or []
        if not lst:
            continue
        first = lst[0] if lst else None
        thumb = _pick_landscape_thumb(first) if first else None
        label = f"{g}: {len(lst)} found"
        add_directory_item(label, {'mode': 'my_list_group', 'group': g}, is_folder=True, thumb=thumb)
        any_folder = True

    if not any_folder:
        xbmcgui.Dialog().notification('NLZiet', 'My List is empty', xbmcgui.NOTIFICATION_INFO)
    xbmcplugin.endOfDirectory(HANDLE)


def browse_my_list_group(group):
    """Show items from the user's My List filtered to a single group."""
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    try:
        items = api.get_my_list() or []
    except Exception:
        items = []

    if not items:
        xbmcgui.Dialog().notification('NLZiet', 'My List is empty', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    filtered = []
    for itm in items:
        try:
            typ = (itm.get('type') or '').lower()
            if group == 'Series' and ('series' in typ or 'tvshow' in typ):
                filtered.append(itm)
            elif group == 'Movies' and ('movie' in typ or 'film' in typ):
                filtered.append(itm)
            elif group == 'Other' and not ('series' in typ or 'tvshow' in typ or 'movie' in typ or 'film' in typ):
                filtered.append(itm)
        except Exception:
            continue

    if not filtered:
        xbmcgui.Dialog().notification('NLZiet', f'No items found for {group}', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for itm in filtered:
        try:
            title = itm.get('title') or itm.get('name') or itm.get('id') or 'Item'
            thumb = itm.get('thumb') or itm.get('posterUrl') or None
            typ = (itm.get('type') or '').lower()
            if 'series' in typ or 'tvshow' in typ:
                add_directory_item(title, {'mode': 'series_detail', 'series_id': itm.get('id')}, is_folder=True, thumb=thumb, content=itm)
            elif 'episode' in typ:
                add_directory_item(title, {'mode': 'play', 'id': itm.get('id')}, is_folder=False, thumb=thumb, content=itm)
            elif 'movie' in typ or 'film' in typ:
                add_directory_item(title, {'mode': 'play', 'id': itm.get('id')}, is_folder=False, thumb=thumb, content=itm)
            else:
                add_directory_item(title, {'mode': 'play', 'id': itm.get('id')}, is_folder=False, thumb=thumb, content=itm)
        except Exception:
            continue
    xbmcplugin.endOfDirectory(HANDLE)


def toggle_mylist(item_id=None, title=None, type=None, thumb=None):
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    if not item_id:
        xbmcgui.Dialog().notification('NLZiet', 'Missing id for My List action', xbmcgui.NOTIFICATION_ERROR)
        return
    # Defensive: only allow Series or Movies to be toggled
    if type and isinstance(type, str):
        tl = type.lower()
        if not any(x in tl for x in ('series', 'tvshow', 'movie', 'film')):
            xbmcgui.Dialog().notification('NLZiet', 'Only Series and Movies can be added to My List', xbmcgui.NOTIFICATION_INFO)
            return
    else:
        # try to detect content type from detail
        try:
            det = api.get_content_detail(item_id) or {}
            raw_type = (det.get('raw') or {}).get('type') or det.get('type') or ''
            if raw_type and not any(x in str(raw_type).lower() for x in ('series', 'tvshow', 'movie', 'film')):
                xbmcgui.Dialog().notification('NLZiet', 'Only Series and Movies can be added to My List', xbmcgui.NOTIFICATION_INFO)
                return
        except Exception:
            pass
    try:
        itm = {'id': item_id, 'title': title, 'type': type, 'posterUrl': thumb}
        if api.is_in_my_list(item_id):
            removed = api.remove_from_my_list(item_id)
            if removed:
                xbmcgui.Dialog().notification('NLZiet', 'Removed from My List', xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification('NLZiet', 'Failed to remove from My List', xbmcgui.NOTIFICATION_ERROR)
        else:
            added = api.add_to_my_list(itm)
            if added:
                xbmcgui.Dialog().notification('NLZiet', 'Added to My List', xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification('NLZiet', 'Failed to add to My List', xbmcgui.NOTIFICATION_ERROR)
    except Exception:
        xbmcgui.Dialog().notification('NLZiet', 'My List action failed', xbmcgui.NOTIFICATION_ERROR)
    # Refresh the current container so context menu changes reflect immediately
    try:
        xbmc.executebuiltin('Container.Refresh')
    except Exception:
        pass


def select_profile(profile_id):
    """Activate the given profile id and re-render the profiles list."""
    if not profile_id:
        xbmcgui.Dialog().notification('NLZiet', 'Missing profile id', xbmcgui.NOTIFICATION_ERROR)
        return

    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    try:
        result = api.select_profile(profile_id)
    except Exception as e:
        xbmc.log(f"NLZiet select_profile error: {e}", xbmc.LOGERROR)
        result = None

    if result:
        # persist selection
        try:
            ADDON.setSetting('profile_id', str(profile_id))
            # attempt to look up a friendly name
            profiles = api.get_profiles() or []
            profile_name = ''
            for p in profiles:
                if str(p.get('id')) == str(profile_id) or str(p.get('profileId')) == str(profile_id):
                    profile_name = p.get('displayName') or p.get('name') or p.get('profileName') or ''
                    break
            ADDON.setSetting('profile_name', profile_name or str(profile_id))
        except Exception:
            pass
        xbmcgui.Dialog().notification('NLZiet', f'Profile switched to {ADDON.getSetting("profile_name") or profile_id}', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('NLZiet', 'Profile switch failed', xbmcgui.NOTIFICATION_ERROR)

    # Replace the current container with the profiles listing so we don't
    # push an extra history entry. This prevents Back from cycling
    # through profile selections and instead returns to the main menu.
    try:
        profiles_url = build_url({'mode': 'profiles'})
        xbmc.executebuiltin('Container.Update(%s,replace)' % profiles_url)
    except Exception:
        # Fallback: if the builtin fails, render profiles directly.
        manage_profiles()


def apply_profile():
    """Apply the `profile_id` stored in settings: perform profile-grant and
    update the stored `profile_name` setting for display in Settings UI.
    """
    pid = ADDON.getSetting('profile_id') or ''
    if not pid:
        xbmcgui.Dialog().notification('NLZiet', 'No Profile ID set in Settings', xbmcgui.NOTIFICATION_INFO)
        return

    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)

    try:
        # Attempt a direct profile switch using the stored master token or
        # cookie session.
        result = api.select_profile(pid)
        if not result:
            # Try to obtain tokens using PKCE and retry selection
            tokens = api.perform_pkce_authorize_and_exchange()
            if tokens:
                result = api.select_profile(pid)
    except Exception as e:
        xbmc.log(f"NLZiet apply_profile error: {e}", xbmc.LOGERROR)
        result = None

    if result:
        # Find a human-friendly name for the profile when possible
        profile_name = ''
        try:
            profiles = api.get_profiles() or []
            for p in profiles:
                if str(p.get('id')) == str(pid) or str(p.get('profileId')) == str(pid):
                    profile_name = p.get('displayName') or p.get('name') or p.get('profileName') or ''
                    break
        except Exception:
            profile_name = ''

        try:
            ADDON.setSetting('profile_name', profile_name or str(pid))
        except Exception:
            pass

        xbmcgui.Dialog().notification('NLZiet', f'Profile applied: {profile_name or pid}', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('NLZiet', 'Failed to apply profile. Try Manage profiles.', xbmcgui.NOTIFICATION_ERROR)


def do_search():
    kb = xbmc.Keyboard('', 'Search NLZiet')
    kb.doModal()
    if not kb.isConfirmed():
        return
    query = kb.getText()
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    results = api.search(query)
    # If the API search failed or returned no results, try fallback endpoints
    if not results:
        fb = []
        ql = (query or '').lower()
        try:
            sers = api.get_series_list(limit=999) or []
            for s in sers:
                try:
                    t = (s.get('title') or '')
                    if ql and ql in t.lower():
                        fb.append(s)
                except Exception:
                    continue
        except Exception:
            pass
        try:
            movs = api.get_movies() or []
            for m in movs:
                try:
                    t = (m.get('title') or '')
                    if ql and ql in t.lower():
                        fb.append(m)
                except Exception:
                    continue
        except Exception:
            pass
        try:
            chs = api.get_channels() or []
            for c in chs:
                try:
                    t = (c.get('title') or '')
                    if ql and ql in t.lower():
                        fb.append(c)
                except Exception:
                    continue
        except Exception:
            pass
        if fb:
            results = fb
        else:
            xbmcgui.Dialog().notification('NLZiet', f'No results for "{query}"', xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(HANDLE)
            return
    # Group search results by their detected type so we can present grouped
    # folders (e.g. "Series" and "Movies") when multiple groups are found.
    group_map = {}
    for item in results:
        try:
            content_id = item.get('id') or item.get('contentId') or item.get('content_id')
        except Exception:
            content_id = None
        try:
            itype = item.get('type') or ''
            itype_l = (str(itype).lower() if itype else '')
        except Exception:
            itype_l = ''

        if not itype_l and content_id:
            try:
                det = api.get_content_detail(content_id) or {}
                raw = det.get('raw') or {}
                itype_l = (str(raw.get('type') or '')).lower()
            except Exception:
                itype_l = itype_l

        group = None
        if 'series' in itype_l or 'tvshow' in itype_l:
            group = 'Series'
        elif 'episode' in itype_l:
            group = 'Episodes'
        elif 'movie' in itype_l or 'film' in itype_l:
            group = 'Movies'
        elif 'channel' in itype_l or 'live' in itype_l:
            group = 'Channels'
        else:
            sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
            if sid:
                group = 'Series'
            else:
                group = 'Other'

        group_map.setdefault(group, []).append(item)

    non_empty = [g for g, v in group_map.items() if v]
    # If results span multiple groups, present top-level folders for each group
    # so the user can open e.g. "Series" or "Movies" individually.
    if len(non_empty) > 1:
        for g in non_empty:
            items_for_group = group_map.get(g) or []
            thumb = None
            try:
                first = items_for_group[0] if items_for_group else None
                thumb = _pick_landscape_thumb(first) if first else None
            except Exception:
                thumb = None
            label = f"{g}: {len(items_for_group)} found"
            add_directory_item(label, {'mode': 'search_group', 'q': query, 'group': g}, is_folder=True, thumb=thumb)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    # Otherwise fall back to presenting each result individually (previous behavior)
    for item in results:
        info = None
        try:
            # prefer description provided directly in the search result to avoid extra requests
            desc = item.get('description') or item.get('subtitle') or ''
            if desc:
                title_for_info = item.get('title') or ''
                expiry_text = item.get('expires_in') or None
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                # plot: include colored expiry on the first line for the info dialog
                plot_full = desc
                # plotoutline (label2): plain expiry prefix + truncated plot for default skin
                po = truncated
                if expiry_text:
                    marker = '🔶 '
                    colored = _make_color_tag(EXPIRY_COLOR_RAW, expiry_text)
                    plot_full = f"{colored}\n{desc}" if desc else colored
                    po = f"{marker}{expiry_text} — {truncated}" if truncated else f"{marker}{expiry_text}"
                info = {
                    'title': title_for_info,
                    'plot': plot_full,
                    'plotoutline': po,
                }
            else:
                cid = item.get('id')
                if cid:
                    detail = api.get_content_detail(cid)
                    if detail:
                        desc = detail.get('description') or detail.get('plot') or ''
                        expiry_text = detail.get('expires_in') or None
                        title_for_info = detail.get('title') or item.get('title') or ''
                        if desc:
                            truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                            plot_full = desc
                            po = truncated
                            if expiry_text:
                                marker = '🔶 '
                                colored = _make_color_tag(EXPIRY_COLOR_RAW, expiry_text)
                                plot_full = f"{colored}\n{desc}" if desc else colored
                                po = f"{marker}{expiry_text} — {truncated}" if truncated else f"{marker}{expiry_text}"
                            info = {
                                'title': title_for_info,
                                'plot': plot_full,
                                'plotoutline': po,
                            }
        except Exception:
            info = None
        # decide how to present the search result based on its detected type
        content_id = item.get('id') or item.get('contentId') or item.get('content_id')
        itype = item.get('type') or ''
        itype_l = (str(itype).lower() if itype else '')

        # If the inline type is not present try to fetch detail to detect it
        if not itype_l and content_id:
            try:
                det = api.get_content_detail(content_id) or {}
                raw = det.get('raw') or {}
                itype_l = (str(raw.get('type') or '')).lower()
            except Exception:
                itype_l = itype_l

        title = item.get('title') or item.get('name') or content_id or 'Result'
        thumb = _pick_landscape_thumb(item)

        # Determine a simple group label so search results indicate their type
        group = None
        if 'series' in itype_l or 'tvshow' in itype_l:
            group = 'Series'
        elif 'episode' in itype_l:
            group = 'Episodes'
        elif 'movie' in itype_l or 'film' in itype_l:
            group = 'Movies'
        elif 'channel' in itype_l or 'live' in itype_l:
            group = 'Channels'
        else:
            sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
            if sid:
                group = 'Series'

        display_title = f"{group}: {title}" if group else title

        # Series / TV show -> open series detail (folder)
        if 'series' in itype_l or 'tvshow' in itype_l:
            add_directory_item(display_title, {'mode': 'series_detail', 'series_id': content_id}, is_folder=True, thumb=thumb, info=info, content=item)
        # Episode -> playable
        elif 'episode' in itype_l:
            add_directory_item(display_title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info, content=item)
        # Movie -> playable
        elif 'movie' in itype_l or 'film' in itype_l:
            add_directory_item(display_title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info, content=item)
        # Channel / Live -> play as live
        elif 'channel' in itype_l or 'live' in itype_l:
            add_directory_item(display_title, {'mode': 'play', 'id': item.get('id'), 'fmt': 'live'}, is_folder=False, thumb=thumb, info=info, content=item)
        else:
            # fallback: treat as series if a seriesId exists, otherwise play
            sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
            if sid:
                add_directory_item(display_title, {'mode': 'series_detail', 'series_id': sid}, is_folder=True, thumb=thumb, info=info, content=item)
            else:
                add_directory_item(display_title, {'mode': 'play', 'id': item.get('id') or content_id}, is_folder=False, thumb=thumb, info=info, content=item)
    xbmcplugin.endOfDirectory(HANDLE)


def browse_category(content_type):
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    epg_map = {}
    if content_type.lower() == 'movies':
        results = api.get_movies()
    elif content_type.lower() == 'channels':
        results = api.get_channels()
        # fetch current program (EPG) for the visible channels and show it
        channel_ids = [r.get('id') for r in results if r.get('id')]
        try:
            epg_map = api.get_current_programs(channel_ids)
        except Exception:
            epg_map = {}
    else:
        results = api.search(content_type, content_type=content_type)
    for item in results:
        info = None
        try:
            desc = item.get('description') or item.get('subtitle') or ''
            if desc:
                title_for_info = item.get('title') or ''
                expiry_text = item.get('expires_in') or None
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                plot_full = desc
                po = truncated
                if expiry_text:
                    marker = '🔶 '
                    colored = _make_color_tag(EXPIRY_COLOR_RAW, expiry_text)
                    plot_full = f"{colored}\n{desc}" if desc else colored
                    po = f"{marker}{expiry_text} — {truncated}" if truncated else f"{marker}{expiry_text}"
                info = {
                    'title': title_for_info,
                    'plot': plot_full,
                    'plotoutline': po,
                }
            else:
                cid = item.get('id')
                if cid:
                    detail = api.get_content_detail(cid)
                    if detail:
                        desc = detail.get('description') or detail.get('plot') or ''
                        expiry_text = detail.get('expires_in') or None
                        title_for_info = detail.get('title') or item.get('title') or ''
                        if desc:
                            truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                            plot_full = desc
                            po = truncated
                            if expiry_text:
                                marker = '🔶 '
                                colored = _make_color_tag(EXPIRY_COLOR_RAW, expiry_text)
                                plot_full = f"{colored}\n{desc}" if desc else colored
                                po = f"{marker}{expiry_text} — {truncated}" if truncated else f"{marker}{expiry_text}"
                            info = {
                                'title': title_for_info,
                                'plot': plot_full,
                                'plotoutline': po,
                            }
                # Attach 'Now' EPG info when available for channels
                if content_type.lower() == 'channels' and item.get('id'):
                    try:
                        prog = epg_map.get(str(item.get('id'))) or epg_map.get(item.get('id'))
                        if not prog:
                            # Fallback: some handshakes include the current program (item/asset).
                            try:
                                hs_info = api.get_stream_info(item.get('id'), context='Live')
                                hs = hs_info.get('handshake') or {}
                                # prefer `item` then `asset` from the handshake
                                hs_prog = None
                                if isinstance(hs, dict):
                                    hs_prog = hs.get('item') or hs.get('asset') or hs.get('streamSessionData') or None
                                if hs_prog and isinstance(hs_prog, dict):
                                    title_prog = hs_prog.get('title') or hs_prog.get('name') or (hs_prog.get('programmeTitle') if isinstance(hs_prog.get('programmeTitle'), str) else '')
                                    # parse start/end from asset or streamSessionData if available
                                    start_ts = None
                                    end_ts = None
                                    asset = hs.get('asset') or {}
                                    if isinstance(asset, dict):
                                        start_ts = api._parse_timestamp(asset.get('startAt') or asset.get('streamStartAt') or asset.get('start'))
                                        end_ts = api._parse_timestamp(asset.get('endAt') or asset.get('streamEndAt') or asset.get('end'))
                                    # as extra fallback, check streamSessionDataString
                                    if (not start_ts or not end_ts) and hs.get('streamSessionData'):
                                        ssd = hs.get('streamSessionData')
                                        if isinstance(ssd, dict):
                                            ssd_str = ssd.get('streamSessionDataString') or ssd.get('streamSessionData')
                                            try:
                                                import json as _json
                                                if isinstance(ssd_str, str):
                                                    parsed_ssd = _json.loads(ssd_str)
                                                    start_ts = start_ts or api._parse_timestamp(parsed_ssd.get('epgAssetStartAt') or parsed_ssd.get('streamStartAt') or parsed_ssd.get('start'))
                                                    end_ts = end_ts or api._parse_timestamp(parsed_ssd.get('endAt') or parsed_ssd.get('streamEndAt') or parsed_ssd.get('end'))
                                            except Exception:
                                                pass
                                    prog = {'title': title_prog or '', 'desc': hs_prog.get('description') or hs_prog.get('summary') or '', 'start': start_ts, 'end': end_ts, 'raw': hs_prog, 'in_now': False}
                            except Exception:
                                prog = None

                        if prog:
                            title_prog = prog.get('title') or ''
                            start_ts = prog.get('start')
                            end_ts = prog.get('end')
                            try:
                                start_s = time.strftime('%H:%M', time.localtime(start_ts)) if start_ts else ''
                            except Exception:
                                start_s = ''
                            try:
                                end_s = time.strftime('%H:%M', time.localtime(end_ts)) if end_ts else ''
                            except Exception:
                                end_s = ''
                            time_range = ''
                            if start_s and end_s:
                                time_range = f"{start_s}-{end_s}"
                            elif start_s:
                                time_range = start_s
                            program_line = f"Now: {title_prog}" + (f" ({time_range})" if time_range else '')
                            desc_text = prog.get('desc') or ''
                            # prepare truncated outline and full plot including description
                            try:
                                desc_short = (desc_text[:120] + '...') if len(desc_text) > 120 else desc_text
                            except Exception:
                                desc_short = ''

                            if info:
                                old_po = info.get('plotoutline', '')
                                old_plot = info.get('plot', '')

                                po_new = program_line
                                if desc_short:
                                    po_new = f"{po_new} — {desc_short}"
                                if old_po:
                                    po_new = f"{po_new}\n{old_po}"
                                info['plotoutline'] = po_new

                                plot_new = program_line
                                if desc_text:
                                    plot_new = f"{plot_new}\n{desc_text}"
                                if old_plot:
                                    plot_new = f"{plot_new}\n{old_plot}"
                                info['plot'] = plot_new
                            else:
                                po_val = program_line + (f" — {desc_short}" if desc_short else '')
                                plot_val = program_line + (f"\n{desc_text}" if desc_text else '')
                                info = {'title': item.get('title'), 'plotoutline': po_val, 'plot': plot_val}
                    except Exception:
                        pass
        except Exception:
            info = None
        # For channels, mark play queries with fmt=live so the player uses
        # the Live handshake when resolving the stream.
        query = {'mode': 'play', 'id': item.get('id')}
        if content_type.lower() == 'channels':
            query['fmt'] = 'live'
        add_directory_item(item.get('title'), query, is_folder=False, thumb=_pick_landscape_thumb(item), info=info, content=item)
    xbmcplugin.endOfDirectory(HANDLE)


def search_group(q, group):
    """Show search results filtered to a single group (e.g. 'Series' or 'Movies').

    This re-runs the search (or fallback) and presents only items that match
    the requested group name.
    """
    if not q:
        xbmcgui.Dialog().notification('NLZiet', 'Missing search query', xbmcgui.NOTIFICATION_INFO)
        return

    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    results = api.search(q)
    if not results:
        fb = []
        ql = (q or '').lower()
        try:
            sers = api.get_series_list(limit=999) or []
            for s in sers:
                try:
                    t = (s.get('title') or '')
                    if ql and ql in t.lower():
                        fb.append(s)
                except Exception:
                    continue
        except Exception:
            pass
        try:
            movs = api.get_movies() or []
            for m in movs:
                try:
                    t = (m.get('title') or '')
                    if ql and ql in t.lower():
                        fb.append(m)
                except Exception:
                    continue
        except Exception:
            pass
        try:
            chs = api.get_channels() or []
            for c in chs:
                try:
                    t = (c.get('title') or '')
                    if ql and ql in t.lower():
                        fb.append(c)
                except Exception:
                    continue
        except Exception:
            pass
        if fb:
            results = fb
        else:
            xbmcgui.Dialog().notification('NLZiet', f'No results for "{q}"', xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(HANDLE)
            return

    # Present only items that match the requested group
    for item in results:
        info = None
        try:
            desc = item.get('description') or item.get('subtitle') or ''
            if desc:
                title_for_info = item.get('title') or ''
                expiry_text = item.get('expires_in') or None
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                plot_full = desc
                po = truncated
                if expiry_text:
                    marker = '🔶 '
                    colored = _make_color_tag(EXPIRY_COLOR_RAW, expiry_text)
                    plot_full = f"{colored}\n{desc}" if desc else colored
                    po = f"{marker}{expiry_text} — {truncated}" if truncated else f"{marker}{expiry_text}"
                info = {'title': title_for_info, 'plot': plot_full, 'plotoutline': po}
            else:
                cid = item.get('id')
                if cid:
                    detail = api.get_content_detail(cid)
                    if detail:
                        desc = detail.get('description') or detail.get('plot') or ''
                        expiry_text = detail.get('expires_in') or None
                        title_for_info = detail.get('title') or item.get('title') or ''
                        if desc:
                            truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                            plot_full = desc
                            po = truncated
                            if expiry_text:
                                marker = '🔶 '
                                colored = _make_color_tag(EXPIRY_COLOR_RAW, expiry_text)
                                plot_full = f"{colored}\n{desc}" if desc else colored
                                po = f"{marker}{expiry_text} — {truncated}" if truncated else f"{marker}{expiry_text}"
                            info = {'title': title_for_info, 'plot': plot_full, 'plotoutline': po}
        except Exception:
            info = None

        content_id = item.get('id') or item.get('contentId') or item.get('content_id')
        itype = item.get('type') or ''
        itype_l = (str(itype).lower() if itype else '')

        if not itype_l and content_id:
            try:
                det = api.get_content_detail(content_id) or {}
                raw = det.get('raw') or {}
                itype_l = (str(raw.get('type') or '')).lower()
            except Exception:
                itype_l = itype_l

        # compute group and skip items that don't match
        group_name = None
        if 'series' in itype_l or 'tvshow' in itype_l:
            group_name = 'Series'
        elif 'episode' in itype_l:
            group_name = 'Episodes'
        elif 'movie' in itype_l or 'film' in itype_l:
            group_name = 'Movies'
        elif 'channel' in itype_l or 'live' in itype_l:
            group_name = 'Channels'
        else:
            sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
            if sid:
                group_name = 'Series'
            else:
                group_name = 'Other'

        if not group_name or str(group_name).lower() != (str(group or '').lower()):
            continue

        title = item.get('title') or item.get('name') or content_id or 'Result'
        thumb = _pick_landscape_thumb(item)

        # Inside a search-group listing we show plain titles; the group
        # context is already provided by the parent folder label.
        display_title = title

        if 'series' in itype_l or 'tvshow' in itype_l:
            add_directory_item(display_title, {'mode': 'series_detail', 'series_id': content_id}, is_folder=True, thumb=thumb, info=info, content=item)
        elif 'episode' in itype_l:
            add_directory_item(display_title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info, content=item)
        elif 'movie' in itype_l or 'film' in itype_l:
            add_directory_item(display_title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info, content=item)
        elif 'channel' in itype_l or 'live' in itype_l:
            add_directory_item(display_title, {'mode': 'play', 'id': item.get('id'), 'fmt': 'live'}, is_folder=False, thumb=thumb, info=info, content=item)
        else:
            sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
            if sid:
                add_directory_item(display_title, {'mode': 'series_detail', 'series_id': sid}, is_folder=True, thumb=thumb, info=info, content=item)
            else:
                add_directory_item(display_title, {'mode': 'play', 'id': item.get('id') or content_id}, is_folder=False, thumb=thumb, info=info, content=item)
    xbmcplugin.endOfDirectory(HANDLE)


def ensure_inputstream_for_drm():
    try:
        xbmcaddon.Addon('inputstream.adaptive')
        return True
    except Exception:
        xbmcgui.Dialog().ok('Dependency missing', 'Please install inputstream.adaptive to play DRM streams.')
        return False


def play_item(content_id, fmt=None):
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    api = NLZietAPI(username=username, password=password)
    if fmt == 'live':
        info = api.get_stream_info(content_id, context='Live')
    else:
        info = api.get_stream_info(content_id)
    manifest = info.get('manifest')
    xbmc.log(f"NLZiet play_item: id={content_id} manifest={manifest} is_drm={info.get('is_drm')}", xbmc.LOGDEBUG)
    if not manifest:
        xbmcgui.Dialog().notification('NLZiet', 'No manifest available', xbmcgui.NOTIFICATION_ERROR)
        return

    if info.get('is_drm'):
        if not ensure_inputstream_for_drm():
            return
        li = xbmcgui.ListItem(path=manifest)
        # prefer new property if available
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        li.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        license_url = info.get('license_url') or ''
        headers = info.get('license_headers') or {}
        xbmc.log("NLZiet DRM: license_url=%s headers=%s" % (license_url, headers), xbmc.LOGINFO)
        drm_security = info.get('drm_security')
        xbmc.log(f"NLZiet DRM security level: {drm_security}", xbmc.LOGINFO)
        try:
            raw = info.get('drm_raw')
            xbmc.log("NLZiet DRM raw (partial): %s" % (str(raw)[:1000]), xbmc.LOGINFO)
        except Exception:
            pass
        if drm_security:
            xbmcgui.Dialog().notification('NLZiet', f'Required DRM: {drm_security}', xbmcgui.NOTIFICATION_INFO)

        # make a safe copy of headers and ensure User-Agent matches the API session
        try:
            headers = dict(headers or {})
        except Exception:
            headers = {}

        try:
            if api and getattr(api, 'user_agent', None):
                headers.setdefault('User-Agent', api.user_agent)
        except Exception:
            pass

        import urllib.parse as _up, json as _json, platform as _platform

        # Extract Nlziet-License directly from the handshake response if available,
        # prefer the raw DRM dict when present.
        try:
            nlziet_license = ''
            drm_obj = info.get('drm_raw') or {}
            if isinstance(drm_obj, dict):
                hdrs = drm_obj.get('headers') or {}
                if isinstance(hdrs, dict):
                    nlziet_license = hdrs.get('Nlziet-License') or hdrs.get('nlziet-license') or ''
            if not nlziet_license:
                nlziet_license = (headers.get('Nlziet-License') or headers.get('nlziet-license') or '')
        except Exception:
            nlziet_license = ''

        # Build the canonical license_key and a matching CRLF `stream_headers` block.
        license_url = info.get('license_url') or ''
        try:
            stream_info = {'drm': info.get('drm_raw') or {}, 'manifestUrl': info.get('manifest')}
            try:
                nlziet_license = stream_info['drm']['headers']['Nlziet-License']
            except Exception:
                nlziet_license = (stream_info.get('drm') or {}).get('headers', {}).get('Nlziet-License') or headers.get('Nlziet-License') or ''

            # derive device/app metadata
            _app_name = 'NLZIET'
            _app_version = '5.13.6'
            _brand = _platform.system() or 'Linux'
            _model = _platform.node() or 'Kodi'
            _platform_version = _platform.release() or ''
            _capabilities = 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile'

            # If this is a live playback request, avoid adding Authorization
            is_live = (fmt == 'live')
            token = api.get_access_token() or ''
            if is_live:
                token = ''

            # header values (unencoded)
            hdr_vals = {
                'Authorization': 'Bearer ' + token if token else '',
                'Nlziet-License': str(nlziet_license),
                'Nlziet-AppName': _app_name,
                'Nlziet-AppVersion': _app_version,
                'Nlziet-BrandName': _brand,
                'Nlziet-ModelName': _model,
                'Nlziet-PlatformVersion': _platform_version,
                'Nlziet-DeviceCapabilities': _capabilities,
                'Content-Type': 'application/octet-stream',
            }

            # canonical header ordering (Authorization first when present)
            header_order = ['Authorization', 'Nlziet-License', 'Nlziet-AppName', 'Nlziet-AppVersion', 'Nlziet-BrandName', 'Nlziet-ModelName', 'Nlziet-PlatformVersion', 'Nlziet-DeviceCapabilities', 'Content-Type']

            pairs = []
            final_headers = {}
            for k in header_order:
                v = hdr_vals.get(k) or headers.get(k) or headers.get(k.lower()) or ''
                if v is None or v == '':
                    continue
                final_headers[k] = str(v)
                pairs.append(f"{k}={_up.quote(str(v), safe='')}")

            # include any remaining handshake headers not present in canonical ordering
            for hk, hv in (headers or {}).items():
                if hk not in final_headers and hv:
                    final_headers[hk] = str(hv)
                    pairs.append(f"{hk}={_up.quote(str(hv), safe='')}")

            header_block = '&'.join(pairs)
            license_url = license_url or 'https://api.nlziet.nl/v9/license/proxy/Widevine'
            license_key = f"{license_url}|{header_block}|R{{SSM}}|"

            # Build CRLF stream headers from final_headers to keep them consistent
            if final_headers:
                header_str = '\r\n'.join(f"{k}: {v}" for k, v in final_headers.items())
                li.setProperty('inputstream.adaptive.stream_headers', header_str)
        except Exception:
            license_key = f"{license_url}|||"

        xbmc.log(f"NLZiet using license_key: {license_key}", xbmc.LOGINFO)

        # Apply the license_key and ensure manifest type is `mpd` for DASH
        li.setProperty('inputstream.adaptive.license_key', license_key)
        li.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        li.setProperty('inputstream.adaptive.manifest_update_decode', 'true')

        # Attach external subtitles (OutOfBand VTT) returned by the handshake
        try:
            subs = info.get('subtitles') or []
            sub_urls = []
            for s in subs:
                if isinstance(s, dict):
                    url = s.get('url') or s.get('uri') or s.get('file')
                else:
                    url = s
                if url:
                    sub_urls.append(url)
            if sub_urls:
                try:
                    enable_subs = ADDON.getSetting('subtitles_default')
                except Exception:
                    enable_subs = None
                # Only attach subtitles automatically when the setting is enabled
                if str(enable_subs or '').lower() in ('true', '1', 'yes'):
                    xbmc.log(f"NLZiet attaching subtitles: {sub_urls}", xbmc.LOGINFO)
                    try:
                        li.setSubtitles(sub_urls)
                    except Exception:
                        # fallback: store as property for debugging or later handling
                        try:
                            li.setProperty('nlziet.subtitles', ';'.join(sub_urls))
                        except Exception:
                            pass
                else:
                    xbmc.log('NLZiet: auto-subtitles disabled by settings', xbmc.LOGDEBUG)
        except Exception:
            pass

        # do not override inputstream's PSSH handling by supplying malformed
        # `inputstream.adaptive.license_data`. The canonical `license_key` and
        # `stream_headers` are sufficient; leaving `license_data` unset avoids
        # the plugin trying to parse incorrect PSSH data from this property.

        li.setMimeType('application/dash+xml')
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        # non-DRM: simply play the manifest URL
        xbmc.log(f"NLZiet non-DRM manifest: {manifest}", xbmc.LOGDEBUG)
        li = xbmcgui.ListItem(path=manifest)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)


def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    mode = params.get('mode')
    if not mode:
        main_menu()
    elif mode == 'login':
        do_login()
    elif mode == 'search':
        do_search()
    elif mode == 'profiles':
        manage_profiles()
    elif mode == 'my_list':
        browse_my_list()
    elif mode == 'my_list_group':
        browse_my_list_group(params.get('group'))
    elif mode == 'toggle_mylist':
        toggle_mylist(params.get('id'), params.get('title'), params.get('type'), params.get('thumb'))
    elif mode == 'select_profile':
        select_profile(params.get('profile_id'))
    elif mode == 'apply_profile':
        apply_profile()
    elif mode == 'series':
        browse_series()
    elif mode == 'search_group':
        search_group(params.get('q'), params.get('group'))
    elif mode == 'series_detail':
        show_series_detail(params.get('series_id'))
    elif mode == 'series_season':
        show_series_season(params.get('series_id'), params.get('season_id'))
    elif mode == 'placement_row':
        browse_placement_row(params.get('items_url'), params.get('placement_id'), params.get('comp_index'))
    elif mode == 'browse':
        browse_category(params.get('type', 'all'))
    elif mode == 'play':
        play_item(params.get('id'), params.get('fmt'))


if __name__ == '__main__':
    router(sys.argv[2][1:] if len(sys.argv) > 2 else '')
