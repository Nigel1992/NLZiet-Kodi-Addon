import importlib
import sys

import pytest


def _import_default(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.nlziet', '42', ''])
    sys.modules.pop('default', None)
    return importlib.import_module('default')


@pytest.mark.parametrize(
    ('paramstring', 'handler_name', 'expected_args', 'sets_video_content'),
    [
        ('', 'main_menu', (), False),
        ('mode=search', 'do_search', (), True),
        ('mode=profiles', 'manage_profiles', (), False),
        ('mode=my_list', 'browse_my_list', (), True),
        ('mode=my_list_group&group=Movies', 'browse_my_list_group', ('Movies',), True),
        ('mode=toggle_mylist&id=m1&title=Movie&type=movie&thumb=poster', 'toggle_mylist', ('m1', 'Movie', 'movie', 'poster'), True),
        ('mode=select_profile&profile_id=p1', 'select_profile', ('p1',), True),
        # Current route dispatch forwards the optional episodes_url as None when absent.
        ('mode=series_season&series_id=s1&season_id=2', 'show_series_season', ('s1', '2', None), True),
        ('mode=placement_row&items_url=https%3A%2F%2Fexample.test%2Fitems&placement_id=pl&comp_index=3', 'browse_placement_row', ('https://example.test/items', 'pl', '3'), True),
        ('mode=browse&type=documentary', 'browse_category', ('documentary',), True),
        ('mode=search_group&q=space+query&group=Movies', 'search_group', ('space query', 'Movies'), True),
    ],
)
def test_router_dispatches_existing_handlers_with_parsed_arguments(
    monkeypatch, kodi_recorder, paramstring, handler_name, expected_args, sets_video_content
):
    default = _import_default(monkeypatch)
    calls = []

    monkeypatch.setattr(default, handler_name, lambda *args: calls.append(args))

    default.router(paramstring)

    assert calls == [expected_args]
    assert kodi_recorder.set_content == ([(42, 'videos')] if sets_video_content else [])


def test_router_ignores_unknown_mode_after_setting_video_content(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)

    default.router('mode=unknown')

    assert kodi_recorder.set_content == [(42, 'videos')]


def test_build_url_uses_plugin_base_and_standard_query_encoding(monkeypatch):
    default = _import_default(monkeypatch)

    assert default.build_url({'mode': 'search_group', 'q': 'space query'}) == (
        'plugin://plugin.video.nlziet?mode=search_group&q=space+query'
    )


def test_main_menu_logged_out_adds_login_entry_and_ends_directory(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)
    entries = []

    class FakeThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(default, '_check_and_handle_token_expiry', lambda: True)
    monkeypatch.setattr(default, '_is_logged_in', lambda: False)
    monkeypatch.setattr(default.threading, 'Thread', FakeThread)
    monkeypatch.setattr(default.os.path, 'exists', lambda path: False)
    monkeypatch.setattr(
        default,
        'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, query, kwargs)),
    )

    default.main_menu()

    assert [entry[1] for entry in entries] == [{'mode': 'login'}]
    assert kodi_recorder.ended == [42]


def test_browse_my_list_groups_existing_items_by_content_type(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)
    entries = []

    class FakeApi:
        def get_my_list(self):
            return [
                {'id': 'series-1', 'type': 'series'},
                {'id': 'movie-1', 'type': 'movie'},
                {'id': 'clip-1', 'type': 'clip'},
            ]

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())
    monkeypatch.setattr(default, '_pick_landscape_thumb', lambda item: 'thumb:' + item['id'])
    monkeypatch.setattr(
        default,
        'add_directory_item',
        lambda title, query, **kwargs: entries.append((title, query, kwargs)),
    )

    default.browse_my_list()

    assert [(title, query) for title, query, _ in entries] == [
        ('Series: 1 found', {'mode': 'my_list_group', 'group': 'Series'}),
        ('Movies: 1 found', {'mode': 'my_list_group', 'group': 'Movies'}),
        ('Other: 1 found', {'mode': 'my_list_group', 'group': 'Other'}),
    ]
    assert kodi_recorder.ended == [42]


def test_browse_my_list_empty_result_notifies_and_ends_directory(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)

    class FakeApi:
        def get_my_list(self):
            return []

    monkeypatch.setattr(default, 'get_api_instance', lambda: FakeApi())

    default.browse_my_list()

    assert kodi_recorder.notifications == [('NLZiet', 'Mijn lijst is leeg', 'info')]
    assert kodi_recorder.ended == [42]
