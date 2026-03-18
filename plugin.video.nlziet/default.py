import sys
import urllib.parse
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


def add_directory_item(title, query, is_folder=True, thumb=None, info=None):
    url = build_url(query)
    li = xbmcgui.ListItem(label=title)
    if thumb:
        li.setArt({'thumb': thumb, 'icon': thumb})
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
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)


def main_menu():
    add_directory_item('Login (set credentials in settings)', {'mode': 'login'})
    add_directory_item('Manage profiles', {'mode': 'profiles'})
    add_directory_item('Search', {'mode': 'search'})
    add_directory_item('Series', {'mode': 'series'})
    add_directory_item('Movies', {'mode': 'browse', 'type': 'movies'})
    add_directory_item('Channels', {'mode': 'browse', 'type': 'channels'})
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
        add_directory_item(item.get('title') or item.get('id') or 'Series', {'mode': 'series_detail', 'series_id': item.get('id')}, is_folder=True, thumb=item.get('thumb'), info=info)
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
    episodes = api.get_series_episodes(series_id, season_id=season_id or None, limit=400)
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

        # Prefer an already-formatted episode numbering string when available
        formatted_label = ep.get('formatted_episode_numbering') or ep.get('formattedEpisodeNumbering') or (ep.get('raw') or {}).get('formattedEpisodeNumbering')
        label_title = ep.get('title') or ''
        if formatted_label:
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

        add_directory_item(label, {'mode': 'play', 'id': ep.get('id')}, is_folder=False, thumb=ep.get('thumb'), info=info)
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
            thumb = src.get('posterUrl') or (src.get('image') or {}).get('portraitUrl') or (src.get('image') or {}).get('landscapeUrl') or src.get('thumb') or src.get('thumbnail')
            desc = src.get('description') or src.get('summary') or ''
            info = None
            if desc:
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                info = {'title': title, 'plot': desc, 'plotoutline': truncated}

            if content_id:
                # Treat as series when possible
                add_directory_item(title, {'mode': 'series_detail', 'series_id': content_id}, is_folder=True, thumb=thumb, info=info)
            else:
                add_directory_item(title, {'mode': 'play', 'id': src.get('playUrl') or src.get('streamUrl') or src.get('id')}, is_folder=False, thumb=thumb, info=info)
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
    """List available profiles and let the user switch the active profile."""
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

    labels = []
    ids = []
    for p in profiles:
        name = p.get('displayName') or p.get('name') or p.get('profileName') or p.get('id') or str(p)
        pid = p.get('id') or p.get('profileId') or p.get('profile_id') or name
        labels.append(name)
        ids.append(pid)

    sel = xbmcgui.Dialog().select('Select NLZIET profile', labels)
    if sel is None or sel < 0:
        return

    chosen_pid = ids[sel]
    result = api.select_profile(chosen_pid)
    if result:
        try:
            ADDON.setSetting('profile_id', str(chosen_pid))
            ADDON.setSetting('profile_name', labels[sel])
        except Exception:
            pass
        xbmcgui.Dialog().notification('NLZiet', f'Profile switched to {labels[sel]}', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('NLZiet', 'Profile switch failed', xbmcgui.NOTIFICATION_ERROR)


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
            sers = api.get_series_list(limit=200) or []
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
        thumb = item.get('thumb') or item.get('posterUrl')

        # Series / TV show -> open series detail (folder)
        if 'series' in itype_l or 'tvshow' in itype_l:
            add_directory_item(title, {'mode': 'series_detail', 'series_id': content_id}, is_folder=True, thumb=thumb, info=info)
        # Episode -> playable
        elif 'episode' in itype_l:
            add_directory_item(title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info)
        # Movie -> playable
        elif 'movie' in itype_l or 'film' in itype_l:
            add_directory_item(title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info)
        # Channel / Live -> play as live
        elif 'channel' in itype_l or 'live' in itype_l:
            add_directory_item(title, {'mode': 'play', 'id': item.get('id'), 'fmt': 'live'}, is_folder=False, thumb=thumb, info=info)
        else:
            # fallback: treat as series if a seriesId exists, otherwise play
            sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
            if sid:
                add_directory_item(title, {'mode': 'series_detail', 'series_id': sid}, is_folder=True, thumb=thumb, info=info)
            else:
                add_directory_item(title, {'mode': 'play', 'id': item.get('id') or content_id}, is_folder=False, thumb=thumb, info=info)
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
        add_directory_item(item.get('title'), query, is_folder=False, thumb=item.get('thumb'), info=info)
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
                xbmc.log(f"NLZiet attaching subtitles: {sub_urls}", xbmc.LOGINFO)
                try:
                    li.setSubtitles(sub_urls)
                except Exception:
                    # fallback: store as property for debugging or later handling
                    try:
                        li.setProperty('nlziet.subtitles', ';'.join(sub_urls))
                    except Exception:
                        pass
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
    elif mode == 'apply_profile':
        apply_profile()
    elif mode == 'series':
        browse_series()
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
