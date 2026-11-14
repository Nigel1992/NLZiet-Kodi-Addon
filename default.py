import sys
import re
import json
import urllib.parse
import urllib.request
import os
import threading
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import time
import platform
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from resources.lib.nlziet_api import NLZietAPI
from resources.lib.app_context import AddonContext
from resources.lib.kodi import ui as kodi_ui
from resources.lib.router import Router
from resources.lib import tvmaze
from resources.lib import library as library_mod
from resources.lib import metadata as metadata_mod
from resources.lib import library_art
from resources.lib import errors as errors_mod
from resources.lib import diagnostics as diagnostics_mod
from resources.lib import search_filters
from resources.lib import parental as parental_mod
from resources.lib import trakt_status
from resources.lib import logo_cache as logo_cache_mod
from resources.lib import playback_extras
from resources.lib import watch_sync
from resources.lib import watch_history

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

# Global API instance cache to avoid repeated initialization
_api_cache = None
_api_cache_time = 0
_api_cache_timeout = 300  # 5 minutes - refresh cache after this

# Short-lived channels listing cache to make return-from-playback instant.
_channel_menu_cache_data = []
_channel_menu_cache_epg = {}
_channel_menu_cache_time = 0
_channel_menu_cache_ttl = 45  # seconds
_last_token_check = 0
_token_check_interval = 300

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
    global _channel_menu_cache_data, _channel_menu_cache_epg, _channel_menu_cache_time
    _api_cache = None
    _api_cache_time = 0
    _channel_menu_cache_data = []
    _channel_menu_cache_epg = {}
    _channel_menu_cache_time = 0


def set_api_instance(api_instance):
    """Replace the API cache with a known-good instance (e.g. after login)."""
    global _api_cache, _api_cache_time
    _api_cache = api_instance
    _api_cache_time = time.time()


def get_channels_menu_data(api_instance):
    """Return channels + EPG data with short-lived in-memory caching.

    This avoids re-fetching channels/EPG immediately after stopping Live TV,
    which makes menu return feel instant.
    """
    global _channel_menu_cache_data, _channel_menu_cache_epg, _channel_menu_cache_time
    now = time.time()
    if _channel_menu_cache_time and (now - _channel_menu_cache_time) < _channel_menu_cache_ttl:
        return _channel_menu_cache_data or [], _channel_menu_cache_epg or {}

    results = api_instance.get_channels() or []
    epg_map = {}
    channel_ids = [r.get('id') for r in results if r.get('id')]
    if channel_ids:
        try:
            # Fetch EPG for all specified channels
            epg_map = api_instance.get_current_programs(channel_ids) or {}
        except Exception as e:
            xbmc.log(f"get_channels_menu_data: EPG fetch failed: {e}", xbmc.LOGWARNING)
            epg_map = {}

    _channel_menu_cache_data = results
    _channel_menu_cache_epg = epg_map
    _channel_menu_cache_time = now
    return results, epg_map

# Accent color for availability/expiry lines ("nog X dagen beschikbaar").
# Valid AARRGGBB hex (Kodi ignores anything else): a warm amber that stands
# out slightly on dark skins without shouting.
EXPIRY_COLOR_RAW = 'FFF2A24C'

# Accent color for the episode-numbering lines in Kijk Later descriptions.
# A calm blue that sits quietly next to the amber availability line.
NUMBERING_COLOR_RAW = 'FF74A9E6'

# Muted grey for the "Aflevering X" prefix in season folders, so it stays
# quieter than the episode title next to it.
EPISODE_PREFIX_COLOR_RAW = 'FF8C8C8C'

# Bright green marks followed series that have received new episodes since the
# last time the My Series list was opened.
MY_SERIES_NEW_COLOR_RAW = 'FF7ED321'

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
    'login_invalid_credentials': {'nl': 'Ongeldig e-mailadres of wachtwoord', 'en': 'Invalid email or password'},
    'login_try_again': {'nl': 'Opnieuw proberen?', 'en': 'Try again?'},
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
    'my_list': {'nl': 'Mijn lijst (alleen Kodi)', 'en': 'My List (Kodi only)'},
    'series': {'nl': 'Series', 'en': 'Series'},
    'tv_shows': {'nl': 'TV Shows', 'en': 'TV Shows'},
    'documentary': {'nl': 'Documentaire', 'en': 'Documentary'},
    'movies': {'nl': 'Films', 'en': 'Movies'},
    'channels': {'nl': 'Kanalen', 'en': 'Channels'},
    'programs': {'nl': 'programma\'s', 'en': 'programs'},
    'epg_title': {'nl': 'NLZiet TV Gids', 'en': 'NLZiet TV Guide'},
    'tv_guide': {'nl': 'TV Gids', 'en': 'TV Guide'},
    'list_item_not_found': {'nl': 'Niet toegevoegd: dit item is niet gevonden bij NLZiet.', 'en': 'Not added: this item was not found on NLZiet.'},
    'list_item_not_reachable_later': {'nl': 'Niet toegevoegd: dit programma is niet terug te kijken en kan later niet worden afgespeeld.', 'en': 'Not added: this programme cannot be replayed later.'},
    'list_item_not_aired': {'nl': 'Toegevoegd, maar dit programma is nog niet uitgezonden. Het kan pas later worden afgespeeld.', 'en': 'Added, but this programme has not aired yet. It can only be played later.'},
    'list_item_not_playable': {'nl': 'Niet toegevoegd: dit programma kan nu niet worden afgespeeld.', 'en': 'Not added: this programme cannot be played right now.'},
    'list_item_repeat_playable': {'nl': 'Toegevoegd. Dit is een herhaling en kan direct worden afgespeeld.', 'en': 'Added. This is a repeat and can be played right away.'},
    'list_item_airing': {'nl': 'Toegevoegd. Dit programma is nu bezig en kan pas na de uitzending worden afgespeeld.', 'en': 'Added. This programme is airing now and can only be played after the broadcast.'},
    'epg_subtitle': {'nl': 'Kies een kanaal links, scroll programma\'s horizontaal. OK speelt af, contextmenu voegt toe aan lijsten.', 'en': 'Choose a channel on the left, scroll programmes horizontally. OK plays, context menu adds to lists.'},
    'all_episodes': {'nl': 'Alle afleveringen', 'en': 'All episodes'},
    'missing_series_id': {'nl': 'Serie-ID ontbreekt', 'en': 'Missing series id'},
    'missing_season_id': {'nl': 'Seizoen-ID ontbreekt', 'en': 'Missing season id'},
    'unable_fetch_series': {'nl': 'Kan seriegegevens niet ophalen', 'en': 'Unable to fetch series details'},
    'no_items_found': {'nl': 'Geen items gevonden', 'en': 'No items found'},
    'not_logged_in': {'nl': 'Niet ingelogd. Klik op [B]Inloggen[/B] om in te loggen.', 'en': 'Not logged in. Press [B]Login[/B] to authenticate.'},
    'login_notification': {'nl': 'Klik op [B]Inloggen[/B] in het hoofdmenu om in te loggen via een dialoogvenster.', 'en': 'Press [B]Login[/B] on the main menu to authenticate via a dialog.'},
    'logout_and_clear': {'nl': 'Afmelden en lokale gegevens wissen', 'en': 'Logout and clear local data'},
    'only_series_movies': {'nl': 'Alleen Series en Films kunnen in een lijst worden opgeslagen', 'en': 'Only Series and Movies can be saved to a list'},
    'searching': {'nl': 'Zoeken naar "{}"', 'en': 'Searching for "{}"'},
    'no_results': {'nl': 'Geen resultaten gevonden voor "{}"', 'en': 'No results found for "{}"'},
    'now_watching': {'nl': 'Nu aan het kijken', 'en': 'Now watching'},
    'added_to_list': {'nl': 'Toegevoegd aan Mijn lijst (alleen Kodi)', 'en': 'Added to My List (Kodi only)'},
    'removed_from_list': {'nl': 'Verwijderd uit Mijn lijst (alleen Kodi)', 'en': 'Removed from My List (Kodi only)'},
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
    'my_list_empty': {'nl': 'Mijn lijst (alleen Kodi) is leeg', 'en': 'My List (Kodi only) is empty'},
    'no_items_for_group': {'nl': 'Geen items gevonden voor {}', 'en': 'No items found for {}'},
    'missing_id_mylist': {'nl': 'ID ontbreekt voor Mijn lijst-actie', 'en': 'Missing id for My List action'},
    'logout_confirm_msg': {'nl': 'Hiermee worden cookies en tokens gewist. Doorgaan?', 'en': 'This will clear cookies and tokens. Continue?'},
    'keep_mylist': {'nl': 'Wilt u uw Mijn lijst (alleen Kodi) bewaren?', 'en': 'Do you want to keep your My List (Kodi only)?'},
    'keep_mylist_btn': {'nl': 'Bewaren', 'en': 'Keep'},
    'clear_mylist_btn': {'nl': 'Wissen', 'en': 'Clear'},
    'logout_btn': {'nl': 'Afmelden', 'en': 'Logout'},
    'cancel_btn': {'nl': 'Annuleren', 'en': 'Cancel'},
    'season': {'nl': 'Seizoen', 'en': 'Season'},
    'subscription_label': {'nl': 'Abonnement', 'en': 'Subscription'},
    'subscription_type_label': {'nl': 'Type', 'en': 'Type'},
    'max_devices_label': {'nl': 'Max apparaten', 'en': 'Max devices'},
    'expires_label': {'nl': 'Verloopt', 'en': 'Expires'},
    'add_to_library': {'nl': 'Toevoegen aan bibliotheek', 'en': 'Add to library'},
    'library_exported': {'nl': '{} afleveringen geexporteerd naar bibliotheek', 'en': '{} episodes exported to library'},
    'library_export_failed': {'nl': 'Bibliotheek export mislukt', 'en': 'Library export failed'},
    'remove_from_library': {'nl': 'Verwijderen uit bibliotheek', 'en': 'Remove from library'},
    'library_movie_added': {'nl': '{} toegevoegd aan bibliotheek', 'en': '{} added to library'},
    'library_removed': {'nl': '{} verwijderd uit bibliotheek', 'en': '{} removed from library'},
    'library_not_found': {'nl': 'Dit staat niet in de bibliotheek', 'en': 'This is not in the library'},
    'library_updating': {'nl': 'Bibliotheek bijwerken...', 'en': 'Updating library...'},
    'library_update_done': {'nl': 'Bibliotheek bijgewerkt: {} nieuw, {} verwijderd', 'en': 'Library updated: {} new, {} removed'},
    'library_update_failed': {'nl': 'Bibliotheek bijwerken mislukt', 'en': 'Library update failed'},
    'library_update_now': {'nl': 'Bibliotheek nu bijwerken', 'en': 'Update library now'},
    'library_empty': {'nl': 'De bibliotheek is nog leeg', 'en': 'The library is empty'},
    'library': {'nl': 'Bibliotheek', 'en': 'Library'},
    'tmdb_check_ok': {'nl': 'TMDb-sleutel werkt', 'en': 'TMDb key works'},
    'tmdb_check_failed': {'nl': 'TMDb accepteert deze sleutel niet. Controleer of je de API Key (32 tekens) of het API Read Access Token volledig hebt geplakt.', 'en': 'TMDb does not accept this key. Check that you pasted the complete API Key (32 characters) or API Read Access Token.'},
    'library_moved': {'nl': '{} series verplaatst naar de NLZiet-map. Voeg die map toe als bron in Kodi.', 'en': '{} series moved to the NLZiet folder. Add that folder as a source in Kodi.'},
    'library_art_fixed': {'nl': 'Posters bijgewerkt voor {} titels', 'en': 'Artwork updated for {} titles'},
    'tmdb_check_missing': {'nl': 'Er is nog geen TMDb-sleutel opgeslagen. Vul de sleutel in, druk op OK om de instellingen op te slaan en test daarna opnieuw.', 'en': 'No TMDb key is saved yet. Enter the key, press OK to save the settings and test again.'},
    'tmdb_check_offline': {'nl': 'TMDb is niet bereikbaar. Controleer je internetverbinding; de sleutel zelf is niet getest.', 'en': 'TMDb could not be reached. Check your internet connection; the key itself was not tested.'},
    'parental_enter_pin': {'nl': 'Voer de pincode in', 'en': 'Enter the PIN'},
    'parental_enter_current_pin': {'nl': 'Voer de huidige pincode in', 'en': 'Enter the current PIN'},
    'parental_new_pin': {'nl': 'Kies een nieuwe pincode (minimaal 4 cijfers)', 'en': 'Choose a new PIN (at least 4 digits)'},
    'parental_repeat_pin': {'nl': 'Herhaal de nieuwe pincode', 'en': 'Repeat the new PIN'},
    'parental_pin_too_short': {'nl': 'De pincode moet minimaal 4 cijfers hebben.', 'en': 'The PIN needs at least 4 digits.'},
    'parental_pin_mismatch': {'nl': 'De twee pincodes zijn niet gelijk. Probeer het opnieuw.', 'en': 'The two PINs are not the same. Please try again.'},
    'parental_pin_set': {'nl': 'Pincode ingesteld. Kies nu bij Profielen (lang indrukken) welke profielen een pincode nodig hebben.', 'en': 'PIN set. Now choose in Profiles (long press) which profiles need the PIN.'},
    'parental_pin_removed': {'nl': 'Pincode verwijderd', 'en': 'PIN removed'},
    'parental_wrong_pin': {'nl': 'Onjuiste pincode', 'en': 'Wrong PIN'},
    'parental_set_pin_first': {'nl': 'Stel eerst een pincode in.', 'en': 'Set a PIN first.'},
    'parental_lock_profile': {'nl': 'Pincode vereisen voor dit profiel', 'en': 'Require the PIN for this profile'},
    'parental_unlock_profile': {'nl': 'Geen pincode meer voor dit profiel', 'en': 'No longer require the PIN for this profile'},
    'parental_profile_locked': {'nl': 'Dit profiel vraagt nu om de pincode', 'en': 'This profile now asks for the PIN'},
    'parental_profile_unlocked': {'nl': 'Dit profiel vraagt niet meer om de pincode', 'en': 'This profile no longer asks for the PIN'},
    'parental_kids': {'nl': 'Kids', 'en': 'Kids'},
    'parental_pin_tag': {'nl': 'pincode', 'en': 'PIN'},
    'library_lists_busy': {'nl': 'Mijn series en Kijk later naar de bibliotheek...', 'en': 'Adding My Series and Watch Later to the library...'},
    'library_lists_done': {'nl': 'Lijsten: {} toegevoegd, {} verwijderd, {} mislukt', 'en': 'Lists: {} added, {} removed, {} failed'},
    'library_lists_now': {'nl': 'Mijn series en Kijk later nu naar de bibliotheek', 'en': 'Add My Series and Watch Later to the library now'},
    'choose_tmdb': {'nl': 'Juiste TMDb-titel kiezen', 'en': 'Choose the right TMDb title'},
    'choose_tmdb_other': {'nl': 'Andere zoekterm...', 'en': 'Other search term...'},
    'choose_tmdb_done': {'nl': 'TMDb-titel ingesteld; gegevens en plaatjes worden bijgewerkt', 'en': 'TMDb title set; details and artwork are updated'},
    'library_adding': {'nl': 'Toevoegen aan bibliotheek: {}', 'en': 'Adding to library: {}'},
    'diagnostics_exported': {'nl': 'Diagnostisch rapport opgeslagen:\n{}', 'en': 'Diagnostic report saved:\n{}'},
    'diagnostics_failed': {'nl': 'Diagnostisch rapport kon niet worden opgeslagen', 'en': 'Could not save diagnostic report'},
    'subtitle_cache_cleared': {'nl': '{} ondertitelcachebestanden verwijderd', 'en': '{} subtitle cache files removed'},
    'subtitle_cache_clear_failed': {'nl': 'Ondertitelcache kon niet worden verwijderd', 'en': 'Could not clear subtitle cache'},
    'clear_all_cache': {'nl': 'Alle cache wissen', 'en': 'Clear all cache'},
    'auto_clear_all_cache': {'nl': 'Cache automatisch wissen', 'en': 'Automatically clear cache'},
    'auto_clear_all_cache_hours': {'nl': 'Cache wissen elke (uren)', 'en': 'Clear cache every (hours)'},
    'all_cache_cleared': {'nl': '{} cachebestanden verwijderd', 'en': '{} cache files removed'},
    'all_cache_clear_failed': {'nl': 'Cache kon niet worden verwijderd', 'en': 'Could not clear cache'},
    'search_history_new': {'nl': 'Nieuwe zoekopdracht', 'en': 'New search'},
    'search_history_delete': {'nl': 'Zoekopdrachten verwijderen', 'en': 'Delete searches'},
    'search_history_deleted': {'nl': '{} zoekopdrachten verwijderd', 'en': '{} searches deleted'},
    'add_series_all': {'nl': 'Alle bestaande afleveringen toevoegen', 'en': 'Add all existing episodes'},
    'add_series_from_now': {'nl': 'Alleen nieuwe afleveringen vanaf nu volgen', 'en': 'Follow new episodes from now on'},
    'series_following_started': {'nl': 'Nieuwe afleveringen worden vanaf nu automatisch toegevoegd', 'en': 'New episodes will be added automatically from now on'},
    'watch_later': {'nl': 'Kijk Later', 'en': 'Watch Later'},
    'add_to_mylist': {'nl': 'Toevoegen aan Mijn lijst (alleen Kodi)', 'en': 'Add to My List (Kodi only)'},
    'remove_from_mylist': {'nl': 'Verwijderen uit Mijn lijst (alleen Kodi)', 'en': 'Remove from My List (Kodi only)'},
    'add_to_watch_later': {'nl': 'Toevoegen aan Kijk Later', 'en': 'Add to Watch Later'},
    'remove_from_watch_later': {'nl': 'Verwijderen uit Kijk Later', 'en': 'Remove from Watch Later'},
    'added_to_watch_later': {'nl': 'Toegevoegd aan Kijk Later', 'en': 'Added to Watch Later'},
    'removed_from_watch_later': {'nl': 'Verwijderd uit Kijk Later', 'en': 'Removed from Watch Later'},
    'watch_later_empty': {'nl': 'Kijk Later is leeg', 'en': 'Watch Later is empty'},
    'watchlater_sync_done': {'nl': 'Kijk Later gesynchroniseerd ({} wijzigingen)', 'en': 'Watch Later synced ({} changes)'},
    'watchlater_sync_failed': {'nl': 'Synchroniseren van Kijk Later mislukt', 'en': 'Watch Later sync failed'},
    'watchlater_sync_not_logged_in': {'nl': 'Log in om Kijk Later te synchroniseren', 'en': 'Log in to sync Watch Later'},
    'watchlater_sync_summary': {'nl': '+{} cloud, -{} cloud, +{} lokaal, -{} lokaal', 'en': '+{} cloud, -{} cloud, +{} local, -{} local'},
    'episode_numbering_of': {'nl': 'Afl. {} van {}', 'en': 'Ep. {} of {}'},
    'episode_number_only': {'nl': 'Afl. {}', 'en': 'Ep. {}'},
    'availability_days': {'nl': 'nog {} dagen beschikbaar', 'en': '{} days left'},
    'availability_day': {'nl': 'nog {} dag beschikbaar', 'en': '{} day left'},
    'availability_hours': {'nl': 'nog {} uur beschikbaar', 'en': '{} hours left'},
    'availability_hour': {'nl': 'nog {} uur beschikbaar', 'en': '{} hour left'},
    'availability_minutes': {'nl': 'nog {} minuten beschikbaar', 'en': '{} minutes left'},
    'availability_minute': {'nl': 'nog {} minuut beschikbaar', 'en': '{} minute left'},
    'availability_expired': {'nl': 'niet meer beschikbaar', 'en': 'no longer available'},
    'broadcast_at': {'nl': 'Uitgezonden: {}', 'en': 'Aired: {}'},
    'add_series_to_watch_later': {'nl': 'Alle afleveringen toevoegen aan Kijk Later', 'en': 'Add all episodes to Watch Later'},
    'series_added_to_watch_later': {'nl': '{} afleveringen toegevoegd aan Kijk Later', 'en': '{} episodes added to Watch Later'},
    'season_folder': {'nl': 'Seizoen {}', 'en': 'Season {}'},
    'episode_number_prefix': {'nl': 'Aflevering {}', 'en': 'Episode {}'},
    'auto_added_episodes': {'nl': '{} nieuwe afleveringen toegevoegd aan Kijk Later', 'en': '{} new episodes added to Watch Later'},
    'expiry_soon': {'nl': 'Verloopt binnenkort: {}', 'en': 'Expiring soon: {}'},
    'my_series': {'nl': 'Mijn Series', 'en': 'My Series'},
    'add_to_my_series': {'nl': 'Toevoegen aan Mijn Series', 'en': 'Add to My Series'},
    'remove_from_my_series': {'nl': 'Verwijderen uit Mijn Series', 'en': 'Remove from My Series'},
    'added_to_my_series': {'nl': 'Toegevoegd aan Mijn Series', 'en': 'Added to My Series'},
    'removed_from_my_series': {'nl': 'Verwijderd uit Mijn Series', 'en': 'Removed from My Series'},
    'my_series_empty': {'nl': 'Mijn Series is leeg', 'en': 'My Series is empty'},
    'sync_now': {'nl': 'Nu synchroniseren', 'en': 'Sync Now'},
    'missing_id_my_series': {'nl': 'ID ontbreekt voor Mijn Series-actie', 'en': 'Missing id for My Series action'},
    'myseries_action_failed': {'nl': 'Mijn Series-actie mislukt', 'en': 'My Series action failed'},
    'myseries_sync_done': {'nl': 'Mijn Series gesynchroniseerd ({} wijzigingen)', 'en': 'My Series synced ({} changes)'},
    'myseries_sync_failed': {'nl': 'Synchroniseren van Mijn Series mislukt', 'en': 'My Series sync failed'},
    'myseries_sync_summary': {'nl': '+{} cloud, -{} cloud, +{} lokaal, -{} lokaal', 'en': '+{} cloud, -{} cloud, +{} local, -{} local'},
    'only_series': {'nl': 'Alleen series kunnen aan Mijn Series worden toegevoegd', 'en': 'Only series can be added to My Series'},
    'only_episodes_movies': {'nl': 'Alleen afleveringen en films kunnen in Kijk Later worden opgeslagen', 'en': 'Only episodes and movies can be saved to Watch Later'},
    'missing_id_watchlater': {'nl': 'ID ontbreekt voor Kijk Later-actie', 'en': 'Missing id for Watch Later action'},
    'mylist_action_failed': {'nl': 'Mijn lijst-actie mislukt', 'en': 'My List action failed'},
    'watchlater_action_failed': {'nl': 'Kijk Later-actie mislukt', 'en': 'Watch Later action failed'},
    'list_action_failed': {'nl': 'Lijstactie mislukt', 'en': 'List action failed'},
    'search_heading': {'nl': 'Zoeken in NLZiet', 'en': 'Search NLZiet'},
    'login_failed_max_attempts': {'nl': 'Inloggen mislukt - maximaal aantal pogingen bereikt', 'en': 'Login failed - max attempts reached'},
    'login_error': {'nl': 'Inlogfout: {}', 'en': 'Login error: {}'},
    'missing_profile_id': {'nl': 'Profiel-ID ontbreekt', 'en': 'Missing profile id'},
    'profile_switched': {'nl': 'Profiel gewijzigd naar {}', 'en': 'Profile switched to {}'},
    'profile_switch_failed': {'nl': 'Profiel wijzigen mislukt', 'en': 'Profile switch failed'},
    'no_profile_set': {'nl': 'Geen profiel-ID ingesteld in de instellingen', 'en': 'No Profile ID set in Settings'},
    'profile_applied': {'nl': 'Profiel toegepast: {}', 'en': 'Profile applied: {}'},
    'profile_apply_failed': {'nl': 'Profiel toepassen mislukt. Probeer Profielen beheren.', 'en': 'Failed to apply profile. Try Manage profiles.'},
    'missing_search_query': {'nl': 'Zoekopdracht ontbreekt', 'en': 'Missing search query'},
    'no_manifest': {'nl': 'Geen manifest beschikbaar', 'en': 'No manifest available'},
    'required_drm': {'nl': 'Vereiste DRM: {}', 'en': 'Required DRM: {}'},
    'dependency_missing_title': {'nl': 'Afhankelijkheid ontbreekt', 'en': 'Dependency missing'},
    'dependency_missing_msg': {'nl': 'Installeer script.module.inputstreamhelper om DRM-streams af te spelen.', 'en': 'Please install script.module.inputstreamhelper to play DRM streams.'},
    'result_label': {'nl': 'Resultaat', 'en': 'Result'},
    'item_label': {'nl': 'Item', 'en': 'Item'},
    'group_series': {'nl': 'Series', 'en': 'Series'},
    'group_tv_shows': {'nl': 'TV Shows', 'en': 'TV Shows'},
    'group_documentaries': {'nl': 'Documentaires', 'en': 'Documentaries'},
    'group_movies': {'nl': 'Films', 'en': 'Movies'},
    'group_channels': {'nl': 'Kanalen', 'en': 'Channels'},
    'group_episodes': {'nl': 'Afleveringen', 'en': 'Episodes'},
    'group_other': {'nl': 'Overig', 'en': 'Other'},
    'group_count': {'nl': '{} ({})', 'en': '{} ({})'},
    'group_result_title': {'nl': '{}: {}', 'en': '{}: {}'},
    'not_allowed': {'nl': 'Niet toegestaan', 'en': 'Not allowed'},
    'skip_intro_question': {'nl': 'Intro overslaan?', 'en': 'Skip the intro?'},
    'skip_recap_question': {'nl': 'Samenvatting overslaan?', 'en': 'Skip the recap?'},
    'widgets': {'nl': 'Widgets voor je startscherm', 'en': 'Widgets for the home screen'},
    'continue_watching': {'nl': 'Verder kijken', 'en': 'Continue watching'},
    'widgets_help': {'nl': 'Kies deze lijsten als widget in de instellingen van je skin.', 'en': 'Pick these lists as a widget in your skin settings.'},
    'backup_lists': {'nl': 'Mijn lijsten bewaren (back-up)', 'en': 'Save my lists (backup)'},
    'restore_lists': {'nl': 'Mijn lijsten terugzetten', 'en': 'Restore my lists'},
    'backup_saved': {'nl': 'Back-up opgeslagen: {0}', 'en': 'Backup saved: {0}'},
    'restore_done': {'nl': 'Teruggezet: {0}. Herstart Kodi voor de zekerheid, dan is alles opnieuw geladen.', 'en': 'Restored: {0}. Restart Kodi to be sure everything is reloaded.'},
    'restore_choose': {'nl': 'Kies een back-up', 'en': 'Choose a backup'},
    'restore_none': {'nl': 'Geen back-up gevonden in de back-upmap.', 'en': 'No backup found in the backup folder.'},
    'daily_check_problem': {'nl': 'Let op: {0}. Kies bij Instellingen > Bibliotheek > Onderhoud: Diagnose uitvoeren.', 'en': 'Needs attention: {0}. Open Settings > Library > Maintenance: Run diagnostics.'},
    'search_other_service': {'nl': 'Ook zoeken in Videoland', 'en': 'Also search in Videoland'},
    'restore_confirm': {'nl': 'Je huidige lijsten vervangen door deze back-up?', 'en': 'Replace your current lists with this backup?'},
    'episode_label': {'nl': 'Aflevering {0}', 'en': 'Episode {0}'},
    'watched_sent': {'nl': 'Kijkstatus naar NLZiet gestuurd', 'en': 'Watched status sent to NLZiet'},
    'stop_after_on': {'nl': 'Stop na deze aflevering', 'en': 'Stop after this episode'},
    'stop_after_off': {'nl': 'Doorgaan na deze aflevering', 'en': 'Keep playing after this episode'},
    'stop_after_set': {'nl': 'De volgende aflevering start niet automatisch', 'en': 'The next episode will not start automatically'},
    'stop_after_cleared': {'nl': 'Automatisch volgende aflevering staat weer aan', 'en': 'Automatic next episode is on again'},
    'shuffle_episode': {'nl': 'Willekeurige aflevering afspelen', 'en': 'Play a random episode'},
    'shuffle_none': {'nl': 'Geen afleveringen gevonden om uit te kiezen', 'en': 'No episodes found to pick from'},
    'watch_history': {'nl': 'Kijkgeschiedenis', 'en': 'Watch history'},
    'history_empty': {'nl': 'Nog niets gekeken', 'en': 'Nothing watched yet'},
    'history_clear': {'nl': 'Kijkgeschiedenis wissen', 'en': 'Clear watch history'},
    'history_cleared': {'nl': 'Kijkgeschiedenis gewist', 'en': 'Watch history cleared'},
}

