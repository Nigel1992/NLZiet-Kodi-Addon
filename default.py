import sys
import re
import urllib.parse
import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import time
import threading
from datetime import datetime

from resources.lib.nlziet_api import NLZietAPI

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

# Global API instance cache to avoid repeated initialization
_api_cache = None
_api_cache_time = 0
_api_cache_timeout = 300  # 5 minutes - refresh cache after this

def get_api_instance():
    """Get or create a cached API instance to avoid repeated disk I/O and initialization."""
    global _api_cache, _api_cache_time
    current_time = time.time()
    
    # If cache exists and is fresh (within timeout), return it
    if _api_cache is not None and (current_time - _api_cache_time) < _api_cache_timeout:
        return _api_cache
    
    # Create new instance (loads cookies, tokens from disk)
    username = ADDON.getSetting('username') or ''
    password = ADDON.getSetting('password') or ''
    _api_cache = NLZietAPI(username=username, password=password)
    _api_cache_time = current_time
    return _api_cache

def clear_api_cache():
    """Clear the API instance cache (call after logout)."""
    global _api_cache, _api_cache_time
    _api_cache = None
    _api_cache_time = 0

# Raw expiry color to test — change this to 'orange' or a hex like 'FFA500' or
# try the exact raw tag you suggested ('ffoooo66') to experiment.
EXPIRY_COLOR_RAW = 'ffoooo66'

# Language/Localization dictionary - Dutch (NL) and English (EN)
TRANSLATIONS = {
    'login': {'nl': 'Inloggen', 'en': 'Login'},
    'sign_out': {'nl': 'Uitloggen', 'en': 'Sign Out'},
    'login_via_dialog': {'nl': 'Inloggen (via dialoogvenster)', 'en': 'Login (via dialog)'},
    'login_dialog_title': {'nl': 'NLZiet Inloggen', 'en': 'NLZiet Login'},
    'login_dialog_email': {'nl': 'E-mailadres', 'en': 'Email address'},
    'login_dialog_password': {'nl': 'Wachtwoord', 'en': 'Password'},
    'login_dialog_ok': {'nl': 'Inloggen', 'en': 'Login'},
    'login_dialog_cancel': {'nl': 'Annuleren', 'en': 'Cancel'},
    'token_expired': {'nl': 'Sessie verlopen - opnieuw inloggen is vereist', 'en': 'Session expired - re-authentication required'},
    'login_again': {'nl': 'Uw sessie is verlopen. Klik op Inloggen om opnieuw in te loggen.', 'en': 'Your session has expired. Please click Login to re-authenticate.'},
    'save_options_title': {'nl': 'Hoe wilt u ingelogd blijven?', 'en': 'How do you want to stay logged in?'},
    'save_option_tokens_only': {'nl': 'Alleen tokens opslaan (aanbevolen)', 'en': 'Save only tokens (recommended)'},
    'save_option_with_credentials': {'nl': 'E-mail en wachtwoord opslaan (niet aanbevolen)', 'en': 'Save email and password (not recommended)'},
    'tokens_only_info': {'nl': 'Alleen tokens worden opgeslagen. Dit is veiliger. U hoeft alleen in te loggen wanneer het sessietoken verloopt.', 'en': 'Only session tokens are saved. This is safer. You only need to login again when your session expires.'},
    'credentials_saved_warning': {'nl': 'E-mailadres en wachtwoord opgeslagen. Deze worden gebruikt om tokens automatisch te vernieuwen.', 'en': 'Email and password saved. These will be used to automatically refresh your session.'},
    'session_token_obtained': {'nl': 'Sessietoken verkregen. U bent aangemeld.', 'en': 'Session token obtained. You are logged in.'},
    'manage_profiles': {'nl': 'Profielen beheren', 'en': 'Manage profiles'},
    'search': {'nl': 'Zoeken', 'en': 'Search'},
    'my_list': {'nl': 'Mijn lijst', 'en': 'My List'},
    'series': {'nl': 'Series', 'en': 'Series'},
    'tv_shows': {'nl': 'TV Shows', 'en': 'TV Shows'},
    'documentary': {'nl': 'Documentaire', 'en': 'Documentary'},
    'movies': {'nl': 'Films', 'en': 'Movies'},
    'channels': {'nl': 'Kanalen', 'en': 'Channels'},
    'all_episodes': {'nl': 'Alle afleveringen', 'en': 'All episodes'},
    'missing_series_id': {'nl': 'Serie-ID ontbreekt', 'en': 'Missing series id'},
    'missing_season_id': {'nl': 'Seizoen-ID ontbreekt', 'en': 'Missing season id'},
    'unable_fetch_series': {'nl': 'Kan seriegegevens niet ophalen', 'en': 'Unable to fetch series details'},
    'no_items_found': {'nl': 'Geen items gevonden', 'en': 'No items found'},
    'not_logged_in': {'nl': 'Niet ingelogd. Klik op [B]Inloggen[/B] om in te loggen.', 'en': 'Not logged in. Press [B]Login[/B] to authenticate.'},
    'login_notification': {'nl': 'Klik op [B]Inloggen[/B] in het hoofdmenu om in te loggen via een dialoogvenster.', 'en': 'Press [B]Login[/B] on the main menu to authenticate via a dialog.'},
    'logout_and_clear': {'nl': 'Afmelden en lokale gegevens wissen', 'en': 'Logout and clear local data'},
    'only_series_movies': {'nl': 'Alleen Series en Films kunnen aan Mijn lijst worden toegevoegd', 'en': 'Only Series and Movies can be added to My List'},
    'searching': {'nl': 'Zoeken naar "{}"', 'en': 'Searching for "{}"'},
    'no_results': {'nl': 'Geen resultaten gevonden voor "{}"', 'en': 'No results found for "{}"'},
    'now_watching': {'nl': 'Nu aan het kijken', 'en': 'Now watching'},
    'added_to_list': {'nl': 'Toegevoegd aan Mijn lijst', 'en': 'Added to My List'},
    'removed_from_list': {'nl': 'Verwijderd uit Mijn lijst', 'en': 'Removed from My List'},
    'all': {'nl': 'Alles', 'en': 'All'},
    'no_episodes_found': {'nl': 'Geen afleveringen gevonden', 'en': 'No episodes found'},
    'account_updated': {'nl': 'Accountinformatie bijgewerkt:', 'en': 'Account info updated:'},
    'account_parse_error': {'nl': 'Accountinformatie kon niet worden verwerkt', 'en': 'Account info could not be parsed'},
    'logged_out': {'nl': 'Afgemeld — lokale gegevens gewist', 'en': 'Logged out — local data cleared'},
    'logout_cancelled': {'nl': 'Afmelden geannuleerd', 'en': 'Logout cancelled'},
    'login_successful_tokens': {'nl': 'Inloggen geslaagd (tokens verkregen)', 'en': 'Login successful (tokens acquired)'},
    'login_successful_no_tokens': {'nl': 'Inloggen geslaagd (geen tokens)', 'en': 'Login successful (no tokens)'},
    'login_failed_demo': {'nl': 'Inloggen mislukt — in demomodus gedraaid', 'en': 'Login failed — running in demo mode'},
    'no_profiles': {'nl': 'Geen profielen beschikbaar. Meld u eerst aan.', 'en': 'No profiles available. Please login first.'},
    'my_list_empty': {'nl': 'Mijn lijst is leeg', 'en': 'My List is empty'},
    'no_items_for_group': {'nl': 'Geen items gevonden voor {}', 'en': 'No items found for {}'},
    'missing_id_mylist': {'nl': 'ID ontbreekt voor Mijn lijst-actie', 'en': 'Missing id for My List action'},
    'logout_confirm_msg': {'nl': 'Hiermee worden cookies en tokens gewist. Doorgaan?', 'en': 'This will clear cookies and tokens. Continue?'},
    'keep_mylist': {'nl': 'Wilt u uw Mijn Lijst / My List bewaren?', 'en': 'Do you want to keep your My List?'},
    'keep_mylist_btn': {'nl': 'Bewaren', 'en': 'Keep'},
    'clear_mylist_btn': {'nl': 'Wissen', 'en': 'Clear'},
    'logout_btn': {'nl': 'Afmelden', 'en': 'Logout'},
    'cancel_btn': {'nl': 'Annuleren', 'en': 'Cancel'},
    'season': {'nl': 'Seizoen', 'en': 'Season'},
    'subscription_label': {'nl': 'Abonnement', 'en': 'Subscription'},
    'max_devices_label': {'nl': 'Max apparaten', 'en': 'Max devices'},
    'expires_label': {'nl': 'Verloopt', 'en': 'Expires'},
}

