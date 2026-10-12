import sys

from resources.lib.app_context import AddonContext


def test_context_from_kodi_parses_argv(monkeypatch):
    monkeypatch.setattr(
        sys,
        'argv',
        ['plugin://plugin.video.nlziet', '42', '?mode=my_list&group=Movies']
    )

    context = AddonContext.from_kodi()

    assert context.handle == 42
    assert context.base_url == 'plugin://plugin.video.nlziet'
    assert context.paramstring == 'mode=my_list&group=Movies'
    assert context.addon_id == 'plugin.video.nlziet'
    assert context.plugin_path == 'C:/addon'


def test_context_preserves_addon_settings_access(fake_addon):
    fake_addon.setSetting('profile_id', 'abc')

    context = AddonContext(fake_addon, 7, 'plugin://base')

    assert context.addon.getSetting('profile_id') == 'abc'
    assert context.addon_id == 'plugin.video.nlziet'