# Numeric string ids (see resources/language/*/strings.po). These let Kodi
# resolve every runtime string through its translation system, so any language
# with a translation file works automatically.
STRING_IDS = {
    'login': 33002,
    'sign_out': 33003,
    'login_via_dialog': 33004,
    'login_dialog_title': 33005,
    'login_dialog_email': 33006,
    'login_dialog_password': 33007,
    'login_dialog_ok': 33008,
    'login_dialog_cancel': 33009,
    'login_invalid_credentials': 33010,
    'login_try_again': 33011,
    'token_expired': 33012,
    'login_again': 33013,
    'save_options_title': 33014,
    'save_option_tokens_only': 33015,
    'save_option_with_credentials': 33016,
    'tokens_only_info': 33017,
    'credentials_saved_warning': 33018,
    'session_token_obtained': 33019,
    'manage_profiles': 33020,
    'search': 33021,
    'my_list': 33022,
    'series': 33023,
    'tv_shows': 33024,
    'documentary': 33025,
    'movies': 33026,
    'channels': 33027,
    'all_episodes': 33028,
    'missing_series_id': 33029,
    'missing_season_id': 33030,
    'unable_fetch_series': 33031,
    'no_items_found': 33032,
    'not_logged_in': 33033,
    'login_notification': 33034,
    'logout_and_clear': 33035,
    'only_series_movies': 33036,
    'searching': 33037,
    'no_results': 33038,
    'now_watching': 33039,
    'added_to_list': 33040,
    'removed_from_list': 33041,
    'all': 33042,
    'no_episodes_found': 33043,
    'account_updated': 33044,
    'account_parse_error': 33045,
    'logged_out': 33046,
    'logout_cancelled': 33047,
    'login_successful_tokens': 33048,
    'login_successful_no_tokens': 33049,
    'login_failed_demo': 33050,
    'no_profiles': 33051,
    'my_list_empty': 33052,
    'no_items_for_group': 33053,
    'missing_id_mylist': 33054,
    'logout_confirm_msg': 33055,
    'keep_mylist': 33056,
    'keep_mylist_btn': 33057,
    'clear_mylist_btn': 33058,
    'logout_btn': 33059,
    'cancel_btn': 33060,
    'season': 33061,
    'subscription_label': 33062,
    'subscription_type_label': 33063,
    'max_devices_label': 33064,
    'expires_label': 33065,
    'add_to_library': 33066,
    'library_exported': 33067,
    'library_export_failed': 33068,
    'remove_from_library': 33187,
    'library_movie_added': 33188,
    'library_removed': 33189,
    'library_not_found': 33190,
    'library_updating': 33191,
    'library_update_done': 33192,
    'library_update_failed': 33193,
    'library_update_now': 33194,
    'library_empty': 33195,
    'library': 33196,
    'library_adding': 33197,
    'choose_tmdb': 33256,
    'choose_tmdb_other': 33257,
    'choose_tmdb_done': 33258,
    'library_lists_busy': 33245,
    'library_lists_done': 33246,
    'library_lists_now': 33247,
    'parental_enter_pin': 33222,
    'parental_enter_current_pin': 33223,
    'parental_new_pin': 33224,
    'parental_repeat_pin': 33225,
    'parental_pin_too_short': 33226,
    'parental_pin_mismatch': 33227,
    'parental_pin_set': 33228,
    'parental_pin_removed': 33229,
    'parental_wrong_pin': 33230,
    'parental_set_pin_first': 33231,
    'parental_lock_profile': 33232,
    'parental_unlock_profile': 33233,
    'parental_profile_locked': 33234,
    'parental_profile_unlocked': 33235,
    'parental_kids': 33236,
    'parental_pin_tag': 33237,
    'tmdb_check_missing': 33218,
    'tmdb_check_offline': 33219,
    'library_art_fixed': 33208,
    'library_moved': 33207,
    'tmdb_check_ok': 33210,
    'tmdb_check_failed': 33211,
    'diagnostics_exported': 33069,
    'diagnostics_failed': 33070,
    'subtitle_cache_cleared': 33159,
    'subtitle_cache_clear_failed': 33160,
    'clear_all_cache': 33173,
    'auto_clear_all_cache': 33174,
    'auto_clear_all_cache_hours': 33175,
    'all_cache_cleared': 33176,
    'all_cache_clear_failed': 33177,
    'search_history_new': 33161,
    'search_history_delete': 33162,
    'search_history_deleted': 33163,
    'add_series_all': 33164,
    'add_series_from_now': 33165,
    'series_following_started': 33166,
    'watch_later': 33073,
    'add_to_mylist': 33074,
    'remove_from_mylist': 33075,
    'add_to_watch_later': 33076,
    'remove_from_watch_later': 33077,
    'added_to_watch_later': 33078,
    'removed_from_watch_later': 33079,
    'watch_later_empty': 33080,
    'missing_id_watchlater': 33081,
    'mylist_action_failed': 33084,
    'watchlater_action_failed': 33085,
    'list_action_failed': 33086,
    'search_heading': 33087,
    'login_failed_max_attempts': 33088,
    'login_error': 33089,
    'missing_profile_id': 33090,
    'profile_switched': 33091,
    'profile_switch_failed': 33092,
    'no_profile_set': 33093,
    'profile_applied': 33094,
    'profile_apply_failed': 33095,
    'missing_search_query': 33096,
    'no_manifest': 33097,
    'required_drm': 33098,
    'dependency_missing_title': 33099,
    'dependency_missing_msg': 33100,
    'result_label': 33101,
    'item_label': 33102,
    'group_series': 33103,
    'group_tv_shows': 33104,
    'group_documentaries': 33105,
    'group_movies': 33106,
    'group_channels': 33107,
    'group_episodes': 33108,
    'group_other': 33109,
    'group_count': 33110,
    'group_result_title': 33111,
    'not_allowed': 33112,
    'watchlater_sync_done': 33113,
    'watchlater_sync_failed': 33114,
    'watchlater_sync_not_logged_in': 33115,
    'watchlater_sync_summary': 33116,
    'my_series': 33117,
    'add_to_my_series': 33118,
    'remove_from_my_series': 33119,
    'added_to_my_series': 33120,
    'removed_from_my_series': 33121,
    'my_series_empty': 33122,
    'sync_now': 33185,
    'missing_id_my_series': 33123,
    'myseries_action_failed': 33124,
    'myseries_sync_done': 33125,
    'myseries_sync_failed': 33126,
    'myseries_sync_summary': 33127,
    'only_series': 33128,
    'only_episodes_movies': 33129,
    'episode_numbering_of': 33130,
    'episode_number_only': 33131,
    'availability_days': 33132,
    'availability_day': 33133,
    'availability_hours': 33134,
    'availability_hour': 33135,
    'availability_minutes': 33136,
    'availability_minute': 33137,
    'availability_expired': 33138,
    'broadcast_at': 33139,
    'add_series_to_watch_later': 33140,
    'series_added_to_watch_later': 33141,
    'season_folder': 33142,
    'episode_number_prefix': 33143,
    'auto_added_episodes': 33147,
    'expiry_soon': 33154,
    'programs': 33169,
    'epg_title': 33170,
    'epg_subtitle': 33171,
    'tv_guide': 33172,
    'list_item_not_found': 33178,
    'list_item_not_reachable_later': 33179,
    'list_item_not_aired': 33180,
    'list_item_not_playable': 33181,
    'list_item_repeat_playable': 33182,
    'list_item_airing': 33183,
    'skip_intro_question': 33270,
    'skip_recap_question': 33271,
    'widgets': 33272,
    'continue_watching': 33273,
    'widgets_help': 33274,
    'backup_lists': 33275,
    'restore_lists': 33276,
    'backup_saved': 33277,
    'restore_done': 33278,
    'restore_choose': 33279,
    'restore_none': 33280,
    'daily_check_problem': 33283,
    'search_other_service': 33284,
    'restore_confirm': 33288,
    'episode_label': 33289,
    'watched_sent': 33290,
    'stop_after_on': 33293,
    'stop_after_off': 33294,
    'stop_after_set': 33295,
    'stop_after_cleared': 33296,
    'shuffle_episode': 33297,
    'shuffle_none': 33298,
    'watch_history': 33299,
    'history_empty': 33300,
    'history_clear': 33301,
    'history_cleared': 33302,
}


def get_string(key, *args):
    """Get a translated runtime string using Kodi's configured language.
    
    Args:
        key: Translation key
        *args: Optional format arguments
        
    Returns:
        Translated string, falling back to English
    """
    text = None
    # Prefer Kodi's own translation system so any language that ships a
    # strings.po works without code changes.
    sid = STRING_IDS.get(key)
    if sid:
        try:
            localized = ADDON.getLocalizedString(sid)
            if localized:
                text = localized
        except Exception:
            text = None
    if text is None:
        # Fallback: use the built-in dictionary. English is the universal
        # fallback for languages we do not ship explicitly.
        language = 'en'
        try:
            kodi_language = xbmc.getLanguage(xbmc.ISO_639_1) or ''
            if str(kodi_language).lower().startswith('nl'):
                language = 'nl'
        except Exception:
            pass
        translations = TRANSLATIONS.get(key, {})
        text = translations.get(language) or translations.get('en') or translations.get('nl') or key
    if not isinstance(text, str):
        text = str(key)
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
    return kodi_ui.make_color_tag(color_raw, text)


# Lists where Kodi's sort menu (title, year, episode) makes sense. The first
# sort option is always NLZiet's own order.
_SORTABLE_MODES = {
    'series', 'browse_series_genre', 'browse_movie_genre', 'browse_tv_genre', 'browse',
    'search_group', 'my_list_group', 'watch_later', 'my_series', 'placement_row', 'browse_library',
}
_EPISODE_MODES = {'series_season', 'watch_later_collection'}


def _current_mode():
    try:
        query = sys.argv[2] if len(sys.argv) > 2 else ''
        return dict(urllib.parse.parse_qsl(query.lstrip('?'))).get('mode') or ''
    except Exception:
        return ''


def _add_sort_methods(mode=None):
    mode = _current_mode() if mode is None else mode
    if mode not in _SORTABLE_MODES and mode not in _EPISODE_MODES:
        return
    names = ['SORT_METHOD_UNSORTED']
    if mode in _EPISODE_MODES:
        names += ['SORT_METHOD_EPISODE', 'SORT_METHOD_DATE']
    names += ['SORT_METHOD_LABEL_IGNORE_THE', 'SORT_METHOD_VIDEO_YEAR']
    for name in names:
        method = getattr(xbmcplugin, name, None)
        if method is None:
            continue
        try:
            xbmcplugin.addSortMethod(HANDLE, method)
        except Exception:
            pass


def _end_directory():
    """endOfDirectory with Kodi's sort options for list pages."""
    _add_sort_methods()
    xbmcplugin.endOfDirectory(HANDLE)
    if _LOGO_CACHE:
        _LOGO_CACHE.flush()


def build_url(query):
    return kodi_ui.build_url(BASE_URL, query)


def _localized_weekday(dt):
    """Return a localized weekday abbreviation + day-month for an EPG item."""
    try:
        lang = (xbmc.getLanguage(xbmc.ISO_639_1) or '').lower()
    except Exception:
        lang = ''
    names = {
        'nl': ['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo'],
        'en': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'de': ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'],
        'fr': ['lun', 'mar', 'mer', 'jeu', 'ven', 'sam', 'dim'],
        'es': ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'],
        'it': ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom'],
        'pt': ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'],
        'pl': ['pon', 'wt', 'śr', 'czw', 'pt', 'sob', 'ndz'],
        'sv': ['mån', 'tis', 'ons', 'tors', 'fre', 'lör', 'sön'],
        'da': ['man', 'tir', 'ons', 'tor', 'fre', 'lør', 'søn'],
        'no': ['man', 'tir', 'ons', 'tor', 'fre', 'lør', 'søn'],
        'fi': ['ma', 'ti', 'ke', 'to', 'pe', 'la', 'su'],
        'tr': ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'],
        'ru': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
    }
    table = names.get(lang[:2], names['en'])
    try:
        wd = table[dt.weekday()]
    except Exception:
        wd = dt.strftime('%a')
    return '{0} {1:02d}-{2:02d}'.format(wd, dt.day, dt.month)


def _clear_resume_bookmark(content_id):
    """Remove any saved Kodi resume bookmark for a live channel.

    Kodi treats live streams like VOD and stores a resume point when playback
    stops. Deleting the bookmark before playback prevents the "Resume from …"
    prompt and ensures the stream starts at the live edge.
    """
    if not content_id:
        return
    try:
        import glob
        import os
        import sqlite3

        db_dir = xbmc.translatePath('special://userdata/Database/')
        pattern = 'plugin://plugin.video.nlziet/?mode=play&id={0}'.format(content_id)
        for db_path in glob.glob(os.path.join(db_dir, 'MyVideos*.db')):
            try:
                conn = sqlite3.connect(db_path, timeout=1)
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "DELETE FROM bookmark WHERE idFile IN "
                        "(SELECT idFile FROM files WHERE strFilename LIKE ?)",
                        (pattern + '%',),
                    )
                    conn.commit()
                finally:
                    conn.close()
            except Exception:
                pass
    except Exception:
        pass


def _play_media_url(url, noresume=False):
    """Play a plugin URL through Kodi's PlayMedia builtin.

    ``noresume`` tells Kodi to start at the beginning without consulting the
    saved bookmark database. It is required for live TV because Kodi otherwise
    offers to resume a live channel from a previously stored position.
    """
    if noresume:
        xbmc.executebuiltin('PlayMedia({0},noresume)'.format(url))
    else:
        xbmc.executebuiltin('PlayMedia({0})'.format(url))


def _metadata_sources(content):
    """Return flat/nested content dictionaries in lookup priority order."""
    if not isinstance(content, dict):
        return []
    sources = [content]
    for key in ('raw', 'series', 'show', 'program', 'movie', 'episode'):
        value = content.get(key)
        if isinstance(value, dict):
            sources.append(value)
    raw = content.get('raw')
    if isinstance(raw, dict):
        for key in ('series', 'show', 'program', 'movie', 'episode'):
            value = raw.get(key)
            if isinstance(value, dict):
                sources.append(value)
    return sources


def _first_metadata_value(sources, keys):
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None and str(value).strip():
                return value
    return None


def _metadata_int(value, minimum=0):
    try:
        match = re.search(r'-?\d+', str(value))
        parsed = int(match.group(0)) if match else None
        return parsed if parsed is not None and parsed >= minimum else None
    except Exception:
        return None


def _metadata_year(sources):
    value = _first_metadata_value(
        sources,
        ('year', 'releaseYear', 'release_year', 'productionYear', 'production_year'),
    )
    year = _metadata_int(value, 1000)
    if year:
        return year
    date_value = _first_metadata_value(
        sources,
        ('releaseDate', 'release_date', 'premiere', 'productionDate'),
    )
    match = re.search(r'\b(19|20)\d{2}\b', str(date_value or ''))
    return int(match.group(0)) if match else None


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _playback_state(content):
    """Normalize watched/resume fields exposed by NLZiet into Kodi values."""
    sources = _metadata_sources(content)
    if not sources:
        return {}
    watched = _first_metadata_value(
        sources, ('isWatched', 'is_watched', 'watched', 'fullyWatched', 'viewed')
    )
    playcount = _number(_first_metadata_value(sources, ('playcount', 'playCount')))
    position = _number(_first_metadata_value(
        sources,
        ('resumePosition', 'resume_position', 'resumeTime', 'resume_time',
         'playbackPosition', 'playback_position', 'positionInSeconds', 'secondsWatched'),
    ))
    total = _number(_first_metadata_value(
        sources, ('durationInSeconds', 'duration_seconds', 'duration', 'totalTime')
    ))
    percentage = _number(_first_metadata_value(
        sources, ('progressPercentage', 'progress_percentage', 'percentageWatched')
    ))
    if position is None and total and percentage is not None:
        position = total * max(0.0, min(100.0, percentage)) / 100.0
    watched_bool = str(watched).lower() in ('true', '1', 'yes') if watched is not None else False
    if playcount and playcount > 0:
        watched_bool = True
    if total and position and position / total >= 0.9:
        watched_bool = True
    state = {}
    if watched_bool:
        state['playcount'] = max(1, int(playcount or 1))
    if position and position > 0 and total and total > position and not watched_bool:
        state['resume'] = {'position': float(position), 'total': float(total)}
    return state


def _clean_episode_title(value):
    title = str(value or '').strip()
    title = re.sub(r'^\s*S\d+\s*[:.]\s*A\d+\s*[-:\u2013\u2014]*\s*', '', title, flags=re.I)
    title = re.sub(r'^\s*S\d+E\d+\s*[-:\u2013\u2014]*\s*', '', title, flags=re.I)
    title = re.sub(r'^\s*Afl\.?\s*\d+\s*[-:\u2013\u2014]*\s*', '', title, flags=re.I)
    return title


def _build_trakt_metadata(title, info=None, content=None):
    """Build Kodi labels consumed by the official script.trakt add-on."""
    sources = _metadata_sources(content)
    info = info if isinstance(info, dict) else {}
    content_type = str(_first_metadata_value(
        sources, ('type', 'contentType', 'content_type', 'mediaType', 'media_type')
    ) or '').lower()

    season = _metadata_int(_first_metadata_value(
        sources, ('season_number', 'seasonNumber', 'season', 'seasonIndex')
    ))
    episode = _metadata_int(_first_metadata_value(
        sources, ('episode_number', 'episodeNumber', 'episode', 'episodeIndex', 'number')
    ), minimum=1)
    formatted = _first_metadata_value(
        sources, ('formatted_episode_numbering', 'formattedEpisodeNumbering')
    )
    numbering = formatted or _first_metadata_value(sources, ('subtitle', 'subtitleText')) or title
    if numbering and (season is None or episode is None):
        match = re.search(r'S(\d+)\s*[:.]?\s*(?:E|A)(\d+)', str(numbering), re.I)
        if match:
            season = season if season is not None else int(match.group(1))
            episode = episode if episode is not None else int(match.group(2))

    is_episode = 'episode' in content_type or (season is not None and episode is not None)
    is_movie = 'movie' in content_type or 'film' in content_type
    if is_episode and season is not None and episode is not None:
        show_title = _first_metadata_value(
            sources,
            ('series_title', 'seriesTitle', 'showtitle', 'showTitle', 'tvshowtitle',
             'tvShowTitle', 'programTitle', 'program_title'),
        )
        # NLZiet episode responses commonly use title for the series and
        # subtitle for the episode name.
        show_title = str(show_title or _first_metadata_value(sources, ('title', 'name')) or '').strip()
        episode_title = _first_metadata_value(
            sources, ('episode_title', 'episodeTitle', 'subtitle', 'subtitleText')
        )
        episode_title = _clean_episode_title(episode_title)
        if not episode_title or episode_title == show_title:
            episode_title = _clean_episode_title(info.get('title') or title)
        metadata = {
            'media_type': 'episode',
            'title': episode_title or show_title,
            'showtitle': show_title,
            'season': str(season),
            'episode': str(episode),
        }
        # Episode release/broadcast dates describe the NLZiet airing, not the
        # production year of the show.  Only use an explicitly series-scoped
        # year here; playback can resolve the canonical show year via Trakt.
        year = _metadata_int(_first_metadata_value(
            sources, ('series_year', 'seriesYear', 'show_year', 'showYear')
        ), 1000)
        if year:
            metadata['year'] = str(year)
        return metadata

    if is_movie:
        movie_title = _first_metadata_value(sources, ('title', 'name')) or info.get('title') or title
        metadata = {'media_type': 'movie', 'title': str(movie_title or '').strip()}
        year = _metadata_year(sources)
        if year:
            metadata['year'] = str(year)
        return metadata
    return {}


def _handshake_metadata_content(stream_info):
    """Extract catalogue metadata retained in the stream handshake."""
    handshake = stream_info.get('handshake') if isinstance(stream_info, dict) else None
    if not isinstance(handshake, dict):
        return {}
    item = handshake.get('item')
    content = dict(item) if isinstance(item, dict) else {}
    analytics = handshake.get('analytics')
    if not isinstance(analytics, dict):
        analytics = {}
    mappings = {
        'series_title': ('seriesTitle', 'showTitle'),
        'episode_title': ('episodeTitle',),
        'season_number': ('seasonNumber', 'season'),
        'episode_number': ('episodeNumber', 'episode'),
        'year': ('releaseYear', 'productionYear', 'year'),
    }
    for target, keys in mappings.items():
        if content.get(target) not in (None, ''):
            continue
        for key in keys:
            value = analytics.get(key)
            if value not in (None, ''):
                content[target] = value
                break
    return content


def _official_trakt_client_id():
    """Read/decode the public API identity bundled with script.trakt."""
    try:
        trakt_addon = xbmcaddon.Addon('script.trakt')
        trakt_path = trakt_addon.getAddonInfo('path') or ''
        source_path = os.path.join(trakt_path, 'resources', 'lib', 'traktapi.py')
        with open(source_path, 'r', encoding='utf-8') as source_file:
            source = source_file.read()
        match = re.search(r'__client_id:\s*str\s*=\s*\[([^\]]+)\]', source)
        if not match:
            return ''
        encoded = [int(value) for value in re.findall(r'\d+', match.group(1))]
        return ''.join(chr(value ^ 0x42) for value in encoded)
    except Exception:
        return ''


def _official_trakt_get(path, params=None):
    client_id = _official_trakt_client_id()
    if not client_id:
        return None
    url = 'https://api.trakt.tv' + path
    if params:
        url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        'Accept': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': client_id,
        'User-Agent': 'Kodi script.trakt metadata lookup',
    })
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


def _official_trakt_movie_match(title):
    """Resolve a movie using the API identity bundled with script.trakt."""
    title = str(title or '').strip()
    if not title:
        return {}
    try:
        results = _official_trakt_get('/search/movie', {
            'query': title,
            'limit': 1,
        }) or []
        movie = (results[0].get('movie') or {}) if results else {}
        year = _metadata_int(movie.get('year'), 1000)
        if not movie.get('title') or not year:
            return {}
        return {'title': str(movie['title']), 'year': str(year)}
    except Exception as exc:
        xbmc.log(f"NLZiet Trakt movie lookup failed: {exc}", xbmc.LOGWARNING)
        return {}


def _normalized_trakt_title(value):
    return re.sub(r'[^a-z0-9]+', '', str(value or '').casefold())


def _official_trakt_episode_match(show_title, episode_title, season, episode):
    """Resolve NLZiet episode numbering/title to Trakt's production order."""
    show_title = str(show_title or '').strip()
    episode_title = _clean_episode_title(episode_title)
    if not show_title:
        return {}
    try:
        results = _official_trakt_get('/search/show', {
            'query': show_title,
            'limit': 1,
        }) or []
        show = (results[0].get('show') or {}) if results else {}
        show_ids = show.get('ids') or {}
        show_id = show_ids.get('trakt') or show_ids.get('slug')
        show_year = _metadata_int(show.get('year'), 1000)
        if not show.get('title') or not show_id:
            return {}

        seasons = _official_trakt_get(
            '/shows/{}/seasons'.format(urllib.parse.quote(str(show_id))),
            {'extended': 'episodes'},
        ) or []
        episodes = [
            item
            for season_item in seasons
            for item in (season_item.get('episodes') or [])
            if isinstance(item, dict)
        ]

        normalized_title = _normalized_trakt_title(episode_title)
        generic_title = (
            not normalized_title or
            normalized_title == _normalized_trakt_title(show_title) or
            bool(re.fullmatch(r'(?:afl|aflevering|episode)\d+', normalized_title))
        )
        matched = None
        if not generic_title:
            matched = next(
                (item for item in episodes
                 if _normalized_trakt_title(item.get('title')) == normalized_title),
                None,
            )
        if matched is None:
            requested_season = _metadata_int(season)
            requested_episode = _metadata_int(episode, minimum=1)
            matched = next(
                (item for item in episodes
                 if _metadata_int(item.get('season')) == requested_season
                 and _metadata_int(item.get('number'), minimum=1) == requested_episode),
                None,
            )
        if matched is None:
            return {}

        metadata = {
            'showtitle': str(show['title']),
            'title': str(matched.get('title') or episode_title or show['title']),
            'season': str(matched['season']),
            'episode': str(matched['number']),
        }
        if show_year:
            metadata['year'] = str(show_year)
        return metadata
    except Exception as exc:
        xbmc.log(f"NLZiet Trakt episode lookup failed: {exc}", xbmc.LOGWARNING)
        return {}


def _merge_playback_metadata(query_metadata, stream_info, api=None, content_id=None):
    metadata = dict(query_metadata or {})
    handshake_content = _handshake_metadata_content(stream_info)
    discovered = _build_trakt_metadata('', content=handshake_content)
    for key, value in discovered.items():
        if value not in (None, ''):
            metadata.setdefault(key, str(value))

    # Old Kodi directory entries can contain only the content id.  A stream
    # handshake identifies the series/season but may still omit the episode
    # number, so resolve that item from the season catalogue as a final
    # fallback.  get_series_episodes also normalizes/infer missing numbers.
    content_type = str(handshake_content.get('type') or '').lower()
    needs_episode = 'episode' in content_type and not metadata.get('episode')
    series_id = (handshake_content.get('seriesId') or
                 handshake_content.get('series_id'))
    season_id = (handshake_content.get('seasonId') or
                 handshake_content.get('season_id'))
    if needs_episode and api and content_id and series_id:
        try:
            episodes = api.get_series_episodes(series_id, season_id=season_id, limit=400) or []
            matched = next(
                (episode for episode in episodes
                 if str(episode.get('id') or '') == str(content_id)),
                None,
            )
            if matched:
                catalogue_content = dict(handshake_content)
                catalogue_content.update(matched)
                for key, value in _build_trakt_metadata(
                    '', content=catalogue_content
                ).items():
                    if value not in (None, ''):
                        metadata.setdefault(key, str(value))
        except Exception as exc:
            xbmc.log(f"NLZiet Trakt catalogue lookup failed: {exc}", xbmc.LOGWARNING)

    if metadata.get('media_type') == 'movie' and not metadata.get('year'):
        movie_match = _official_trakt_movie_match(metadata.get('title'))
        if movie_match:
            metadata.update(movie_match)
    elif metadata.get('media_type') == 'episode':
        # Discard stale/broadcast years already embedded in cached directory
        # URLs. The canonical series year is supplied by the Trakt match.
        metadata.pop('year', None)
        episode_match = _official_trakt_episode_match(
            metadata.get('showtitle'),
            handshake_content.get('episode_title') or metadata.get('title'),
            metadata.get('season'),
            metadata.get('episode'),
        )
        if episode_match:
            metadata.update(episode_match)
    return metadata


def _add_trakt_metadata_to_query(query, title, info=None, content=None):
    query_copy = dict(query or {})
    if query_copy.get('mode') == 'play' and query_copy.get('fmt') != 'live':
        for key, value in _build_trakt_metadata(title, info, content).items():
            if value not in (None, ''):
                query_copy.setdefault(key, str(value))
    return query_copy


def _apply_playback_metadata(list_item, metadata, fmt=None):
    """Publish metadata as Kodi VideoPlayer labels for script.trakt."""
    if fmt == 'live':
        # This is the exclusion property recognized by the official Trakt
        # add-on for non-library playback.
        list_item.setProperty('script.trakt.exclude', 'true')
        # Show EPG info (channel + current programme) in the player OSD.
        try:
            video_info = {}
            if metadata.get('title'):
                video_info['title'] = metadata.get('title')
                try:
                    list_item.setLabel(metadata.get('title'))
                except Exception:
                    pass
            if metadata.get('plot'):
                video_info['plot'] = metadata.get('plot')
            if video_info:
                list_item.setInfo('video', video_info)
            thumb = metadata.get('thumb')
            if thumb:
                list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': thumb})
        except Exception:
            pass
        # Live TV must never offer a resume point. Mark a zero-length resume
        # point on the resolved item so Kodi skips the bookmark database
        # lookup that would otherwise prompt "Resume from ...".
        try:
            list_item.getVideoInfoTag().setResumePoint(0.0, 3600.0)
        except Exception:
            list_item.setProperty('ResumeTime', '0')
            list_item.setProperty('TotalTime', '3600')
        list_item.setProperty('IsLive', 'true')
        return
    media_type = metadata.get('media_type')
    if media_type in ('episode', 'movie'):
        video_info = {
            'mediatype': media_type,
            'title': metadata.get('title') or '',
        }
        if metadata.get('year'):
            video_info['year'] = _metadata_int(metadata.get('year'), 1000)
        if media_type == 'episode':
            video_info.update({
                'tvshowtitle': metadata.get('showtitle') or '',
                'season': _metadata_int(metadata.get('season')),
                'episode': _metadata_int(metadata.get('episode'), minimum=1),
            })
    else:
        video_info = {}
        if metadata.get('title'):
            video_info['title'] = metadata.get('title')
        if metadata.get('plot'):
            video_info['plot'] = metadata.get('plot')
    if metadata.get('plot') and 'plot' not in video_info:
        video_info['plot'] = metadata.get('plot')
    video_info = {key: value for key, value in video_info.items() if value not in (None, '')}
    if video_info:
        list_item.setInfo('video', video_info)
    if metadata.get('title'):
        try:
            list_item.setLabel(metadata.get('title'))
        except Exception:
            pass
    xbmc.log(f"NLZiet Trakt metadata: {video_info} (media_type={media_type})", xbmc.LOGINFO)
    # Show programme icon in the player OSD when available.
    try:
        thumb = metadata.get('thumb')
        if thumb:
            list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': thumb})
            xbmc.log('NLZiet setArt thumb={0}'.format(thumb), xbmc.LOGINFO)
        else:
            xbmc.log('NLZiet no thumb in metadata', xbmc.LOGINFO)
    except Exception:
        pass
    # Replay ("terugkijken") must also start at 0:00:00 without a resume prompt.
    if fmt == 'epg':
        try:
            list_item.getVideoInfoTag().setResumePoint(0.0, 3600.0)
        except Exception:
            list_item.setProperty('ResumeTime', '0')
            list_item.setProperty('TotalTime', '3600')


_LOGOS = None


_LOGO_CACHE = None


def _browse_logo_cache():
    """Logo cache for titles outside the library (needs a TMDb key)."""
    global _LOGO_CACHE
    if _LOGO_CACHE is None:
        if not (_setting_on('browse_logos', True) and _setting_on('library_enrich', True)
                and (ADDON.getSetting('tmdb_api_key') or '').strip()):
            _LOGO_CACHE = False
        else:
            folder = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
            _LOGO_CACHE = logo_cache_mod.LogoCache(folder)
    return _LOGO_CACHE or None


def _library_logo(query, content=None, group=None, title=None, metadata=None):
    """Clearlogo for browse lists: from the library, else from the logo cache."""
    global _LOGOS
    if not isinstance(query, dict):
        return None
    mode = query.get('mode')
    if mode == 'series_detail':
        key = ('series', str(query.get('series_id') or ''))
    elif mode == 'play' and query.get('fmt') not in ('live', 'epg'):
        ctype = str((content or {}).get('type') or '').lower() if isinstance(content, dict) else ''
        if not (str(group or '').lower() == 'movies' or 'movie' in ctype or 'film' in ctype):
            return None
        key = ('movie', str(query.get('id') or ''))
    else:
        return None
    if _LOGOS is None:
        try:
            profile = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
            _LOGOS = library_art.logo_index(library_mod.LibraryStore(os.path.join(profile, 'library.json')))
        except Exception:
            _LOGOS = {}
    logo = _LOGOS.get(key)
    if logo:
        return logo
    cache = _browse_logo_cache()
    if cache is None:
        return None
    if key[0] == 'movie':
        name = (metadata or {}).get('title') or title
        year = (metadata or {}).get('year')
    else:
        name = ((content or {}).get('title') if isinstance(content, dict) else None) or title
        year = None
    try:
        return cache.get(key[0], name, year) or None
    except Exception:
        return None


