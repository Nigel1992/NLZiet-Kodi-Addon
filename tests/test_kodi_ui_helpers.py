from resources.lib.kodi import ui


class FakeListItem:
    def __init__(self, label, offscreen):
        self.label = label
        self.offscreen = offscreen
        self.art = []
        self.properties = {}
        self.info = []
        self.context_menu = []

    def setArt(self, art):
        self.art.append(art)

    def setProperty(self, key, value):
        self.properties[key] = value

    def setInfo(self, kind, info):
        self.info.append((kind, info))

    def setLabel2(self, value):
        self.label2 = value

    def addContextMenuItems(self, items):
        self.context_menu.extend(items)


class FakeAddon:
    def getAddonInfo(self, key):
        return 'C:/addon' if key == 'path' else ''


def test_build_url_preserves_plugin_base_and_query_encoding():
    assert ui.build_url('plugin://plugin.video.nlziet', {'q': 'space query'}) == (
        'plugin://plugin.video.nlziet?q=space+query'
    )


def test_make_color_tag_uses_raw_value_or_default():
    assert ui.make_color_tag('', 'x') == '[COLOR FFA500]x[/COLOR]'
    assert ui.make_color_tag('FF0000', 'x') == '[COLOR FF0000]x[/COLOR]'


def test_pick_menu_icon_prefers_png_then_svg(monkeypatch):
    monkeypatch.setattr(ui.os.path, 'exists', lambda path: path.endswith('.svg'))

    assert ui.pick_menu_icon('C:/addon', 'series').endswith('menu_series.svg')
    assert ui.pick_menu_png('C:/addon', 'series').endswith('menu_series.svg')


def test_add_directory_item_marks_playable_items_and_preserves_url(monkeypatch):
    items = []
    added = []
    monkeypatch.setattr(
        ui.xbmcgui,
        'ListItem',
        lambda **kwargs: items.append(FakeListItem(**kwargs)) or items[-1],
    )
    monkeypatch.setattr(ui.os.path, 'exists', lambda path: False)
    monkeypatch.setattr(
        ui.xbmcplugin,
        'addDirectoryItem',
        lambda handle, url, item, isFolder: added.append((handle, url, item, isFolder)),
    )

    ui.add_directory_item(
        FakeAddon(),
        42,
        lambda query: ui.build_url('plugin://plugin.video.nlziet', query),
        lambda: None,
        'Episode',
        {'mode': 'play', 'id': 'e1'},
        is_folder=False,
        thumb='https://image.test/poster.jpg',
    )

    assert added[0][0] == 42
    assert added[0][1] == 'plugin://plugin.video.nlziet?mode=play&id=e1'
    assert added[0][3] is False
    assert items[0].properties['IsPlayable'] == 'true'
    assert items[0].art[-1]['thumb'] == 'https://image.test/poster.jpg'


def test_artwork_helpers_prefer_landscape_for_fanart_and_portrait_for_poster():
    item = FakeListItem('Title', True)

    ui.set_smart_artwork(item, {
        'landscapeUrl': 'https://image.test/landscape.jpg',
        'portraitUrl': 'https://image.test/portrait.jpg',
    })

    assert item.art == [{
        'fanart': 'https://image.test/landscape.jpg?width=3840',
        'landscape': 'https://image.test/landscape.jpg?width=3840',
        'poster': 'https://image.test/portrait.jpg?width=3840',
        'thumb': 'https://image.test/landscape.jpg?width=3840',
        'icon': 'https://image.test/landscape.jpg?width=3840',
    }]


class FakeListAPI:
    def __init__(self, in_mylist=False, in_watchlater=False):
        self._in_mylist = in_mylist
        self._in_watchlater = in_watchlater

    def is_in_my_list(self, content_id):
        return self._in_mylist

    def is_in_watch_later(self, content_id):
        return self._in_watchlater