def get_string(key, *args):
    """Get translated string based on language setting.
    
    Args:
        key: Translation key
        *args: Optional format arguments
        
    Returns:
        Translated string in user's selected language (default: Dutch)
    """
    lang_setting = ADDON.getSetting('language') or '0'
    
    # Map setting values to language codes
    # Settings.xml has values="Dutch|English" so it returns "Dutch" or "English"
    # Also handle indices 0/1 and language codes nl/en as fallback
    lang_map = {
        '0': 'nl',
        '1': 'en',
        'Dutch': 'nl',
        'English': 'en',
        'nl': 'nl',
        'en': 'en',
        'Nederlands': 'nl'
    }
    lang = lang_map.get(lang_setting, 'nl')
    
    text = TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get('en', key))
    if args:
        try:
            text = text.format(*args)
        except (IndexError, KeyError):
            pass
    return text

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
    if thumb or content:
        # Use smart artwork assignment to respect aspect ratios
        # Prevents face-cutting and image stretching by assigning portraits to poster, landscapes to fanart
        _set_smart_artwork(li, content, thumb=thumb)
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
                # Use cached API instance instead of creating new ones for every item
                api_tmp = get_api_instance()
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


def _optimize_image_url(url):
    """Optimize image URLs to request higher-resolution versions for fanart.
    
    The NLZiet image service returns low-res images (1280x720) by default.
    We request a larger resolution to avoid pixelation when displayed as fanart.
    
    Args:
        url: Image URL
        
    Returns:
        Optimized URL requesting higher-resolution image
    """
    if not url or not isinstance(url, str):
        return url
    
    # Remove any existing width/crop parameters
    if '?' in url:
        url = url.split('?')[0]
    
    # Request a much larger width for fanart (3840px = 4K width)
    # This ensures crisp display even on large screens
    url = url + '?width=3840'
    
    return url