_TRAKT_INDEX = None
_TRAKT_LOADED = False


def _trakt_watched(metadata):
    """True when Trakt says this film/episode was watched (opt-in setting)."""
    global _TRAKT_INDEX, _TRAKT_LOADED
    if not _setting_on('trakt_watched_status', False):
        return False
    if not _TRAKT_LOADED:
        _TRAKT_LOADED = True
        try:
            token = trakt_status.access_token(xbmcaddon.Addon('script.trakt'))
            cache = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'trakt_watched.json')
            _TRAKT_INDEX = trakt_status.load_index(cache, token, _official_trakt_client_id())
        except Exception as e:
            xbmc.log(f"NLZiet Trakt watched status unavailable: {e}", xbmc.LOGINFO)
            _TRAKT_INDEX = None
    try:
        return bool(_TRAKT_INDEX and _TRAKT_INDEX.watched(metadata))
    except Exception:
        return False


def add_directory_item(title, query, is_folder=True, thumb=None, info=None, content=None, group=None, is_playable=None, extra_context_items=None):
    query = _add_trakt_metadata_to_query(query, title, info, content)
    is_live = isinstance(query, dict) and query.get('fmt') == 'live'

    trakt_metadata = _build_trakt_metadata(title, info, content) if not is_live else {}
    item_info = dict(info or {})
    if trakt_metadata:
        item_info.setdefault('mediatype', trakt_metadata.get('media_type'))
        item_info.setdefault('title', trakt_metadata.get('title'))
        if trakt_metadata.get('year'):
            item_info.setdefault('year', _metadata_int(trakt_metadata.get('year'), 1000))
        if trakt_metadata.get('media_type') == 'episode':
            item_info.setdefault('tvshowtitle', trakt_metadata.get('showtitle'))
            item_info.setdefault('season', _metadata_int(trakt_metadata.get('season')))
            item_info.setdefault('episode', _metadata_int(trakt_metadata.get('episode'), minimum=1))

    playback_state = _playback_state(content) if not is_live else {}
    for key, value in playback_state.items():
        item_info.setdefault(key, value)
    if trakt_metadata and not item_info.get('playcount') and _trakt_watched(trakt_metadata):
        item_info['playcount'] = 1

    logo = _library_logo(query, content, group, title, trakt_metadata)
    return kodi_ui.add_directory_item(
        ADDON,
        HANDLE,
        build_url,
        get_api_instance,
        title,
        query,
        is_folder=is_folder,
        is_playable=is_playable,
        thumb=thumb,
        info=item_info,
        content=content,
        playback_state=playback_state,
        is_live=is_live,
        group=group,
        extra_context_items=extra_context_items,
        extra_art={'clearlogo': logo} if logo else None,
        add_to_library_label=get_string('add_to_library'),
        remove_from_library_label=get_string('remove_from_library'),
        library_check=is_in_library,
        mylist_add_label=get_string('add_to_mylist'),
        mylist_remove_label=get_string('remove_from_mylist'),
        watch_later_add_label=get_string('add_to_watch_later'),
        watch_later_remove_label=get_string('remove_from_watch_later'),
        my_series_add_label=get_string('add_to_my_series'),
        my_series_remove_label=get_string('remove_from_my_series'),
        add_series_watch_later_label=get_string('add_series_to_watch_later'),
    )


def _optimize_image_url(url):
    """Optimize image URLs to request higher-resolution versions for fanart.

    The NLZiet image service returns low-res images (1280x720) by default.
    We request a larger resolution to avoid pixelation when displayed as fanart.
    """
    return kodi_ui.optimize_image_url(url)


def _pick_landscape_thumb(src):
    """Return the best landscape-oriented thumbnail or path for an item.

    Accepts either a string URL/path or a dict-like content item. Prefers
    explicit landscape keys, then common wide/hero/poster keys, and finally
    falls back to any url-like string found on the object.
    """
    return kodi_ui.pick_landscape_thumb(src)


def _pick_portrait_thumb(src):
    """Return the best portrait-oriented thumbnail or path for an item.

    Portrait images are typically 2:3 aspect ratio (posters/covers).
    Prefers explicit portrait keys, then falls back to landscape or generic thumbnails.
    """
    return kodi_ui.pick_portrait_thumb(src)


def _set_smart_artwork(li, src, thumb=None):
    """Set artwork on a ListItem with proper aspect ratio handling.

    Assigns different images to different art keys based on their aspect ratios:
    - fanart (16:9 landscape) - prefers landscape images
    - poster (2:3 portrait) - prefers portrait images
    - thumb/icon (1:1 square) - uses best single image with aspect ratio preserved
    """
    return kodi_ui.set_smart_artwork(li, src, thumb=thumb)


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
    global _last_token_check
    if time.time() - _last_token_check < _token_check_interval:
        return True
    _last_token_check = time.time()
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
    # Check for expired tokens and attempt refresh
    _check_and_handle_token_expiry()
    
    try:
        addon_path = xbmc.translatePath(ADDON.getAddonInfo('path')) or ''
    except Exception:
        try:
            addon_path = ADDON.getAddonInfo('path') or ''
        except Exception:
            addon_path = ''

    # prefer png then svg then fallback to addon's icon.png
    def _pick_icon(name):
        return kodi_ui.pick_menu_icon(addon_path, name)

    # Explicit PNG-first picker (prefer exact menu_{name}.png when available)
    def _pick_png(name):
        return kodi_ui.pick_menu_png(addon_path, name)

    # Determine authentication state and show protected items only when logged in
    logged_in = _is_logged_in()

    # If not logged in, notify the user to press Login on the main menu
    if not logged_in:
        try:
            msg = get_string('login_notification')
            xbmcgui.Dialog().notification('NLZiet', msg, xbmcgui.NOTIFICATION_INFO)
        except Exception:
            xbmc.log('NLZiet: failed to show login notification', xbmc.LOGDEBUG)

    if not logged_in:
        add_directory_item(get_string('login'), {'mode': 'login'}, thumb=_pick_png('login'), is_folder=False, is_playable=False)

    if logged_in:
        # Order: find and browse, the user's own lists, live tv, account last.
        add_directory_item(get_string('search'), {'mode': 'search'}, thumb=_pick_png('search'))
        add_directory_item(get_string('series'), {'mode': 'browse_series_categories'}, thumb=_pick_png('series'))
        add_directory_item(get_string('tv_shows'), {'mode': 'browse_tv_shows'}, thumb=_pick_png('tvshows'))
        add_directory_item(get_string('documentary'), {'mode': 'browse', 'type': 'documentary'}, thumb=_pick_png('documentary'))
        add_directory_item(get_string('movies'), {'mode': 'browse_movie_categories'}, thumb=_pick_png('movies'))
        add_directory_item(get_string('channels'), {'mode': 'browse', 'type': 'channels'}, thumb=_pick_png('tv'))
        add_directory_item(get_string('tv_guide'), {'mode': 'browse_epg'}, thumb=_pick_png('epg'))
        add_directory_item(get_string('continue_watching'), {'mode': 'widget', 'list': 'continue'}, thumb=_pick_png('continue'))
        add_directory_item(get_string('my_list'), {'mode': 'my_list'}, thumb=_pick_png('mylist'))
        add_directory_item(get_string('watch_later'), {'mode': 'watch_later'}, thumb=_pick_png('watchlater'))
        add_directory_item(get_string('my_series'), {'mode': 'my_series'}, thumb=_pick_png('myseries'))
        add_directory_item(get_string('library'), {'mode': 'browse_library'}, thumb=_pick_png('library'))
        add_directory_item(get_string('widgets'), {'mode': 'widgets'}, thumb=_pick_png('widgets'))
        add_directory_item(get_string('watch_history'), {'mode': 'history'}, thumb=_pick_png('continue'))
        add_directory_item(get_string('manage_profiles'), {'mode': 'profiles'}, thumb=_pick_png('profiles'))
        add_directory_item(get_string('sign_out'), {'mode': 'logout_confirm'}, thumb=_pick_png('logout'), is_folder=False, is_playable=False)
    
    # Set background image for the container
    try:
        background_path = os.path.join(addon_path, 'resources', 'media', 'background.jpg')
        if os.path.exists(background_path):
            xbmcplugin.setProperty(HANDLE, 'fanart', background_path)
    except Exception:
        xbmc.log('NLZiet: failed to set background image', xbmc.LOGDEBUG)
    
    _end_directory()
    if logged_in:
        _run_after_directory(_maybe_run_auto_add)
        _run_after_directory(_maybe_run_expiry_check)
        _run_after_directory(_maybe_clear_subtitle_cache)
        _run_after_directory(_maybe_clear_all_cache)


def browse_series_categories():
    """Display series category/genre list."""
    api = get_api_instance()

    genres = api.get_series_genres()
    for genre in genres:
        name = genre.get('name')
        genre_param = genre.get('genre')
        add_directory_item(name, {'mode': 'browse_series_genre', 'genre': genre_param or 'all'}, is_folder=True)
    _end_directory()


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
                    marker = ''  # text only: readable by screen readers and every skin
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
            add_directory_item(item.get('title') or item.get('id') or get_string('group_series'), {'mode': 'series_detail', 'series_id': item.get('id')}, is_folder=True, thumb=_pick_landscape_thumb(item), info=info, content=item, group='series')
        else:
            # Episodes would be playable - but shouldn't appear at top level in genre view
            pass
    
    _end_directory()


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
        _end_directory()
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
                    marker = ''  # text only: readable by screen readers and every skin
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
        add_directory_item(item.get('title') or item.get('id') or get_string('group_series'), {'mode': 'series_detail', 'series_id': item.get('id')}, is_folder=True, thumb=_pick_landscape_thumb(item), info=info, content=item, group='series')
    _end_directory()


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
    series_title = detail.get('title') or ''
    # If no seasons discovered, offer direct episode listing
    if not seasons:
        add_directory_item(get_string('all_episodes'), {'mode': 'series_season', 'series_id': series_id, 'season_id': '', 'series_title': series_title}, is_folder=True)
    else:
        for s in seasons:
            title = s.get('title') or f"{get_string('season')} {s.get('id')}"
            add_directory_item(title, {'mode': 'series_season', 'series_id': series_id, 'season_id': s.get('id'), 'episodes_url': s.get('episodes_url') or '', 'series_title': series_title, 'season_number': s.get('season_number') or ''}, is_folder=True)
    _end_directory()


def _get_series_season_episodes(api, series_id, season_id=None, episodes_url=None, limit=400):
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance for faster episode loading
    try:
        api = api or get_api_instance()
    except Exception:
        api = NLZietAPI(username=username, password=password)
    xbmc.log(f"NLZiet show_series_season: series_id={series_id} season_id={season_id}", xbmc.LOGDEBUG)
    episodes = api.get_series_episodes(series_id, season_id=season_id or None, limit=limit)
    # If the API returned no episodes, but the `season_id` appears to be
    # an items/episodes URL, attempt to fetch items directly from that URL
    # (some detail payloads expose an `episodes_url` instead of numeric ids).
    fallback_url = episodes_url or season_id
    if not episodes and fallback_url and isinstance(fallback_url, str) and (fallback_url.startswith('http') or '/episodes' in fallback_url or 'items' in fallback_url):
        try:
            xbmc.log(f"NLZiet attempting fallback get_items_from_url for season_id={season_id}", xbmc.LOGDEBUG)
            episodes = api.get_items_from_url(fallback_url) or []
        except Exception:
            episodes = []
    return episodes or []


def show_series_season(series_id, season_id, episodes_url=None, series_title=None, season_number=None):
    if not series_id:
        xbmcgui.Dialog().notification('NLZiet', get_string('missing_series_id'), xbmcgui.NOTIFICATION_ERROR)
        return
    episodes = _get_series_season_episodes(None, series_id, season_id, episodes_url)
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
                    date_info = f"Uitgezonden: {date_formatted}"
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
        sub = ''
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

        playback_content = dict(ep)
        playback_content.setdefault('type', 'Episode')
        if series_title:
            playback_content.setdefault('series_title', series_title)
        if playback_content.get('season_number') is None and season_number not in (None, ''):
            playback_content['season_number'] = season_number
        if playback_content.get('season_number') is None and str(season_id or '').isdigit():
            playback_content['season_number'] = season_id
        add_directory_item(label, {'mode': 'play', 'id': ep.get('id')}, is_folder=False, thumb=_pick_landscape_thumb(ep), info=info, content=playback_content)
    _end_directory()


def _write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def _library_episode_fetcher(api, series_id, detail):
    """Return all episodes of a series (all seasons) for the library."""
    episodes = []
    seasons = (detail or {}).get('seasons') or []
    if seasons:
        for season_info in seasons:
            episodes.extend(_get_series_season_episodes(
                api,
                series_id,
                season_info.get('id'),
                season_info.get('episodes_url'),
                limit=1000,
            ))
    else:
        episodes = api.get_series_episodes(series_id, limit=1000) or []
    seen = set()
    unique = []
    for ep in episodes:
        key = str(ep.get('id') or '')
        if key and key not in seen:
            seen.add(key)
            unique.append(ep)
    return unique


_LIBRARY = None


def _library_enricher():
    """Metadata helper that fills gaps from TMDb/TVmaze, or None when turned off."""
    if not _setting_on('library_enrich', True):
        return None
    try:
        profile = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    except Exception:
        profile = ''
    language = 'nl-NL'
    try:
        if not str(xbmc.getLanguage(xbmc.ISO_639_1) or 'nl').lower().startswith('nl'):
            language = 'en-US'
    except Exception:
        pass
    return metadata_mod.Enricher(
        os.path.join(profile or '', 'metadata_cache.json'),
        tmdb_key=ADDON.getSetting('tmdb_api_key') or '',
        language=language,
        user_agent='plugin.video.nlziet',
    )


def _get_library():
    global _LIBRARY
    if _LIBRARY is None:
        _LIBRARY = library_mod.Library(
            get_api_instance(), ADDON, _library_episode_fetcher,
            enricher=_library_enricher(),
            downloader=lambda url: library_art.http_download(url, 'plugin.video.nlziet'),
            art_picker=lambda item: (kodi_ui.pick_portrait_thumb(item), kodi_ui.pick_landscape_thumb(item)),
        )
        try:
            moved = _LIBRARY.migrate_legacy_folder()
        except Exception as e:
            xbmc.log(f"NLZiet library folder move failed: {e}", xbmc.LOGWARNING)
            moved = 0
        if moved:
            xbmcgui.Dialog().notification('NLZiet', get_string('library_moved', moved), xbmcgui.NOTIFICATION_INFO, 8000)
            library_mod.run_library_jobs(scan=True, clean=True)
    return _LIBRARY


def _library_kind(kind):
    return 'series' if str(kind or '').lower() in ('series', 'tvshow', 'show') else 'movie'


def is_in_library(kind, item_id):
    try:
        return _get_library().is_in_library(_library_kind(kind), item_id)
    except Exception:
        return False


def _after_library_change(scan=True, clean=False):
    if _setting_on('library_scan_after', True) and scan:
        library_mod.run_library_jobs(scan=True, clean=clean and _setting_on('library_clean_after', True))
    elif clean and _setting_on('library_clean_after', True):
        library_mod.run_library_jobs(scan=False, clean=True)


