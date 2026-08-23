import urllib.parse

import xbmcplugin


class Router:
    """Explicit route dispatcher for Kodi plugin modes."""

    def __init__(self, context, handlers):
        self.context = context
        self.handlers = handlers

    def dispatch(self, paramstring=None):
        params = dict(urllib.parse.parse_qsl(
            self.context.paramstring if paramstring is None else paramstring
        ))
        mode = params.get('mode')
        if mode and mode not in ('profiles'):
            xbmcplugin.setContent(self.context.handle, 'videos')
        if not mode:
            self.handlers['main_menu']()
        elif mode == 'login':
            self.handlers['do_login']()
        elif mode == 'search':
            self.handlers['do_search']()
        elif mode == 'profiles':
            self.handlers['manage_profiles']()
        elif mode == 'my_list':
            self.handlers['browse_my_list']()
        elif mode == 'my_list_group':
            self.handlers['browse_my_list_group'](params.get('group'))
        elif mode == 'toggle_mylist':
            self.handlers['toggle_mylist'](
                params.get('id'),
                params.get('title'),
                params.get('type'),
                params.get('thumb')
            )
        elif mode == 'select_profile':
            self.handlers['select_profile'](params.get('profile_id'))
        elif mode == 'apply_profile':
            self.handlers['apply_profile']()
        elif mode == 'series':
            self.handlers['browse_series']()
        elif mode == 'logout':
            self.handlers['do_logout']()
        elif mode == 'logout_keep_mylist':
            self.handlers['do_logout'](keep_mylist=True)
        elif mode == 'logout_confirm':
            self.handlers['confirm_logout']()
        elif mode == 'account_summary':
            self.handlers['refresh_account_info']()
        elif mode == 'search_group':
            self.handlers['search_group'](params.get('q'), params.get('group'))
        elif mode == 'series_detail':
            self.handlers['show_series_detail'](params.get('series_id'))
        elif mode == 'series_season':
            self.handlers['show_series_season'](
                params.get('series_id'),
                params.get('season_id'),
                params.get('episodes_url')
            )
        elif mode == 'export_series_library':
            self.handlers['export_series_library'](params.get('series_id'))
        elif mode == 'placement_row':
            self.handlers['browse_placement_row'](
                params.get('items_url'),
                params.get('placement_id'),
                params.get('comp_index')
            )
        elif mode == 'browse_tv_shows':
            self.handlers['browse_tv_shows']()
        elif mode == 'browse_tv_genre':
            self.handlers['browse_tv_genre'](params.get('genre'))
        elif mode == 'browse_series_categories':
            self.handlers['browse_series_categories']()
        elif mode == 'browse_series_genre':
            self.handlers['browse_series_genre'](params.get('genre'))
        elif mode == 'browse_movie_categories':
            self.handlers['browse_movie_categories']()
        elif mode == 'browse_movie_genre':
            self.handlers['browse_movie_genre'](params.get('genre'))
        elif mode == 'browse':
            self.handlers['browse_category'](params.get('type', 'all'))
        elif mode == 'play':
            content_id = params.pop('id')
            self.handlers['play_item'](content_id, **params)
        elif mode == 'iptv-select-channels':
            self.handlers['select_iptv_channels']()
        elif mode == 'iptv-channels':
            from resources.lib import iptvmgr
            iptvmgr.IPTVManager(int(params['port'])).send_channels()
        elif mode == 'iptv.epg':
            from resources.lib import iptvmgr
            iptvmgr.IPTVManager(int(params['port'])).send_epg()