def _pick_landscape_thumb(src):
    """Return the best landscape-oriented thumbnail or path for an item.

    Accepts either a string URL/path or a dict-like content item. Prefers
    explicit landscape keys, then common wide/hero/poster keys, and finally
    falls back to any url-like string found on the object.
    """
    if not src:
        return None
    if isinstance(src, str):
        return _optimize_image_url(src)
    try:
        # Prefer explicit landscape / wide keys first
        for k in ('landscapeUrl', 'landscape', 'thumbnailLandscape', 'thumbnail_landscape', 'posterLandscape', 'poster_landscape', 'heroImage', 'heroImageUrl', 'widePosterUrl'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return _optimize_image_url(v)

        # Common poster/thumbnail fields (posterUrl may be portrait but is a useful fallback)
        for k in ('posterUrl', 'poster', 'thumbnail', 'thumb'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return _optimize_image_url(v)

        # Check nested image dicts for landscape keys
        for img_key in ('image', 'images'):
            img = src.get(img_key)
            if isinstance(img, dict):
                for k in ('landscapeUrl', 'landscape', 'landscape_url', 'wide', 'wideUrl', 'large', 'largeUrl', 'posterUrl', 'thumbnail', 'thumb'):
                    v = img.get(k)
                    if isinstance(v, str) and v:
                        return _optimize_image_url(v)
                for kk, vv in img.items():
                    if isinstance(kk, str) and 'landscape' in kk.lower() and isinstance(vv, str) and vv:
                        return vv

        # Any key name containing 'landscape' on the top-level
        for kk, vv in src.items():
            if isinstance(kk, str) and 'landscape' in kk.lower() and isinstance(vv, str) and vv:
                return _optimize_image_url(vv)

        # As a final fallback, return any url-like string value
        for vv in src.values():
            if isinstance(vv, str) and (vv.startswith('http://') or vv.startswith('https://') or vv.startswith('file://')):
                return _optimize_image_url(vv)
    except Exception:
        pass
    return None


def _pick_portrait_thumb(src):
    """Return the best portrait-oriented thumbnail or path for an item.
    
    Portrait images are typically 2:3 aspect ratio (posters/covers).
    Prefers explicit portrait keys, then falls back to landscape or generic thumbnails.
    """
    if not src:
        return None
    if isinstance(src, str):
        return _optimize_image_url(src)
    try:
        # Prefer explicit portrait / tall keys first
        for k in ('portraitUrl', 'portrait', 'posterUrl', 'poster', 'thumbnailPortrait', 'thumbnail_portrait', 'coverUrl', 'cover'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return _optimize_image_url(v)
        # Check nested image dicts for portrait keys
        for img_key in ('image', 'images'):
            img = src.get(img_key)
            if isinstance(img, dict):
                for k in ('portraitUrl', 'portrait', 'portrait_url', 'posterUrl', 'poster', 'coverUrl', 'cover', 'thumbnail', 'thumb'):
                    v = img.get(k)
                    if isinstance(v, str) and v:
                        return _optimize_image_url(v)
        # Fallback to any image URL
        for vv in src.values():
            if isinstance(vv, str) and (vv.startswith('http://') or vv.startswith('https://') or vv.startswith('file://')):
                return _optimize_image_url(vv)
    except Exception:
        pass
    return None


def _set_smart_artwork(li, src, thumb=None):
    """Set artwork on a ListItem with proper aspect ratio handling.
    
    Assigns different images to different art keys based on their aspect ratios:
    - fanart (16:9 landscape) - prefers landscape images
    - poster (2:3 portrait) - prefers portrait images  
    - thumb/icon (1:1 square) - uses best single image with aspect ratio preserved
    
    Args:
        li: xbmcgui.ListItem to set artwork on
        src: Content dict (to extract multiple image URLs)
        thumb: Fallback single image URL if src doesn't provide multiple images
    """
    if not thumb and not src:
        return
    
    # Extract different image types from content object
    landscape_img = None
    portrait_img = None
    
    if src and isinstance(src, dict):
        landscape_img = _pick_landscape_thumb(src)
        portrait_img = _pick_portrait_thumb(src)
    
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


def _is_logged_in():
    """Return True when the addon has an active authenticated session.

    We consider the user logged in when a valid access token exists or a
    cookie-session was established by the form login. This is intentionally
    lightweight and avoids forcing network calls during menu rendering.
    """
    try:
        api = get_api_instance()
        try:
            token = api.get_access_token()
        except Exception:
            token = None
        if token:
            return True
        if getattr(api, 'token', None) == 'cookie-session':
            # Heuristic: presence of nlziet cookies indicates an active session
            try:
                for c in api.cookie_jar:
                    dom = getattr(c, 'domain', '') or ''
                    if 'nlziet' in dom.lower():
                        return True
            except Exception:
                return True
    except Exception:
        pass
    return False


def _check_and_handle_token_expiry():
    """Check if token is expired and needs refresh. Show notification if re-login is required."""
    try:
        api = get_api_instance()
        
        # Try to get a valid token (which handles refresh automatically)
        token = api.get_access_token()
        if token:
            # Token is valid or was successfully refreshed
            return True
        
        # Token is expired and refresh failed - user needs to re-login
        save_creds = ADDON.getSetting('save_credentials') in ('true', '1', 'yes', True)
        if not save_creds:
            # No saved credentials, notify user to login
            try:
                xbmcgui.Dialog().notification('NLZiet', get_string('login_again'), xbmcgui.NOTIFICATION_INFO)
            except Exception:
                pass
        return False
    except Exception:
        pass
    return False


def main_menu():
    # Check if language changed and reload addon if needed
    check_and_reload_on_settings_change()
    
    # Check for expired tokens and attempt refresh
    _check_and_handle_token_expiry()
    
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

    # Start background refresh of account info (silent) on addon launch
    try:
        threading.Thread(target=refresh_account_info, args=(False,), daemon=True).start()
    except Exception:
        xbmc.log('NLZiet: failed to start account refresh thread', xbmc.LOGDEBUG)

    # Determine authentication state and show protected items only when logged in
    logged_in = _is_logged_in()

    # If not logged in, notify the user to press Login on the main menu
    if not logged_in:
        try:
            msg = get_string('login_notification')
            xbmcgui.Dialog().notification('NLZiet', msg, xbmcgui.NOTIFICATION_INFO)
        except Exception:
            xbmc.log('NLZiet: failed to show login notification', xbmc.LOGDEBUG)

    # Show Login or Sign Out button based on auth status
    if logged_in:
        add_directory_item(get_string('sign_out'), {'mode': 'logout_confirm'}, thumb=_pick_png('logout'))
    else:
        add_directory_item(get_string('login'), {'mode': 'login'}, thumb=_pick_png('login'))
    
    if logged_in:
        add_directory_item(get_string('manage_profiles'), {'mode': 'profiles'}, thumb=_pick_png('profiles'))
        add_directory_item(get_string('search'), {'mode': 'search'}, thumb=_pick_png('search'))
        add_directory_item(get_string('my_list'), {'mode': 'my_list'}, thumb=_pick_png('mylist'))
        add_directory_item(get_string('series'), {'mode': 'browse_series_categories'}, thumb=_pick_png('series'))
        add_directory_item(get_string('tv_shows'), {'mode': 'browse_tv_shows'}, thumb=_pick_png('tvshows'))
        add_directory_item(get_string('documentary'), {'mode': 'browse', 'type': 'documentary'}, thumb=_pick_png('documentary'))
        add_directory_item(get_string('movies'), {'mode': 'browse_movie_categories'}, thumb=_pick_png('movies'))
        # Some icon sets use 'tv' instead of 'channels' (we check menu_tv.png)
        add_directory_item(get_string('channels'), {'mode': 'browse', 'type': 'channels'}, thumb=_pick_png('tv'))
    xbmcplugin.endOfDirectory(HANDLE)


def browse_series_categories():
    """Display series category/genre list."""
    api = get_api_instance()

    genres = api.get_series_genres()
    for genre in genres:
        name = genre.get('name')
        genre_param = genre.get('genre')
        add_directory_item(name, {'mode': 'browse_series_genre', 'genre': genre_param or 'all'}, is_folder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def browse_series_genre(genre=None):
    """Display series in a selected genre."""
    api = get_api_instance()

    # Handle "all" as None for the API
    genre_param = None if genre == 'all' else genre
    results = api.get_series_by_genre(genre_param)
    
    for item in results:
        item_type = item.get('type', 'Series')
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
        except Exception:
            info = None
        
        # Series items should open as folders showing seasons/episodes
        if item_type == 'Series':
            add_directory_item(item.get('title') or item.get('id') or 'Series', {'mode': 'series_detail', 'series_id': item.get('id')}, is_folder=True, thumb=_pick_landscape_thumb(item), info=info, content=item)
        else:
            # Episodes would be playable - but shouldn't appear at top level in genre view
            pass
    
    xbmcplugin.endOfDirectory(HANDLE)


def browse_series():
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance for faster menu navigation
    try:
        api = get_api_instance()
    except Exception:
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
        except Exception:
            info = None
        add_directory_item(item.get('title') or item.get('id') or 'Series', {'mode': 'series_detail', 'series_id': item.get('id')}, is_folder=True, thumb=_pick_landscape_thumb(item), info=info, content=item)
    xbmcplugin.endOfDirectory(HANDLE)


def show_series_detail(series_id):
    if not series_id:
        xbmcgui.Dialog().notification('NLZiet', get_string('missing_series_id'), xbmcgui.NOTIFICATION_ERROR)
        return
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance for faster detail loading
    try:
        api = get_api_instance()
    except Exception:
        api = NLZietAPI(username=username, password=password)
    detail = api.get_series_detail(series_id)
    if not detail:
        xbmcgui.Dialog().notification('NLZiet', get_string('unable_fetch_series'), xbmcgui.NOTIFICATION_ERROR)
        return
    seasons = detail.get('seasons') or []
    # If no seasons discovered, offer direct episode listing
    if not seasons:
        add_directory_item(get_string('all_episodes'), {'mode': 'series_season', 'series_id': series_id, 'season_id': ''}, is_folder=True)
    else:
        for s in seasons:
            title = s.get('title') or f"{get_string('season')} {s.get('id')}"
            add_directory_item(title, {'mode': 'series_season', 'series_id': series_id, 'season_id': s.get('id')}, is_folder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def show_series_season(series_id, season_id):
    if not series_id:
        xbmcgui.Dialog().notification('NLZiet', get_string('missing_series_id'), xbmcgui.NOTIFICATION_ERROR)
        return
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance for faster episode loading
    try:
        api = get_api_instance()
    except Exception:
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
        xbmcgui.Dialog().notification('NLZiet', get_string('no_episodes_found'), xbmcgui.NOTIFICATION_INFO)
        return
    for ep in episodes:
        info = None
        try:
            desc = ep.get('description') or ep.get('subtitle') or ''
            title_for_info = ep.get('title') or ''
            aired_date = ep.get('raw', {}).get('broadcastAt') or ep.get('aired_date') or ep.get('broadcastDate') or ep.get('aired') or None
            
            # Format broadcast date info
            date_info = ''
            if aired_date:
                try:
                    # Parse and format date
                    if 'T' in aired_date:
                        date_obj = datetime.fromisoformat(aired_date.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.strptime(aired_date, '%Y-%m-%d')
                    
                    date_formatted = date_obj.strftime('%d-%m-%Y')
                    lang_code = ADDON.getSetting('language')
                    if lang_code == '0':  # Dutch
                        date_info = f"Uitgezonden: {date_formatted}"
                    else:  # English
                        date_info = f"Aired: {date_formatted}"
                except Exception:
                    date_info = ''
            
            # Build description with broadcast date if available
            plot_full = desc
            po = desc
            
            if date_info:
                plot_full = f"{date_info}\n{desc}" if desc else date_info
                po = f"{date_info} — {desc[:100]}" if desc else date_info
            
            if desc or date_info:
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                info = {
                    'title': title_for_info,
                    'plot': plot_full,
                    'plotoutline': po,
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


def browse_tv_shows():
    """Show TV show categories/genres for browsing."""
    api = get_api_instance()
    
    genres = api.get_tv_show_genres()
    for genre in genres:
        query = {'mode': 'browse_tv_genre', 'genre': genre.get('genre') or 'all'}
        add_directory_item(genre.get('name'), query, is_folder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def browse_tv_genre(genre=None):
    """Show TV shows for a specific genre."""
    api = get_api_instance()
    
    # Get shows for the genre (None for 'all')
    genre_param = None if genre == 'all' else genre
    results = api.get_videos_by_genre(genre=genre_param, limit=999)
    
    for item in results:
        # Use subtitle as primary display title if available (for episodes with episode names)
        display_title = item.get('subtitle') or item.get('title') or ''
        info = None
        try:
            desc = item.get('description') or item.get('subtitle') or ''
            title_for_info = item.get('title') or ''
            expiry_text = item.get('expires_in') or None
            aired_date = item.get('aired_date') or None
            
            truncated = (desc[:250] + '...') if len(desc) > 250 else desc
            plot_full = desc
            po = truncated
            
            # Add aired/broadcast date info if available
            date_info = ''
            if aired_date:
                try:
                    # Parse and format date
                    if 'T' in aired_date:
                        date_obj = datetime.fromisoformat(aired_date.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.strptime(aired_date, '%Y-%m-%d')
                    
                    date_formatted = date_obj.strftime('%d-%m-%Y')
                    lang_code = ADDON.getSetting('language')
                    if lang_code == '0':  # Dutch
                        date_info = f"Uitgezonden: {date_formatted}"
                    else:  # English
                        date_info = f"Aired: {date_formatted}"
                except Exception:
                    date_info = ''
            
            # Build full plot with date info
            parts = []
            if date_info:
                parts.append(date_info)
            if expiry_text:
                marker = '🔶 '
                colored = _make_color_tag(EXPIRY_COLOR_RAW, expiry_text)
                parts.append(colored)
            if desc:
                parts.append(desc)
            
            plot_full = '\n'.join(parts) if parts else ''
            
            # Build plotoutline with date
            po_parts = []
            if date_info:
                po_parts.append(date_info)
            if expiry_text:
                marker = '🔶 '
                po_parts.append(f"{marker}{expiry_text}")
            if truncated:
                po_parts.append(truncated)
            
            po = ' — '.join(po_parts) if po_parts else truncated
            
            # Create info if we have any data (title, date, or description)
            if title_for_info or date_info or expiry_text or desc:
                info = {
                    'title': title_for_info,
                    'plot': plot_full,
                    'plotoutline': po,
                }
        except Exception:
            info = None
        
        # Determine query mode based on item type
        item_type = (item.get('type') or '').lower()
        query = {'mode': 'play', 'id': item.get('id')}
        is_folder = False
        
        if item_type == 'series':
            # Series open as folders showing seasons/episodes
            query = {'mode': 'series_detail', 'series_id': item.get('id')}
            is_folder = True
        
        add_directory_item(display_title, query, is_folder=is_folder, thumb=_pick_landscape_thumb(item), info=info, content=item)
    xbmcplugin.endOfDirectory(HANDLE)


def browse_movie_categories():
    """Display movie category/genre list."""
    api = get_api_instance()

    genres = api.get_movie_genres()
    for genre in genres:
        name = genre.get('name')
        genre_param = genre.get('genre')
        add_directory_item(name, {'mode': 'browse_movie_genre', 'genre': genre_param or 'all'}, is_folder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def browse_movie_genre(genre=None):
    """Display movies in a selected genre."""
    api = get_api_instance()

    # Handle "all" as None for the API
    genre_param = None if genre == 'all' else genre
    results = api.get_movies_by_genre(genre_param)
    
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
        except Exception:
            info = None
        
        # Movies are playable items
        add_directory_item(item.get('title'), {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=_pick_landscape_thumb(item), info=info, content=item)
    
    xbmcplugin.endOfDirectory(HANDLE)


def browse_placement_row(items_url=None, placement_id=None, comp_index=None):
    """List items for a placement row. Accepts either `items_url` or a
    `placement_id` + `comp_index` to locate inline items.
    """
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance for faster placement loading
    try:
        api = get_api_instance()
    except Exception:
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
        xbmcgui.Dialog().notification('NLZiet', get_string('no_items_found'), xbmcgui.NOTIFICATION_INFO)
        return

    for src in items:
        try:
            content_id = src.get('id') or src.get('contentId') or src.get('content_id') or src.get('seriesId') or src.get('movieId') or src.get('assetId')
            title = src.get('title') or src.get('name') or ''
            thumb = _pick_landscape_thumb(src)
            desc = src.get('description') or src.get('summary') or ''
            info = None
            if desc:
                expiry_text = src.get('expires_in') or None
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                plot_full = desc
                po = truncated
                if expiry_text:
                    marker = '🔶 '
                    colored = _make_color_tag(EXPIRY_COLOR_RAW, expiry_text)
                    plot_full = f"{colored}\n{desc}" if desc else colored
                    po = f"{marker}{expiry_text} — {truncated}" if truncated else f"{marker}{expiry_text}"
                info = {'title': title, 'plot': plot_full, 'plotoutline': po}

            if content_id:
                # Treat as series when possible
                add_directory_item(title, {'mode': 'series_detail', 'series_id': content_id}, is_folder=True, thumb=thumb, info=info, content=src)
            else:
                add_directory_item(title, {'mode': 'play', 'id': src.get('playUrl') or src.get('streamUrl') or src.get('id')}, is_folder=False, thumb=thumb, info=info, content=src)
        except Exception:
            continue
    xbmcplugin.endOfDirectory(HANDLE)


def _extract_max_devices(summary):
    """Try to parse max devices from API summary payload."""
    def _find(data):
        if isinstance(data, dict):
            title = str(data.get('title') or data.get('name') or '')
            if title and 'apparaten' in title.lower():
                # direct title may contain number
                m = re.search(r"(\d+)", title)
                if m:
                    return m.group(1)
            terms = data.get('terms') or data.get('term') or []
            if isinstance(terms, list):
                for t in terms:
                    if isinstance(t, dict):
                        label = str(t.get('label') or '')
                        if 'apparaten' in label.lower():
                            m = re.search(r"(\d+)", label)
                            if m:
                                return m.group(1)
                        res = _find(t)
                        if res:
                            return res
            for v in data.values():
                res = _find(v)
                if res:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = _find(item)
                if res:
                    return res
        return None

    result = _find(summary)
    return str(result) if result else ''


def _extract_subscription_name(summary):
    """Try to parse subscription name from API summary payload."""
    if not isinstance(summary, dict):
        return ''
    # first, look for direct subscription field
    sub = summary.get('subscription') or summary.get('plan') or summary.get('product') or {}
    if isinstance(sub, dict):
        name = sub.get('name') or sub.get('title') or ''
        if name:
            return str(name)
    # fallback: find any name field in root with known hints
    for k in ('name', 'subscriptionName', 'planName'):
        if summary.get(k):
            return str(summary.get(k))
    # recursively find object with 'name' and context
    def _find(data):
        if isinstance(data, dict):
            for k, v in data.items():
                if k.lower() == 'name' and isinstance(v, str) and v.strip():
                    return v
                res = _find(v)
                if res:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = _find(item)
                if res:
                    return res
        return None
    found = _find(summary)
    return str(found) if found else ''


def _extract_subscription_expiry(summary):
    """Try to parse subscription expiry (nextDate) from API summary payload."""
    if not summary:
        return ''
    # direct field on root
    if isinstance(summary, dict):
        if 'nextDate' in summary and summary.get('nextDate'):
            return _format_date_string(summary.get('nextDate'))
        sub = summary.get('subscription') or summary.get('plan') or summary.get('product') or {}
        if isinstance(sub, dict) and sub.get('nextDate'):
            return _format_date_string(sub.get('nextDate'))
    # recurse into lists/dicts
    if isinstance(summary, (list, tuple)):
        for item in summary:
            d = _extract_subscription_expiry(item)
            if d:
                return d
    if isinstance(summary, dict):
        for v in summary.values():
            d = _extract_subscription_expiry(v)
            if d:
                return d
    return ''


def _format_date_string(dtstr):
    """Normalize various date formats to YYYY-MM-DD string."""
    if not dtstr:
        return ''
    from datetime import datetime
    s = str(dtstr)
    formats = ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    # try numeric timestamp (seconds or milliseconds)
    try:
        t = float(s)
        if t > 1e12:
            t = t / 1000.0
        dt = datetime.fromtimestamp(t)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return s


def refresh_account_info(notify=True):
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance to avoid repeated disk I/O and initialization overhead
    try:
        api = get_api_instance()
    except Exception:
        # Fallback to creating a new instance if cache fails
        api = NLZietAPI(username=username, password=password)
    summary = api.get_customer_summary() or {}

    subscription = _extract_subscription_name(summary) or ''
    max_devices = _extract_max_devices(summary) or ''
    subscription_expires = _extract_subscription_expiry(summary) or ''

    try:
        ADDON.setSetting('subscription_name', subscription)
        ADDON.setSetting('max_devices', max_devices)
        ADDON.setSetting('subscription_expires', subscription_expires)
    except Exception:
        pass

    display_values = []
    if subscription:
        display_values.append(f"{get_string('subscription_label')}: {subscription}")
    if max_devices:
        display_values.append(f"{get_string('max_devices_label')}: {max_devices}")
    if subscription_expires:
        display_values.append(f"{get_string('expires_label')}: {subscription_expires}")

    if notify:
        if display_values:
            xbmcgui.Dialog().notification('NLZiet', get_string('account_updated') + '\n' + '\n'.join(display_values), xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification('NLZiet', get_string('account_parse_error'), xbmcgui.NOTIFICATION_INFO)
    else:
        if display_values:
            xbmc.log('NLZiet: Account info updated: ' + ', '.join(display_values), xbmc.LOGDEBUG)
        else:
            xbmc.log('NLZiet: Account info could not be parsed', xbmc.LOGDEBUG)


def do_logout(keep_mylist=False):
    """Clear persistent addon data (cookies, tokens, profile) and refresh the UI.

    Args:
        keep_mylist: If True, keep the My List file; if False, delete it
    
    This removes cookie/token/profile files saved under the addon's
    profile directory, clears the stored profile settings, and replaces the
    current container with the main menu so the addon appears like a fresh
    install.
    """
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance when available
    try:
        api = get_api_instance()
    except Exception:
        api = NLZietAPI(username=username, password=password)
    
    # remove persistent files (cookies, profile, tokens)
    # optionally remove mylist based on keep_mylist parameter
    paths = [getattr(api, 'cookie_file', None), getattr(api, 'stream_cookie_file', None), getattr(api, 'profile_file', None), getattr(api, 'token_file', None)]
    if not keep_mylist:
        paths.append(getattr(api, 'mylist_file', None))
    
    for p in paths:
        try:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    try:
                        with open(p, 'w', encoding='utf-8') as f:
                            f.write('')
                    except Exception:
                        pass
        except Exception:
            pass

    # clear in-memory cookie jar and tokens
    try:
        api.cookie_jar.clear()
    except Exception:
        pass
    try:
        api.tokens = {}
        api.token = None
    except Exception:
        pass

    # Clear API instance cache
    clear_api_cache()
    
    # Clear relevant addon settings so the addon appears fresh
    try:
        for key in ('profile_id', 'profile_name', 'subscription_name', 'subscription_expires', 'max_devices', 'username', 'password', 'save_credentials'):
            try:
                ADDON.setSetting(key, '')
            except Exception:
                pass
    except Exception:
        pass

    xbmcgui.Dialog().notification('NLZiet', get_string('logged_out'), xbmcgui.NOTIFICATION_INFO)

    # Refresh UI to main menu so the addon appears like a fresh install
    try:
        main_url = build_url({})
        xbmc.executebuiltin('Container.Update(%s,replace)' % main_url)
    except Exception:
        try:
            xbmc.executebuiltin('RunPlugin(%s)' % BASE_URL)
        except Exception:
            pass


def confirm_logout():
    """Show confirmation dialogs before performing logout.
    
    First asks to confirm logout, then asks whether to keep My List.
    """
    d = xbmcgui.Dialog()
    msg = get_string('logout_confirm_msg')
    try:
        ok = d.yesno('NLZiet', msg, yeslabel=get_string('logout_btn'), nolabel=get_string('cancel_btn'))
    except Exception:
        try:
            ok = d.yesno('NLZiet', msg)
        except Exception:
            ok = False
    
    if not ok:
        try:
            xbmcgui.Dialog().notification('NLZiet', get_string('logout_cancelled'), xbmcgui.NOTIFICATION_INFO)
        except Exception:
            pass
        return
    
    # Confirmed logout - now ask about My List
    keep_mylist = False
    try:
        keep = d.yesno('NLZiet', get_string('keep_mylist'), yeslabel=get_string('keep_mylist_btn'), nolabel=get_string('clear_mylist_btn'))
        keep_mylist = keep
    except Exception:
        try:
            keep = d.yesno('NLZiet', get_string('keep_mylist'))
            keep_mylist = keep
        except Exception:
            pass
    
    do_logout(keep_mylist=keep_mylist)


def show_login_dialog():
    """Show login dialog to get email and password from user.
    
    Returns:
        Tuple of (email, password) or (None, None) if cancelled
    """
    dialog = xbmcgui.Dialog()
    
    # Get email from user
    email = dialog.input(get_string('login_dialog_email'), type=0)
    if not email:
        return None, None
    
    # Get password from user (type=0 for text input)
    password = dialog.input(get_string('login_dialog_password'), type=0)
    if not password:
        return None, None
    
    return email, password


def do_login():
    """Handle login via dialog or saved credentials."""
    save_creds = ADDON.getSetting('save_credentials') in ('true', '1', 'yes', True)
    
    # Check if we have saved credentials
    saved_username = ADDON.getSetting('username')
    saved_password = ADDON.getSetting('password')
    
    email = None
    password = None
    
    # If credentials are saved and save_credentials is enabled, use them
    if save_creds and saved_username and saved_password:
        email = saved_username
        password = saved_password
        use_saved = True
    else:
        # Show login dialog
        email, password = show_login_dialog()
        use_saved = False
        if not email or not password:
            return
    
    # Attempt login with provided credentials
    api = NLZietAPI(username=email, password=password)
    ok = api.login()
    
    if ok:
        # attempt PKCE authorize + token exchange (uses the saved cookie session)
        tokens = api.perform_pkce_authorize_and_exchange()
        if tokens:
            # Store tokens in API (they're persistent via save_tokens)
            xbmcgui.Dialog().notification('NLZiet', get_string('session_token_obtained'), xbmcgui.NOTIFICATION_INFO)
            
            # If user didn't use saved credentials, ask how to save the session
            if not use_saved and not save_creds:
                try:
                    options = [
                        get_string('save_option_tokens_only'),
                        get_string('save_option_with_credentials')
                    ]
                    choice = xbmcgui.Dialog().select(get_string('save_options_title'), options)
                    
                    if choice == 0:
                        # User chose tokens only (recommended)
                        xbmcgui.Dialog().ok('NLZiet', get_string('tokens_only_info'))
                    elif choice == 1:
                        # User chose to save email and password
                        xbmcgui.Dialog().ok('NLZiet', get_string('credentials_saved_warning'))
                        # Save credentials
                        ADDON.setSetting('username', email)
                        ADDON.setSetting('password', password)
                        ADDON.setSetting('save_credentials', 'true')
                except Exception:
                    pass
        else:
            xbmcgui.Dialog().notification('NLZiet', get_string('login_successful_no_tokens'), xbmcgui.NOTIFICATION_INFO)
        
        try:
            refresh_account_info()
        except Exception:
            pass
    else:
        xbmcgui.Dialog().notification('NLZiet', get_string('login_failed_demo'), xbmcgui.NOTIFICATION_INFO)


def manage_profiles():
    """List available profiles and let the user switch the active profile.

    This renders a directory of profiles where the currently active profile
    is displayed in green. Selecting a profile will activate it and re-open
    the list so the active profile remains highlighted until another is
    chosen.
    """
    api = get_api_instance()
    profiles = api.get_profiles()
    # Try to obtain tokens if profiles empty
    if not profiles:
        try:
            api.perform_pkce_authorize_and_exchange()
            profiles = api.get_profiles() or []
        except Exception:
            profiles = profiles or []

    if not profiles:
        xbmcgui.Dialog().notification('NLZiet', get_string('no_profiles'), xbmcgui.NOTIFICATION_INFO)
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
    # Use cached API instance for faster list loading
    try:
        api = get_api_instance()
    except Exception:
        api = NLZietAPI(username=username, password=password)
    try:
        items = api.get_my_list() or []
    except Exception:
        items = []

    if not items:
        xbmcgui.Dialog().notification('NLZiet', get_string('my_list_empty'), xbmcgui.NOTIFICATION_INFO)
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
        xbmcgui.Dialog().notification('NLZiet', get_string('my_list_empty'), xbmcgui.NOTIFICATION_INFO)
    xbmcplugin.endOfDirectory(HANDLE)


def browse_my_list_group(group):
    """Show items from the user's My List filtered to a single group."""
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance for faster group loading
    try:
        api = get_api_instance()
    except Exception:
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
        xbmcgui.Dialog().notification('NLZiet', get_string('no_items_for_group').format(group), xbmcgui.NOTIFICATION_INFO)
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
    # Use cached API instance to respond instantly to My List actions
    try:
        api = get_api_instance()
    except Exception:
        # Fallback to creating a new instance if cache fails
        api = NLZietAPI(username=username, password=password)
    if not item_id:
        xbmcgui.Dialog().notification('NLZiet', get_string('missing_id_mylist'), xbmcgui.NOTIFICATION_ERROR)
        return
    # Defensive: only allow Series or Movies to be toggled
    if type and isinstance(type, str):
        tl = type.lower()
        if not any(x in tl for x in ('series', 'tvshow', 'movie', 'film')):
            xbmcgui.Dialog().notification('NLZiet', get_string('only_series_movies'), xbmcgui.NOTIFICATION_INFO)
            return
    else:
        # try to detect content type from detail
        try:
            det = api.get_content_detail(item_id) or {}
            raw_type = (det.get('raw') or {}).get('type') or det.get('type') or ''
            if raw_type and not any(x in str(raw_type).lower() for x in ('series', 'tvshow', 'movie', 'film')):
                xbmcgui.Dialog().notification('NLZiet', get_string('only_series_movies'), xbmcgui.NOTIFICATION_INFO)
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
    # Use cached API instance for faster profile switching
    try:
        api = get_api_instance()
    except Exception:
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
    # Use cached API instance for faster profile application
    try:
        api = get_api_instance()
    except Exception:
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

        try:
            refresh_account_info()
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
    # Use cached API instance for search
    try:
        api = get_api_instance()
    except Exception:
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
    # Use cached API instance for faster menu navigation
    try:
        api = get_api_instance()
    except Exception:
        api = NLZietAPI(username=username, password=password)
    epg_map = {}
    if content_type.lower() == 'movies':
        results = api.get_movies()
    elif content_type.lower() == 'videos':
        results = api.get_videos()
    elif content_type.lower() == 'documentary':
        results = api.get_documentaries()
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
                # Skip detail fetch for channels - they don't support /v9/content/detail/ endpoint
                if cid and content_type.lower() != 'channels':
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
        
        # Determine query mode based on item type
        # Documentaries and Series should open series detail, not try to play directly
        item_type = (item.get('type') or '').lower()
        query = {'mode': 'play', 'id': item.get('id')}
        is_folder = False
        
        if item_type == 'series' or content_type.lower() == 'documentary':
            # Series and documentaries open as folders with series detail
            query = {'mode': 'series_detail', 'series_id': item.get('id')}
            is_folder = True
        elif content_type.lower() == 'channels':
            query['fmt'] = 'live'
        
        add_directory_item(item.get('title'), query, is_folder=is_folder, thumb=_pick_landscape_thumb(item), info=info, content=item)
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
    # Use cached API instance for search results
    try:
        api = get_api_instance()
    except Exception:
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
    # Use cached API instance - still makes the stream info call but avoids object init overhead
    try:
        api = get_api_instance()
    except Exception:
        # Fallback to creating a new instance if cache fails
        api = NLZietAPI(username=username, password=password)
    xbmc.log(f"NLZiet play_item called: id={content_id} fmt={fmt}", xbmc.LOGINFO)
    if fmt == 'live':
        info = api.get_stream_info(content_id, context='Live')
        xbmc.log(f"NLZiet LIVE TV: id={content_id} context='Live'", xbmc.LOGINFO)
    else:
        info = api.get_stream_info(content_id)
        xbmc.log(f"NLZiet REGULAR content: id={content_id} (not live)", xbmc.LOGINFO)
    manifest = info.get('manifest')
    is_drm = info.get('is_drm')
    subs_in_info = info.get('subtitles')
    xbmc.log(f"NLZiet play_item: id={content_id} manifest={manifest} is_drm={is_drm} fmt={fmt} has_subs={bool(subs_in_info)}", xbmc.LOGINFO)
    xbmc.log(f"NLZiet info subtitles value: {repr(subs_in_info)} (type: {type(subs_in_info).__name__})", xbmc.LOGINFO)
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
            xbmc.log(f"NLZiet DRM subtitles array: {subs} (type: {type(subs).__name__}, len={len(subs) if subs else 0})", xbmc.LOGINFO)
            
            sub_urls = []
            for s in subs:
                if isinstance(s, dict):
                    url = s.get('url') or s.get('uri') or s.get('file')
                else:
                    url = s
                if url:
                    sub_urls.append(url)
            xbmc.log(f"NLZiet DRM extracted sub_urls: {sub_urls}", xbmc.LOGINFO)
            
            if sub_urls:
                try:
                    enable_subs = ADDON.getSetting('subtitles_default')
                    xbmc.log(f"NLZiet DEBUG subtitles_default raw value: {repr(enable_subs)} (type: {type(enable_subs).__name__})", xbmc.LOGINFO)
                except Exception as e:
                    enable_subs = None
                    xbmc.log(f"NLZiet ERROR reading subtitles_default: {e}", xbmc.LOGINFO)
                
                # Convert to boolean - handle all possible Kodi return values
                if enable_subs is None or enable_subs == '' or enable_subs == 'false' or enable_subs is False:
                    subs_enabled = False
                elif enable_subs == 'true' or enable_subs is True or enable_subs == '1':
                    subs_enabled = True
                else:
                    # Fallback: try string parsing
                    subs_enabled = str(enable_subs).lower().strip() in ('true', '1', 'yes', 'on')
                
                xbmc.log(f"NLZiet DRM subtitles: raw={repr(enable_subs)} -> enabled={subs_enabled}", xbmc.LOGINFO)
                
                if subs_enabled:
                    xbmc.log(f"NLZiet attaching subtitles: {sub_urls}", xbmc.LOGINFO)
                    try:
                        li.setSubtitles(sub_urls)
                    except Exception as e:
                        xbmc.log(f"NLZiet subtitle attach failed: {e}", xbmc.LOGINFO)
                        # fallback: store as property for debugging or later handling
                        try:
                            li.setProperty('nlziet.subtitles', ';'.join(sub_urls))
                        except Exception:
                            pass
                else:
                    xbmc.log(f'NLZiet: auto-subtitles disabled', xbmc.LOGINFO)
            else:
                xbmc.log(f'NLZiet: no subtitles in stream response', xbmc.LOGINFO)
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
        
        # Also handle subtitles for non-DRM streams
        try:
            subs = info.get('subtitles') or []
            xbmc.log(f"NLZiet non-DRM subtitles array: {subs} (type: {type(subs).__name__}, len={len(subs) if subs else 0})", xbmc.LOGINFO)
            
            sub_urls = []
            for s in subs:
                if isinstance(s, dict):
                    url = s.get('url') or s.get('uri') or s.get('file')
                else:
                    url = s
                if url:
                    sub_urls.append(url)
            xbmc.log(f"NLZiet non-DRM extracted sub_urls: {sub_urls}", xbmc.LOGINFO)
            
            if sub_urls:
                try:
                    enable_subs = ADDON.getSetting('subtitles_default')
                    xbmc.log(f"NLZiet DEBUG non-DRM subtitles_default raw: {repr(enable_subs)} (type: {type(enable_subs).__name__})", xbmc.LOGINFO)
                except Exception as e:
                    enable_subs = None
                    xbmc.log(f"NLZiet ERROR reading subtitles_default: {e}", xbmc.LOGINFO)
                
                # Convert to boolean - handle all possible return values from Kodi
                if enable_subs is None or enable_subs == '' or enable_subs == 'false' or enable_subs is False:
                    subs_enabled = False
                elif enable_subs == 'true' or enable_subs is True or enable_subs == '1':
                    subs_enabled = True
                else:
                    # Fallback: try string parsing
                    subs_enabled = str(enable_subs).lower().strip() in ('true', '1', 'yes', 'on')
                
                xbmc.log(f"NLZiet non-DRM subtitles: raw={repr(enable_subs)} -> enabled={subs_enabled}", xbmc.LOGINFO)
                
                if subs_enabled:
                    xbmc.log(f"NLZiet non-DRM attaching subtitles: {sub_urls}", xbmc.LOGINFO)
                    try:
                        li.setSubtitles(sub_urls)
                    except Exception as e:
                        xbmc.log(f"NLZiet non-DRM subtitle attach failed: {e}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"NLZiet exception in non-DRM subtitle handling: {e}", xbmc.LOGINFO)
        
        xbmcplugin.setResolvedUrl(HANDLE, True, li)


def check_and_reload_on_settings_change():
    """Check if language setting changed and notify user to reload addon.
    
    Compares current language setting with stored value. If language
    differs, shows a notification prompting user to reload the addon
    to apply the language change.
    """
    try:
        current_language = ADDON.getSetting('language')
        
        # Read last known language from addon data directory (persistent storage)
        addon_data_dir = xbmc.translatePath(ADDON.getAddonInfo('profile'))
        lang_file = os.path.join(addon_data_dir, 'last_language.txt')
        
        stored_language = None
        if os.path.exists(lang_file):
            try:
                with open(lang_file, 'r') as f:
                    stored_language = f.read().strip()
            except Exception:
                pass
        
        # Create data dir if needed
        try:
            if not os.path.exists(addon_data_dir):
                os.makedirs(addon_data_dir)
        except Exception:
            pass
        
        # Write current language for next check
        try:
            with open(lang_file, 'w') as f:
                f.write(current_language)
        except Exception:
            pass
        
        # Log for debugging
        xbmc.log(f"NLZiet language check: {stored_language}->{current_language}", xbmc.LOGDEBUG)
        
        # Check if language setting changed
        if stored_language is not None and stored_language != current_language:
            xbmc.log(f"NLZiet detected language change", xbmc.LOGINFO)
            
            # Show notification to user asking them to reload
            langs = {0: 'Dutch', 1: 'English'}
            new_lang = langs.get(int(current_language), current_language)
            notification = f'Language changed to {new_lang}.\nPlease reload the addon to apply changes.'
            
            try:
                xbmcgui.Dialog().notification('NLZiet', notification, xbmcgui.NOTIFICATION_INFO, 3000)
            except Exception:
                pass
            
    except Exception as e:
        xbmc.log(f"NLZiet error in language change check: {e}", xbmc.LOGDEBUG)


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
    elif mode == 'logout':
        do_logout()
    elif mode == 'logout_confirm':
        confirm_logout()
    elif mode == 'account_summary':
        refresh_account_info()
    elif mode == 'search_group':
        search_group(params.get('q'), params.get('group'))
    elif mode == 'series_detail':
        show_series_detail(params.get('series_id'))
    elif mode == 'series_season':
        show_series_season(params.get('series_id'), params.get('season_id'))
    elif mode == 'placement_row':
        browse_placement_row(params.get('items_url'), params.get('placement_id'), params.get('comp_index'))
    elif mode == 'browse_tv_shows':
        browse_tv_shows()
    elif mode == 'browse_tv_genre':
        browse_tv_genre(params.get('genre'))
    elif mode == 'browse_series_categories':
        browse_series_categories()
    elif mode == 'browse_series_genre':
        browse_series_genre(params.get('genre'))
    elif mode == 'browse_movie_categories':
        browse_movie_categories()
    elif mode == 'browse_movie_genre':
        browse_movie_genre(params.get('genre'))
    elif mode == 'browse':
        browse_category(params.get('type', 'all'))
    elif mode == 'play':
        play_item(params.get('id'), params.get('fmt'))


if __name__ == '__main__':
    router(sys.argv[2][1:] if len(sys.argv) > 2 else '')