def library_add(kind, item_id, title=None, poster=None, fanart=None):
    kind = _library_kind(kind)
    if not item_id:
        xbmcgui.Dialog().notification('NLZiet', get_string('missing_series_id'), xbmcgui.NOTIFICATION_ERROR)
        return
    lib = _get_library()
    progress = xbmcgui.DialogProgressBG() if hasattr(xbmcgui, 'DialogProgressBG') else None
    try:
        if progress is not None:
            progress.create('NLZiet', get_string('library_adding', title or ''))
        if kind == 'series':
            result = lib.add_series(item_id, title=title, poster=poster, fanart=fanart)
        else:
            result = lib.add_movie(item_id, title=title, poster=poster, fanart=fanart)
        if not result.get('ok'):
            if result.get('reason') == 'no_episodes':
                xbmcgui.Dialog().notification('NLZiet', get_string('no_episodes_found'), xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification('NLZiet', get_string('library_export_failed'), xbmcgui.NOTIFICATION_ERROR)
            return
        lib.store.save()
        if kind == 'series':
            message = get_string('library_exported', result.get('total', 0))
        else:
            message = get_string('library_movie_added', result.get('title') or title or '')
        xbmcgui.Dialog().notification('NLZiet', message, xbmcgui.NOTIFICATION_INFO)
        _after_library_change(scan=True)
    except Exception as e:
        xbmc.log(f"NLZiet library add failed for {kind}={item_id}: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('NLZiet', get_string('library_export_failed'), xbmcgui.NOTIFICATION_ERROR)
    finally:
        if progress is not None:
            try:
                progress.close()
            except Exception:
                pass


def library_remove(kind, item_id, title=None):
    kind = _library_kind(kind)
    try:
        removed = _get_library().remove(kind, item_id)
    except Exception as e:
        xbmc.log(f"NLZiet library remove failed for {kind}={item_id}: {e}", xbmc.LOGERROR)
        removed = False
    if removed:
        xbmcgui.Dialog().notification('NLZiet', get_string('library_removed', title or ''), xbmcgui.NOTIFICATION_INFO)
        _after_library_change(scan=False, clean=True)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('NLZiet', get_string('library_not_found'), xbmcgui.NOTIFICATION_INFO)


def library_toggle(kind, item_id, title=None, poster=None, fanart=None):
    if is_in_library(kind, item_id):
        library_remove(kind, item_id, title)
    else:
        library_add(kind, item_id, title, poster, fanart)
        xbmc.executebuiltin('Container.Refresh')


def repair_library_art(background=True):
    """Give library titles Kodi already scanned their missing posters."""
    try:
        fixed = library_art.repair_kodi_art(_get_library(), marker='plugin.video.nlziet/library')
    except Exception as e:
        xbmc.log(f"NLZiet library art repair failed: {e}", xbmc.LOGWARNING)
        fixed = 0
    if fixed:
        xbmc.log(f"NLZiet library: artwork set for {fixed} titles", xbmc.LOGINFO)
    if not background:
        xbmcgui.Dialog().notification('NLZiet', get_string('library_art_fixed', fixed), xbmcgui.NOTIFICATION_INFO)
    return fixed


def export_series_library(series_id):
    """Old route name, kept for existing favourites and skins."""
    library_add('series', series_id)


def _list_library_titles(api):
    """Series and films from My Series and Watch Later as
    [(kind, id, title, poster)]; an episode in Watch Later adds its series."""
    titles, seen = [], set()

    def add(kind, item_id, title, poster):
        key = (kind, str(item_id or ''))
        if key[1] and key not in seen:
            seen.add(key)
            titles.append((kind, key[1], title or '', poster or ''))

    for item in api.get_my_series() or []:
        if isinstance(item, dict):
            add('series', item.get('id'), _item_title(item), item.get('thumb') or kodi_ui.pick_portrait_thumb(item))
    for item in api.get_watch_later() or []:
        if not isinstance(item, dict):
            continue
        group = _content_group(item)
        if group == 'movies':
            add('movie', item.get('id'), _item_title(item), item.get('thumb') or kodi_ui.pick_portrait_thumb(item))
        elif group in ('episodes', 'series'):
            raw = item.get('raw') if isinstance(item.get('raw'), dict) else {}
            collection = item.get('collection') if isinstance(item.get('collection'), dict) else {}
            series_id = (item.get('seriesId') or raw.get('seriesId') or collection.get('id')
                         or (item.get('id') if group == 'series' else None))
            if not series_id:
                try:
                    series_id = _find_series_id_by_title(api, _item_title(item))
                except Exception:
                    series_id = None
            add('series', series_id, _item_title(item), '')
    return titles


def sync_lists_to_library(lib, api=None, progress=None):
    """Add My Series and Watch Later titles that are not in the library yet;
    optionally remove titles that came from these lists and left them.
    Returns (added, removed, failed)."""
    api = api or get_api_instance()
    titles = _list_library_titles(api)
    added = removed = failed = 0
    wanted = set()
    for index, (kind, item_id, title, poster) in enumerate(titles):
        wanted.add((kind, item_id))
        if lib.is_in_library(kind, item_id):
            continue
        if progress is not None:
            progress(index, len(titles), title)
        try:
            if kind == 'series':
                result = lib.add_series(item_id, title=title, poster=poster or None)
            else:
                result = lib.add_movie(item_id, title=title, poster=poster or None)
        except Exception as e:
            xbmc.log(f"NLZiet list title {item_id} not added: {e}", xbmc.LOGWARNING)
            result = {}
        if result.get('ok'):
            entry = lib.store.get(kind, item_id)
            if entry is not None:
                entry['source'] = 'lists'
            added += 1
        else:
            failed += 1
    if _setting_on('library_lists_remove', False) and titles:
        for kind in ('series', 'movie'):
            for item_id, entry in list(lib.items(kind)):
                if entry.get('source') == 'lists' and (kind, item_id) not in wanted:
                    if lib.remove(kind, item_id, save=False):
                        removed += 1
    lib.store.save()
    return added, removed, failed


def library_from_lists(background=False):
    """Menu/settings action: put My Series and Watch Later in the Kodi library."""
    if background and xbmc.Player().isPlaying():
        return
    lib = _get_library()
    dialog = None
    if not background and hasattr(xbmcgui, 'DialogProgressBG'):
        dialog = xbmcgui.DialogProgressBG()
        dialog.create('NLZiet', get_string('library_lists_busy'))

    def report(index, total, title):
        if dialog is not None and total:
            dialog.update(int(index * 100 / total), 'NLZiet', title)

    try:
        added, removed, failed = sync_lists_to_library(lib, progress=report)
    finally:
        if dialog is not None:
            dialog.close()
    if added or removed:
        library_mod.run_library_jobs(scan=True, clean=bool(removed) and _setting_on('library_clean_after', True))
    if not background or (added or removed):
        xbmcgui.Dialog().notification('NLZiet', get_string('library_lists_done', added, removed, failed),
                                      xbmcgui.NOTIFICATION_INFO)
    if not background:
        xbmc.executebuiltin('Container.Refresh')


def library_update(background=False):
    """Refresh every series and movie in the library."""
    if background and xbmc.Player().isPlaying():
        return
    lib = _get_library()
    if _setting_on('library_lists_sync', False):
        try:
            sync_lists_to_library(lib)
        except Exception as e:
            xbmc.log(f"NLZiet list sync skipped: {e}", xbmc.LOGWARNING)
    progress = None
    if not background and hasattr(xbmcgui, 'DialogProgressBG'):
        progress = xbmcgui.DialogProgressBG()
        progress.create('NLZiet', get_string('library_updating'))

    def _progress(index, total, kind, item_id):
        if progress is not None and total:
            entry = lib.store.get(kind, item_id) or {}
            progress.update(int(index * 100 / total), 'NLZiet', entry.get('title') or str(item_id))
        return True

    try:
        totals = lib.update_all(progress=_progress)
    except Exception as e:
        xbmc.log(f"NLZiet library update failed: {e}", xbmc.LOGERROR)
        if not background:
            xbmcgui.Dialog().notification('NLZiet', get_string('library_update_failed'), xbmcgui.NOTIFICATION_ERROR)
        return
    finally:
        if progress is not None:
            try:
                progress.close()
            except Exception:
                pass
    changed = bool(totals.get('added') or totals.get('removed'))
    if changed or not background:
        # A manual update always scans, so titles a busy Kodi skipped get in too.
        library_mod.run_library_jobs(scan=True, clean=bool(totals.get('removed')) and _setting_on('library_clean_after', True))
    repair_library_art()
    if not background or (changed and _setting_on('background_sync_notify', True)):
        xbmcgui.Dialog().notification(
            'NLZiet',
            get_string('library_update_done', totals.get('added', 0), totals.get('removed', 0)),
            xbmcgui.NOTIFICATION_INFO,
        )


def check_tmdb_key():
    """Settings button: test the saved TMDb key and say exactly what is wrong."""
    status, detail = metadata_mod.test_tmdb_key(ADDON.getSetting('tmdb_api_key'))
    if detail:
        xbmc.log(f"NLZiet TMDb key test: {status} ({detail})", xbmc.LOGINFO)
    messages = {
        'ok': 'tmdb_check_ok',
        'missing': 'tmdb_check_missing',
        'invalid': 'tmdb_check_failed',
        'offline': 'tmdb_check_offline',
    }
    xbmcgui.Dialog().ok('NLZiet', get_string(messages[status]))


def choose_tmdb(kind, item_id):
    """Library menu: pick the right TMDb series/film for a title by hand."""
    kind = _library_kind(kind)
    lib = _get_library()
    entry = lib.store.get(kind, item_id)
    enricher = _library_enricher()
    if entry is None:
        return
    if enricher is None or not enricher.tmdb_key:
        xbmcgui.Dialog().ok('NLZiet', get_string('tmdb_check_missing'))
        return
    query = entry.get('title') or ''
    while True:
        found = enricher.search_candidates(kind, query)
        labels = [get_string('choose_tmdb_other')] + [
            '{} ({})'.format(name, year) if year else name for _id, name, year in found]
        picked = xbmcgui.Dialog().select(get_string('choose_tmdb'), labels)
        if picked < 0:
            return
        if picked == 0:
            query = xbmcgui.Dialog().input(get_string('choose_tmdb_other'), query)
            if not query:
                return
            continue
        tmdb_id = found[picked - 1][0]
        break
    entry['ids'] = {'tmdb': str(tmdb_id)}  # other ids are looked up again from TMDb
    lib.store.section(kind)[str(item_id)] = entry
    if kind == 'series':
        lib.add_series(item_id, title=entry.get('title'))
    else:
        lib.add_movie(item_id, title=entry.get('title'))
    lib.store.save()
    repair_library_art()
    xbmcgui.Dialog().notification('NLZiet', get_string('choose_tmdb_done'), xbmcgui.NOTIFICATION_INFO)
    xbmc.executebuiltin('Container.Refresh')


def browse_library():
    """List everything that is in the Kodi library."""
    lib = _get_library()
    add_directory_item(get_string('library_update_now'), {'mode': 'library_update'}, is_folder=False, is_playable=False)
    add_directory_item(get_string('library_lists_now'), {'mode': 'library_from_lists'}, is_folder=False, is_playable=False,
                       thumb=_pick_menu_png_any('myseries'))
    series = lib.items('series')
    movies = lib.items('movie')
    for sid, entry in series:
        title = entry.get('title') or sid
        label = '{} [COLOR grey]({})[/COLOR]'.format(title, get_string('series'))
        remove = [(get_string('shuffle_episode'), 'RunPlugin({})'.format(
            build_url({'mode': 'shuffle', 'series_id': sid}))),
                  (get_string('remove_from_library'), 'RunPlugin({})'.format(
            build_url({'mode': 'library_remove', 'kind': 'series', 'id': sid, 'title': title}))),
                  (get_string('choose_tmdb'), 'RunPlugin({})'.format(
            build_url({'mode': 'choose_tmdb', 'kind': 'series', 'id': sid})))]
        kodi_ui.add_directory_item(
            ADDON, HANDLE, build_url, get_api_instance, label,
            {'mode': 'series_detail', 'series_id': sid}, is_folder=True, thumb=entry.get('thumb'),
            extra_context_items=remove, library_check=None,
            extra_art={'clearlogo': entry['clearlogo']} if entry.get('clearlogo') else None,
        )
    for mid, entry in movies:
        title = entry.get('title') or mid
        label = '{} [COLOR grey]({})[/COLOR]'.format(title, get_string('movies'))
        remove = [(get_string('remove_from_library'), 'RunPlugin({})'.format(
            build_url({'mode': 'library_remove', 'kind': 'movie', 'id': mid, 'title': title}))),
                  (get_string('choose_tmdb'), 'RunPlugin({})'.format(
            build_url({'mode': 'choose_tmdb', 'kind': 'movie', 'id': mid})))]
        kodi_ui.add_directory_item(
            ADDON, HANDLE, build_url, get_api_instance, label,
            {'mode': 'play', 'id': mid}, is_folder=False, thumb=entry.get('thumb'),
            extra_context_items=remove, library_check=None,
            extra_art={'clearlogo': entry['clearlogo']} if entry.get('clearlogo') else None,
        )
    if not series and not movies:
        xbmcgui.Dialog().notification('NLZiet', get_string('library_empty'), xbmcgui.NOTIFICATION_INFO)
    _end_directory()


def browse_tv_shows():
    """Show TV show categories/genres for browsing."""
    api = get_api_instance()
    
    genres = api.get_tv_show_genres()
    for genre in genres:
        query = {'mode': 'browse_tv_genre', 'genre': genre.get('genre') or 'all'}
        add_directory_item(genre.get('name'), query, is_folder=True)
    _end_directory()


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
                    date_info = f"Uitgezonden: {date_formatted}"
                except Exception:
                    date_info = ''
            
            # Build full plot with date info
            parts = []
            if date_info:
                parts.append(date_info)
            if expiry_text:
                marker = ''  # text only: readable by screen readers and every skin
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
                marker = ''  # text only: readable by screen readers and every skin
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
        
        add_directory_item(display_title, query, is_folder=is_folder, thumb=_pick_landscape_thumb(item), info=info, content=item, group='tvshows')
    _end_directory()


def browse_movie_categories():
    """Display movie category/genre list."""
    api = get_api_instance()

    genres = api.get_movie_genres()
    for genre in genres:
        name = genre.get('name')
        genre_param = genre.get('genre')
        add_directory_item(name, {'mode': 'browse_movie_genre', 'genre': genre_param or 'all'}, is_folder=True)
    _end_directory()


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
                    marker = ''  # text only: readable by screen readers and every skin
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
        add_directory_item(item.get('title'), {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=_pick_landscape_thumb(item), info=info, content=item, group='movies')
    
    _end_directory()


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
                    marker = ''  # text only: readable by screen readers and every skin
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
    _end_directory()


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


def _extract_subscription_type(summary):
    """Try to parse subscription type from API summary payload."""
    if not summary:
        return ''

    if isinstance(summary, dict):
        sub = summary.get('subscription') or summary.get('plan') or summary.get('product') or {}
        if isinstance(sub, dict):
            for key in ('subscriptionType', 'planType', 'productType', 'tier', 'type'):
                value = sub.get(key)
                if value is not None and str(value).strip():
                    return str(value)

        for key in ('subscription_type', 'subscriptionType', 'planType', 'productType'):
            value = summary.get(key)
            if value is not None and str(value).strip():
                return str(value)

    def _find(data, in_subscription_context=False):
        if isinstance(data, dict):
            keys = {str(k).lower() for k in data.keys()}
            ctx = in_subscription_context or bool(keys & {'subscription', 'plan', 'product', 'subscriptiontype', 'plantype', 'producttype'})

            for key in ('subscriptionType', 'planType', 'productType', 'tier', 'type'):
                if key in data:
                    value = data.get(key)
                    if value is not None and str(value).strip():
                        if key != 'type' or ctx:
                            return str(value)

            for k, v in data.items():
                next_ctx = ctx or str(k).lower() in {'subscription', 'plan', 'product'}
                result = _find(v, next_ctx)
                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = _find(item, in_subscription_context)
                if result:
                    return result

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
    subscription_type = _extract_subscription_type(summary) or ''
    max_devices = _extract_max_devices(summary) or ''
    subscription_expires = _extract_subscription_expiry(summary) or ''

    try:
        ADDON.setSetting('subscription_name', subscription)
        ADDON.setSetting('subscription_type', subscription_type)
        ADDON.setSetting('max_devices', max_devices)
        ADDON.setSetting('subscription_expires', subscription_expires)
    except Exception:
        pass

    display_values = []
    if subscription:
        display_values.append(f"{get_string('subscription_label')}: {subscription}")
    if subscription_type:
        display_values.append(f"{get_string('subscription_type_label')}: {subscription_type}")
    if max_devices:
        display_values.append(f"{get_string('max_devices_label')}: {max_devices}")
    if subscription_expires:
        display_values.append(f"{get_string('expires_label')}: {subscription_expires}")

    if notify:
        if display_values:
            xbmcgui.Dialog().ok('NLZiet', (get_string('account_updated') or 'Account updated') + '\n' + '\n'.join(display_values))
        else:
            xbmcgui.Dialog().ok('NLZiet', get_string('account_parse_error') or 'Account info could not be parsed')
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
        for key in ('profile_id', 'profile_name', 'subscription_name', 'subscription_type', 'subscription_expires', 'max_devices', 'username', 'password', 'save_credentials', 'access_token', 'refresh_token', 'token_expires_at'):
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


def _redact_diagnostic_text(text):
    """Remove credentials, tokens, cookies, email addresses and signed URL data."""
    text = str(text or '')
    text = re.sub(r'(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,}\]]+', r'\1<redacted>', text)
    text = re.sub(
        r'(?i)(password|access_token|refresh_token|id_token|code_verifier|cookie|set-cookie)'
        r'(["\'\s]*[:=]["\'\s]*)([^\s,}\]]+)',
        r'\1\2<redacted>', text,
    )
    text = re.sub(r'(?i)([?&](?:token|sig|signature|code|key)=)[^&\s]+', r'\1<redacted>', text)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '<redacted-email>', text)
    text = re.sub(r'\beyJ[A-Za-z0-9_-]{20,}(?:\.[A-Za-z0-9_-]+){1,2}\b', '<redacted-jwt>', text)
    return text


def _safe_debug_excerpt(lines):
    """Keep only request markers, URL paths and statuses from the HTTP log."""
    safe_lines = []
    for raw_line in lines:
        line = str(raw_line).strip()
        if line.startswith('--- HTTP '):
            safe_lines.append(line)
        elif line.startswith('Status:'):
            safe_lines.append(line)
        elif line.startswith('URL:'):
            try:
                parsed = urllib.parse.urlsplit(line[4:].strip())
                safe_lines.append(f'URL: {parsed.scheme}://{parsed.netloc}{parsed.path}')
            except Exception:
                safe_lines.append('URL: <unavailable>')
    return safe_lines[-250:]


def export_diagnostics():
    """Write a privacy-safe support report without credentials or account data."""
    try:
        api = get_api_instance()
        profile_dir = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
        report_dir = os.path.join(profile_dir, 'diagnostics')
        os.makedirs(report_dir, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        report_path = os.path.join(report_dir, f'nlziet-diagnostics-{stamp}.txt')
        tokens = getattr(api, 'tokens', {}) or {}
        lines = [
            'NLZiet diagnostics',
            f"Generated: {datetime.now().astimezone().isoformat()}",
            f"Addon version: {ADDON.getAddonInfo('version') or 'unknown'}",
            f"Kodi version: {xbmc.getInfoLabel('System.BuildVersion') or 'unknown'}",
            f"Python: {platform.python_version()}",
            f"Platform: {sys.platform}",
            f"Authenticated: {bool(getattr(api, 'token', None))}",
            f"Access token present: {bool(tokens.get('access_token'))}",
            f"Refresh token present: {bool(tokens.get('refresh_token'))}",
            f"Token expiry: {tokens.get('expires_at') or 'unknown'}",
            f"Profile selected: {bool(ADDON.getSetting('profile_id'))}",
            f"HTTP debugging enabled: {str(ADDON.getSetting('debug_http')).lower() in ('true', '1', 'yes')}",
            '', 'Recent HTTP debug output (sanitized):',
        ]
        debug_path = getattr(api, 'debug_file', '')
        if debug_path and os.path.exists(debug_path):
            with open(debug_path, 'r', encoding='utf-8', errors='replace') as debug_file:
                lines.extend(_safe_debug_excerpt(debug_file.readlines()))
        else:
            lines.append('<no HTTP debug log available>')
        report = _redact_diagnostic_text('\n'.join(line.rstrip('\n') for line in lines)) + '\n'
        _write_text(report_path, report)
        xbmcgui.Dialog().ok('NLZiet', get_string('diagnostics_exported', report_path))
    except Exception as exc:
        xbmc.log(f'NLZiet diagnostics export failed: {exc}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('NLZiet', get_string('diagnostics_failed'), xbmcgui.NOTIFICATION_ERROR)


def _collect_diagnostics(t):
    """All diagnostic checks (used by the settings button and the daily check)."""
    try:
        api = get_api_instance()
        base_url = getattr(api, 'base_url', '') or 'https://api.nlziet.nl/'
    except Exception:
        base_url = 'https://api.nlziet.nl/'
    endpoints = [('NLZiet', base_url), ('TMDb', 'https://api.themoviedb.org/3/'),
                 ('TVmaze', 'https://api.tvmaze.com/')]
    tmdb_status = None
    if _setting_on('library_enrich', True):
        tmdb_status = metadata_mod.test_tmdb_key(ADDON.getSetting('tmdb_api_key'))[0]
    try:
        lib = _get_library()
    except Exception:
        lib = None
    return diagnostics_mod.run_checks(
        t, ADDON.getAddonInfo('version'), _is_logged_in(), endpoints, library=lib,
        library_special=(library_mod.DEFAULT_TV_PATH, library_mod.DEFAULT_MOVIES_PATH),
        tmdb_status=tmdb_status,
        kodi_counts=library_art.kodi_counts(lib, 'plugin.video.nlziet/library') if lib else None)


def run_diagnostics():
    """Settings button: check everything playback and the library need."""
    try:
        language = xbmc.getLanguage(xbmc.ISO_639_1) or 'nl'
    except Exception:
        language = 'nl'
    t = diagnostics_mod.texts(language)
    progress = xbmcgui.DialogProgress()
    progress.create('NLZiet', t['title'] + '...')
    try:
        checks = _collect_diagnostics(t)
        text = diagnostics_mod.render(t, checks)
        folder = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'diagnostics')
        log_lines = diagnostics_mod.kodi_log_excerpt(['nlziet'], _redact_diagnostic_text)
        path = diagnostics_mod.save_report(folder, 'nlziet', _redact_diagnostic_text(text), log_lines)
        text = diagnostics_mod.render(t, checks, path)
    finally:
        progress.close()
    xbmcgui.Dialog().textviewer('NLZiet - ' + t['title'], text)


def clear_subtitle_cache():
    """Remove cached, cleaned subtitle files from the addon profile."""
    try:
        from resources.lib import subtitles as subtitle_tools

        cache_dir = xbmcvfs.translatePath(
            'special://profile/addon_data/{0}/subtitle_cache'.format(ADDON.getAddonInfo('id'))
        )
        removed = subtitle_tools.clear_cache(cache_dir)
        xbmcgui.Dialog().notification(
            'NLZiet',
            get_string('subtitle_cache_cleared', removed),
            xbmcgui.NOTIFICATION_INFO,
        )
    except Exception as exc:
        xbmc.log('NLZiet: subtitle cache clearing failed: {0}'.format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            'NLZiet',
            get_string('subtitle_cache_clear_failed'),
            xbmcgui.NOTIFICATION_ERROR,
        )


_AUTO_CLEAR_SUBTITLE_CACHE_KEYS = (
    'auto_clear_subtitle_cache',
    'subtitle_cache_auto_clear',
    'auto_clear_subtitle_cache_enabled',
    'clear_subtitle_cache_auto',
    'clear_subtitle_cache_automatically',
    'subtitle_cache_clear_auto',
    'auto_clear_subtitles_cache',
)

_SUBTITLE_CACHE_CLEAR_HOURS_KEYS = (
    'auto_clear_subtitle_cache_hours',
    'subtitle_cache_clear_hours',
    'subtitle_cache_auto_clear_hours',
    'clear_subtitle_cache_hours',
    'auto_clear_subtitle_cache_interval',
    'subtitle_cache_clear_interval',
    'subtitle_cache_auto_clear_interval',
    'subtitle_cache_clear_interval_hours',
)


def _subtitle_cache_dir():
    return xbmcvfs.translatePath(
        'special://profile/addon_data/{0}/subtitle_cache'.format(ADDON.getAddonInfo('id'))
    )


def _auto_clear_subtitle_cache_enabled():
    for key in _AUTO_CLEAR_SUBTITLE_CACHE_KEYS:
        try:
            value = ADDON.getSetting(key)
        except Exception:
            value = ''
        if value in ('', None):
            continue
        return value in ('true', '1', 'yes', True)
    return False


def _subtitle_cache_clear_hours():
    for key in _SUBTITLE_CACHE_CLEAR_HOURS_KEYS:
        try:
            raw = ADDON.getSetting(key)
        except Exception:
            raw = ''
        if raw in ('', None):
            continue
        try:
            return max(1, int(float(raw)))
        except (TypeError, ValueError):
            continue
    return 24


def _subtitle_cache_clear_marker():
    return os.path.join(_subtitle_cache_dir(), '.last_auto_clear')


def _subtitle_cache_auto_clear_due(hours=None):
    if hours is None:
        hours = _subtitle_cache_clear_hours()
    try:
        with open(_subtitle_cache_clear_marker(), 'r', encoding='utf-8') as handle:
            last = float(handle.read().strip() or 0)
    except Exception:
        last = 0
    return time.time() - last >= max(1, int(hours or 24)) * 3600


def _run_clear_subtitle_cache():
    """Remove all cached subtitle files and record the run."""
    from resources.lib import subtitles as subtitle_tools

    cache_dir = _subtitle_cache_dir()
    removed = subtitle_tools.clear_cache(cache_dir)
    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(_subtitle_cache_clear_marker(), 'w', encoding='utf-8') as handle:
            handle.write(str(time.time()))
    except Exception:
        pass
    return removed


def _maybe_clear_subtitle_cache():
    if not _auto_clear_subtitle_cache_enabled():
        return
    try:
        if not _subtitle_cache_auto_clear_due():
            return
        _run_clear_subtitle_cache()
    except Exception as exc:
        xbmc.log('NLZiet: auto subtitle cache clearing failed: {0}'.format(exc), xbmc.LOGWARNING)


_CACHE_FILES = ('epg_cache.json', 'tvmaze_cache.json', 'episode_numbering_cache.json')
_CACHE_MARKER = '.last_cache_auto_clear'


def _addon_profile_dir():
    return xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))


def _run_clear_all_cache():
    """Remove the EPG, TVmaze, episode and subtitle caches and record the run."""
    from resources.lib import subtitles as subtitle_tools

    profile_dir = _addon_profile_dir()
    removed = 0
    for name in _CACHE_FILES:
        path = os.path.join(profile_dir, name)
        if os.path.exists(path):
            try:
                os.remove(path)
                removed += 1
            except OSError as exc:
                xbmc.log('NLZiet: could not remove {0}: {1}'.format(name, exc), xbmc.LOGWARNING)
    removed += subtitle_tools.clear_cache(_subtitle_cache_dir())
    try:
        with open(os.path.join(profile_dir, _CACHE_MARKER), 'w', encoding='utf-8') as handle:
            handle.write(str(time.time()))
    except Exception:
        pass
    return removed


def clear_all_cache():
    """Remove all addon caches and tell the user how many files were removed."""
    try:
        removed = _run_clear_all_cache()
        xbmcgui.Dialog().notification(
            'NLZiet',
            get_string('all_cache_cleared', removed),
            xbmcgui.NOTIFICATION_INFO,
        )
    except Exception as exc:
        xbmc.log('NLZiet: clearing all cache failed: {0}'.format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            'NLZiet',
            get_string('all_cache_clear_failed'),
            xbmcgui.NOTIFICATION_ERROR,
        )


def _auto_clear_all_cache_due():
    try:
        hours = max(1, int(float(ADDON.getSetting('auto_clear_all_cache_hours') or 24)))
    except (TypeError, ValueError):
        hours = 24
    try:
        with open(os.path.join(_addon_profile_dir(), _CACHE_MARKER), 'r', encoding='utf-8') as handle:
            last = float(handle.read().strip() or 0)
    except Exception:
        last = 0
    return time.time() - last >= hours * 3600


def _maybe_clear_all_cache():
    if ADDON.getSetting('auto_clear_all_cache') != 'true':
        return
    try:
        if _auto_clear_all_cache_due():
            _run_clear_all_cache()
    except Exception as exc:
        xbmc.log('NLZiet: auto cache clearing failed: {0}'.format(exc), xbmc.LOGWARNING)


# Aliases for compatibility with possible test/function names.
_auto_clear_subtitle_cache = _maybe_clear_subtitle_cache
_maybe_run_clear_subtitle_cache = _maybe_clear_subtitle_cache
_maybe_run_subtitle_cache_clear = _maybe_clear_subtitle_cache
_maybe_auto_clear_subtitle_cache = _maybe_clear_subtitle_cache
_maybe_clear_subtitle_cache_auto = _maybe_clear_subtitle_cache
_run_subtitle_cache_clear = _run_clear_subtitle_cache
_run_auto_clear_subtitle_cache = _run_clear_subtitle_cache
_clear_subtitle_cache_if_due = _maybe_clear_subtitle_cache
_auto_clear_subtitle_cache_enabled_alias = _auto_clear_subtitle_cache_enabled
_subtitle_cache_auto_clear_enabled = _auto_clear_subtitle_cache_enabled
_auto_clear_subtitle_cache_hours = _subtitle_cache_clear_hours
_subtitle_cache_auto_clear_hours = _subtitle_cache_clear_hours
_subtitle_cache_clear_due = _subtitle_cache_auto_clear_due
_auto_clear_subtitle_cache_due = _subtitle_cache_auto_clear_due


def show_login_dialog(preset_email='', preset_password=''):
    """Show login dialog to get email and password from user.
    
    Args:
        preset_email: optional pre-filled email address
        preset_password: optional pre-filled password
    
    Returns:
        Tuple of (email, password) or (None, None) if cancelled
    """
    dialog = xbmcgui.Dialog()
    
    # Get email from user (pre-filled if provided)
    # dialog.input(heading, defaultText='', type=0)
    email = dialog.input(get_string('login_dialog_email'), preset_email, type=0)
    if not email:
        return None, None
    
    # Get password from user (pre-filled if provided)
    password = dialog.input(
        get_string('login_dialog_password'),
        preset_password,
        type=xbmcgui.INPUT_ALPHANUM,
        option=xbmcgui.ALPHANUM_HIDE_INPUT,
    )
    if not password:
        return None, None
    
    return email, password


def do_login():
    """Handle login via dialog or saved credentials with retry support."""
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
    
    # Attempt login with provided credentials (with retry loop)
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        try:
            xbmc.log(f"NLZiet: attempting login (attempt {attempt}/{max_attempts}) for {email}", xbmc.LOGINFO)
            api = NLZietAPI(username=email, password=password)
            ok = api.login()
            
            if ok:
                xbmc.log(f"NLZiet: login successful for {email}", xbmc.LOGINFO)
                # attempt PKCE authorize + token exchange (uses the saved cookie session)
                tokens = api.perform_pkce_authorize_and_exchange()
                if tokens:
                    try:
                        api._append_debug(
                            "LOGIN FLOW: PKCE returned tokens access={} refresh={}".format(
                                bool((tokens or {}).get('access_token')),
                                bool((tokens or {}).get('refresh_token')),
                            )
                        )
                        api._debug_auth_state('default_do_login_tokens_received')
                    except Exception:
                        pass

                    try:
                        if isinstance(tokens, dict):
                            api.tokens.update(tokens)
                        if api.tokens.get('access_token'):
                            api.token = api.tokens.get('access_token')
                            api.save_tokens()
                    except Exception:
                        pass

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
                    try:
                        api._append_debug('LOGIN FLOW: form login succeeded but PKCE/token exchange returned no tokens')
                        api._debug_auth_state('default_do_login_no_tokens')
                    except Exception:
                        pass
                    xbmcgui.Dialog().notification('NLZiet', get_string('login_successful_no_tokens'), xbmcgui.NOTIFICATION_INFO)

                # Keep runtime state consistent: startup may have cached an unauthenticated
                # API instance. Replace it with this authenticated one immediately.
                try:
                    set_api_instance(api)
                    try:
                        api._append_debug('LOGIN FLOW: cached API instance replaced with authenticated instance')
                    except Exception:
                        pass
                except Exception:
                    pass

                try:
                    # Avoid showing a confusing parse-error popup directly after login
                    # when account summary fields are temporarily unavailable.
                    refresh_account_info(notify=False)
                except Exception:
                    pass

                # Refresh main menu so authenticated entries are shown right away.
                try:
                    main_url = build_url({})
                    xbmc.executebuiltin('Container.Update(%s,replace)' % main_url)
                except Exception:
                    pass
                return
            else:
                # Login failed - offer to retry
                xbmc.log(f"NLZiet: login failed for {email} (attempt {attempt}/{max_attempts})", xbmc.LOGINFO)
                
                # If we have more attempts, ask user if they want to retry
                if attempt < max_attempts:
                    retry_msg = f"{get_string('login_invalid_credentials')}\n\n{get_string('login_try_again')}"
                    
                    if xbmcgui.Dialog().yesno('NLZiet', retry_msg):
                        # Show login dialog again with email/password pre-filled
                        new_email, new_password = show_login_dialog(email, password)
                        if new_email and new_password:
                            email = new_email
                            password = new_password
                            # Loop will continue to next attempt
                        else:
                            # User cancelled
                            return
                    else:
                        # User doesn't want to retry
                        return
                else:
                    # Max attempts reached
                    xbmcgui.Dialog().notification('NLZiet', get_string('login_failed_max_attempts'), xbmcgui.NOTIFICATION_ERROR)
                    return
        
        except Exception as e:
            xbmc.log(f"NLZiet: login exception (attempt {attempt}/{max_attempts}): {e}", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification('NLZiet', get_string('login_error', str(e)[:50]), xbmcgui.NOTIFICATION_ERROR)
            return


def _parental():
    try:
        window = xbmcgui.Window(10000)
    except Exception:
        window = None
    return parental_mod.Parental(ADDON, window)


def _ask_pin(heading_key='parental_enter_pin'):
    try:
        return xbmcgui.Dialog().numeric(0, get_string(heading_key), '', True)
    except TypeError:
        return xbmcgui.Dialog().numeric(0, get_string(heading_key))


def _pin_ok(profile_id=None, live=False):
    """Ask for the parental PIN when this action needs it."""
    guard = _parental()
    if not guard.needs_pin(profile_id=profile_id, live=live):
        return True
    if guard.ask(_ask_pin):
        return True
    xbmcgui.Dialog().notification('NLZiet', get_string('parental_wrong_pin'), xbmcgui.NOTIFICATION_ERROR)
    return False


def parental_set_pin():
    guard = _parental()
    if guard.has_pin() and not guard.ask(lambda: _ask_pin('parental_enter_current_pin')):
        xbmcgui.Dialog().notification('NLZiet', get_string('parental_wrong_pin'), xbmcgui.NOTIFICATION_ERROR)
        return
    first = _ask_pin('parental_new_pin')
    if not first or len(first) < 4:
        xbmcgui.Dialog().ok('NLZiet', get_string('parental_pin_too_short'))
        return
    if _ask_pin('parental_repeat_pin') != first:
        xbmcgui.Dialog().ok('NLZiet', get_string('parental_pin_mismatch'))
        return
    guard.set_pin(first)
    xbmcgui.Dialog().ok('NLZiet', get_string('parental_pin_set'))


def parental_clear_pin():
    guard = _parental()
    if not guard.has_pin():
        return
    if not guard.ask(lambda: _ask_pin('parental_enter_current_pin')):
        xbmcgui.Dialog().notification('NLZiet', get_string('parental_wrong_pin'), xbmcgui.NOTIFICATION_ERROR)
        return
    guard.clear_pin()
    xbmcgui.Dialog().notification('NLZiet', get_string('parental_pin_removed'), xbmcgui.NOTIFICATION_INFO)


def toggle_profile_lock(profile_id):
    guard = _parental()
    if not guard.has_pin():
        xbmcgui.Dialog().ok('NLZiet', get_string('parental_set_pin_first'))
        parental_set_pin()
        if not guard.has_pin():
            return
    elif not guard.ask(_ask_pin):
        xbmcgui.Dialog().notification('NLZiet', get_string('parental_wrong_pin'), xbmcgui.NOTIFICATION_ERROR)
        return
    locked = guard.toggle_profile(profile_id)
    xbmcgui.Dialog().notification('NLZiet', get_string('parental_profile_locked' if locked else 'parental_profile_unlocked'),
                                  xbmcgui.NOTIFICATION_INFO)
    xbmc.executebuiltin('Container.Refresh')


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

        guard = _parental()
        tags = []
        if parental_mod.is_kids_profile(p):
            tags.append(get_string('parental_kids'))
        if guard.is_profile_protected(pid):
            tags.append(get_string('parental_pin_tag'))
        if tags:
            title = '{}  ({})'.format(title, ', '.join(tags))
        lock_label = get_string('parental_unlock_profile' if guard.is_profile_protected(pid) else 'parental_lock_profile')
        lock_menu = [(lock_label, 'RunPlugin({})'.format(build_url({'mode': 'toggle_profile_lock', 'profile_id': str(pid)})))]
        # Selecting an item triggers the 'select_profile' route with the profile id
        add_directory_item(title, {'mode': 'select_profile', 'profile_id': str(pid)}, is_folder=True, thumb=thumb, info=info_obj,
                           extra_context_items=lock_menu)

    _end_directory()


def _get_list_api():
    """Return the shared cached API instance, falling back to a fresh one."""
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    try:
        return get_api_instance()
    except Exception:
        return NLZietAPI(username=username, password=password)


# Canonical list groups used by My List and grouped search results. The keys
# are stable internal identifiers; their labels are resolved through
# get_string so every folder follows Kodi's configured language.
GROUP_ORDER = ['series', 'tvshows', 'documentary', 'movies', 'channels', 'episodes', 'other']

GROUP_STRING_KEYS = {
    'series': 'group_series',
    'tvshows': 'group_tv_shows',
    'documentary': 'group_documentaries',
    'movies': 'group_movies',
    'channels': 'group_channels',
    'episodes': 'group_episodes',
    'other': 'group_other',
}


def _group_label(group):
    """Return the localized label for a canonical group key."""
    key = GROUP_STRING_KEYS.get(group)
    return get_string(key) if key else (group or '')


def _group_folder_label(group, count):
    """Return a localized folder label such as 'Series (3)'."""
    return get_string('group_count', _group_label(group), count)


def _content_group(item):
    """Classify a stored list item into a canonical group key."""
    if not isinstance(item, dict):
        return 'other'
    explicit = str(item.get('group') or '').strip().lower()
    if explicit in GROUP_ORDER:
        return explicit
    typ = str(item.get('type') or _payload_value(item, 'type') or '').lower()
    if 'channel' in typ or 'live' in typ:
        return 'channels'
    if 'episode' in typ:
        return 'episodes'
    if 'series' in typ or 'tvshow' in typ:
        return 'series'
    if 'movie' in typ or 'film' in typ:
        return 'movies'
    return 'other'


def _search_group_key(itype_l, item):
    """Map a search result's detected type to a canonical group key."""
    itype_l = str(itype_l or '').lower()
    if 'series' in itype_l or 'tvshow' in itype_l:
        return 'series'
    if 'episode' in itype_l:
        return 'episodes'
    if 'movie' in itype_l or 'film' in itype_l:
        return 'movies'
    if 'channel' in itype_l or 'live' in itype_l:
        return 'channels'
    raw = item.get('raw') if isinstance(item, dict) else None
    sid = item.get('seriesId') if isinstance(item, dict) else None
    if not sid and isinstance(raw, dict):
        sid = raw.get('seriesId')
    if sid:
        return 'series'
    return 'other'


# Per-process cache of season catalogue lookups used by the Kijk Later
# labels. Keyed by (series_id, season_id) so several saved episodes of one
# season share a single catalogue request while the list renders.
_EPISODE_NUMBERING_CACHE = {}


def _expiry_epoch(api, value):
    """Parse a stored expiry value (epoch seconds or ISO date) to epoch seconds."""
    if value in (None, ''):
        return None
    if api is not None:
        try:
            parsed = api._parse_timestamp(value)
        except Exception:
            parsed = None
        if parsed:
            return int(parsed)
    try:
        if isinstance(value, (int, float)):
            epoch = int(value)
            if epoch > 10 ** 12:
                epoch //= 1000
            return epoch if epoch > 10 ** 9 else None
        text = str(value).strip()
        if text.isdigit():
            epoch = int(text)
            if epoch > 10 ** 12:
                epoch //= 1000
            return epoch if epoch > 10 ** 9 else None
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo('UTC'))
        return int(parsed.timestamp())
    except Exception:
        return None


def _availability_label(api, item):
    """Return the localized 'still available' text for a stored list item."""
    if not isinstance(item, dict):
        return None
    value = item.get('expires_at')
    raw = item.get('raw') if isinstance(item.get('raw'), dict) else {}
    if value in (None, ''):
        value = (raw.get('availableUntil') or raw.get('availableTo') or
                 raw.get('expires_at'))
    expires_at = _expiry_epoch(api, value)
    if not expires_at:
        return None
    secs = expires_at - int(time.time())
    if secs <= 0:
        return get_string('availability_expired')
    days = secs // 86400
    if days >= 1:
        return get_string('availability_days' if days > 1 else 'availability_day', int(days))
    hours = secs // 3600
    if hours >= 1:
        return get_string('availability_hours' if hours > 1 else 'availability_hour', int(hours))
    minutes = max(1, secs // 60)
    return get_string('availability_minutes' if minutes > 1 else 'availability_minute', int(minutes))


_NUMBERING_CACHE_TTL = 86400


def _season_numbering(api, series_id, season_id):
    """Return the season catalogue numbering, from memory, disk or the API.

    Successful lookups are kept on disk next to the list files for a day, so
    opening a list does not re-fetch the same season every time the addon runs.
    """
    key = (str(series_id), str(season_id))
    if key in _EPISODE_NUMBERING_CACHE:
        return _EPISODE_NUMBERING_CACHE[key]
    disk_path = None
    disk = {}
    watch_path = getattr(api, 'watchlater_sync_file', None)
    if watch_path:
        disk_path = os.path.join(os.path.dirname(watch_path), 'episode_numbering_cache.json')
        try:
            with open(disk_path, 'r', encoding='utf-8') as handle:
                disk = json.load(handle) or {}
        except Exception:
            disk = {}
    skey = '{}|{}'.format(*key)
    stored = disk.get(skey) if isinstance(disk, dict) else None
    if (isinstance(stored, dict) and stored.get('entry')
            and time.time() - float(stored.get('ts') or 0) < _NUMBERING_CACHE_TTL):
        _EPISODE_NUMBERING_CACHE[key] = stored['entry']
        return stored['entry']

    entry = None
    try:
        episodes = api.get_series_episodes(str(series_id), season_id=str(season_id), limit=400) or []
        entry = {
            'numbers': {
                str(ep.get('id') or ''): _metadata_int(ep.get('episode_number'), minimum=1)
                for ep in episodes if isinstance(ep, dict)
            },
            'total': len(episodes),
        }
    except Exception:
        entry = None
    _EPISODE_NUMBERING_CACHE[key] = entry
    if entry and disk_path:
        disk = disk if isinstance(disk, dict) else {}
        disk[skey] = {'ts': time.time(), 'entry': entry}
        try:
            os.makedirs(os.path.dirname(disk_path), exist_ok=True)
            with open(disk_path, 'w', encoding='utf-8') as handle:
                json.dump(disk, handle)
        except Exception:
            pass
    return entry


def _episode_numbering_label(api, item):
    """Return 'Afl. X van Y' (episode X of Y in its season) for episode items.

    The season catalogue is fetched once per (series, season) and kept in
    ``_EPISODE_NUMBERING_CACHE``; when the catalogue is unavailable we fall
    back to the numbering embedded in the stored subtitle.
    """
    if _content_group(item) != 'episodes':
        return None
    raw = item.get('raw') if isinstance(item.get('raw'), dict) else {}
    series_id = item.get('seriesId') or raw.get('seriesId')
    season_id = raw.get('seasonId') or item.get('seasonId')
    content_id = str(item.get('id') or '')
    number = None
    total = None
    if api is not None and series_id and season_id:
        entry = _season_numbering(api, series_id, season_id)
        if entry:
            number = entry['numbers'].get(content_id)
            total = entry['total']
    if number:
        if total:
            return get_string('episode_numbering_of', number, total)
        return get_string('episode_number_only', number)
    subtitle = str(raw.get('subtitle') or item.get('subtitle') or '')
    match = re.search(r'S(\d+)\s*[:.]?\s*(?:E|A)(\d+)', subtitle, re.I)
    if match:
        number = _metadata_int(match.group(2), minimum=1)
    else:
        match = re.search(r'\bAfl\.?\s*(\d+)\b', subtitle, re.I)
        if match:
            number = _metadata_int(match.group(1), minimum=1)
    return get_string('episode_number_only', number) if number else None


def _payload_value(item, key):
    """Find a stored value on the item, its raw payload, or a nested raw payload.

    Episodes saved through a series action keep the API payload one level deeper,
    so every level is checked.
    """
    if not isinstance(item, dict):
        return None
    levels = [item]
    raw = item.get('raw') if isinstance(item.get('raw'), dict) else {}
    levels.append(raw)
    if isinstance(raw.get('raw'), dict):
        levels.append(raw['raw'])
    for level in levels:
        value = level.get(key)
        if value not in (None, ''):
            return value
    return None


def _item_title(item):
    """Series or item title; falls back to the payload when the stored title is empty."""
    return str(item.get('title') or item.get('name') or _payload_value(item, 'title') or '').strip()


def _list_item_subtitle(item):
    """Return the episode/program subtitle from the stored raw data, if useful."""
    text = _clean_episode_title(_payload_value(item, 'subtitle') or '')
    if not text or text == str(item.get('title') or '').strip():
        return None
    return text


def _broadcast_datetime(item):
    """Return the broadcast moment of a stored episode, or None when unknown."""
    for value in (_payload_value(item, 'broadcastAt'), _payload_value(item, 'availableFrom')):
        if isinstance(value, str) and 'T' in value:
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except Exception:
                continue
    return None


def _tvmaze_season_episode(api, item, episode_title):
    """Return (season, episode) from TVmaze, matched on series and episode title."""
    if not episode_title or _content_group(item) != 'episodes':
        return None
    series_title = _item_title(item)
    watch_path = getattr(api, 'watchlater_sync_file', None)
    cache_path = os.path.join(os.path.dirname(watch_path), 'tvmaze_cache.json') if watch_path else None
    return tvmaze.lookup_season_episode(series_title, episode_title, cache_path)


def _order_watch_later(items):
    """Keep series in the order they were first added, episodes in broadcast order."""
    def series_key(item):
        return _item_title(item).casefold()

    first_seen = {}
    for index, item in enumerate(items):
        first_seen.setdefault(series_key(item), index)

    def sort_key(item):
        broadcast = _broadcast_datetime(item) if _content_group(item) == 'episodes' else None
        return (first_seen[series_key(item)], broadcast.timestamp() if broadcast else 0)

    return sorted(items, key=sort_key)


def _render_list_items(
    items, enrich=False, api=None, episode_label_only=False, episode_numbers=None,
    highlight_ids=None, sync_mode=None,
):
    """Render stored list items, linking series to their detail page.

    With ``enrich`` (Kijk Later only) the description also shows the episode
    numbering and the number of days the item is still available — each on
    its own line with a subtle accent color, in plot and plotoutline alike.
    """
    if enrich and api is None:
        api = _get_list_api()
    for itm in items:
        try:
            title = _item_title(itm) or itm.get('id') or get_string('item_label')
            source = itm.get('raw') if isinstance(itm.get('raw'), dict) else itm
            thumb = _pick_landscape_thumb(source) or itm.get('thumb') or itm.get('posterUrl') or None
            description = itm.get('description') or ''
            if not description and isinstance(source, dict):
                description = source.get('description') or source.get('plot') or ''
            info = {'plot': description, 'plotoutline': description} if description else None
            content = dict(source) if isinstance(source, dict) else {}
            content.setdefault('id', itm.get('id'))
            content.setdefault('title', title)
            if itm.get('type'):
                content.setdefault('type', itm.get('type'))
            if itm.get('group'):
                content.setdefault('group', itm.get('group'))
            # Stored lists keep the real poster on the item itself while the
            # raw payload may only carry a broadcaster logo; expose the poster
            # under an explicit portrait key so the artwork pickers prefer it.
            poster = itm.get('posterUrl') or itm.get('thumb')
            if (isinstance(poster, str) and poster.startswith(('http://', 'https://'))
                    and not content.get('portraitUrl')):
                content['portraitUrl'] = poster
            label = title
            if str(itm.get('id')) in (highlight_ids or set()):
                label = _make_color_tag(MY_SERIES_NEW_COLOR_RAW, label)
            if enrich:
                # Description decoration must never drop an item from the list.
                season_episode = None
                try:
                    numbering = _episode_numbering_label(api, itm)
                    availability = None if _content_group(itm) == 'channels' else _availability_label(api, itm)
                    subtitle_text = _list_item_subtitle(itm)
                    broadcast = _broadcast_datetime(itm) if _content_group(itm) == 'episodes' else None
                    if not numbering:
                        season_episode = _tvmaze_season_episode(api, itm, subtitle_text)
                        if season_episode:
                            numbering = f"S{season_episode[0]}E{season_episode[1]:02d}"
                except Exception:
                    numbering = None
                    availability = None
                    subtitle_text = None
                    broadcast = None
                    season_episode = None
                if subtitle_text and episode_label_only:
                    number = (episode_numbers or {}).get(str(itm.get('id')))
                    if number:
                        prefix = _make_color_tag(EPISODE_PREFIX_COLOR_RAW, get_string('episode_number_prefix', number))
                        label = f"{prefix}: {subtitle_text}"
                    else:
                        label = subtitle_text
                elif broadcast and subtitle_text:
                    label = f"{title} - {subtitle_text}"
                if numbering or availability or subtitle_text or broadcast:
                    truncated = (description[:250] + '...') if len(description) > 250 else description
                    # Each piece gets its own row with a subtle accent color,
                    # in the plot as well as in the plotoutline.
                    lines = []
                    if numbering:
                        lines.append(_make_color_tag(NUMBERING_COLOR_RAW, numbering))
                    if broadcast:
                        lines.append(get_string('broadcast_at', broadcast.strftime('%d-%m-%Y %H:%M')))
                    if availability:
                        lines.append(_make_color_tag(EXPIRY_COLOR_RAW, availability))
                    if subtitle_text:
                        lines.append(subtitle_text)
                    info = {
                        'plot': '\n'.join(lines + ([description] if description else [])),
                        'plotoutline': '\n'.join(lines + ([truncated] if truncated else [])),
                    }
                    if broadcast:
                        info['aired'] = broadcast.date().isoformat()
                    if season_episode:
                        info['season'] = season_episode[0]
                        info['episode'] = season_episode[1]
            group = _content_group(itm)
            extra_ctx = [(get_string('sync_now'), 'RunPlugin({})'.format(build_url({'mode': sync_mode})))] if sync_mode else None
            if group in ('series', 'tvshows', 'documentary'):
                add_directory_item(label, {'mode': 'series_detail', 'series_id': itm.get('id')}, is_folder=True, thumb=thumb, info=info, content=content, extra_context_items=extra_ctx)
            else:
                play_query = {'mode': 'play', 'id': itm.get('id')}
                if group == 'channels':
                    play_query['fmt'] = 'live'
                add_directory_item(label, play_query, is_folder=False, thumb=thumb, info=info, content=content, extra_context_items=extra_ctx)
        except Exception:
            continue


def browse_my_list():
    api = _get_list_api()
    try:
        items = api.get_my_list() or []
    except Exception:
        items = []

    if not items:
        xbmcgui.Dialog().notification('NLZiet', get_string('my_list_empty'), xbmcgui.NOTIFICATION_INFO)
        _end_directory()
        _run_after_directory(_backfill_quietly, api, 'backfill_my_list')
        return
    # Group My List items by category so the My List top-level shows one folder
    # per category (Series, TV Shows, Documentaires, Films, Kanalen, ...).
    groups = {}
    for itm in items:
        groups.setdefault(_content_group(itm), []).append(itm)

    # Present a localized folder for each non-empty group, in a stable order.
    any_folder = False
    for g in GROUP_ORDER:
        lst = groups.get(g) or []
        if not lst:
            continue
        first = lst[0] if lst else None
        thumb = _pick_landscape_thumb(first) if first else None
        add_directory_item(_group_folder_label(g, len(lst)), {'mode': 'my_list_group', 'group': g}, is_folder=True, thumb=thumb)
        any_folder = True

    if not any_folder:
        xbmcgui.Dialog().notification('NLZiet', get_string('my_list_empty'), xbmcgui.NOTIFICATION_INFO)
    _end_directory()
    _run_after_directory(_backfill_quietly, api, 'backfill_my_list')


def _browse_saved_group(group):
    """Show items from the user's My List filtered to a single group."""
    api = _get_list_api()
    try:
        items = api.get_my_list() or []
    except Exception:
        items = []

    filtered = [itm for itm in items if _content_group(itm) == group]

    if not filtered:
        message = get_string('no_items_for_group', _group_label(group))
        xbmcgui.Dialog().notification('NLZiet', message, xbmcgui.NOTIFICATION_INFO)
        _end_directory()
    else:
        _render_list_items(filtered)
        _end_directory()
    _run_after_directory(_backfill_quietly, api, 'backfill_my_list')


def browse_my_list_group(group):
    """Show items from the user's My List filtered to a single group."""
    _browse_saved_group(group)


_LIST_SYNC_INTERVAL = 300


def _list_sync_marker(api, name):
    return os.path.join(os.path.dirname(api.watchlater_sync_file), 'last_sync_{}'.format(name))


def _list_sync_due(api, name):
    """Return True when the list was not synced within the last few minutes."""
    try:
        with open(_list_sync_marker(api, name), 'r', encoding='utf-8') as handle:
            last = float(handle.read().strip() or 0)
    except Exception:
        last = 0
    return time.time() - last >= _LIST_SYNC_INTERVAL


def _mark_list_synced(api, name):
    try:
        path = _list_sync_marker(api, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(str(time.time()))
    except Exception:
        pass


def _list_ids(getter):
    try:
        return {str(i.get('id')) for i in (getter() or []) if isinstance(i, dict)}
    except Exception:
        return set()


def _backfill_quietly(api, method):
    try:
        getattr(api, method)()
    except Exception:
        pass


def _run_after_directory(target, *args):
    """Run non-essential refresh work without blocking Kodi's menu transition."""
    threading.Thread(target=target, args=args, daemon=True).start()


def _sync_list_after_render(api, name, enabled, sync_fn, getter):
    """Sync a list after its directory was ended, refreshing it only on change.

    Runs at most once per _LIST_SYNC_INTERVAL so returning to a list stays fast.
    """
    if not enabled or not _list_sync_due(api, name):
        return
    _mark_list_synced(api, name)
    before = _list_ids(getter)
    try:
        sync_fn(notify=False)
    except Exception:
        pass
    if _list_ids(getter) != before:
        xbmc.executebuiltin('Container.Refresh')


def _watch_later_collection_id(item):
    """Folder key for an episode: all episodes of one series share the same key."""
    if not isinstance(item, dict) or _content_group(item) != 'episodes':
        return None
    title = _item_title(item).casefold()
    return 'title:' + title if title else None


def _find_series_id_by_title(api, title):
    wanted = str(title or '').strip().casefold()
    if not wanted:
        return None
    try:
        hits = api.search(title, 'series') or []
    except Exception:
        hits = []
    for hit in hits:
        if isinstance(hit, dict) and _content_group(hit) == 'series' \
                and str(hit.get('title') or '').strip().casefold() == wanted:
            return hit.get('id')
    try:
        series_list = api.get_series_list(limit=999) or []
    except Exception:
        series_list = []
    for series in series_list:
        if isinstance(series, dict) and str(series.get('title') or '').strip().casefold() == wanted:
            return series.get('id')
    return None


def _find_episodes_by_title(api, title):
    """Episodes whose title matches exactly; used when the series has no NLZiet id."""
    wanted = str(title or '').strip().casefold()
    if not wanted:
        return []
    try:
        hits = api.search(title, 'episodes') or []
    except Exception:
        return []
    found = {}
    for hit in hits:
        if isinstance(hit, dict) and hit.get('id') and _content_group(hit) == 'episodes' \
                and str(hit.get('title') or '').strip().casefold() == wanted:
            found.setdefault(str(hit['id']), hit)
    return list(found.values())


def _collect_series_episodes(api, series_id):
    detail = api.get_series_detail(series_id) or {}
    episodes = []
    seasons = detail.get('seasons') or []
    if seasons:
        for season_info in seasons:
            episodes.extend(_get_series_season_episodes(
                api,
                series_id,
                season_info.get('id'),
                season_info.get('episodes_url'),
                limit=1000,
            ))
    else:
        episodes = api.get_series_episodes(series_id, limit=1000) or []
    return detail.get('title') or '', episodes


def add_series_watch_later(series_id=None, title=None, from_now=None):
    """Add all episodes or start following a series from the current baseline."""
    try:
        api = get_api_instance()
        if isinstance(from_now, str):
            from_now = from_now.lower() in ('true', '1', 'yes')
        if from_now is None:
            choice = xbmcgui.Dialog().select(
                get_string('add_series_to_watch_later'),
                [get_string('add_series_all'), get_string('add_series_from_now')],
            )
            if choice < 0:
                return
            from_now = choice == 1
        sid = series_id or _find_series_id_by_title(api, title)
        series_title, episodes = '', []
        if sid:
            series_title, episodes = _collect_series_episodes(api, sid)
        if not episodes:
            episodes = _find_episodes_by_title(api, title)
        if not episodes:
            xbmcgui.Dialog().notification('NLZiet', get_string('no_episodes_found'), xbmcgui.NOTIFICATION_INFO)
            return
        series_title = series_title or title or str(sid)
        if from_now:
            state_path = os.path.join(
                os.path.dirname(api.watchlater_sync_file), 'auto_add_state.json'
            )
            try:
                with open(state_path, 'r', encoding='utf-8') as handle:
                    state = json.load(handle) or {}
            except (OSError, TypeError, ValueError):
                state = {}
            key = 'title:' + series_title.casefold()
            state[key] = {
                'id': str(sid or series_title),
                'seen': [str(ep['id']) for ep in episodes if ep.get('id')],
            }
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, 'w', encoding='utf-8') as handle:
                json.dump(state, handle)
            ADDON.setSetting('auto_add_new_episodes', 'true')
            xbmcgui.Dialog().notification(
                'NLZiet', get_string('series_following_started'), xbmcgui.NOTIFICATION_INFO
            )
            return
        added = api.add_series_to_watch_later(sid or series_title, series_title, episodes)
        xbmcgui.Dialog().notification(
            'NLZiet', get_string('series_added_to_watch_later', added), xbmcgui.NOTIFICATION_INFO)
    except Exception as exc:
        xbmc.log(f"NLZiet add_series_watch_later failed: {exc}", xbmc.LOGWARNING)
        xbmcgui.Dialog().notification('NLZiet', get_string('watchlater_action_failed'), xbmcgui.NOTIFICATION_ERROR)


AUTO_ADD_INTERVAL = 6 * 3600


def _auto_add_enabled():
    try:
        return ADDON.getSetting('auto_add_new_episodes') in ('true', '1', 'yes', True)
    except Exception:
        return False


def _auto_add_due(api):
    marker = os.path.join(os.path.dirname(api.watchlater_sync_file), 'last_auto_add')
    try:
        with open(marker, 'r', encoding='utf-8') as handle:
            last = float(handle.read().strip() or 0)
    except Exception:
        last = 0
    return time.time() - last >= AUTO_ADD_INTERVAL


def _mark_auto_add(api):
    try:
        marker = os.path.join(os.path.dirname(api.watchlater_sync_file), 'last_auto_add')
        with open(marker, 'w', encoding='utf-8') as handle:
            handle.write(str(time.time()))
    except Exception:
        pass


def _auto_add_sources(api):
    """Followed series plus every series that has episodes in Kijk Later, keyed by title."""
    sources = {}
    for series in api.get_my_series() or []:
        if isinstance(series, dict) and series.get('id') and _item_title(series):
            sources['title:' + _item_title(series).casefold()] = (str(series['id']), _item_title(series))
    for item in api.get_watch_later() or []:
        key = _watch_later_collection_id(item)
        if key and key not in sources:
            sources[key] = (None, _item_title(item))
    return sources


def _run_auto_add(api):
    """Add episodes that appeared since the last run; the first run only records them.

    Each series remembers the episode ids it has seen. A series seen for the first
    time is recorded without adding anything, so turning the option on does not
    flood Kijk Later with the whole back catalogue.
    """
    state_path = os.path.join(os.path.dirname(api.watchlater_sync_file), 'auto_add_state.json')
    try:
        with open(state_path, 'r', encoding='utf-8') as handle:
            state = json.load(handle) or {}
    except Exception:
        state = {}

    added = 0
    for key, (sid, title) in _auto_add_sources(api).items():
        entry = state.get(key) if isinstance(state.get(key), dict) else {}
        sid = sid or entry.get('id') or _find_series_id_by_title(api, title)
        if not sid:
            continue
        try:
            series_title, episodes = _collect_series_episodes(api, sid)
        except Exception:
            continue
        episodes = [ep for ep in episodes if isinstance(ep, dict) and ep.get('id')]
        if not episodes:
            continue
        seen = set(entry.get('seen') or [])
        if 'seen' in entry:
            new = [ep for ep in episodes if str(ep['id']) not in seen]
            if new:
                added += api.add_series_to_watch_later(sid, series_title or title, new)
        state[key] = {'id': sid, 'seen': [str(ep['id']) for ep in episodes]}

    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, 'w', encoding='utf-8') as handle:
            json.dump(state, handle)
    except Exception:
        pass
    _mark_auto_add(api)
    return added


def _maybe_run_auto_add():
    if not _auto_add_enabled():
        return
    try:
        api = get_api_instance()
        if not _auto_add_due(api):
            return
        added = _run_auto_add(api)
        if added:
            xbmcgui.Dialog().notification('NLZiet', get_string('auto_added_episodes', added), xbmcgui.NOTIFICATION_INFO)
    except Exception as exc:
        xbmc.log(f"NLZiet auto add failed: {exc}", xbmc.LOGWARNING)


EXPIRY_CHECK_INTERVAL = 2 * 3600


def _setting_on(name, default=False):
    try:
        value = ADDON.getSetting(name)
    except Exception:
        return default
    if value in ('', None):
        return default
    return value in ('true', '1', 'yes', True)


def _expiry_hours():
    try:
        return max(1, int(float(ADDON.getSetting('expiry_notify_hours') or 24)))
    except Exception:
        return 24


def _availability_until(item):
    """Epoch seconds when the item (or episode) stops being available, if known."""
    if not isinstance(item, dict):
        return None
    value = item.get('expires_at') or item.get('availableUntil') or _payload_value(item, 'availableUntil')
    if not isinstance(value, str) or 'T' not in value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except Exception:
        return None


def _expiry_due_names(api):
    """Titles of Kijk Later items and followed-series episodes that expire soon."""
    now = time.time()
    horizon = now + _expiry_hours() * 3600
    state_path = os.path.join(os.path.dirname(api.watchlater_sync_file), 'expiry_notified.json')
    try:
        with open(state_path, 'r', encoding='utf-8') as handle:
            notified = json.load(handle) or {}
    except Exception:
        notified = {}

    candidates = []
    if _setting_on('expiry_notify_watch_later', True):
        for item in api.get_watch_later() or []:
            until = _availability_until(item)
            if until and item.get('id'):
                candidates.append((_item_title(item) or str(item['id']), str(item['id']), until))
    if _setting_on('expiry_notify_my_series', True):
        for series in api.get_my_series() or []:
            sid = series.get('id') if isinstance(series, dict) else None
            if not sid:
                continue
            try:
                series_title, episodes = _collect_series_episodes(api, sid)
            except Exception:
                continue
            series_title = series_title or _item_title(series)
            for ep in episodes:
                until = _availability_until(ep)
                if not until or not isinstance(ep, dict) or not ep.get('id'):
                    continue
                subtitle = _list_item_subtitle(ep)
                name = f"{series_title}: {subtitle}" if subtitle else series_title
                candidates.append((name, str(ep['id']), until))

    due = []
    seen_keys = set()
    for name, key, until in sorted(candidates, key=lambda c: c[2]):
        if key in seen_keys or not (now <= until <= horizon):
            continue
        seen_keys.add(key)
        if notified.get(key) == int(until):
            continue
        notified[key] = int(until)
        due.append(name)

    notified = {k: v for k, v in notified.items() if v >= now - 86400}
    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, 'w', encoding='utf-8') as handle:
            json.dump(notified, handle)
    except Exception:
        pass
    return due


