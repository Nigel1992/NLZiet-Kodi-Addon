import importlib
import sys
from types import SimpleNamespace

from resources.lib.router import Router


EXPECTED_HANDLER_NAMES = {
    'main_menu', 'do_login', 'do_search', 'manage_profiles',
    'browse_my_list', 'browse_my_list_group',
    'browse_watch_later', 'toggle_mylist',
    'toggle_watch_later',
    'select_profile', 'apply_profile', 'browse_series', 'do_logout',
    'confirm_logout', 'refresh_account_info', 'export_diagnostics',
    'search_group', 'show_series_detail', 'show_series_season',
    'export_series_library', 'browse_placement_row', 'browse_tv_shows',
    'browse_tv_genre', 'browse_series_categories', 'browse_series_genre',
    'browse_movie_categories', 'browse_movie_genre', 'browse_category',
    'play_item', 'select_iptv_channels',
}


def _handlers(calls):
    def make(name):
        def handler(*args, **kwargs):
            calls.append((name, args, kwargs))
        return handler

    return {name: make(name) for name in EXPECTED_HANDLER_NAMES}


def test_default_route_handler_mapping_covers_current_route_contract(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.nlziet', '42', ''])
    sys.modules.pop('default', None)
    default = importlib.import_module('default')

    assert set(default.get_route_handlers()) == EXPECTED_HANDLER_NAMES


def test_missing_mode_dispatches_main_menu():
    calls = []
    context = SimpleNamespace(handle=5, paramstring='')

    Router(context, _handlers(calls)).dispatch()

    assert calls == [('main_menu', (), {})]


def test_known_mode_dispatches_with_parsed_parameters(kodi_recorder):
    calls = []
    context = SimpleNamespace(
        handle=5,
        paramstring=(
            'mode=series_season&series_id=s1&season_id=2'
            '&episodes_url=https%3A%2F%2Fexample.test'
            '&series_title=Show&season_number=3'
        ),
    )

    Router(context, _handlers(calls)).dispatch()

    assert calls == [
        ('show_series_season', ('s1', '2', 'https://example.test', 'Show', '3'), {})
    ]
    assert kodi_recorder.set_content == [(5, 'videos')]


def test_profiles_mode_does_not_set_video_content(kodi_recorder):
    calls = []
    context = SimpleNamespace(handle=5, paramstring='mode=profiles')

    Router(context, _handlers(calls)).dispatch()

    assert calls == [('manage_profiles', (), {})]
    assert kodi_recorder.set_content == []


def test_my_list_routes_preserve_parameters():
    calls = []
    router = Router(SimpleNamespace(handle=5, paramstring=''), _handlers(calls))

    router.dispatch('mode=my_list_group&group=Movies')
    router.dispatch('mode=toggle_mylist&id=1&type=movie&title=T&thumb=img')

    assert calls == [
        ('browse_my_list_group', ('Movies',), {}),
        ('toggle_mylist', ('1', 'T', 'movie', 'img', None), {}),
    ]


def test_watch_later_route_dispatches():
    calls = []
    router = Router(SimpleNamespace(handle=5, paramstring=''), _handlers(calls))

    router.dispatch('mode=watch_later')
    router.dispatch('mode=toggle_watch_later&id=s1&type=series&title=Show&thumb=img')

    assert calls == [
        ('browse_watch_later', (), {}),
        ('toggle_watch_later', ('s1', 'Show', 'series', 'img', None), {}),
    ]


def test_unknown_mode_matches_existing_noop_except_content(kodi_recorder):
    calls = []
    context = SimpleNamespace(handle=5, paramstring='mode=unknown')

    Router(context, _handlers(calls)).dispatch()

    assert calls == []
    assert kodi_recorder.set_content == [(5, 'videos')]


def test_library_export_and_diagnostics_routes_dispatch():
    calls = []
    router = Router(SimpleNamespace(handle=5, paramstring=''), _handlers(calls))

    router.dispatch('mode=export_series_library&series_id=s1')
    router.dispatch('mode=export_diagnostics')

    assert calls == [
        ('export_series_library', ('s1',), {}),
        ('export_diagnostics', (), {}),
    ]