def test_context_menu_combines_mylist_watch_later_and_library(monkeypatch):
    items = []
    monkeypatch.setattr(
        ui.xbmcgui,
        'ListItem',
        lambda **kwargs: items.append(FakeListItem(**kwargs)) or items[-1],
    )
    monkeypatch.setattr(ui.os.path, 'exists', lambda path: False)
    monkeypatch.setattr(ui.xbmcplugin, 'addDirectoryItem', lambda *a, **k: None)

    ui.add_directory_item(
        FakeAddon(),
        42,
        lambda query: ui.build_url('plugin://plugin.video.nlziet', query),
        lambda: FakeListAPI(in_mylist=True, in_watchlater=False),
        'Show',
        {'mode': 'series_detail', 'series_id': 's1'},
        thumb='https://image.test/poster.jpg',
        content={'id': 's1', 'type': 'series'},
    )

    labels = [label for label, _ in items[0].context_menu]
    assert labels == ['Remove from My List', 'Add to Watch Later', 'Add to library']


def test_context_menu_reflects_watch_later_membership(monkeypatch):
    items = []
    monkeypatch.setattr(
        ui.xbmcgui,
        'ListItem',
        lambda **kwargs: items.append(FakeListItem(**kwargs)) or items[-1],
    )
    monkeypatch.setattr(ui.os.path, 'exists', lambda path: False)
    monkeypatch.setattr(ui.xbmcplugin, 'addDirectoryItem', lambda *a, **k: None)

    ui.add_directory_item(
        FakeAddon(),
        42,
        lambda query: ui.build_url('plugin://plugin.video.nlziet', query),
        lambda: FakeListAPI(in_mylist=False, in_watchlater=True),
        'Film',
        {'mode': 'play', 'id': 'm1'},
        is_folder=False,
        thumb='https://image.test/poster.jpg',
        content={'id': 'm1', 'type': 'movie'},
    )

    labels = [label for label, _ in items[0].context_menu]
    assert labels == ['Add to My List', 'Remove from Watch Later']


def test_context_menu_allows_my_list_and_watch_later_for_any_content(monkeypatch):
    items = []
    monkeypatch.setattr(
        ui.xbmcgui,
        'ListItem',
        lambda **kwargs: items.append(FakeListItem(**kwargs)) or items[-1],
    )
    monkeypatch.setattr(ui.os.path, 'exists', lambda path: False)
    monkeypatch.setattr(ui.xbmcplugin, 'addDirectoryItem', lambda *a, **k: None)

    ui.add_directory_item(
        FakeAddon(),
        42,
        lambda query: ui.build_url('plugin://plugin.video.nlziet', query),
        lambda: FakeListAPI(in_mylist=False, in_watchlater=False),
        'Kanaal 1',
        {'mode': 'play', 'id': 'c1', 'fmt': 'live'},
        is_folder=False,
        content={'id': 'c1', 'type': 'channel'},
    )

    labels = [label for label, _ in items[0].context_menu]
    assert labels == ['Add to My List', 'Add to Watch Later']


def test_context_menu_includes_group_in_toggle_queries(monkeypatch):
    items = []
    monkeypatch.setattr(
        ui.xbmcgui,
        'ListItem',
        lambda **kwargs: items.append(FakeListItem(**kwargs)) or items[-1],
    )
    monkeypatch.setattr(ui.os.path, 'exists', lambda path: False)
    monkeypatch.setattr(ui.xbmcplugin, 'addDirectoryItem', lambda *a, **k: None)

    ui.add_directory_item(
        FakeAddon(),
        42,
        lambda query: ui.build_url('plugin://plugin.video.nlziet', query),
        lambda: FakeListAPI(in_mylist=False, in_watchlater=False),
        'Show',
        {'mode': 'series_detail', 'series_id': 's1'},
        thumb='https://image.test/poster.jpg',
        content={'id': 's1', 'type': 'Series'},
        group='tvshows',
    )

    actions = [action for _, action in items[0].context_menu]
    assert any('mode=toggle_mylist' in a and 'group=tvshows' in a for a in actions)
    assert any('mode=toggle_watch_later' in a and 'group=tvshows' in a for a in actions)
