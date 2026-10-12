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
        ('mode=series_season&series_id=s1&season_id=2', 'show_series_season', ('s1', '2', None, None, None), True),
        ('mode=placement_row&items_url=https%3A%2F%2Fexample.test%2Fitems&placement_id=pl&comp_index=3', 'browse_placement_row', ('https://example.test/items', 'pl', '3'), True),
        ('mode=browse&type=documentary', 'browse_category', ('documentary',), True),
        ('mode=search_group&q=space+query&group=Movies', 'search_group', ('space query', 'Movies'), True),
        ('mode=export_diagnostics', 'export_diagnostics', (), True),
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


def test_get_string_uses_kodi_language(monkeypatch):
    default = _import_default(monkeypatch)

    monkeypatch.setattr(default.xbmc, 'getLanguage', lambda *args: 'en')
    assert default.get_string('login') == 'Login'

    monkeypatch.setattr(default.xbmc, 'getLanguage', lambda *args: 'nl')
    assert default.get_string('login') == 'Inloggen'


def test_login_dialog_masks_password(monkeypatch):
    default = _import_default(monkeypatch)
    calls = []

    class Dialog:
        def input(self, heading, default='', type=0, option=0):
            calls.append((heading, type, option))
            return 'user@example.test' if len(calls) == 1 else 'secret'

    monkeypatch.setattr(default.xbmcgui, 'Dialog', Dialog)

    assert default.show_login_dialog() == ('user@example.test', 'secret')
    assert calls[1][1:] == (
        default.xbmcgui.INPUT_ALPHANUM,
        default.xbmcgui.ALPHANUM_HIDE_INPUT,
    )


def test_resume_state_is_published_to_kodi(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default.os.path, 'exists', lambda path: False)

    default.add_directory_item(
        'Episode',
        {'mode': 'play', 'id': 'episode-1'},
        is_folder=False,
        content={
            'type': 'Episode',
            'durationInSeconds': 1800,
            'resumePosition': 600,
        },
    )

    item = kodi_recorder.directory_items[-1][2]
    assert item.info['video']['resume'] == {'position': 600.0, 'total': 1800.0}
    assert item.properties['ResumeTime'] == '600.0'
    assert item.properties['TotalTime'] == '1800.0'


def test_watched_state_sets_playcount(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default.os.path, 'exists', lambda path: False)

    default.add_directory_item(
        'Movie',
        {'mode': 'play', 'id': 'movie-1'},
        is_folder=False,
        content={'type': 'Movie', 'isWatched': True},
    )

    assert kodi_recorder.directory_items[-1][2].info['video']['playcount'] == 1


def test_diagnostic_redaction_removes_private_values(monkeypatch):
    default = _import_default(monkeypatch)
    source = (
        'Authorization: Bearer secret-token\n'
        'password=secret-password\n'
        'email=user@example.test\n'
        'https://example.test/video?signature=signed-value&quality=high'
    )

    redacted = default._redact_diagnostic_text(source)

    assert 'secret-token' not in redacted
    assert 'secret-password' not in redacted
    assert 'user@example.test' not in redacted
    assert 'signed-value' not in redacted


def test_main_menu_logged_out_adds_login_entry_and_ends_directory(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)
    entries = []

    monkeypatch.setattr(default, '_check_and_handle_token_expiry', lambda: True)
    monkeypatch.setattr(default, '_is_logged_in', lambda: False)
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