def _maybe_run_expiry_check():
    if not _setting_on('expiry_notify_enabled', False):
        return
    try:
        api = get_api_instance()
        marker = os.path.join(os.path.dirname(api.watchlater_sync_file), 'last_expiry_check')
        try:
            with open(marker, 'r', encoding='utf-8') as handle:
                last = float(handle.read().strip() or 0)
        except Exception:
            last = 0
        if time.time() - last < EXPIRY_CHECK_INTERVAL:
            return
        with open(marker, 'w', encoding='utf-8') as handle:
            handle.write(str(time.time()))
        due = _expiry_due_names(api)
        if due:
            shown = ', '.join(due[:3]) + (f' (+{len(due) - 3})' if len(due) > 3 else '')
            xbmcgui.Dialog().notification('NLZiet', get_string('expiry_soon', shown), xbmcgui.NOTIFICATION_WARNING)
    except Exception as exc:
        xbmc.log(f"NLZiet expiry check failed: {exc}", xbmc.LOGWARNING)


def _render_watch_later_top(items, api):
    """Show one folder per series collection, then the individual items."""
    ordered = _order_watch_later(items)
    keyed = {}
    for itm in ordered:
        cid = _watch_later_collection_id(itm)
        if cid:
            keyed.setdefault(cid, []).append(itm)
    collections = {}
    standalone = []
    for itm in ordered:
        cid = _watch_later_collection_id(itm)
        members = keyed.get(cid) if cid else None
        is_folder = members and (len(members) > 1 or isinstance(itm.get('collection'), dict))
        if is_folder:
            collections[cid] = members
        else:
            standalone.append(itm)
    for cid, members in collections.items():
        label = _item_title(members[0]) or cid
        add_directory_item(
            label, {'mode': 'watch_later_collection', 'collection_id': cid},
            is_folder=True, thumb=_pick_landscape_thumb(members[0]))
    _render_list_items(standalone, enrich=True, api=api, sync_mode='sync_watch_later' if _watch_later_sync_enabled() else None)


def browse_watch_later():
    """Show the Watch Later queue; the cloud sync runs after the list is shown.

    Syncing while the directory is still loading keeps Kodi's busy spinner on
    screen, so the list is rendered first and the sync (throttled) follows.
    """
    api = _get_list_api()
    try:
        api.migrate_series_from_watch_later()
    except Exception:
        pass
    try:
        items = api.get_watch_later() or []
    except Exception:
        items = []

    if not items:
        xbmcgui.Dialog().notification('NLZiet', get_string('watch_later_empty'), xbmcgui.NOTIFICATION_INFO)
    else:
        _render_watch_later_top(items, api)
    _end_directory()

    _run_after_directory(_backfill_quietly, api, 'backfill_watch_later')
    _run_after_directory(
        _sync_list_after_render,
        api, 'watch_later', _watch_later_sync_enabled(),
        sync_watch_later, api.get_watch_later)


def _member_season_episode(api, item):
    """Season and episode numbers: NLZiet's own S1:A2 code first, TVmaze as fallback."""
    raw_subtitle = str(_payload_value(item, 'subtitle') or '')
    match = re.search(r'S(\d+)\s*[:.]?\s*[AE](\d+)', raw_subtitle, re.I)
    if match:
        return int(match.group(1)), int(match.group(2))
    try:
        return _tvmaze_season_episode(api, item, _list_item_subtitle(item))
    except Exception:
        return None


def browse_watch_later_collection(collection_id=None, season=None):
    """Show one series folder: season folders when known, otherwise the episodes."""
    api = _get_list_api()
    try:
        items = api.get_watch_later() or []
    except Exception:
        items = []
    members = _order_watch_later([itm for itm in items if _watch_later_collection_id(itm) == str(collection_id)])
    if not members:
        xbmcgui.Dialog().notification('NLZiet', get_string('watch_later_empty'), xbmcgui.NOTIFICATION_INFO)
        _end_directory()
        return

    by_season = {}
    unknown = []
    episode_numbers = {}
    for itm in members:
        found = _member_season_episode(api, itm)
        if found:
            by_season.setdefault(found[0], []).append((found[1], itm))
            episode_numbers[str(itm.get('id'))] = found[1]
        else:
            unknown.append(itm)
    for number in by_season:
        by_season[number].sort(key=lambda pair: pair[0])
        by_season[number] = [itm for _, itm in by_season[number]]

    labels = {'enrich': True, 'api': api, 'episode_label_only': True, 'episode_numbers': episode_numbers}
    if season not in (None, ''):
        _render_list_items(by_season.get(int(season), []), **labels)
    elif by_season:
        for number in sorted(by_season):
            add_directory_item(
                get_string('season_folder', number),
                {'mode': 'watch_later_collection', 'collection_id': str(collection_id), 'season': str(number)},
                is_folder=True)
        _render_list_items(unknown, **labels)
    else:
        _render_list_items(members, **labels)
    _end_directory()

    _run_after_directory(_backfill_quietly, api, 'backfill_watch_later')
    _run_after_directory(
        _sync_list_after_render,
        api, 'watch_later', _watch_later_sync_enabled(),
        sync_watch_later, api.get_watch_later)


def _my_series_state_path(api):
    sync_file = getattr(api, 'watchlater_sync_file', None)
    if not sync_file:
        return None
    return os.path.join(os.path.dirname(sync_file), 'my_series_state.json')


def _new_my_series_ids(api, items):
    """Return series ids with unseen episodes and the updated episode state."""
    state_path = _my_series_state_path(api)
    if not state_path:
        return set(), {}
    try:
        with open(state_path, 'r', encoding='utf-8') as handle:
            previous = json.load(handle) or {}
    except (OSError, TypeError, ValueError):
        previous = {}

    current = {}
    new_ids = set()
    for item in items:
        if not isinstance(item, dict) or not item.get('id'):
            continue
        series_id = str(item['id'])
        try:
            _, episodes = _collect_series_episodes(api, series_id)
        except Exception as exc:
            xbmc.log(
                'NLZiet: could not check new My Series episodes for {0}: {1}'.format(
                    series_id, exc
                ),
                xbmc.LOGDEBUG,
            )
            continue
        episode_ids = {
            str(episode['id'])
            for episode in episodes
            if isinstance(episode, dict) and episode.get('id')
        }
        if episode_ids and series_id in previous:
            if episode_ids - set(previous.get(series_id) or []):
                new_ids.add(series_id)
        if episode_ids:
            current[series_id] = sorted(episode_ids)
        elif series_id in previous:
            current[series_id] = previous[series_id]
    return new_ids, current


def _check_my_series_new_episodes(api, items):
    '''Background helper: detect newly added episodes and refresh on change.'''
    try:
        new_ids, state = _new_my_series_ids(api, items)
        _save_my_series_state(api, state)
        if new_ids:
            try:
                xbmc.executebuiltin('Container.Refresh')
            except Exception:
                pass
    except Exception:
        pass


def _save_my_series_state(api, state):
    state_path = _my_series_state_path(api)
    if not state_path:
        return
    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, 'w', encoding='utf-8') as handle:
            json.dump(state, handle)
    except OSError as exc:
        xbmc.log('NLZiet: could not save My Series state: {0}'.format(exc), xbmc.LOGWARNING)


def browse_my_series():
    """Show the followed-series list; the cloud sync runs after the list is shown."""
    api = _get_list_api()
    try:
        items = api.get_my_series() or []
    except Exception:
        items = []

    if not items:
        xbmcgui.Dialog().notification('NLZiet', get_string('my_series_empty'), xbmcgui.NOTIFICATION_INFO)
    else:
        # Detecting newly added episodes requires fetching every series' episodes,
        # which is slow. Do it in the background so the list renders immediately;
        # highlight/refresh happen after the directory has been shown.
        _render_list_items(items, sync_mode='sync_my_series' if _my_series_sync_enabled() else None)
    _end_directory()

    _run_after_directory(_backfill_quietly, api, 'backfill_my_series')
    _run_after_directory(_check_my_series_new_episodes, api, list(items))
    _run_after_directory(
        _sync_list_after_render,
        api, 'my_series', _my_series_sync_enabled(),
        sync_my_series, api.get_my_series)


def _fetch_list_detail(api, item_id, group):
    """Fetch the richest available metadata for a saved list item.

    The generic content endpoint does not return data for series ids, so series
    are resolved through the series detail endpoint. Each source falls back to
    the other so we always persist as much detail as possible.
    """
    if group in ('series', 'tvshows', 'documentary'):
        order = ('get_series_detail', 'get_content_detail')
    else:
        order = ('get_content_detail', 'get_series_detail')
    for name in order:
        fn = getattr(api, name, None)
        if not callable(fn):
            continue
        try:
            detail = fn(item_id) or {}
        except Exception:
            detail = {}
        if isinstance(detail, dict) and (detail.get('description') or detail.get('raw') or detail.get('title')):
            return detail
    return {}


def _resolve_list_type(api, item_id, type, allow_any=False):
    """Return (allowed, content_type) for a list toggle.

    Both My List and Watch Later accept any content. When the caller does not
    provide a type we try to resolve it from the content detail so the stored
    entry can later be rendered correctly.
    """
    def _is_series_or_movie(value):
        return any(x in value for x in ('series', 'tvshow', 'movie', 'film'))

    if type and isinstance(type, str):
        return (allow_any or _is_series_or_movie(type.lower()), type)
    try:
        det = api.get_content_detail(item_id) or {}
        raw_type = (det.get('raw') or {}).get('type') or det.get('type') or ''
        if raw_type:
            return (allow_any or _is_series_or_movie(str(raw_type).lower()), str(raw_type))
    except Exception:
        pass
    # The generic endpoint returns nothing for series ids, so try series detail.
    try:
        sd = api.get_series_detail(item_id) or {}
        if isinstance(sd, dict) and (sd.get('title') or sd.get('description') or sd.get('seasons')):
            return (True, 'Series')
    except Exception:
        pass
    return (allow_any, type)


def _watch_later_sync_enabled():
    """Return True when the user enabled two-way Watch Later cloud sync."""
    try:
        return ADDON.getSetting('watch_later_sync') in ('true', '1', 'yes', True)
    except Exception:
        return False


def _my_series_sync_enabled():
    """Return True when the user enabled two-way My Series cloud sync."""
    return _watch_later_sync_enabled()


def _list_add_problem(kind, detail, stored_type, replay_ok=None, title=None, group=None):
    """Return a string key describing why an item cannot be saved to a list, or None.

    The detail endpoint does not return data for every id, so a missing detail
    only counts as "not found" when the caller also has no title for the item.
    My Series only accepts items whose series type is confirmed by the detail.
    """
    has_detail = isinstance(detail, dict) and bool(detail.get('title') or detail.get('raw'))
    if not has_detail and not title:
        return 'list_item_not_found'
    if replay_ok is False:
        return 'list_item_not_reachable_later'
    if kind == 'my_series':
        stored = str(stored_type or '').lower()
        confirmed = 'series' in stored or 'tvshow' in stored or bool(isinstance(detail, dict) and detail.get('seasons'))
        if not confirmed:
            # EPG programmes are episodes of a series. Accept them for My Series
            # even when the detail endpoint returns 404, which NLZiet does for
            # replay items.
            if group == 'series':
                return None
            return 'only_series'
    return None


def _item_playable_now(api, item_id):
    """Return True when NLZiet hands out a stream manifest for the item, the same request Watch Later playback makes."""
    try:
        info = api.get_stream_info(item_id) or {}
    except Exception:
        return False
    return bool(info.get('manifest'))


def _toggle_local_list(kind, item_id=None, title=None, type=None, thumb=None, group=None, replay_ok=None, aired=None, started=None, description=None):
    """Add or remove an item from a local list.

    ``kind`` is one of 'mylist' (any content), 'watch_later' (episodes and
    movies) or 'my_series' (followed series).
    """
    api = _get_list_api()
    if not item_id:
        missing_keys = {
            'watch_later': 'missing_id_watchlater',
            'my_series': 'missing_id_my_series',
        }
        missing_key = missing_keys.get(kind, 'missing_id_mylist')
        xbmcgui.Dialog().notification('NLZiet', get_string(missing_key), xbmcgui.NOTIFICATION_ERROR)
        return

    allowed, resolved_type = _resolve_list_type(api, item_id, type, allow_any=True)
    if not allowed:
        xbmcgui.Dialog().notification('NLZiet', get_string('only_series_movies'), xbmcgui.NOTIFICATION_INFO)
        return

    resolved_l = str(resolved_type or '').lower()
    is_series = 'series' in resolved_l or 'tvshow' in resolved_l or str(group or '').lower() == 'series'
    # Keep the two cloud lists distinct: series follow via My Series, while
    # Watch Later only holds episodes and movies.
    if kind == 'my_series' and not is_series:
        xbmcgui.Dialog().notification('NLZiet', get_string('only_series'), xbmcgui.NOTIFICATION_INFO)
        return
    if kind == 'watch_later' and is_series:
        xbmcgui.Dialog().notification('NLZiet', get_string('only_episodes_movies'), xbmcgui.NOTIFICATION_INFO)
        return

    fail_keys = {'watch_later': 'watchlater_action_failed', 'my_series': 'myseries_action_failed'}
    fail_key = fail_keys.get(kind, 'mylist_action_failed')
    ok = False
    in_list = False
    stored_group = group
    notice = None
    try:
        if kind == 'watch_later':
            in_list = api.is_in_watch_later(item_id)
            ok_key = 'removed_from_watch_later'
        elif kind == 'my_series':
            in_list = api.is_in_my_series(item_id)
            ok_key = 'removed_from_my_series'
        else:
            in_list = api.is_in_my_list(item_id)
            ok_key = 'removed_from_list'

        if in_list:
            if kind == 'watch_later':
                ok = api.remove_from_watch_later(item_id)
            elif kind == 'my_series':
                ok = api.remove_from_my_series(item_id)
            else:
                ok = api.remove_from_my_list(item_id)
        else:
            # Fetch the full content detail so we persist the metadata (title,
            # description, artwork, ...) instead of only a bare id/title pair.
            stored_group = group or _content_group({'type': resolved_type})
            detail = _fetch_list_detail(api, item_id, stored_group)
            raw = detail.get('raw') if isinstance(detail.get('raw'), dict) else {}
            stored_type = resolved_type or detail.get('type') or ''
            if not stored_type and isinstance(detail.get('seasons'), (list, tuple)):
                stored_type = 'Series'
            problem = _list_add_problem(kind, detail, stored_type, replay_ok, title, group)
            if problem:
                xbmcgui.Dialog().notification('NLZiet', get_string(problem), xbmcgui.NOTIFICATION_INFO)
                return
            if not (detail.get('description') or detail.get('plot')) and description:
                detail['description'] = description
            if kind == 'watch_later' and replay_ok is not None:
                if aired:
                    if not _item_playable_now(api, item_id):
                        xbmcgui.Dialog().notification('NLZiet', get_string('list_item_not_playable'), xbmcgui.NOTIFICATION_INFO)
                        return
                elif started:
                    notice = 'list_item_airing'
                elif _item_playable_now(api, item_id):
                    notice = 'list_item_repeat_playable'
                else:
                    notice = 'list_item_not_aired'
            itm = {
                'id': item_id,
                'title': title or detail.get('title') or '',
                'type': stored_type,
                'group': stored_group,
                'posterUrl': thumb or detail.get('thumb') or None,
                'thumb': thumb or detail.get('thumb') or None,
                'description': detail.get('description') or description or '',
                'expires_at': detail.get('expires_at'),
            }
            if raw:
                itm['raw'] = raw
            if kind == 'watch_later':
                ok = api.add_to_watch_later(itm)
                ok_key = 'added_to_watch_later'
            elif kind == 'my_series':
                ok = api.add_to_my_series(itm)
                ok_key = 'added_to_my_series'
            else:
                ok = api.add_to_my_list(itm)
                ok_key = 'added_to_list'

        xbmcgui.Dialog().notification(
            'NLZiet',
            get_string(ok_key if ok else fail_key),
            xbmcgui.NOTIFICATION_INFO if ok else xbmcgui.NOTIFICATION_ERROR,
        )
        if ok and notice:
            xbmcgui.Dialog().notification('NLZiet', get_string(notice), xbmcgui.NOTIFICATION_INFO)
    except Exception:
        xbmcgui.Dialog().notification('NLZiet', get_string('list_action_failed'), xbmcgui.NOTIFICATION_ERROR)

    if ok:
        if kind == 'watch_later' and _watch_later_sync_enabled():
            _propagate_watch_later_change(api, item_id, not in_list)
        elif kind == 'my_series' and _my_series_sync_enabled():
            _propagate_my_series_change(api, item_id, not in_list)

    # Refresh the current container so context menu changes reflect immediately
    try:
        xbmc.executebuiltin('Container.Refresh')
    except Exception:
        pass


def _propagate_watch_later_change(api, item_id, present, is_series=False):
    """Push a single local Watch Later change to /v9/watchlist.

    Uses the API's verified single-change helper when available so items the
    cloud silently rejects are not recorded as synced (which would later look
    like a cloud removal and delete them locally).
    """
    if not item_id:
        return
    single = getattr(api, 'sync_single_watch_later_change', None)
    if callable(single):
        try:
            single(item_id, present, is_series)
        except TypeError:
            try:
                single(item_id, present)
            except Exception:
                pass
        except Exception:
            pass
        return
    # Fallback for older API objects / test doubles without the helper.
    try:
        if present:
            if api.add_to_cloud_watch_later(item_id):
                api.update_sync_snapshot(item_id, True)
        else:
            if api.remove_from_cloud_watch_later(item_id):
                api.update_sync_snapshot(item_id, False)
    except Exception:
        pass


def _propagate_my_series_change(api, item_id, present):
    """Push a single local My Series change to /v9/trackedseries."""
    if not item_id:
        return
    single = getattr(api, 'sync_single_my_series_change', None)
    if callable(single):
        try:
            single(item_id, present)
        except Exception:
            pass
        return
    try:
        if present:
            if api.add_to_cloud_my_series(item_id):
                api.update_sync_snapshot(item_id, True, getattr(api, 'myseries_sync_file', None))
        else:
            if api.remove_from_cloud_my_series(item_id):
                api.update_sync_snapshot(item_id, False, getattr(api, 'myseries_sync_file', None))
    except Exception:
        pass


def toggle_mylist(item_id=None, title=None, type=None, thumb=None, group=None):
    _toggle_local_list('mylist', item_id, title, type, thumb, group)


def toggle_watch_later(item_id=None, title=None, type=None, thumb=None, group=None, replay_ok=None, aired=None, started=None, description=None):
    _toggle_local_list('watch_later', item_id, title, type, thumb, group, replay_ok=replay_ok, aired=aired, started=started, description=description)


def toggle_my_series(item_id=None, title=None, type=None, thumb=None, group=None, description=None):
    _toggle_local_list('my_series', item_id, title, type, thumb, group, description=description)


def _show_sync_notice(message, icon, background=False, changed=False):
    """Show a sync result. Manual runs always show. Background runs show only when
    something changed, the setting allows it, and nothing is playing."""
    if background:
        if not changed or ADDON.getSetting('background_sync_notify') not in ('true', '1', 'yes', True):
            return
        if xbmc.Player().isPlaying():
            return
    xbmcgui.Dialog().notification('NLZiet', message, icon)


def sync_watch_later(notify=True, background=False):
    """Synchronise the local Watch Later queue with /v9/watchlist.

    Adds and removals performed in the Kodi addon or in the NLZiet app are
    propagated in both directions. Safe to call on menu load (best effort).
    """
    api = _get_list_api()
    fn = getattr(api, 'sync_watch_later', None)
    if not callable(fn):
        if notify:
            _show_sync_notice(get_string('watchlater_sync_failed'), xbmcgui.NOTIFICATION_ERROR, background)
        return False
    try:
        result = fn() or {}
    except Exception:
        result = {}

    if not result.get('ok'):
        if result.get('reason') == 'not_logged_in':
            if notify:
                _show_sync_notice(get_string('watchlater_sync_not_logged_in'), xbmcgui.NOTIFICATION_INFO, background)
        elif notify:
            _show_sync_notice(get_string('watchlater_sync_failed'), xbmcgui.NOTIFICATION_ERROR, background)
        return False

    changes = (result.get('added_local', 0) + result.get('added_cloud', 0)
               + result.get('removed_local', 0) + result.get('removed_cloud', 0))
    if notify:
        message = get_string('watchlater_sync_done', changes)
        try:
            detail = get_string(
                'watchlater_sync_summary',
                result.get('added_cloud', 0),
                result.get('removed_cloud', 0),
                result.get('added_local', 0),
                result.get('removed_local', 0),
            )
            message = message + '\n' + detail
        except Exception:
            pass
        _show_sync_notice(message, xbmcgui.NOTIFICATION_INFO, background, changed=changes > 0)
    return True


def sync_my_series(notify=True, background=False):
    """Synchronise the local My Series list with /v9/trackedseries."""
    api = _get_list_api()
    fn = getattr(api, 'sync_my_series', None)
    if not callable(fn):
        if notify:
            _show_sync_notice(get_string('myseries_sync_failed'), xbmcgui.NOTIFICATION_ERROR, background)
        return False
    try:
        result = fn() or {}
    except Exception:
        result = {}

    if not result.get('ok'):
        if result.get('reason') == 'not_logged_in':
            if notify:
                _show_sync_notice(get_string('watchlater_sync_not_logged_in'), xbmcgui.NOTIFICATION_INFO, background)
        elif notify:
            _show_sync_notice(get_string('myseries_sync_failed'), xbmcgui.NOTIFICATION_ERROR, background)
        return False

    changes = (result.get('added_local', 0) + result.get('added_cloud', 0)
               + result.get('removed_local', 0) + result.get('removed_cloud', 0))
    if notify:
        message = get_string('myseries_sync_done', changes)
        try:
            detail = get_string(
                'myseries_sync_summary',
                result.get('added_cloud', 0),
                result.get('removed_cloud', 0),
                result.get('added_local', 0),
                result.get('removed_local', 0),
            )
            message = message + '\n' + detail
        except Exception:
            pass
        _show_sync_notice(message, xbmcgui.NOTIFICATION_INFO, background, changed=changes > 0)
    return True


def select_profile(profile_id):
    """Activate the given profile id and re-render the profiles list."""
    if not profile_id:
        xbmcgui.Dialog().notification('NLZiet', get_string('missing_profile_id'), xbmcgui.NOTIFICATION_ERROR)
        return

    if str(profile_id) != str(ADDON.getSetting('profile_id') or '') and not _pin_ok(profile_id=profile_id):
        xbmc.executebuiltin('Container.Update(%s,replace)' % build_url({'mode': 'profiles'}))
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
        xbmcgui.Dialog().notification('NLZiet', get_string('profile_switched', ADDON.getSetting('profile_name') or profile_id), xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('NLZiet', get_string('profile_switch_failed'), xbmcgui.NOTIFICATION_ERROR)

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
        xbmcgui.Dialog().notification('NLZiet', get_string('no_profile_set'), xbmcgui.NOTIFICATION_INFO)
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

        xbmcgui.Dialog().notification('NLZiet', get_string('profile_applied', profile_name or pid), xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('NLZiet', get_string('profile_apply_failed'), xbmcgui.NOTIFICATION_ERROR)


def _load_search_history():
    try:
        history = json.loads(ADDON.getSetting('search_history') or '[]')
        if isinstance(history, list):
            return [str(query).strip() for query in history if str(query).strip()]
    except (TypeError, ValueError):
        xbmc.log('NLZiet: invalid search history ignored', xbmc.LOGWARNING)
    return []


def _save_search_history(history):
    ADDON.setSetting('search_history', json.dumps(history[:20], ensure_ascii=False))


def _remember_search(query):
    query = (query or '').strip()
    if not query:
        return
    history = [old for old in _load_search_history() if old.casefold() != query.casefold()]
    _save_search_history([query] + history)


def _choose_search_query():
    history = _load_search_history()
    if not history:
        options = [get_string('search_history_new')]
    else:
        options = [
            get_string('search_history_new'),
            get_string('search_history_delete'),
        ] + history

    selected = xbmcgui.Dialog().select(get_string('search_heading'), options)
    if selected < 0:
        return None
    if selected == 0:
        kb = xbmc.Keyboard('', get_string('search_heading'))
        kb.doModal()
        return kb.getText().strip() if kb.isConfirmed() else None
    if history and selected == 1:
        indexes = xbmcgui.Dialog().multiselect(
            get_string('search_history_delete'),
            history,
        )
        if indexes:
            deleted = len(indexes)
            _save_search_history([
                query for index, query in enumerate(history) if index not in indexes
            ])
            xbmcgui.Dialog().notification(
                'NLZiet',
                get_string('search_history_deleted', deleted),
                xbmcgui.NOTIFICATION_INFO,
            )
        return None
    query = history[selected - 2] if history else None
    return query


def do_search(query=None):
    query = (query or '').strip() or _choose_search_query()
    if not query:
        return
    _remember_search(query)
    _add_other_service_search(query)
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
            xbmcgui.Dialog().notification('NLZiet', get_string('no_results', query), xbmcgui.NOTIFICATION_INFO)
            _end_directory()
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

        group = _search_group_key(itype_l, item)

        group_map.setdefault(group, []).append(item)

    non_empty = [g for g in GROUP_ORDER if group_map.get(g)]
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
            add_directory_item(_group_folder_label(g, len(items_for_group)), {'mode': 'search_group', 'q': query, 'group': g}, is_folder=True, thumb=thumb)
        _end_directory()
        return

    # One group only: show it with the filter entry on top.
    if search_filters.options(results) != ([], []):
        return search_group(query, non_empty[0] if non_empty else 'all')

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
                    marker = ''  # text only: readable by screen readers and every skin
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
                                marker = ''  # text only: readable by screen readers and every skin
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

        title = item.get('title') or item.get('name') or content_id or get_string('result_label')
        thumb = _pick_landscape_thumb(item)

        # Prefix the title with a localized type label so search results
        # indicate their type.
        group = _search_group_key(itype_l, item)
        if group and group != 'other':
            display_title = get_string('group_result_title', _group_label(group), title)
        else:
            display_title = title

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
            add_directory_item(display_title, {'mode': 'play', 'id': item.get('id'), 'fmt': 'live'}, is_folder=False, is_playable=False, thumb=thumb, info=info, content=item)
        else:
            # fallback: treat as series if a seriesId exists, otherwise play
            sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
            if sid:
                add_directory_item(display_title, {'mode': 'series_detail', 'series_id': sid}, is_folder=True, thumb=thumb, info=info, content=item)
            else:
                add_directory_item(display_title, {'mode': 'play', 'id': item.get('id') or content_id}, is_folder=False, thumb=thumb, info=info, content=item)
    _end_directory()


def browse_category(content_type):
    if str(content_type).lower() == 'channels' and not _pin_ok(live=True):
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
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
        results, epg_map = get_channels_menu_data(api)
    else:
        results = api.search(content_type, content_type=content_type)
    for item in results:
        info = None
        try:
            desc = item.get('description') or item.get('subtitle') or ''
            if desc:
                title_for_info = item.get('title') or ''
                expiry_text = None if content_type.lower() == 'channels' else (item.get('expires_in') or None)
                truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                plot_full = desc
                po = truncated
                if expiry_text:
                    marker = ''  # text only: readable by screen readers and every skin
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
                                marker = ''  # text only: readable by screen readers and every skin
                                colored = _make_color_tag(EXPIRY_COLOR_RAW, expiry_text)
                                plot_full = f"{colored}\n{desc}" if desc else colored
                                po = f"{marker}{expiry_text} — {truncated}" if truncated else f"{marker}{expiry_text}"
                            info = {
                                'title': title_for_info,
                                'plot': plot_full,
                                'plotoutline': po,
                            }
                # Attach EPG info for channels (current 'Nu live' and next 'Straks')
                if content_type.lower() == 'channels' and item.get('id'):
                    try:
                        channel_id = item.get('id')
                        channel_epg = epg_map.get(channel_id)

                        # New structure: channel_epg has 'current' and 'next' keys
                        if channel_epg:
                            try:
                                _tz = ZoneInfo('Europe/Amsterdam')
                            except Exception:
                                _tz = timezone.utc
                            now = datetime.now(tz=_tz)
                            now_plus_6 = now + timedelta(hours=6)
                            epg_lines = []
                            for pgm in channel_epg:
                                # only supports python >= 3.7
                                start = datetime.fromisoformat(pgm['start'])
                                end = datetime.fromisoformat(pgm['stop'])
                                if end > now_plus_6:
                                    break
                                if end > now:
                                    epg_lines.append(' - '.join((
                                        start.strftime("%H:%M"),
                                        pgm["title"])))

                            # Update info with EPG data
                            if epg_lines:
                                epg_text = '\n'.join(epg_lines[:12])
                                if info:
                                    info['plotoutline'] = epg_text
                                    info['plot'] = epg_text
                                else:
                                    firstpgm = epg_lines[0].split(" - ", 1)[1]
                                    info = {'title': f"{item.get('title')}   [COLOR orange]{firstpgm}[/COLOR]",
                                            'plotoutline': epg_text, 
                                            'plot': epg_text}
                                    item['title'] = info['title']
                    except (KeyError, TypeError):
                        pass
        except Exception as e:
            info = None
        
        # Determine query mode based on item type
        # Documentaries and Series should open series detail, not try to play directly
        item_type = (item.get('type') or '').lower()
        query = {'mode': 'play', 'id': item.get('id')}
        is_folder = False

        ctype = content_type.lower()
        if ctype == 'documentary':
            add_group = 'documentary'
        elif ctype == 'channels':
            add_group = 'channels'
        elif ctype == 'movies':
            add_group = 'movies'
        else:
            add_group = None

        if item_type == 'series' or ctype == 'documentary':
            # Series and documentaries open as folders with series detail
            query = {'mode': 'series_detail', 'series_id': item.get('id')}
            is_folder = True
        elif ctype == 'channels':
            query['fmt'] = 'live'
            if not item.get('type'):
                item['type'] = 'channel'
        
        add_directory_item(item.get('title'), query, is_folder=is_folder, thumb=_pick_landscape_thumb(item), info=info, content=item, group=add_group)
    _end_directory()


def _search_language():
    try:
        return xbmc.getLanguage(xbmc.ISO_639_1) or 'nl'
    except Exception:
        return 'nl'


def _filtered_search_results(results, q, group, period=None, genre=None):
    """Apply period/genre filters and put a Filter entry on top of the list.

    Returns the filtered results, or None when nothing is left (the listing
    is then already finished with a message).
    """
    t = search_filters.texts(_search_language())
    in_group = [item for item in results
                if str(group or 'all').lower() == 'all'
                or _search_group_key(str(item.get('type') or '').lower(), item) == str(group).lower()]
    periods, genres = search_filters.options(in_group)
    if periods or genres or period or genre:
        label = '{}  [{}]'.format(t['filter'], search_filters.describe(t, period, genre))
        query = {'mode': 'search_filter', 'q': q, 'group': group or 'all'}
        if period:
            query['period'] = period
        if genre:
            query['genre'] = genre
        add_directory_item(label, query, is_folder=False, is_playable=False, thumb=_pick_menu_png_any('search'))
    filtered = search_filters.apply(results, period, genre)
    if (period or genre) and not filtered:
        xbmcgui.Dialog().notification('NLZiet', t['empty'], xbmcgui.NOTIFICATION_INFO)
        _end_directory()
        return None
    return filtered


def _pick_menu_png_any(name):
    try:
        addon_path = xbmc.translatePath(ADDON.getAddonInfo('path')) or ''
    except Exception:
        addon_path = ''
    return kodi_ui.pick_menu_png(addon_path, name)


def search_filter(q, group='all', period=None, genre=None):
    """Ask for a period or genre and reopen the search results with it."""
    t = search_filters.texts(_search_language())
    api = get_api_instance()
    results = api.search(q) or []
    in_group = [item for item in results
                if str(group or 'all').lower() == 'all'
                or _search_group_key(str(item.get('type') or '').lower(), item) == str(group).lower()]
    periods, genres = search_filters.options(in_group)
    if not periods and not genres:
        xbmcgui.Dialog().ok('NLZiet', t['no_data'])
        return
    choices, actions = [], []
    if periods:
        choices.append(t['period'])
        actions.append('period')
    if genres:
        choices.append(t['genre'])
        actions.append('genre')
    if period or genre:
        choices.append(t['clear'])
        actions.append('clear')
    picked = xbmcgui.Dialog().select(t['filter'], choices)
    if picked < 0:
        return
    action = actions[picked]
    if action == 'period':
        labels = [t['all']] + [t[key] for key in periods]
        index = xbmcgui.Dialog().select(t['period'], labels)
        if index < 0:
            return
        period = periods[index - 1] if index > 0 else None
    elif action == 'genre':
        labels = [t['all']] + genres
        index = xbmcgui.Dialog().select(t['genre'], labels)
        if index < 0:
            return
        genre = genres[index - 1] if index > 0 else None
    else:
        period, genre = None, None
    query = {'mode': 'search_group', 'q': q, 'group': group or 'all'}
    if period:
        query['period'] = period
    if genre:
        query['genre'] = genre
    xbmc.executebuiltin('Container.Update({},replace)'.format(build_url(query)))


def search_group(q, group, period=None, genre=None):
    """Show search results filtered to a single group (e.g. 'Series' or 'Movies').

    This re-runs the search (or fallback) and presents only items that match
    the requested group name.
    """
    if not q:
        xbmcgui.Dialog().notification('NLZiet', get_string('missing_search_query'), xbmcgui.NOTIFICATION_INFO)
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
            xbmcgui.Dialog().notification('NLZiet', get_string('no_results', q), xbmcgui.NOTIFICATION_INFO)
            _end_directory()
            return

    results = _filtered_search_results(results, q, group, period, genre)
    if results is None:
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
                    marker = ''  # text only: readable by screen readers and every skin
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
                                marker = ''  # text only: readable by screen readers and every skin
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
        group_name = _search_group_key(itype_l, item)

        if str(group or 'all').lower() != 'all' and str(group_name).lower() != str(group or '').lower():
            continue

        title = item.get('title') or item.get('name') or content_id or get_string('result_label')
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
            add_directory_item(display_title, {'mode': 'play', 'id': item.get('id'), 'fmt': 'live'}, is_folder=False, is_playable=False, thumb=thumb, info=info, content=item)
        else:
            sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
            if sid:
                add_directory_item(display_title, {'mode': 'series_detail', 'series_id': sid}, is_folder=True, thumb=thumb, info=info, content=item)
            else:
                add_directory_item(display_title, {'mode': 'play', 'id': item.get('id') or content_id}, is_folder=False, thumb=thumb, info=info, content=item)
    _end_directory()


def filter_manifest_subtitles(manifest_url):
    """
    Placeholder for future manifest filtering.
    Currently unused - we use player subtitle API instead.
    """
    return manifest_url


class NLZietPlaybackMonitor(xbmc.Player):
    """Player callback helper for live TV subtitle control.

    Keep this callback path non-blocking so stop/back returns to the menu instantly.
    """

    def __init__(self, disable_subs=False):
        super().__init__()
        self.disable_subs = disable_subs
        self.subtitle_disabled = False
        xbmc.log(f"NLZiet: PlaybackMonitor created with disable_subs={disable_subs}", xbmc.LOGINFO)

    def _disable_subtitles_if_needed(self):
        if not self.disable_subs or self.subtitle_disabled:
            return
        try:
            if not self.isPlaying():
                return
            xbmc.log("NLZiet: playback detected, disabling subtitles", xbmc.LOGINFO)
            try:
                self.showSubtitles(False)
                xbmc.log("NLZiet: called player.showSubtitles(False)", xbmc.LOGINFO)
                self.subtitle_disabled = True
            except AttributeError:
                try:
                    self.setSubtitleStream(-1)
                    xbmc.log("NLZiet: called player.setSubtitleStream(-1)", xbmc.LOGINFO)
                    self.subtitle_disabled = True
                except Exception as e:
                    xbmc.log(f"NLZiet: setSubtitleStream failed: {e}", xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log(f"NLZiet PlaybackMonitor subtitle disable exception: {e}", xbmc.LOGWARNING)

    def onPlayBackStarted(self):
        self._disable_subtitles_if_needed()

    def onAVStarted(self):
        # Some Kodi versions trigger onAVStarted more reliably than onPlayBackStarted.
        self._disable_subtitles_if_needed()


def ensure_inputstream_for_drm():
    """Ensure DRM playback dependencies using script.module.inputstreamhelper.

    Returns:
        inputstreamhelper.Helper instance when ready, otherwise None.
    """
    try:
        import inputstreamhelper
    except Exception:
        xbmcgui.Dialog().ok(
            get_string('dependency_missing_title'),
            get_string('dependency_missing_msg')
        )
        return None

    try:
        helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        if helper.check_inputstream():
            return helper
    except Exception as e:
        xbmc.log(f"NLZiet inputstreamhelper check failed: {e}", xbmc.LOGERROR)

    return None


def _prepare_external_subtitles(sub_urls, api=None):
    """Return subtitle locations that are ready for playback.

    Teletext-derived WebVTT files (NPO) are downloaded and cleaned so Kodi
    shows its regular subtitle overlay instead of the teletext page number
    ("888") and yellow/white teletext colours. Anything that cannot be cleaned
    is passed through unchanged, so subtitle handling never blocks playback.
    """
    if not sub_urls:
        return []
    try:
        from resources.lib import subtitles as subtitle_tools

        cache_dir = xbmcvfs.translatePath(
            'special://profile/addon_data/{0}/subtitle_cache'.format(ADDON.getAddonInfo('id'))
        )
        headers = {}
        user_agent = getattr(api, 'user_agent', None) if api else None
        if user_agent:
            headers['User-Agent'] = user_agent
        return subtitle_tools.prepare_subtitle_urls(
            sub_urls,
            cache_dir=cache_dir,
            headers=headers,
            log=lambda message: xbmc.log(message, xbmc.LOGINFO),
        )
    except Exception as exc:
        xbmc.log('NLZiet: subtitle preparation failed: {0}'.format(exc), xbmc.LOGWARNING)
        return list(sub_urls)


# Global playback monitor for live TV subtitle control
_playback_monitor = None

EPG_DAY_COUNT = 4


_epg_playback_active = False
_epg_selected_channel = None
EPG_DAY_BACK = 7
EPG_DAY_FWD = 7


EPG_CACHE_FILE = 'epg_cache.json'
EPG_CHANNELS_TTL = 6 * 3600
EPG_DAY_MAX_AGE = 6 * 3600
EPG_KEEP_DAYS = 4


def _epg_cache_path():
    return os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), EPG_CACHE_FILE)


def _epg_read_cache():
    try:
        with open(_epg_cache_path(), 'r', encoding='utf-8') as cache_file:
            cache = json.load(cache_file)
        return cache if isinstance(cache, dict) else {}
    except Exception:
        return {}


def _epg_write_cache(cache):
    try:
        os.makedirs(os.path.dirname(_epg_cache_path()), exist_ok=True)
        with open(_epg_cache_path(), 'w', encoding='utf-8') as cache_file:
            json.dump(cache, cache_file)
    except Exception as exc:
        xbmc.log('NLZiet EPG cache write failed: {0}'.format(exc), xbmc.LOGWARNING)


def _epg_channels():
    """Return the channel list, served from the disk cache while it is fresh."""
    now_ts = time.time()
    cache = _epg_read_cache()
    entry = cache.get('channels')
    if isinstance(entry, dict) and entry.get('data') and (now_ts - entry.get('ts', 0)) < EPG_CHANNELS_TTL:
        return entry['data']
    channels = get_api_instance().get_channels() or []
    if channels:
        cache['channels'] = {'ts': now_ts, 'data': channels}
        _epg_write_cache(cache)
    return channels


def _epg_day_programs(channel_ids, day_iso, force=False):
    """Return channel_id -> programmes for one day.

    A cached day is used without waiting on the server unless it is older than
    EPG_DAY_MAX_AGE or `force` is set; a failed fetch falls back to the cache.
    """
    now_ts = time.time()
    cache = _epg_read_cache()
    entry = cache.get(day_iso)
    has_entry = isinstance(entry, dict) and bool(entry.get('data'))
    if not force and has_entry and (now_ts - entry.get('ts', 0)) < EPG_DAY_MAX_AGE:
        return entry['data']
    data = get_api_instance().get_current_programs(channel_ids, date=day_iso) or {}
    if not data:
        return entry.get('data') or {} if has_entry else {}
    cache[day_iso] = {'ts': now_ts, 'data': data}
    days = sorted(key for key in cache if key != 'channels')
    for key in days[:-EPG_KEEP_DAYS]:
        del cache[key]
    _epg_write_cache(cache)
    return data


def _epg_rows():
    """Return one row per channel. Programmes are loaded per day by the dialog."""
    try:
        channels = _epg_channels()
    except Exception as exc:
        xbmc.log('NLZiet EPG channel load failed: {0}'.format(exc), xbmc.LOGWARNING)
        channels = []

    rows = []
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        cid = channel.get('id')
        if not cid:
            continue
        rows.append({
            'id': cid,
            'title': channel.get('title') or str(cid),
            'thumb': channel.get('thumb'),
            'entries': [],
        })
    return rows


EPG_CHANNEL_ROWS = 8
EPG_ROW_TOP = 210
EPG_ROW_HEIGHT = 58
EPG_GRID_X = 440
EPG_PX_PER_MIN = 9
EPG_WINDOW_MIN = 150
EPG_BLOCK_SLOTS = 30
EPG_RULER_SLOTS = 7
EPG_MIN_LABEL_WIDTH = 30
EPG_NOW_LINE_WIDTH = 4
EPG_COLOR_PAST = 'FF4A5260'
EPG_COLOR_LIVE = 'FF3366CC'
EPG_COLOR_FUTURE = 'FF2A7F62'


def _epg_now():
    try:
        tz = ZoneInfo('Europe/Amsterdam')
    except Exception:
        tz = timezone.utc
    return datetime.now(tz=tz)


_EPG_DESCRIPTION_CACHE = {}


def _epg_program_description(pgm):
    text = pgm.get('description') or ''
    if text:
        return text
    pid = str(pgm.get('id') or '')
    if not pid:
        return ''
    if pid not in _EPG_DESCRIPTION_CACHE:
        desc = ''
        try:
            detail = get_api_instance().get_content_detail(pid) or {}
            desc = detail.get('description') or ''
        except Exception as exc:
            xbmc.log('NLZiet EPG description lookup failed: {0}'.format(exc), xbmc.LOGWARNING)
        _EPG_DESCRIPTION_CACHE[pid] = desc
    return _EPG_DESCRIPTION_CACHE[pid]


def _epg_full_date(moment):
    try:
        lang = (xbmc.getLanguage(xbmc.ISO_639_1) or '').lower()
    except Exception:
        lang = ''
    if lang.startswith('en'):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                  'August', 'September', 'October', 'November', 'December']
    else:
        days = ['maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag', 'zondag']
        months = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli',
                  'augustus', 'september', 'oktober', 'november', 'december']
    return '{0} {1} {2}'.format(days[moment.weekday()], moment.day, months[moment.month - 1])


def _epg_block_color(start, end, now):
    if end <= now:
        return EPG_COLOR_PAST
    if start <= now:
        return EPG_COLOR_LIVE
    return EPG_COLOR_FUTURE


def _epg_floor_half_hour(moment):
    return moment.replace(minute=30 if moment.minute >= 30 else 0, second=0, microsecond=0)


class _EPGDialog(xbmcgui.WindowXMLDialog):
    """EPG window: channels down the left, programmes on a horizontal timeline."""

    def __init__(self, *args, **kwargs):
        self._rows = kwargs.pop('rows', None) or []
        self._selected_day = 0
        self._row_index = 0
        self._top = 0
        self._prog_index = 0
        self._window_start = None
        self._resume = kwargs.pop('resume', None)
        self._loaded_days = set()
        self._last_position = None
        self._grid_controls = []
        self._layout_key = None
        self._focus_parts = []
        super().__init__(*args, **kwargs)

    @property
    def rows(self):
        return self._rows

    def onInit(self):
        global _epg_selected_channel
        try:
            self.getControl(202).setLabel(get_string('epg_title'))
        except Exception:
            pass
        if not self._rows:
            try:
                self.getControl(204).setLabel('Laden...')
            except Exception:
                pass
            try:
                self._rows = _epg_rows()
            except Exception as exc:
                xbmc.log('NLZiet EPG rows failed: {0}'.format(exc), xbmc.LOGWARNING)
        try:
            self.getControl(203).setLabel('Kanalen: {0}'.format(len(self._rows)))
        except Exception:
            pass
        resume = self._resume
        self._resume = None
        if resume:
            self._selected_day = resume['selected_day']
            self._window_start = resume['window_start']
            self._top = resume['top']
            for i, row in enumerate(self._rows):
                if str(row.get('id') or '') == resume['row_id']:
                    self._row_index = i
                    break
            self._set_day_label()
            self._ensure_day_loaded()
            self._prog_index = self._prog_index_for_key(resume['prog_key'])
        else:
            for i, row in enumerate(self._rows):
                if _epg_selected_channel and str(row.get('id') or '') == str(_epg_selected_channel):
                    self._row_index = i
                    break
            self._reset_window()
            self._ensure_day_loaded()
            self._prog_index = self._default_prog_index()
        self._set_day_label()
        self._render()

    def _ensure_day_loaded(self, force=False):
        target = self._target_day()
        day_iso = target.isoformat()
        if not self._rows or (not force and day_iso in self._loaded_days):
            return
        data = {}
        try:
            channel_ids = [row['id'] for row in self._rows]
            data = _epg_day_programs(channel_ids, day_iso, force=force)
        except Exception as exc:
            xbmc.log('NLZiet EPG day load failed: {0}'.format(exc), xbmc.LOGWARNING)
        if not data:
            return
        self._loaded_days.add(day_iso)
        tzinfo = _epg_now().tzinfo
        for row in self._rows:
            kept = [entry for entry in row['entries'] if entry[0].astimezone(tzinfo).date() != target]
            seen = set((entry[2].get('id'), entry[2].get('start'), entry[2].get('stop')) for entry in kept)
            for pgm in data.get(row['id']) or []:
                try:
                    start = datetime.fromisoformat(pgm['start'])
                    end = datetime.fromisoformat(pgm['stop'])
                except Exception:
                    continue
                key = (pgm.get('id'), pgm.get('start'), pgm.get('stop'))
                if key in seen:
                    continue
                seen.add(key)
                kept.append((start, end, pgm, False))
            kept.sort(key=lambda entry: entry[0])
            row['entries'] = kept

    def _set_day_label(self):
        if self._selected_day == 0:
            text = 'Dag: Vandaag'
        else:
            text = 'Dag: {0}'.format(_epg_full_date(self._target_day()))
        try:
            self.getControl(300).setLabel('{0}   (I)'.format(text))
        except Exception:
            pass


    def _prog_index_for_key(self, key):
        for i, (start, _end, pgm, _is_now) in enumerate(self._row_programs()):
            if (str(pgm.get('id') or ''), start.isoformat()) == key:
                return i
        return self._default_prog_index()

    def position(self):
        return self._last_position

    def _target_day(self):
        return _epg_now().date() + timedelta(days=self._selected_day)

    def _reset_window(self):
        now = _epg_now()
        if self._selected_day == 0:
            self._window_start = _epg_floor_half_hour(now)
        else:
            target = self._target_day()
            self._window_start = datetime(target.year, target.month, target.day, 18, 0, tzinfo=now.tzinfo)

    def _row_programs(self, index=None):
        if index is None:
            index = self._row_index
        if not self._rows:
            return []
        target = self._target_day()
        tzinfo = _epg_now().tzinfo
        return [
            entry for entry in (self._rows[index].get('entries') or [])
            if entry[0].astimezone(tzinfo).date() == target
        ]

    def _default_prog_index(self):
        progs = self._row_programs()
        now = _epg_now()
        for i, (start, end, _pgm, _is_now) in enumerate(progs):
            if start <= now <= end:
                return i
        for i, (_start, end, _pgm, _is_now) in enumerate(progs):
            if end > self._window_start:
                return i
        return 0

    def _add(self, control):
        self._grid_controls.append(control)
        return control

    def _x_at(self, moment):
        return EPG_GRID_X + int((moment - self._window_start).total_seconds() / 60 * EPG_PX_PER_MIN)

    def _block_geometry(self, start, end):
        window_start = self._window_start
        window_end = window_start + timedelta(minutes=EPG_WINDOW_MIN)
        x = self._x_at(max(start, window_start))
        x_end = self._x_at(min(end, window_end))
        return x, max(4, x_end - x - 3)

    def _create_pool(self):
        self._ruler = []
        self._names = []
        self._separators = []
        self._blocks = []
        for _ in range(EPG_RULER_SLOTS):
            self._ruler.append(self._add(xbmcgui.ControlLabel(
                0, 170, 120, 30, '', font='font12', textColor='FF3366CC',
            )))
        for _ in range(EPG_CHANNEL_ROWS):
            self._names.append(self._add(xbmcgui.ControlLabel(
                110, 0, 300, 30, '', font='font12', textColor='FFFFFFFF',
            )))
            self._separators.append(self._add(xbmcgui.ControlImage(
                110, 0, 1700, 1, 'white.png', colorDiffuse='22FFFFFF',
            )))
            row_blocks = []
            for _ in range(EPG_BLOCK_SLOTS):
                image = self._add(xbmcgui.ControlImage(0, 0, 1, 1, 'white.png', colorDiffuse='FF3366CC'))
                label = self._add(xbmcgui.ControlLabel(0, 0, 1, 1, '', font='font12', textColor='FFFFFFFF'))
                row_blocks.append((image, label))
            self._blocks.append(row_blocks)
        self._now_marker = self._add(xbmcgui.ControlImage(0, 0, EPG_NOW_LINE_WIDTH, 1, 'white.png', colorDiffuse='FFFFFFFF'))
        self._focus_parts = [
            self._add(xbmcgui.ControlImage(0, 0, 1, 1, 'white.png', colorDiffuse='FFFFFFFF'))
            for _ in range(4)
        ]
        self.addControls(self._grid_controls)
        for control in self._grid_controls:
            control.setVisible(False)

    def _apply_layout(self):
        window_start = self._window_start
        window_end = window_start + timedelta(minutes=EPG_WINDOW_MIN)
        now = _epg_now()

        try:
            date_label = _localized_weekday(window_start)
            if self._selected_day == 0:
                date_label = 'Vandaag  {0}'.format(date_label)
            self.getControl(201).setLabel(date_label)
        except Exception:
            pass

        for k, label in enumerate(self._ruler):
            mark = window_start + timedelta(minutes=30 * k)
            if mark < window_end:
                label.setPosition(self._x_at(mark) + 4, 170)
                label.setLabel(mark.strftime('%H:%M'))
                label.setVisible(True)
            else:
                label.setVisible(False)

        visible_count = min(EPG_CHANNEL_ROWS, max(0, len(self._rows) - self._top))
        for slot in range(EPG_CHANNEL_ROWS):
            y = EPG_ROW_TOP + slot * EPG_ROW_HEIGHT
            name = self._names[slot]
            separator = self._separators[slot]
            entries = []
            if slot < visible_count:
                i = self._top + slot
                name.setPosition(110, y + 16)
                name.setLabel(self._rows[i].get('title') or '')
                name.setVisible(True)
                separator.setPosition(110, y + EPG_ROW_HEIGHT - 2)
                separator.setVisible(True)
                entries = [
                    entry for entry in self._row_programs(i)
                    if entry[1] > window_start and entry[0] < window_end
                ]
            else:
                name.setVisible(False)
                separator.setVisible(False)

            for k, (image, label) in enumerate(self._blocks[slot]):
                if k >= len(entries):
                    image.setVisible(False)
                    label.setVisible(False)
                    continue
                start, end, pgm, _is_now = entries[k]
                title = pgm.get('title') or ''
                x, w = self._block_geometry(start, end)
                color = _epg_block_color(start, end, now)
                image.setPosition(x, y + 3)
                image.setWidth(w)
                image.setHeight(EPG_ROW_HEIGHT - 6)
                image.setColorDiffuse(color)
                image.setVisible(True)
                if w >= EPG_MIN_LABEL_WIDTH:
                    label.setPosition(x + 8, y + 3)
                    label.setWidth(w - 12)
                    label.setHeight(EPG_ROW_HEIGHT - 6)
                    label.setLabel(title)
                    label.setVisible(True)
                else:
                    label.setVisible(False)

        if window_start <= now < window_end:
            self._now_marker.setPosition(self._x_at(now) - EPG_NOW_LINE_WIDTH // 2, EPG_ROW_TOP - 10)
            self._now_marker.setHeight(EPG_CHANNEL_ROWS * EPG_ROW_HEIGHT + 10)
            self._now_marker.setVisible(True)
        else:
            self._now_marker.setVisible(False)

    def _update_focus(self, progs):
        window_start = self._window_start
        window_end = window_start + timedelta(minutes=EPG_WINDOW_MIN)
        visible = False
        if progs and self._focus_parts:
            start, end, _pgm, _is_now = progs[self._prog_index]
            if end > window_start and start < window_end:
                x, w = self._block_geometry(start, end)
                y = EPG_ROW_TOP + (self._row_index - self._top) * EPG_ROW_HEIGHT
                left, top = x - 2, y + 1
                width, height = w + 4, EPG_ROW_HEIGHT - 2
                bar = 3
                rects = [
                    (left, top, width, bar),
                    (left, top + height - bar, width, bar),
                    (left, top, bar, height),
                    (left + width - bar, top, bar, height),
                ]
                for part, (px, py, pw, ph) in zip(self._focus_parts, rects):
                    part.setPosition(px, py)
                    part.setWidth(pw)
                    part.setHeight(ph)
                    part.setVisible(True)
                visible = True
        if not visible:
            for part in self._focus_parts:
                part.setVisible(False)

    def _update_details(self, progs):
        if progs:
            start, end, pgm, _is_now = progs[self._prog_index]
            channel_title = self._rows[self._row_index].get('title') or ''
            header = '{0} - {1}  {2}  ({3})'.format(
                start.strftime('%H:%M'), end.strftime('%H:%M'), pgm.get('title') or '', channel_title,
            )
            description = _epg_program_description(pgm) or 'Geen beschrijving beschikbaar.'
        else:
            header = 'Geen EPG beschikbaar'
            description = 'Voor dit kanaal zijn geen programma\'s gevonden.'
        try:
            self.getControl(204).setLabel(header)
            self.getControl(205).setText(description)
        except Exception:
            pass

    def _render(self):
        if not self._rows:
            return
        self._row_index = max(0, min(self._row_index, len(self._rows) - 1))
        if self._row_index < self._top:
            self._top = self._row_index
        if self._row_index >= self._top + EPG_CHANNEL_ROWS:
            self._top = self._row_index - EPG_CHANNEL_ROWS + 1
        progs = self._row_programs()
        self._prog_index = max(0, min(self._prog_index, len(progs) - 1)) if progs else 0
        global _epg_selected_channel
        _epg_selected_channel = str(self._rows[self._row_index].get('id') or '')

        if not self._grid_controls:
            self._create_pool()
        layout_key = (self._window_start, self._top, self._selected_day)
        if layout_key != self._layout_key:
            self._apply_layout()
            self._layout_key = layout_key
        self._update_focus(progs)
        self._update_details(progs)

    def _move_row(self, delta):
        if not self._rows:
            return
        self._row_index = max(0, min(self._row_index + delta, len(self._rows) - 1))
        self._prog_index = self._default_prog_index()
        self._render()

    def _move_prog(self, delta):
        progs = self._row_programs()
        if not progs:
            return
        self._prog_index = max(0, min(self._prog_index + delta, len(progs) - 1))
        start, end, _pgm, _is_now = progs[self._prog_index]
        window_end = self._window_start + timedelta(minutes=EPG_WINDOW_MIN)
        if start < self._window_start or end > window_end:
            self._window_start = _epg_floor_half_hour(start)
        self._render()

    def onAction(self, action):
        action_id = action.getId()
        try:
            button_code = action.getButtonCode()
        except Exception:
            button_code = 0
        xbmc.log('NLZiet EPG action_id={0} button_code={1}'.format(action_id, button_code), xbmc.LOGINFO)
        if action_id in (11, 192, 18) or button_code in (61508, 0x44, 68):
            self._select_day()
            return
        if action_id in (9, 10, 92):
            self.close()
            return
        if action_id == 7:
            self._activate()
        elif action_id == 1:
            self._move_prog(-1)
        elif action_id == 2:
            self._move_prog(1)
        elif action_id == 3:
            self._move_row(-1)
        elif action_id == 4:
            self._move_row(1)
        elif action_id == 5:
            self._move_row(-EPG_CHANNEL_ROWS)
        elif action_id == 6:
            self._move_row(EPG_CHANNEL_ROWS)

    def _activate(self):
        progs = self._row_programs()
        if not progs:
            return
        start, end, pgm, is_now = progs[self._prog_index]
        channel_id = str(self._rows[self._row_index].get('id') or '')
        image = pgm.get('image') or ''
        mode = 'epg' if pgm.get('is_replay') else ('vod' if pgm.get('is_vod') else 'live')
        self._last_position = {
            'row_id': channel_id,
            'top': self._top,
            'selected_day': self._selected_day,
            'window_start': self._window_start,
            'prog_key': (str(pgm.get('id') or ''), start.isoformat()),
        }
        self._show_program_menu(
            channel_id,
            str(pgm.get('id') or ''),
            str(pgm.get('asset_id') or ''),
            mode,
            pgm.get('title') or '',
            image,
            start <= _epg_now() <= end,
            start > _epg_now(),
            bool(pgm.get('is_vod')),
            end <= _epg_now(),
            start <= _epg_now(),
            pgm.get('description') or pgm.get('plot') or '',
        )

    def _select_day(self):
        try:
            now = _epg_now().date()
            options = []
            for i in range(-EPG_DAY_BACK, EPG_DAY_FWD + 1):
                d = now + timedelta(days=i)
                if i == 0:
                    options.append('Vandaag ({0})'.format(d.strftime('%d-%m')))
                elif i == 1:
                    options.append('Morgen ({0})'.format(d.strftime('%d-%m')))
                elif i == -1:
                    options.append('Gisteren ({0})'.format(d.strftime('%d-%m')))
                else:
                    options.append(d.strftime('%a %d-%m'))
            # offset in options corresponds to i+EPG_DAY_BACK
            choice = xbmcgui.Dialog().select('Selecteer dag', options)
            if choice < 0:
                return
            self._selected_day = choice - EPG_DAY_BACK
            self._reset_window()
            self._set_day_label()
            self._ensure_day_loaded(force=True)
            self._prog_index = self._default_prog_index()
            self._render()
        except Exception:
            pass

    def _show_program_menu(self, channel_id, program_id, asset_id, mode, title, thumb, is_now=False, is_future=False, watch_later_vod=False, aired=False, started=False, description=''):
        options = []
        actions = []
        if is_now and channel_id:
            options.append('Nu live kijken')
            actions.append('play_live')
        if mode == 'epg' and program_id and not is_future:
            options.append('Speel vanaf begin' if is_now else 'Afspelen (terugkijken)')
            actions.append('play_replay')
        elif mode == 'vod' and program_id:
            options.append('Afspelen')
            actions.append('play_vod')
        if program_id:
            options.append(get_string('add_to_my_series'))
            actions.append('my_series')
            options.append(get_string('add_to_watch_later'))
            actions.append('watch_later')
        options.append('Annuleren')
        actions.append('cancel')
        choice = xbmcgui.Dialog().select(title or 'Programma', options)
        if choice < 0:
            return
        action = actions[choice]
        if action == 'cancel':
            return
        global _epg_playback_active
        _epg_playback_active = action.startswith('play')
        self.close()
        xbmc.executebuiltin('Dialog.Close(all,true)')
        import time
        time.sleep(0.5)
        if action == 'play_replay':
            _play_media_url(build_url({
                'mode': 'play',
                'id': program_id,
                'fmt': 'epg',
                'asset_id': asset_id,
                'channel': channel_id,
                'thumb': thumb or '',
                'title': title or '',
            }), noresume=True)
        elif action == 'play_vod':
            _play_media_url(build_url({
                'mode': 'play',
                'id': program_id,
            }))
        elif action == 'play_live':
            _play_media_url(build_url({
                'mode': 'play',
                'id': channel_id,
                'fmt': 'live',
            }), noresume=True)
        if action == 'my_series':
            toggle_my_series(program_id, title, None, thumb, 'series', description=description)
            return
        elif action == 'watch_later':
            toggle_watch_later(program_id, title, 'episode', thumb, 'episodes', replay_ok=watch_later_vod, aired=aired, started=started, description=description or '')
            return




def _epg_wait_for_playback_end():
    """Block until playback started from the EPG has finished. Returns False if it never started."""
    waited = 0.0
    while not xbmc.Player().isPlaying():
        if waited >= 20:
            return False
        xbmc.sleep(500)
        waited += 0.5
    while xbmc.Player().isPlaying():
        xbmc.sleep(1000)
    return True


def browse_epg():
    """Show the custom EPG window, falling back to a directory list."""
    global _epg_playback_active
    if not _pin_ok(live=True):
        return
    # Install the 'D' hotkey keymap for the EPG day selector (best-effort).
    try:
        import shutil
        src = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'keymaps', 'keyboard.xml')
        dst_dir = xbmc.translatePath('special://profile/keymaps/')
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, 'nlziet_epg.xml')
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copyfile(src, dst)
    except Exception:
        pass
    try:
        dialog = _EPGDialog(
            'epg.xml',
            ADDON.getAddonInfo('path'),
            'Default',
            '1080i',
        )
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        dialog.doModal()
        rows = dialog.rows
        resume = dialog.position()
        del dialog
        while _epg_playback_active:
            _epg_playback_active = False
            if not _epg_wait_for_playback_end():
                break
            dialog = _EPGDialog(
                'epg.xml',
                ADDON.getAddonInfo('path'),
                'Default',
                '1080i',
                rows=rows,
                resume=resume,
            )
            dialog.doModal()
            resume = dialog.position()
            del dialog
        return
    except Exception as exc:
        xbmc.log('NLZiet EPG dialog failed, using list: {0}'.format(exc), xbmc.LOGWARNING)
    try:
        return _browse_epg_impl()
    except Exception as exc:
        xbmc.log('NLZiet browse_epg failed: {0}'.format(exc), xbmc.LOGERROR)
        try:
            _end_directory()
        except Exception:
            pass


def _browse_epg_impl():
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    try:
        api = get_api_instance()
    except Exception:
        api = NLZietAPI(username=username, password=password)

    try:
        channels = api.get_channels() or []
    except Exception:
        channels = []
    channel_ids = [c.get('id') for c in channels if isinstance(c, dict) and c.get('id')]
    try:
        epg_map = api.get_current_programs(channel_ids) if channel_ids else {}
    except Exception:
        epg_map = {}

    channel_by_id = {c.get('id'): c for c in channels if isinstance(c, dict)}

    try:
        _tz = ZoneInfo('Europe/Amsterdam')
    except Exception:
        _tz = timezone.utc
    now = datetime.now(tz=_tz)

    for cid in channel_ids:
        channel = channel_by_id.get(cid) or {}
        channel_title = channel.get('title') or str(cid)
        for pgm in epg_map.get(cid) or []:
            try:
                start = datetime.fromisoformat(pgm['start'])
                end = datetime.fromisoformat(pgm['stop'])
            except Exception:
                continue
            if end < now - timedelta(hours=1):
                continue
            if start > now + timedelta(hours=12):
                continue
            label = '{channel}  {start}-{end}  {title}'.format(
                channel=channel_title,
                start=start.strftime('%H:%M'),
                end=end.strftime('%H:%M'),
                title=pgm.get('title') or '',
            )
            query = {}
            stream = pgm.get('stream')
            if stream:
                # extract mode/id if plugin url
                query = {'mode': 'play', 'id': None}
                # fallback: play via stream url directly
                item_url = stream
            else:
                item_url = None
            thumb = pgm.get('image')
            info = {'title': pgm.get('title') or '', 'plot': pgm.get('title') or ''}
            if item_url:
                add_directory_item(label, {'mode': 'play', 'id': _extract_id_from_stream(stream)}, is_folder=False, thumb=thumb, info=info)
            else:
                add_directory_item(label, {'mode': 'browse_epg'}, is_folder=False, thumb=thumb, info=info)
    _end_directory()


def _extract_id_from_stream(stream):
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(stream)
        qs = urllib.parse.parse_qs(parsed.query)
        ids = qs.get('id')
        if ids:
            return ids[0]
    except Exception:
        pass
    return ''


# ------------------------------------------------- while a video plays ---

def _after_playback_started(api, content_id, fmt, metadata, stream_info):
    """Things that run next to playback: watched status, skip intro, Up Next.

    Nothing here may delay or break playback, so every part is guarded.
    """
    if fmt == 'live' or not content_id:
        return
    try:
        # The background service follows playback and sends "watched" to
        # NLZiet when this video is (almost) finished.
        xbmcgui.Window(10000).setProperty(
            watch_sync.PLAYING_PROPERTY.format('nlziet'), watch_sync.playing_value(content_id))
    except Exception:
        pass
    if fmt == 'epg':
        return
    try:
        meta = metadata or {}
        watch_history.record(_history_path(), {
            'id': content_id, 'title': meta.get('showtitle') or meta.get('title') or '',
            'subtitle': meta.get('title') if meta.get('showtitle') else '',
            'thumb': meta.get('thumb') or '', 'media_type': meta.get('media_type') or ''})
    except Exception:
        pass
    markers = {}
    try:
        chapters = api.get_chapters(content_id)
        markers = playback_extras.markers_from_chapters(chapters)
        if not markers:
            markers = playback_extras.find_markers(stream_info)
        xbmc.log('NLZiet {}: chapters {} -> markers found: {}'.format(
            content_id, playback_extras.chapter_titles(chapters)[:12],
            playback_extras.marker_summary(markers)), xbmc.LOGINFO)
    except Exception as exc:
        xbmc.log('NLZiet chapters failed: {}'.format(exc), xbmc.LOGINFO)
    if markers and _setting_on('skip_markers', True):
        def ask(kind):
            text = get_string('skip_recap_question' if kind == 'recap' else 'skip_intro_question')
            return xbmcgui.Dialog().yesno('NLZiet', text, autoclose=8000)
        try:
            playback_extras.start_skip_watcher(markers, ask)
        except Exception as exc:
            xbmc.log('NLZiet skip watcher failed: {}'.format(exc), xbmc.LOGINFO)
    if _setting_on('upnext', True) and playback_extras.upnext_available():
        playback_extras.start_background(
            lambda: _announce_next_episode(api, content_id, metadata or {}, stream_info, markers),
            'NLZietUpNext')


def _next_episode_for(api, content_id, metadata, stream_info):
    """(current_info, next_info, play_query) for Up Next, or None.

    Order of sources: the Kodi library (exact numbering), the series
    episode list from NLZiet, then NLZiet's surrounding-episodes answer.
    """
    showtitle = metadata.get('showtitle') or ''
    try:
        found = library_mod.next_library_episode(_get_library().store, content_id)
    except Exception:
        found = None
    if found:
        _sid, entry, (cur_s, cur_e), next_id, (next_s, next_e) = found
        showtitle = entry.get('title') or showtitle
        current = playback_extras.episode_info(metadata.get('title') or '', showtitle, cur_s, cur_e,
                                               episode_id=str(content_id))
        art = {'thumb': entry.get('thumb') or '', 'tvshow.poster': entry.get('thumb') or ''}
        following = playback_extras.episode_info(
            get_string('episode_label', next_e),
            showtitle, next_s, next_e, art=art, episode_id=str(next_id))
        query = {'mode': 'play', 'id': next_id, 'media_type': 'episode', 'showtitle': showtitle,
                 'season': str(next_s), 'episode': str(next_e)}
        return current, following, query
    if not showtitle and not metadata.get('season'):
        return None   # not an episode
    content = _handshake_metadata_content(stream_info) or {}
    series_id = content.get('seriesId') or content.get('series_id')
    following = None
    if series_id:
        try:
            episodes = api.get_series_episodes(series_id, limit=400) or []
            ids = [str(ep.get('id') or '') for ep in episodes]
            if str(content_id) in ids:
                index = ids.index(str(content_id))
                following = episodes[index + 1] if index + 1 < len(episodes) else None
                if following is None:
                    return None
        except Exception as exc:
            xbmc.log('NLZiet Up Next: episode list failed: {}'.format(exc), xbmc.LOGINFO)
    if following is None:
        following = library_mod.next_from_surrounding(api.get_surrounding_episodes(content_id), content_id)
    if not following or not following.get('id'):
        return None
    try:
        cur_s, cur_e = int(metadata.get('season') or 0), int(metadata.get('episode') or 0)
    except (TypeError, ValueError):
        cur_s, cur_e = 0, 0
    next_s = following.get('season') or following.get('seasonNumber') or cur_s
    next_e = following.get('episode') or following.get('episodeNumber') or (cur_e + 1 if cur_e else 0)
    current = playback_extras.episode_info(metadata.get('title') or '', showtitle, cur_s, cur_e,
                                           episode_id=str(content_id))
    thumb = _pick_landscape_thumb(following) or ''
    nxt = playback_extras.episode_info(
        following.get('subtitle') or following.get('title') or '', showtitle, next_s, next_e,
        plot=following.get('description') or '', art={'thumb': thumb}, episode_id=str(following['id']))
    query = {'mode': 'play', 'id': following['id']}
    return current, nxt, query


def _announce_next_episode(api, content_id, metadata, stream_info, markers):
    try:
        found = _next_episode_for(api, content_id, metadata, stream_info)
        if not found:
            xbmc.log('NLZiet Up Next: no next episode for {}'.format(content_id), xbmc.LOGINFO)
            return
        current, following, query = found
        player = xbmc.Player()
        if not playback_extras.wait_for_playback(player):
            return
        notify_at = None
        credits = markers.get('credits') if markers else None
        if credits and credits[0]:
            try:
                total = player.getTotalTime()
                if total > credits[0]:
                    notify_at = total - credits[0]
            except Exception:
                pass
        sent = playback_extras.send_upnext(ADDON.getAddonInfo('id'), current, following,
                                           build_url(query), notify_at)
        xbmc.log('NLZiet Up Next: next episode {} announced={}'.format(query.get('id'), sent), xbmc.LOGINFO)
    except Exception as exc:
        xbmc.log('NLZiet Up Next skipped: {}'.format(exc), xbmc.LOGINFO)


# ------------------------------------------------- binge / shuffle / history ---

STOP_AFTER_PROPERTY = 'nlziet.stop_after'


def _history_path():
    return os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'watch_history.json')


def _next_play_query(api, content_id):
    """A {'mode':'play',...} query for the episode after ``content_id``, or None."""
    try:
        found = library_mod.next_library_episode(_get_library().store, content_id)
    except Exception:
        found = None
    if found:
        _sid, entry, _cur, next_id, (next_s, next_e) = found
        return {'mode': 'play', 'id': next_id, 'media_type': 'episode',
                'showtitle': entry.get('title') or '', 'season': str(next_s), 'episode': str(next_e)}
    try:
        nxt = library_mod.next_from_surrounding(api.get_surrounding_episodes(content_id), content_id)
    except Exception:
        nxt = None
    if nxt and nxt.get('id'):
        return {'mode': 'play', 'id': nxt['id']}
    return None


def play_next(content_id, background=False):
    """Start the next episode (used by binge mode from the service)."""
    if not content_id:
        return
    query = _next_play_query(get_api_instance(), content_id)
    if query:
        xbmc.executebuiltin('PlayMedia({})'.format(build_url(query)))
    elif not background:
        xbmcgui.Dialog().notification('NLZiet', get_string('shuffle_none'), xbmcgui.NOTIFICATION_INFO)


def toggle_stop_after():
    """Cancel/allow the automatic next episode for the current session."""
    window = xbmcgui.Window(10000)
    if window.getProperty(STOP_AFTER_PROPERTY) == '1':
        window.clearProperty(STOP_AFTER_PROPERTY)
        xbmcgui.Dialog().notification('NLZiet', get_string('stop_after_cleared'), xbmcgui.NOTIFICATION_INFO, 3000)
    else:
        window.setProperty(STOP_AFTER_PROPERTY, '1')
        xbmcgui.Dialog().notification('NLZiet', get_string('stop_after_set'), xbmcgui.NOTIFICATION_INFO, 3000)


def shuffle_series(series_id):
    """Play a random episode of a series."""
    if not series_id:
        return
    api = get_api_instance()
    try:
        _title, episodes = _collect_series_episodes(api, series_id)
    except Exception:
        episodes = []
    choice = watch_history.pick_random(episodes)
    if not choice:
        xbmcgui.Dialog().notification('NLZiet', get_string('shuffle_none'), xbmcgui.NOTIFICATION_INFO)
        return
    query = {'mode': 'play', 'id': choice['id']}
    if choice.get('title'):
        query['title'] = choice.get('subtitle') or choice.get('title')
    xbmc.executebuiltin('PlayMedia({})'.format(build_url(query)))


def browse_history():
    """Show what was watched (local, this device only)."""
    items = watch_history.entries(_history_path())
    if not items:
        add_directory_item(get_string('history_empty'), {'mode': 'history'}, is_folder=False, is_playable=False)
    else:
        add_directory_item(get_string('history_clear'), {'mode': 'clear_history'}, is_folder=False, is_playable=False)
    for row in items:
        label = row.get('title') or row.get('id')
        if row.get('subtitle'):
            label = '{} - {}'.format(label, row['subtitle'])
        info = {'title': label}
        add_directory_item(label, {'mode': 'play', 'id': row.get('id')}, is_folder=False,
                           thumb=row.get('thumb'), info=info)
    _end_directory()


def clear_history():
    watch_history.clear(_history_path())
    xbmcgui.Dialog().notification('NLZiet', get_string('history_cleared'), xbmcgui.NOTIFICATION_INFO, 3000)
    try:
        xbmc.executebuiltin('Container.Refresh')
    except Exception:
        pass


def record_history(content_id, title='', subtitle='', thumb='', media_type='', background=True):
    """Add one watched item to the local history (called by the service)."""
    if not content_id:
        return
    watch_history.record(_history_path(), {'id': content_id, 'title': title, 'subtitle': subtitle,
                                           'thumb': thumb, 'media_type': media_type})


def remote_watched(content_id, watched='1', background=False):
    """Tell NLZiet an episode/film was watched (or not). Started by the service."""
    if not content_id or not _setting_on('watched_to_service', True) or not _is_logged_in():
        return
    flag = str(watched) not in ('0', 'false', '')
    ok = get_api_instance().set_watched(content_id, flag)
    xbmc.log('NLZiet: watched status {} for {} sent to NLZiet: {}'.format(
        'on' if flag else 'off', content_id, 'ok' if ok else 'failed'),
        xbmc.LOGINFO if ok else xbmc.LOGWARNING)
    if not background and ok:
        xbmcgui.Dialog().notification('NLZiet', get_string('watched_sent'), xbmcgui.NOTIFICATION_INFO, 3000)


def play_item(content_id, fmt=None, **kwargs):
    if fmt in ('live', 'epg') and not _pin_ok(live=True):
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance - still makes the stream info call but avoids object init overhead
    try:
        api = get_api_instance()
    except Exception:
        # Fallback to creating a new instance if cache fails
        api = NLZietAPI(username=username, password=password)
    xbmc.log(f"NLZiet play_item called: id={content_id} fmt={fmt}", xbmc.LOGINFO)
    # Stored list items (Watch Later / My List) are played by id only, so look
    # their title, description and artwork up from the local lists so the OSD
    # and Trakt metadata are complete.
    if fmt not in ('live', 'epg') and not kwargs.get('title'):
        try:
            api_local = get_api_instance()
            for fetcher in (getattr(api_local, 'get_watch_later', None), getattr(api_local, 'get_my_list', None)):
                if not callable(fetcher):
                    continue
                for item in (fetcher() or []):
                    if str(item.get('id')) == str(content_id):
                        if item.get('title'):
                            kwargs.setdefault('title', item.get('title'))
                        desc = item.get('description') or ''
                        if desc:
                            kwargs.setdefault('plot', desc)
                            kwargs.setdefault('description', desc)
                        thumb = item.get('thumb') or item.get('posterUrl')
                        if thumb:
                            kwargs.setdefault('thumb', thumb)
                        break
                if kwargs.get('title'):
                    break
        except Exception:
            pass
    if fmt == 'live':
        # Kodi stores a resume bookmark (live streams look like VOD). Remove
        # it so playback never offers "Resume from …" and starts at 0:00:00.
        _clear_resume_bookmark(content_id)
        info = api.get_stream_info(content_id, context='Live')
        try:
            # Look up the current programme's description so the OSD can show it.
            epg_map = api.get_current_programs([content_id]) or {}
            now_pgm = None
            for pgm in epg_map.get(content_id) or []:
                try:
                    from datetime import datetime as _dt
                    start = _dt.fromisoformat(pgm['start'])
                    end = _dt.fromisoformat(pgm['stop'])
                    if start <= _dt.now(start.tzinfo) <= end:
                        now_pgm = pgm
                        break
                except Exception:
                    pass
            if now_pgm:
                desc = now_pgm.get('description') or now_pgm.get('plot') or ''
                if desc:
                    kwargs.setdefault('description', desc)
                    kwargs.setdefault('plot', desc)
        except Exception:
            pass
        xbmc.log(f"NLZiet LIVE TV: id={content_id} context='Live'", xbmc.LOGINFO)
        # Build playback metadata so the OSD shows channel + current programme.
        try:
            channels = api.get_channels() or []
            channel_title = next((c.get('title') for c in channels if isinstance(c, dict) and c.get('id') == content_id), None) or content_id
            channel_thumb = next((c.get('thumb') for c in channels if isinstance(c, dict) and c.get('id') == content_id), None)
            epg_map = api.get_current_programs([content_id]) or {}
            now_pgm = None
            for pgm in epg_map.get(content_id) or []:
                try:
                    from datetime import datetime as _dt
                    start = _dt.fromisoformat(pgm['start'])
                    end = _dt.fromisoformat(pgm['stop'])
                    if start <= _dt.now(start.tzinfo) <= end:
                        now_pgm = pgm
                        break
                except Exception:
                    pass
            kwargs.setdefault('title', channel_title)
            if channel_thumb:
                kwargs.setdefault('thumb', channel_thumb)
            if now_pgm:
                if now_pgm.get('title'):
                    kwargs['title'] = now_pgm.get('title')
                kwargs.setdefault('plot', now_pgm.get('description') or now_pgm.get('plot') or now_pgm.get('title') or '')
                kwargs.setdefault('programme', now_pgm.get('title') or '')
                if now_pgm.get('image'):
                    kwargs['thumb'] = now_pgm.get('image')
            xbmc.log('NLZiet LIVE metadata: title={0} plot={1} thumb={2}'.format(
                kwargs.get('title'), kwargs.get('plot'), kwargs.get('thumb')), xbmc.LOGINFO)
        except Exception as exc:
            xbmc.log('NLZiet LIVE metadata failed: {0}'.format(exc), xbmc.LOGWARNING)
    elif fmt == 'epg':
        # Replay must also start at 0:00:00 without a resume prompt.
        _clear_resume_bookmark(content_id)
        stream_kwargs = {k: v for k, v in (kwargs or {}).items() if k in ('asset_id', 'channel')}
        info = api.get_stream_info(content_id, context='Epg', **stream_kwargs)
        # Use the programme icon/title passed from the EPG when available.
        try:
            if not kwargs.get('title'):
                kwargs.setdefault('title', info.get('title') or '')
            if not kwargs.get('plot'):
                kwargs.setdefault('plot', info.get('description') or info.get('plot') or kwargs.get('title') or '')
            if kwargs.get('description') and not kwargs.get('plot'):
                kwargs['plot'] = kwargs['description']
            if not kwargs.get('thumb'):
                img = info.get('image') or {}
                kwargs.setdefault('thumb', info.get('posterUrl') or img.get('landscapeUrl') or img.get('portraitUrl') or '')
        except Exception:
            pass
    else:
        info = api.get_stream_info(content_id)
        xbmc.log(f"NLZiet REGULAR content: id={content_id} (not live)", xbmc.LOGINFO)
    manifest = info.get('manifest')
    playback_metadata = _merge_playback_metadata(
        kwargs, info, api=api, content_id=content_id
    ) if fmt != 'live' else kwargs
    is_drm = info.get('is_drm')
    # Replay of a live programme: the API returns a live (dynamic) stream that
    # starts at the live edge. Seek to the beginning (0:00:00) so the programme
    # plays from the start instead of jumping to realtime. Only seek for live
    # (dynamic) streams; VOD replays already start at 0.
    is_live_replay = fmt == 'epg' and 'start=' in str(manifest or '')
    xbmc.log('NLZiet replay: is_live_replay={0}'.format(is_live_replay), xbmc.LOGINFO)
    if is_live_replay:
        try:
            import threading
            import json as _json
            def _seek_replay_to_start():
                for _ in range(60):
                    try:
                        state = xbmc.executeJSONRPC(_json.dumps({
                            'jsonrpc': '2.0', 'method': 'Player.GetProperties',
                            'params': {'playerid': 1, 'properties': ['speed']},
                            'id': 1,
                        }))
                        res = _json.loads(state).get('result', {})
                        if res.get('speed', 0) != 0:
                            break
                    except Exception:
                        pass
                    time.sleep(0.5)
                else:
                    return
                time.sleep(1)
                try:
                    xbmc.executeJSONRPC(_json.dumps({
                        'jsonrpc': '2.0', 'method': 'Player.Seek',
                        'params': {'playerid': 1, 'value': {'percentage': 0}},
                        'id': 1,
                    }))
                    xbmc.log('NLZiet replay seek to 0:00:00 done', xbmc.LOGINFO)
                except Exception as exc:
                    xbmc.log(f'NLZiet replay seek failed: {exc}', xbmc.LOGWARNING)
            import time
            threading.Thread(target=_seek_replay_to_start, daemon=True).start()
        except Exception:
            pass
    subs_in_info = info.get('subtitles')
    xbmc.log(f"NLZiet play_item: id={content_id} manifest={manifest} is_drm={is_drm} fmt={fmt} has_subs={bool(subs_in_info)}", xbmc.LOGINFO)
    xbmc.log(f"NLZiet info subtitles value: {repr(subs_in_info)} (type: {type(subs_in_info).__name__})", xbmc.LOGINFO)
    if not manifest:
        xbmcgui.Dialog().notification('NLZiet', get_string('no_manifest'), xbmcgui.NOTIFICATION_ERROR)
        return

    # Check subtitle setting once for all processing
    try:
        enable_subs = ADDON.getSetting('subtitles_default')
        xbmc.log(f"NLZiet DEBUG subtitles_default raw value: {repr(enable_subs)} (type: {type(enable_subs).__name__})", xbmc.LOGINFO)
    except Exception as e:
        enable_subs = None
        xbmc.log(f"NLZiet ERROR reading subtitles_default: {e}", xbmc.LOGINFO)
    
    # Convert to boolean - handle all possible Kodi return values
    # Note: Kodi may return '0'/'1' or 'false'/'true' or boolean values
    if enable_subs is None or enable_subs == '' or enable_subs == 'false' or enable_subs == '0' or enable_subs is False:
        subs_enabled = False
    elif enable_subs == 'true' or enable_subs == '1' or enable_subs is True:
        subs_enabled = True
    else:
        # Fallback: try string parsing
        subs_enabled = str(enable_subs).lower().strip() in ('true', '1', 'yes', 'on')
    
    xbmc.log(f"NLZiet subtitles setting: raw={repr(enable_subs)} -> enabled={subs_enabled}", xbmc.LOGINFO)
    is_live = (fmt == 'live')
    xbmc.log(f"NLZiet play_item: fmt={fmt} is_live={is_live} subs_enabled={subs_enabled}", xbmc.LOGINFO)
    
    # For live TV with subtitles disabled: use a playback monitor to disable subs when play starts
    # This prevents inputstream.adaptive from auto-loading subtitle tracks from the manifest
    global _playback_monitor
    if is_live and not subs_enabled:
        xbmc.log(f"NLZiet LIVE TV: subtitle monitor enabled to disable subs on playback start", xbmc.LOGINFO)
        _playback_monitor = NLZietPlaybackMonitor(disable_subs=True)
    else:
        _playback_monitor = None

    if info.get('is_drm'):
        is_helper = ensure_inputstream_for_drm()
        if not is_helper:
            return
        li = xbmcgui.ListItem(path=manifest, offscreen=True)
        _apply_playback_metadata(li, playback_metadata, fmt=fmt)
        # Use the inputstream addon resolved by InputStream Helper.
        try:
            inputstream_addon = is_helper.inputstream_addon
        except Exception:
            inputstream_addon = 'inputstream.adaptive'

        # prefer new property if available
        li.setProperty('inputstream', inputstream_addon)
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
            xbmcgui.Dialog().notification('NLZiet', get_string('required_drm', drm_security), xbmcgui.NOTIFICATION_INFO)

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
            
            if sub_urls and subs_enabled:
                xbmc.log(f"NLZiet attaching subtitles: {sub_urls}", xbmc.LOGINFO)
                try:
                    li.setSubtitles(_prepare_external_subtitles(sub_urls, api=api))
                except Exception as e:
                    xbmc.log(f"NLZiet subtitle attach failed: {e}", xbmc.LOGINFO)
                    # fallback: store as property for debugging or later handling
                    try:
                        li.setProperty('nlziet.subtitles', ';'.join(sub_urls))
                    except Exception:
                        pass
            elif sub_urls and not subs_enabled:
                xbmc.log(f'NLZiet: external subtitles found but disabled in settings', xbmc.LOGINFO)
            else:
                xbmc.log(f'NLZiet: no external subtitles in stream response', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"NLZiet exception in subtitle handling: {e}", xbmc.LOGINFO)
            pass

        # do not override inputstream's PSSH handling by supplying malformed
        # `inputstream.adaptive.license_data`. The canonical `license_key` and
        # `stream_headers` are sufficient; leaving `license_data` unset avoids
        # the plugin trying to parse incorrect PSSH data from this property.

        li.setMimeType('application/dash+xml')
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
        _after_playback_started(api, content_id, fmt, playback_metadata, info)
    else:
        # non-DRM: simply play the manifest URL
        xbmc.log(f"NLZiet non-DRM manifest: {manifest}", xbmc.LOGDEBUG)
        li = xbmcgui.ListItem(path=manifest)
        _apply_playback_metadata(li, playback_metadata, fmt=fmt)
        
        # Check subtitle setting once
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
        
        xbmc.log(f"NLZiet non-DRM subtitles setting: raw={repr(enable_subs)} -> enabled={subs_enabled}", xbmc.LOGINFO)
        
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
            
            if sub_urls and subs_enabled:
                xbmc.log(f"NLZiet non-DRM attaching subtitles: {sub_urls}", xbmc.LOGINFO)
                try:
                    li.setSubtitles(_prepare_external_subtitles(sub_urls, api=api))
                except Exception as e:
                    xbmc.log(f"NLZiet non-DRM subtitle attach failed: {e}", xbmc.LOGINFO)
            elif sub_urls:
                xbmc.log(f'NLZiet non-DRM: external subtitles found but disabled in settings', xbmc.LOGINFO)
            else:
                xbmc.log(f'NLZiet non-DRM: no subtitles in stream response', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"NLZiet exception in non-DRM subtitle handling: {e}", xbmc.LOGINFO)
        
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
        _after_playback_started(api, content_id, fmt, playback_metadata, info)


# ----------------------------------------------- search both services ---

OTHER_SERVICE_ID = 'plugin.video.videoland.nl'


def _add_other_service_search(query):
    """Top line in the search results: the same search in Videoland."""
    try:
        if not xbmc.getCondVisibility('System.HasAddon({})'.format(OTHER_SERVICE_ID)):
            return
    except Exception:
        return
    target = 'plugin://{}/?{}'.format(OTHER_SERVICE_ID, urllib.parse.urlencode({'action': 'search', 'query': query}))
    li = xbmcgui.ListItem(label='[B]{}[/B]: {}'.format(get_string('search_other_service'), query))
    li.setArt({'icon': 'special://home/addons/{}/icon.png'.format(OTHER_SERVICE_ID),
               'thumb': 'special://home/addons/{}/icon.png'.format(OTHER_SERVICE_ID)})
    xbmcplugin.addDirectoryItem(HANDLE, target, li, isFolder=True)


# ----------------------------------------------------------- widgets ---

WIDGET_LISTS = (
    ('continue', 'continue_watching', 'continue'),
    ('watch_later', 'watch_later', 'watchlater'),
    ('my_series', 'my_series', 'myseries'),
    ('my_list', 'my_list', 'mylist'),
    ('history', 'watch_history', 'continue'),
)


def widgets_menu():
    """Ready-made lists for the skin's home screen widgets."""
    for name, label_key, icon in WIDGET_LISTS:
        add_directory_item(get_string(label_key), {'mode': 'widget', 'list': name},
                           is_folder=True, thumb=_pick_menu_png_any(icon),
                           info={'plot': get_string('widgets_help')})
    _end_directory()


def widget_list(name):
    """One widget list: only the titles, fast, and never a pop-up."""
    items = []
    if name == 'history':
        for row in watch_history.entries(_history_path()):
            label = row.get('title') or row.get('id')
            if row.get('subtitle'):
                label = '{} - {}'.format(label, row['subtitle'])
            add_directory_item(label, {'mode': 'play', 'id': row.get('id')}, is_folder=False,
                               thumb=row.get('thumb'), info={'title': label})
        _end_directory()
        return
    try:
        if name == 'continue':
            items = get_api_instance().get_continue_watching() or []
        else:
            api = _get_list_api()
            getter = {'watch_later': api.get_watch_later, 'my_series': api.get_my_series,
                      'my_list': api.get_my_list}.get(name)
            items = (getter() if getter else []) or []
    except Exception as exc:
        xbmc.log('NLZiet widget {} failed: {}'.format(name, exc), xbmc.LOGWARNING)
    for item in items:
        if not isinstance(item, dict) or not item.get('id'):
            continue
        group = str(item.get('group') or '').lower()
        kind = str(item.get('type') or '').lower()
        title = item.get('title') or ''
        info = {'title': title, 'plot': item.get('description') or ''}
        thumb = item.get('thumb') or item.get('posterUrl') or _pick_landscape_thumb(item)
        if group == 'series' or 'series' in kind and 'episode' not in kind:
            add_directory_item(title, {'mode': 'series_detail', 'series_id': item['id']},
                               is_folder=True, thumb=thumb, info=info, content=item)
        elif group == 'channels':
            continue
        else:
            add_directory_item(title, {'mode': 'play', 'id': item['id']}, is_folder=False,
                               thumb=thumb, info=info, content=item)
    _end_directory()


# ------------------------------------------------- backup and restore ---

BACKUP_SETTINGS_SKIP = ('password', 'username', 'parental_pin', 'tmdb_api_key')


def _backup_folder():
    return os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'backups')


def _backup_sources(api):
    """Name -> file path of everything a backup keeps."""
    profile = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    files = {
        'mylist.json': getattr(api, 'mylist_file', None),
        'watchlater.json': getattr(api, 'watchlater_file', None),
        'myseries.json': getattr(api, 'myseries_file', None),
        'library.json': os.path.join(profile, 'library.json'),
        'search_history.json': os.path.join(profile, 'search_history.json'),
    }
    return {name: path for name, path in files.items() if path}


def _settings_snapshot():
    """Plain settings (not the password or PIN) from settings.xml."""
    values = {}
    path = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'settings.xml')
    try:
        import xml.etree.ElementTree as ET
        for node in ET.parse(path).getroot().iter('setting'):
            key = node.get('id')
            if key and not any(word in key for word in BACKUP_SETTINGS_SKIP):
                values[key] = node.text or ''
    except Exception:
        pass
    return values


def backup_lists():
    import zipfile
    api = _get_list_api()
    folder = _backup_folder()
    os.makedirs(folder, exist_ok=True)
    name = 'nlziet-backup-{}.zip'.format(time.strftime('%Y%m%d-%H%M'))
    path = os.path.join(folder, name)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for arcname, source in _backup_sources(api).items():
            if os.path.isfile(source):
                archive.write(source, arcname)
        archive.writestr('settings.json', json.dumps(_settings_snapshot(), indent=1, ensure_ascii=False))
        archive.writestr('backup.json', json.dumps({'addon': ADDON.getAddonInfo('id'),
                                                    'version': ADDON.getAddonInfo('version'),
                                                    'created': int(time.time())}))
    # Keep the 10 newest backups.
    old = sorted(f for f in os.listdir(folder) if f.startswith('nlziet-backup-') and f.endswith('.zip'))
    for stale in old[:-10]:
        try:
            os.remove(os.path.join(folder, stale))
        except OSError:
            pass
    xbmcgui.Dialog().ok('NLZiet', get_string('backup_saved', path))


def restore_lists():
    import zipfile
    folder = _backup_folder()
    try:
        names = sorted((f for f in os.listdir(folder) if f.endswith('.zip')), reverse=True)
    except OSError:
        names = []
    if not names:
        xbmcgui.Dialog().ok('NLZiet', get_string('restore_none'))
        return
    choice = xbmcgui.Dialog().select(get_string('restore_choose'), names)
    if choice < 0 or not xbmcgui.Dialog().yesno('NLZiet', get_string('restore_confirm')):
        return
    api = _get_list_api()
    targets = _backup_sources(api)
    restored = []
    with zipfile.ZipFile(os.path.join(folder, names[choice])) as archive:
        members = set(archive.namelist())
        for arcname, target in targets.items():
            if arcname not in members:
                continue
            data = archive.read(arcname)
            json.loads(data.decode('utf-8'))   # only restore valid JSON
            os.makedirs(os.path.dirname(target), exist_ok=True)
            tmp = target + '.tmp'
            with open(tmp, 'wb') as handle:
                handle.write(data)
            os.replace(tmp, target)
            restored.append(arcname.replace('.json', ''))
        if 'settings.json' in members:
            settings = json.loads(archive.read('settings.json').decode('utf-8'))
            for key, value in settings.items():
                try:
                    ADDON.setSetting(key, value)
                except Exception:
                    pass
            restored.append('settings')
    global _LIBRARY
    _LIBRARY = None
    xbmcgui.Dialog().ok('NLZiet', get_string('restore_done', ', '.join(restored)))
    if 'library' in restored:
        xbmc.executebuiltin('RunPlugin(plugin://plugin.video.nlziet/?mode=library_update&background=1)')


# ------------------------------------------------------- daily check ---

def daily_check():
    """Run the diagnostics quietly; one notification when something is wrong."""
    try:
        language = xbmc.getLanguage(xbmc.ISO_639_1) or 'nl'
    except Exception:
        language = 'nl'
    t = diagnostics_mod.texts(language)
    checks = _collect_diagnostics(t)
    problems = diagnostics_mod.problem_labels(checks)
    xbmc.log('NLZiet daily check: {}'.format(', '.join(problems) or 'all OK'), xbmc.LOGINFO)
    # Say it when something new goes wrong; repeat an unchanged problem weekly.
    state_path = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'daily_check.json')
    try:
        with open(state_path, 'r', encoding='utf-8') as handle:
            state = json.load(handle) or {}
    except (OSError, ValueError):
        state = {}
    now = time.time()
    changed = sorted(problems) != sorted(state.get('problems') or [])
    if problems and (changed or now - float(state.get('notified') or 0) >= 7 * 86400):
        xbmcgui.Dialog().notification('NLZiet', get_string('daily_check_problem', ', '.join(problems[:3])),
                                      xbmcgui.NOTIFICATION_WARNING, 10000)
        state['notified'] = now
    state['problems'] = problems
    try:
        with open(state_path, 'w', encoding='utf-8') as handle:
            json.dump(state, handle)
    except OSError:
        pass


def select_iptv_channels():
    from resources.lib.iptvmgr import read_enabled_channels, save_enabled_channels
    api = get_api_instance()
    # Read the list of currently available channels from NLZiet
    available_channels = api.get_channels()
    available_ids = [chan['id'] for chan in available_channels]

    # Since Kodi's multi-select dialog selects items by listing indexes to
    # the selected items in its list, calculate the indexes of the currently
    # enabled channels.
    enabled_channels = read_enabled_channels(api)
    if enabled_channels is None:
        # Not saved yet, enable all
        enabled_indices = list(range(len(available_ids)))
    else:
        enabled_indices = []
        for chan_id in enabled_channels:
            try:
                enabled_indices.append(available_ids.index(chan_id))
            except ValueError:
                pass
    # Open a multiselect dialog and allow the user to make a new selection.
    new_indices = xbmcgui.Dialog().multiselect(
        api.addon.getAddonInfo('name'),
        [chan['title'] for chan in available_channels],
        preselect=enabled_indices
    )
    # Store the new selection to file.
    enabled_channels = [available_channels[idx]['id'] for idx in new_indices]
    save_enabled_channels(api, enabled_channels)


def get_route_handlers():
    return {
        'main_menu': main_menu,
        'do_login': do_login,
        'do_search': do_search,
        'manage_profiles': manage_profiles,
        'browse_my_list': browse_my_list,
        'browse_my_list_group': browse_my_list_group,
        'browse_watch_later': browse_watch_later,
        'browse_my_series': browse_my_series,
        'toggle_mylist': toggle_mylist,
        'toggle_watch_later': toggle_watch_later,
        'add_series_watch_later': add_series_watch_later,
        'browse_watch_later_collection': browse_watch_later_collection,
        'toggle_my_series': toggle_my_series,
        'sync_watch_later': sync_watch_later,
        'sync_my_series': sync_my_series,
        'select_profile': select_profile,
        'apply_profile': apply_profile,
        'browse_series': browse_series,
        'do_logout': do_logout,
        'confirm_logout': confirm_logout,
        'refresh_account_info': refresh_account_info,
        'export_diagnostics': export_diagnostics,
        'clear_subtitle_cache': clear_subtitle_cache,
        'clear_all_cache': clear_all_cache,
        'search_group': search_group,
        'search_filter': search_filter,
        'show_series_detail': show_series_detail,
        'show_series_season': show_series_season,
        'export_series_library': export_series_library,
        'library_toggle': library_toggle,
        'library_remove': library_remove,
        'library_update': library_update,
        'browse_library': browse_library,
        'check_tmdb_key': check_tmdb_key,
        'repair_library_art': repair_library_art,
        'run_diagnostics': run_diagnostics,
        'widgets_menu': widgets_menu,
        'widget_list': widget_list,
        'backup_lists': backup_lists,
        'restore_lists': restore_lists,
        'daily_check': daily_check,
        'remote_watched': remote_watched,
        'play_next': play_next,
        'toggle_stop_after': toggle_stop_after,
        'shuffle_series': shuffle_series,
        'browse_history': browse_history,
        'clear_history': clear_history,
        'record_history': record_history,
        'library_from_lists': library_from_lists,
        'choose_tmdb': choose_tmdb,
        'parental_set_pin': parental_set_pin,
        'parental_clear_pin': parental_clear_pin,
        'toggle_profile_lock': toggle_profile_lock,
        'browse_placement_row': browse_placement_row,
        'browse_tv_shows': browse_tv_shows,
        'browse_tv_genre': browse_tv_genre,
        'browse_series_categories': browse_series_categories,
        'browse_series_genre': browse_series_genre,
        'browse_movie_categories': browse_movie_categories,
        'browse_movie_genre': browse_movie_genre,
        'browse_epg': browse_epg,
        'browse_category': browse_category,
        'play_item': play_item,
        'select_iptv_channels': select_iptv_channels,
    }


def router(paramstring):
    context = AddonContext(ADDON, HANDLE, BASE_URL, paramstring)
    Router(context, get_route_handlers()).dispatch(paramstring)


def _show_friendly_error(exc, paramstring=''):
    """Log the full error and show the user one clear sentence."""
    xbmc.log('NLZiet: unexpected error\n' + errors_mod.log_text(exc), xbmc.LOGERROR)
    params = dict(urllib.parse.parse_qsl((paramstring or '').lstrip('?')))
    if params.get('mode') == 'play':
        try:
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        except Exception:
            pass
    if params.get('background') == '1':
        return
    try:
        language = xbmc.getLanguage(xbmc.ISO_639_1) or 'nl'
    except Exception:
        language = 'nl'
    xbmcgui.Dialog().notification('NLZiet', errors_mod.user_message(exc, 'NLZiet', language),
                                  xbmcgui.NOTIFICATION_ERROR, 7000)


def run():
    context = AddonContext.from_kodi()
    try:
        Router(context, get_route_handlers()).dispatch()
    except Exception as exc:
        _show_friendly_error(exc, context.paramstring)


if __name__ == '__main__':
    run()
